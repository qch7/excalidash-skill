# API 和场景数据

以下接口已通过真实 ExcaliDash 实例验证。路径以配置的 `base_url` 为前缀，不将实例地址或真实账号写入技能。

## 登录与请求

1. `GET /api/csrf-token` 返回 `{token, header}`；缺少 header 时使用 `x-csrf-token`。
2. `POST /api/auth/login`，JSON `{email, password}`，附 CSRF 头、网站 Origin 和登录页 Referer。使用同一 CookieJar 接收会话 Cookie。
3. 登录后重新获取 CSRF，防止登录时轮换；后续写操作带该头和 Cookie。
4. `GET /api/auth/me` 返回当前用户（部分版本包装在 user 内），可核验邮箱和角色。

Cookie 不落盘。401 是认证失败；403 应区分 CSRF 与权限；409 是画板版本冲突。脚本不自动重放写请求。

## 已验证的画板接口

| 方法与路径 | 请求和返回 |
| --- | --- |
| `GET /api/drawings` | 自己的画板列表；参数 limit、offset；返回 drawings、totalCount、limit、offset |
| `GET /api/drawings/shared` | “与我共享”列表，分页格式同上 |
| `GET /api/drawings/{id}` | 完整画板，含 name/elements/appState/files/preview/version/accessLevel 等 |
| `POST /api/drawings` | JSON 至少有 name，可带 elements/appState/files/preview/collectionId；返回新画板或 drawing 包装 |
| `PUT /api/drawings/{id}` | JSON 含读取时的画板 version 和待改字段；返回更新后画板 |

列表项不含完整场景，不能代替完整读取结果保存。GET 中 id/userId/accessLevel/createdAt/updatedAt 等为只读元数据，不随更新发送。

画板页面为 `<base_url>/editor/<id>`；`/shared/<id>` 也是页面路由，不是列表接口。公开链接权限与账号共享权限可能不同，以实际接口返回为准。

## 原生 Excalidraw 场景

常见元素类型为 rectangle、ellipse、diamond、text、arrow、line。基础字段示例：

```json
{
  "id": "unique-element-id", "type": "rectangle",
  "x": 100, "y": 100, "width": 240, "height": 100, "angle": 0,
  "strokeColor": "#364fc7", "backgroundColor": "#dbe4ff",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "roundness": {"type": 3},
  "groupIds": [], "frameId": null, "boundElements": null,
  "seed": 12345, "version": 1, "versionNonce": 67890,
  "isDeleted": false, "link": null, "locked": false,
  "index": "a0", "updated": 1700000000000
}
```

- 新元素使用唯一 ID、随机 seed/nonce 和当前毫秒时间，不在所有元素中重复示例 ID 和时间。
- index 使用有效、递增的 fractional index，例如 a0、a1、a2；编辑时保留原有顺序。
- 文本另含 text/originalText/fontSize/fontFamily/textAlign/verticalAlign/containerId/autoResize/lineHeight。常用行高 1.25，text 与 originalText 同步更新。容器文字通过 containerId 与容器的 `boundElements: [{id, type: "text"}]` 双向对应。
- 箭头另含 `points: [[0,0],[dx,dy]]`、startBinding/endBinding、startArrowhead/endArrowhead、elbowed。未绑定时 binding 为 null，箭头末端通常为 `"arrow"`。
- appState 可含 viewBackgroundColor、gridSize、zoom、scrollX/scrollY，不写入运行时 Map 或协作者对象。
- files 是图片元素引用的文件映射，改文字时不要丢弃它；没有文件时使用 `{}`。
- preview 是 SVG 字符串。更新已有 SVG 可通过 XML 解析器修改对应文字或形状，保留无关部分。

## 接口发生变化时

读取首页 HTML 的模块脚本 URL，再检查动态加载的 Dashboard、Editor 和公共 API 模块。构建文件名带 hash，会改变，不能硬编码。搜索 `/drawings/shared`、`/drawings/${...}`、version、`/csrf-token` 和 `/auth/login`，以实际请求代码确认变化。无需启动浏览器、操作服务器或读取后端数据库。
