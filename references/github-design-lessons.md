# GitHub 架构图经验

用于选择视图、布局与走线方法。下表记录已阅读的一手资料，以及在 Excalidraw 中的应用。研究日期：2026-10-26。

| 项目与资料 | 来源中的方法 | 本技能的应用 |
| --- | --- | --- |
| [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML)，[布局指南](https://github.com/plantuml-stdlib/C4-PlantUML/blob/master/LayoutOptions.md)，[核心视图示例](https://github.com/plantuml-stdlib/C4-PlantUML/blob/master/samples/C4CoreDiagrams.md) | 区分视图；先定义对象与边界；在同一嵌套层次使用少量一致的布局约束 | 标明图的范围；内部步骤归入所属组件；位置约束与业务关系分别处理 |
| [Diagrams](https://github.com/mingrammer/diagrams)，[分组指南](https://github.com/mingrammer/diagrams/blob/master/docs/guides/cluster.md)，[边指南](https://diagrams.mingrammer.com/docs/guides/edge) | Cluster 表达分组；形状与边样式表达角色和关系 | 用局部分区、存储符号与图例减少重复文字，保持关系标签可见 |
| [D2](https://github.com/d2lang/d2)，[网格指南](https://d2lang.com/tour/grid-diagrams/)，[位置指南](https://d2lang.com/tour/positions/) | 行列、间距与尺寸协调；标签和图例可独立定位；主题统一字体和样式 | 先定行列与留白，统一同类节点尺寸，标题与连线标签使用独立空间 |
| [ELK / elkjs](https://github.com/kieler/elkjs) | 分层布局适用于有方向的节点图；显式端口；布局计算与渲染分开 | 沿主方向分层，为查询、异常和辅助关系预留端口与通道，再渲染检查 |

[C4 记号指南](https://c4model.com/diagrams/notation) 补充标题、简短职责、有方向关系与图例的要求。只标注已知技术和协议。

## 应用边界

- 上述方法可用于手工编排原生元素。按任务需要选择工具，沿用用户指定的画板平台。
- C4-PlantUML 对包围全部内容的大边界有引擎相关限制；在 Excalidraw 中按分组含义决定边界。
- D2 网格统一位置。线路仍需单独检查，部分引擎的网格内部连接为中心到中心直线。
- Diagrams 的边合并依赖 Graphviz 路由条件；直角线路需按实际关系规划。线条减少后仍须能辨认起止对象。
- ELK 计算位置和线路。字体、标签、样式和实际渲染仍需视觉检查。
- 本技能采用的跨视图同名引用、短标签与简洁陈述，是针对可编辑画板的实践选择。
