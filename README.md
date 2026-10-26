# ExcaliDash Skill

通过 HTTP API 让 AI 读取、创建和修改 ExcaliDash 画板，生成可编辑的架构图与流程图。

## 项目来源

画板服务来自 [ZimengXiong/ExcaliDash](https://github.com/ZimengXiong/ExcaliDash)。请按源项目说明部署 ExcaliDash，并准备可登录的账号。本仓库提供配套的 Agent 技能和 HTTP 客户端。

## 功能

- 读取自己的画板和与我共享的画板。
- 创建画板，按最新版本修改内容，保存后回读验证。
- 使用原生 Excalidraw 元素保留可编辑性。
- 按视图、分组、网格和端口规划布局，减少连线交叉。
- 使用简短标签和直接陈述，让图形表达流程与关系。

脚本使用 Python 3.10+ 标准库，无第三方依赖。网站操作通过 HTTP 完成。

## 通过 Agent 安装

将以下指令发给支持本地技能、终端和网络访问的 Agent：

```text
请从 https://github.com/qch7/excalidash-skill 安装 excalidash 技能。
先阅读仓库的 README.md 和 SKILL.md，确认当前 Agent 的技能目录，再安装并检查 Python 3.10+。
已有同名安装时先检查，保留本地改动。
安装后运行 config-status。已有有效配置时直接使用；缺失时引导我填写 ExcaliDash 网址、邮箱和密码。
配置保存到 ~/.config/ExcaliDashSkill/config.json，密码通过本机终端隐藏输入填写。
最后检查技能是否可加载，并说明调用方法。
```

在 Codex 中，也可以调用内置安装技能：

```text
$skill-installer 请安装 https://github.com/qch7/excalidash-skill 仓库根目录中的 excalidash 技能。
```

安装后可在新会话中调用。技能未显示时重启 Codex。其他 Agent 按各自的技能加载方式使用本目录。

## 手动安装到 Codex

下面使用 [OpenAI 官方文档](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) 列出的用户级目录 `~/.agents/skills/excalidash`。已有安装时沿用当前环境识别的技能目录，避免同名重复安装。

Windows PowerShell：

```powershell
git clone https://github.com/qch7/excalidash-skill.git "$env:USERPROFILE/.agents/skills/excalidash"
Set-Location "$env:USERPROFILE/.agents/skills/excalidash"
```

Linux / macOS：

```sh
git clone https://github.com/qch7/excalidash-skill.git "$HOME/.agents/skills/excalidash"
cd "$HOME/.agents/skills/excalidash"
```

## 通过 Agent 使用

在 Codex 中用 `$excalidash` 指定技能，也可以直接描述 ExcaliDash 任务。首次连接网站时，Agent 先检查本地配置，缺失时引导填写。

创建画板：

```text
$excalidash 创建一个测试画板，画出 Web → API 网关 → 应用服务 → 数据库的请求流程。
使用原生可编辑元素，对齐节点并标注连线动作。保存后给我画板链接。
```

读取共享画板：

```text
$excalidash 列出与我共享的画板，读取我选择的画板并概述内容。
```

修改已有画板，将占位符替换为实际链接：

```text
$excalidash 修改这个画板：<画板链接>。
将并列节点对齐，减少连线交叉，保留原有组件和调用关系。
查看修改后的预览，保存并验证结果。
```

## 首次配置

以下 CLI 示例均在本仓库根目录运行。

```sh
python scripts/excalidash.py config-status
python scripts/excalidash.py configure
python scripts/excalidash.py whoami
```

`configure` 询问网站完整网址、登录邮箱和密码。密码通过隐藏输入填写。配置保存到：

```text
~/.config/ExcaliDashSkill/config.json
```

Windows 中 `~` 为当前用户目录。后续调用直接读取已有配置。

配置字段为 `base_url`、`email` 和 `password`。配置文件包含明文密码，应保存在当前用户可访问的位置。Cookie 与 CSRF 令牌仅保留在单次进程内存中。Linux / macOS 上脚本以 `0600` 权限创建配置文件；Windows 上访问范围由目录和文件的 ACL 决定。

账号、密码、实例地址和画板导出文件保留在本机。提交前检查暂存区，日志与问题反馈中的凭据需先脱敏。

仅生成本地场景和预览时可跳过网站配置。

## 常用命令

```sh
# 查看帮助
python scripts/excalidash.py --help

# 自己的画板
python scripts/excalidash.py list --all

# 与我共享的画板
python scripts/excalidash.py list --shared --all

# 读取完整画板
python scripts/excalidash.py get BOARD_ID --out drawing.json

# 创建画板；scene.excalidraw 为原生场景
python scripts/excalidash.py create --name "测试画板" --input scene.excalidraw

# 修改后提交，输入需保留 get 返回的画板 version
python scripts/excalidash.py update BOARD_ID --input edited-drawing.json
```

使用独立配置时，将全局参数放在子命令前：

```sh
python scripts/excalidash.py --config /path/to/config.json list --all
```

命令返回 JSON，失败时退出码为 `2`。更新发生版本冲突时，重新读取并合并改动。写请求超时后先检查远端状态，避免重复创建。

## 绘图方式

AI 根据 [Skill 指令](SKILL.md) 编排原生元素，脚本负责登录、读写与回读验证。

[架构图设计](references/diagram-design.md) 说明视图、节点文字、分组、走线和视觉检查。[GitHub 经验](references/github-design-lessons.md) 记录 C4-PlantUML、Diagrams、D2 和 elkjs 的适用方法与来源。

结构性改版需要从实际元素生成预览并查看。预览的字体与线条效果取决于渲染方式。HTTP 客户端本身不提供图形布局引擎或渲染器。

## 目录

```text
SKILL.md                         AI 操作指令
agents/openai.yaml               Codex 技能元数据
scripts/excalidash.py             HTTP 客户端与配置工具
references/api-and-scenes.md     API 与原生场景格式
references/diagram-design.md     架构图设计方法
references/github-design-lessons.md  布局经验与来源
```

## 兼容性与贡献

客户端依赖 [API 参考](references/api-and-scenes.md) 中的 ExcaliDash 接口。不同部署版本可能调整接口或权限规则。脚本支持读取、创建和更新；删除、权限变更与共享设置尚未封装。

欢迎通过 [Issues](https://github.com/qch7/excalidash-skill/issues) 反馈问题，或提交 Pull Request。请提供脱敏后的复现步骤、Python 版本和错误码。修改脚本后可先做离线检查：

```sh
python -m compileall -q scripts
python scripts/excalidash.py --help
```

涉及 API 行为的修改应使用模拟服务验证版本冲突和写后校验，保留默认配置文件。

## 许可证

[MIT](LICENSE)。本仓库是独立的社区技能项目。
