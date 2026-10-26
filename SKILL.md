---
name: excalidash
description: 通过 HTTP API 读取、创建和修改 ExcaliDash 画板，支持共享画板与可编辑架构图。用于 ExcaliDash 安装配置、画板链接和绘图任务；安装后主动检查配置并引导填写网站、账号和密码，后续优先复用本地配置。无需浏览器自动化。
---

# ExcaliDash

使用本技能的 `scripts/excalidash.py` 调用网站自身的 HTTP API。需要 Python 3.10+，无第三方依赖。将下文脚本路径解析为本技能目录中的绝对路径，不依赖当前项目。

## 安装后主动引导配置

处理安装任务时，完成文件安装后立即执行下方检查，主动引导用户完成首次配置。安装任务包括配置引导和登录验证；配置尚未完成时说明待填写项，并给出下一步操作。完成反馈说明安装状态、配置状态和登录验证结果。

仅生成本地场景、预览或进行明确不联网的验收时，跳过本节配置和认证，不读取凭据；需要连接真实网站时按本节操作。

配置默认存放于 `~/.config/ExcaliDashSkill/config.json`（Windows 中 `~` 为当前用户目录）。网址、邮箱和密码只存放在那里；技能文件、脚本、示例和项目文件不保存真实账号密码。Cookie 和 CSRF 令牌仅在单次进程内存中保留。

首次安装、首次调用及后续调用，都先执行本地检查：

```powershell
python "<技能绝对路径>/scripts/excalidash.py" config-status
```

- 若 `configured: true`，直接复用已有配置。安装后的设置流程运行 `whoami` 验证登录；后续画板命令自行登录。用户要求切换账号时再更新配置。
- 若返回 `CONFIG_MISSING` 或 `CONFIG_INVALID`，一次性询问缺失的网站完整网址、登录邮箱和密码。当前会话中已明确提供的值可直接沿用，只询问缺失项；不要猜测凭据。
- 引导用户在本机终端运行 `configure`，密码通过隐藏输入填写；或将用户明确提供的配置 JSON 通过 stdin 传给 `configure --stdin-json`。避免把密码放进命令行参数、临时脚本或普通任务文件，不回显配置全文。
- 本地检查不联网。配置保存后运行 `whoami` 验证登录。认证失败时报告实际错误，并引导用户检查网址或凭据；不自动换账号或恢复旧密码。

```powershell
python "<技能绝对路径>/scripts/excalidash.py" configure
python "<技能绝对路径>/scripts/excalidash.py" whoami
```

配置是 UTF-8 JSON，字段为 `base_url`、`email`、`password`。脚本的 `--config <路径>` 用于用户明确选择其他配置或隔离测试；正常操作使用默认目录。

## 读取画板

```powershell
python "<技能绝对路径>/scripts/excalidash.py" list --all
python "<技能绝对路径>/scripts/excalidash.py" list --shared --all
python "<技能绝对路径>/scripts/excalidash.py" get "<画板 ID>" --out "<工作目录>/drawing.json"
```

全部绘图和与我共享使用不同接口。普通列表为空不代表没有共享画板，必须查询 `list --shared`。链接中的 `/editor/<id>`、`/shared/<id>` 使用同一个画板 ID；完整读取后的 `accessLevel` 表示当前账号的权限。列表成功不等于画板内容可读，需要 `get` 读取目标内容。

## 架构图先表达关系

新建架构图、流程图或整体重排时，先阅读 [references/diagram-design.md](references/diagram-design.md)，确定视图范围、关键对象和主阅读路径。需要选择布局方法时，参考 [references/github-design-lessons.md](references/github-design-lessons.md) 中的来源与适用条件。

- 分区表达归属，位置表达层次，箭头表达方向和动作。按内容选择主流程、分支、泳道、存储符号或局部展开。
- 节点使用名称和一行短标签；连线使用动作、传递物或条件。文字用直接陈述，句子简短；避免转折句、修饰词堆叠和近义词并列，不用引号强调名词。
- 区分组件、内部处理步骤和属性。仅绘制输入支持的对象与关系。颜色、线型与符号保持一致含义。
- 同层对齐，间距均匀，并列分支围绕主轴平衡展开。先预留节点和走线通道，再连接；通过调整顺序、端口和通道减少交叉，避开文字与无关节点。
- 新图及结构性改版须由实际原生 elements 生成预览并查看。检查关系、平衡、留白、标签、交叉和溢出，修正后交付。

已有画板局部修改保留用户的结构与视觉习惯。图形形式服务于解释，复杂程度随内容调整。

## 创建和修改

按用户需求编排原生 Excalidraw 元素 JSON，保留可编辑性。创建输入可以是画板 JSON，也可以是 `.excalidraw` 场景，后者通过 `--name` 提供名称。普通创建至少需要名称，元素和画布状态可以省略。

```powershell
python "<技能绝对路径>/scripts/excalidash.py" create --name "测试画板" --input "<工作目录>/scene.json"
python "<技能绝对路径>/scripts/excalidash.py" update "<画板 ID>" --input "<工作目录>/edited-drawing.json"
```

修改前先 `get` 最新内容，将结果保存为工作副本，只改用户指定的元素或字段。`update` 接受完整工作副本并过滤只读元数据；也可提供包含 `version` 和待修改字段的局部 JSON。修改图形时保留其他元素、原有 ID、绑定关系及文件；变更元素时增加该元素自身的 `version`，更新 `versionNonce` 和 `updated`。画板级 `version` 使用读取值，不能自行增加或省略。

脚本检查编辑权限和画板版本，单次发送创建或更新请求，随后读取并核对提交字段。409 时重新读取并合并用户的改动，再提交新版本；不要直接替换版本号或盲目重试。写请求超时后可能已保存，先检查服务器状态，尤其不要重复创建。

列表缩略图由 `preview` SVG 提供，与 `elements` 是不同数据。需要缩略图时按同一图形数据生成 SVG；修改影响预览的内容时同步更新 SVG。预览图片不能替代可编辑元素。

脚本处理登录 Cookie、CSRF 和保存后验证，不执行删除、权限变更或共享设置。需要未封装操作或接口变化时，阅读 [references/api-and-scenes.md](references/api-and-scenes.md)，再按实际公开前端确认接口，不假定读权限意味着写权限。

交付时提供 `url` 和实际验证结果。验证失败时保留画板 ID，分别说明写入与验证状态，不仅凭 HTTP 200 宣称全部成功。
