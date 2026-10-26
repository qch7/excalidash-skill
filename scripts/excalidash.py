#!/usr/bin/env python3
"""ExcaliDash HTTP client; credentials are read from a user-owned config file."""
import argparse
import getpass
import http.cookiejar
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_CONFIG = Path.home() / '.config' / 'ExcaliDashSkill' / 'config.json'
WRITABLE = {'name', 'elements', 'appState', 'files', 'preview', 'collectionId'}
READ_ONLY = {'id', 'userId', 'creatorName', 'accessLevel', 'createdAt', 'updatedAt'}

class SkillError(Exception):
    def __init__(self, code, message, **details):
        self.result = {'ok': False, 'code': code, 'message': message, **details}
        super().__init__(message)

def emit(value, stream=None):
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream or sys.stdout)

def read_json(path):
    try:
        with Path(path).open('r', encoding='utf-8-sig') as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise SkillError('INPUT_INVALID', 'Cannot read valid UTF-8 JSON.', path=str(Path(path).absolute())) from exc
    if not isinstance(data, dict):
        raise SkillError('INPUT_INVALID', 'JSON root must be an object.')
    return data

def validate_config(data):
    if not isinstance(data, dict):
        raise SkillError('CONFIG_INVALID', 'Config must be a JSON object.')
    missing = [k for k in ('base_url', 'email', 'password') if not isinstance(data.get(k), str) or not data[k].strip()]
    if missing:
        raise SkillError('CONFIG_INVALID', 'Configure missing connection fields.', configured=False, missing=missing)
    try:
        p = urllib.parse.urlsplit(data['base_url'].strip())
        valid = p.scheme in ('http', 'https') and p.hostname and not (p.username or p.password or p.query or p.fragment)
        p.port
    except ValueError:
        valid = False
    if not valid:
        raise SkillError('CONFIG_INVALID', 'base_url must be an HTTP(S) site URL without credentials, query, or fragment.')
    return {'base_url': data['base_url'].strip().rstrip('/'), 'email': data['email'].strip(), 'password': data['password']}

def load_config(path):
    if not path.is_file():
        raise SkillError('CONFIG_MISSING', 'Ask for the site URL, email, and password, then run configure.', configured=False, config_path=str(path))
    try:
        data = read_json(path)
    except SkillError as exc:
        raise SkillError('CONFIG_INVALID', 'Config is unreadable or invalid JSON; guide the user to repair it.', configured=False, config_path=str(path)) from exc
    return validate_config(data)

def write_json(path, data, private=False):
    path = Path(path).expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        if private:
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def configure(args):
    if args.stdin_json:
        try:
            data = json.load(sys.stdin)
        except ValueError as exc:
            raise SkillError('CONFIG_INVALID', 'stdin must contain one config JSON object.') from exc
    else:
        if not sys.stdin.isatty():
            raise SkillError('INPUT_REQUIRED', 'Run configure interactively, or pass config JSON to stdin with --stdin-json.')
        old = {}
        if args.config.exists():
            try:
                old = load_config(args.config)
            except SkillError:
                print('Existing config is invalid. Enter all connection fields.', file=sys.stderr)
        data = {}
        for key, label in (('base_url', 'ExcaliDash URL'), ('email', 'Login email')):
            default = old.get(key, '')
            data[key] = input(label + (f' [{default}]' if default else '') + ': ').strip() or default
        data['password'] = getpass.getpass('Password' + (' [Enter keeps existing]' if old.get('password') else '') + ': ') or old.get('password', '')
    config = validate_config(data)
    write_json(args.config, config, private=True)
    emit({'ok': True, 'configured': True, 'config_path': str(args.config), 'base_url': config['base_url'], 'email': config['email']})

def origin(url):
    p = urllib.parse.urlsplit(url)
    return p.scheme.lower(), p.hostname, p.port or (443 if p.scheme == 'https' else 80)

class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if origin(req.full_url) != origin(newurl):
            raise SkillError('REDIRECT_BLOCKED', 'API redirected to another origin; verify the configured URL.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Client:
    def __init__(self, config, timeout=20):
        self.base = config['base_url']
        self.email = config['email']
        self.password = config['password']
        self.timeout = timeout
        self.csrf_header = 'x-csrf-token'
        self.csrf_token = None
        self.opener = urllib.request.build_opener(SameOriginRedirect(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def redact(self, value):
        result = str(value)
        for secret in (self.password, self.csrf_token):
            if secret:
                result = result.replace(secret, '[REDACTED]')
        return result

    def request(self, method, path, data=None):
        headers = {'Accept': 'application/json'}
        body = None
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if method not in ('GET', 'HEAD'):
            p = urllib.parse.urlsplit(self.base)
            headers.update({'Origin': f'{p.scheme}://{p.netloc}', 'Referer': self.base + '/login'})
            if self.csrf_token:
                headers[self.csrf_header] = self.csrf_token
        req = urllib.request.Request(self.base + '/api' + path, data=body, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                raw = response.read()
                if 'json' not in response.headers.get('Content-Type', ''):
                    raise SkillError('API_INVALID', 'Expected JSON; check the configured URL and server version.', endpoint=path)
                try:
                    return json.loads(raw.decode('utf-8-sig'))
                except (ValueError, UnicodeError) as exc:
                    raise SkillError('API_INVALID', 'API returned invalid JSON.', endpoint=path) from exc
        except urllib.error.HTTPError as exc:
            try:
                error = json.loads(exc.read(8192).decode('utf-8'))
                message = error.get('message') or error.get('error') or 'API request failed.'
            except (ValueError, UnicodeError, AttributeError):
                message = 'API request failed.'
            code = {401: 'AUTH_FAILED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 409: 'VERSION_CONFLICT'}.get(exc.code, 'HTTP_ERROR')
            raise SkillError(code, self.redact(message), status=exc.code, endpoint=path, write_may_have_succeeded=method not in ('GET', 'HEAD') and exc.code >= 500) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SkillError('NETWORK_ERROR', self.redact(exc), endpoint=path, write_may_have_succeeded=method not in ('GET', 'HEAD')) from exc

    def csrf(self):
        response = self.request('GET', '/csrf-token')
        if not isinstance(response, dict) or not isinstance(response.get('token'), str) or not response['token']:
            raise SkillError('API_INVALID', 'CSRF endpoint did not return a token.')
        self.csrf_token = response['token']
        self.csrf_header = response.get('header') or 'x-csrf-token'

    def login(self):
        self.csrf()
        self.request('POST', '/auth/login', {'email': self.email, 'password': self.password})
        self.csrf()

    def get(self, drawing_id):
        result = self.request('GET', '/drawings/' + urllib.parse.quote(drawing_id, safe=''))
        board = result.get('drawing', result) if isinstance(result, dict) else None
        if not isinstance(board, dict) or not isinstance(board.get('elements'), list):
            raise SkillError('API_INVALID', 'Expected a complete drawing with an elements array.')
        return board

    def list(self, shared=False, limit=50, offset=0, all_pages=False):
        path = '/drawings/shared' if shared else '/drawings'
        collected = []
        while True:
            page = self.request('GET', path + '?' + urllib.parse.urlencode({'limit': limit, 'offset': offset}))
            if not isinstance(page, dict) or not isinstance(page.get('drawings'), list):
                raise SkillError('API_INVALID', 'Expected a paginated drawings list.')
            if not all_pages:
                return page
            items = page['drawings']
            collected.extend(items)
            offset += len(items)
            if not items or offset >= page.get('totalCount', offset):
                return {**page, 'drawings': collected, 'returnedCount': len(collected)}

    def save(self, payload, drawing_id=None):
        if drawing_id:
            current = self.get(drawing_id)
            if current.get('accessLevel') not in ('edit', 'owner'):
                raise SkillError('FORBIDDEN', 'Configured account has no confirmed edit permission.', accessLevel=current.get('accessLevel'))
            if current.get('version') != payload['version']:
                raise SkillError('VERSION_CONFLICT', 'Board changed after the snapshot; read it again and merge before saving.', expected_version=payload['version'], current_version=current.get('version'))
            self.request('PUT', '/drawings/' + urllib.parse.quote(drawing_id, safe=''), payload)
        else:
            result = self.request('POST', '/drawings', payload)
            created = result.get('drawing', result) if isinstance(result, dict) else {}
            drawing_id = created.get('id')
            if not isinstance(drawing_id, str) or not drawing_id:
                raise SkillError('CREATE_UNCONFIRMED', 'Creation returned no ID; inspect the list before retrying.', write_may_have_succeeded=True)
        url = self.base + '/editor/' + urllib.parse.quote(drawing_id, safe='')
        try:
            saved = self.get(drawing_id)
        except SkillError as exc:
            raise SkillError('VERIFICATION_FAILED', 'Write returned successfully but read-back failed; inspect this board before retrying.', id=drawing_id, url=url, write_succeeded=True, cause=exc.result['code']) from exc
        mismatches = [key for key, value in payload.items() if key != 'version' and saved.get(key) != value]
        if mismatches:
            raise SkillError('VERIFICATION_FAILED', 'Saved board differs from submitted fields; inspect before retrying.', id=drawing_id, url=url, fields=mismatches, write_succeeded=True)
        return {'ok': True, 'verified': True, 'id': drawing_id, 'name': saved.get('name'), 'url': url, 'version': saved.get('version'), 'element_count': len(saved['elements']), 'accessLevel': saved.get('accessLevel')}

def prepare_payload(data, updating=False, name=None):
    unknown = set(data) - WRITABLE - READ_ONLY - {'type', 'source', 'version'}
    if unknown:
        raise SkillError('INPUT_INVALID', 'Unsupported drawing fields.', fields=sorted(unknown))
    payload = {k: v for k, v in data.items() if k in WRITABLE}
    if name is not None:
        payload['name'] = name
    if updating:
        version = data.get('version')
        if data.get('type') == 'excalidraw' or isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise SkillError('INPUT_INVALID', 'Updates require the board version from get, not an .excalidraw format version.')
        if not payload:
            raise SkillError('INPUT_INVALID', 'No writable fields provided.')
        payload['version'] = version
    else:
        payload.setdefault('elements', [])
        payload.setdefault('appState', {})
        payload.setdefault('files', {})
        if not isinstance(payload.get('name'), str) or not payload['name'].strip():
            raise SkillError('INPUT_INVALID', 'Provide a board name using --name or the input name field.')
    if 'name' in payload and (not isinstance(payload['name'], str) or not payload['name'].strip()):
        raise SkillError('INPUT_INVALID', 'Board name must be non-empty text.')
    for key, expected in (('elements', list), ('appState', dict), ('files', dict)):
        if key in payload and not isinstance(payload[key], expected):
            raise SkillError('INPUT_INVALID', f'{key} must be a JSON {expected.__name__}.')
    if 'elements' in payload:
        ids = [e.get('id') if isinstance(e, dict) else None for e in payload['elements']]
        if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
            raise SkillError('INPUT_INVALID', 'Every element needs a unique, non-empty string ID.')
    if 'preview' in payload and payload['preview'] is not None and not isinstance(payload['preview'], str):
        raise SkillError('INPUT_INVALID', 'preview must be an SVG string or null.')
    return payload

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=lambda p: Path(p).expanduser().absolute(), default=DEFAULT_CONFIG)
    parser.add_argument('--timeout', type=float, default=20)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('config-status', help='Check config locally without printing the password or contacting the server')
    p = sub.add_parser('configure', help='Guide initial setup or edit existing config')
    p.add_argument('--stdin-json', action='store_true', help='Read the config object from stdin')
    sub.add_parser('whoami')
    p = sub.add_parser('list')
    p.add_argument('--shared', action='store_true')
    p.add_argument('--all', dest='all_pages', action='store_true')
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--offset', type=int, default=0)
    p = sub.add_parser('get')
    p.add_argument('id')
    p.add_argument('--out', type=Path)
    p = sub.add_parser('create')
    p.add_argument('--input', type=Path)
    p.add_argument('--name')
    p = sub.add_parser('update')
    p.add_argument('id')
    p.add_argument('--input', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.timeout <= 0:
            raise SkillError('INPUT_INVALID', 'timeout must be positive.')
        if args.command == 'configure':
            configure(args)
            return 0
        config = load_config(args.config)
        if args.command == 'config-status':
            emit({'ok': True, 'configured': True, 'config_path': str(args.config), 'base_url': config['base_url'], 'email': config['email']})
            return 0
        payload = None
        if args.command in ('create', 'update'):
            payload = prepare_payload(read_json(args.input) if args.input else {}, args.command == 'update', getattr(args, 'name', None))
        if args.command == 'list' and (args.limit < 1 or args.offset < 0):
            raise SkillError('INPUT_INVALID', 'limit must be positive and offset non-negative.')
        client = Client(config, args.timeout)
        client.login()
        if args.command == 'whoami':
            emit(client.request('GET', '/auth/me'))
        elif args.command == 'list':
            emit(client.list(args.shared, args.limit, args.offset, args.all_pages))
        elif args.command == 'get':
            board = client.get(args.id)
            if args.out:
                write_json(args.out, board)
                emit({'ok': True, 'path': str(args.out.expanduser().absolute()), 'id': board.get('id'), 'version': board.get('version'), 'accessLevel': board.get('accessLevel'), 'element_count': len(board['elements'])})
            else:
                emit(board)
        else:
            emit(client.save(payload, args.id if args.command == 'update' else None))
        return 0
    except SkillError as exc:
        emit(exc.result, sys.stderr)
        return 2
    except (OSError, EOFError) as exc:
        emit({'ok': False, 'code': 'LOCAL_IO_ERROR', 'message': 'A local file or interactive input could not be accessed.', 'error_type': type(exc).__name__}, sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
