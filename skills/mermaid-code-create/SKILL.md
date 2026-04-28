---
name: mermaid-code-create
description: 
  生成思维图，流程图等图形与图表的mermaid代码
---

## 执行流程

### 1. 根据用户输入内容，选择附录1中一种或多种图类型

分析用户输入的核心需求(流程、架构、数据分布、项目管理等)，匹配附录1中最合适的图表类型。

若用户需求涉及多个维度，可输出多种图表类型，如"流程图 + 甘特图”。

### 2. 加载对应的图类型示例文件

示例文件夹路径为 skills/mermaid-code-create/references/ 
每个图表类型对应一个独立文件(如 flowchart.md, gantt.md)。

### 3. 根据用户输入内容，生成对应的 Mermaid 图表代码

遵循图表的语法规范和最低版本要求，生成可直接渲染的 Mermaid 代码块。

### 4. 将图表代码写入对应的 Markdown 文件

文件夹路径为 automate_output/ 
文件内容结构示例：

markdown
# [图表名称]

## 说明
[简短描述该图表的用途和适用场景]

## Mermaid 代码
```mermaid
[生成的图表代码]
```

### 5. 输出结果

向用户展示:
- 选择的图表类型及理由。
- 生成的 Mermaid 代码(可直接复制使用)。
- 保存的文件名(如reactor_study.md)。
- 若用户未明确指定图表类型，可先给出推荐方案，并询问是否调整。

### 6. 迭代优化

根据用户反馈(如"节点太多"、"布局方向不对")，修改图表代码并重新写入文件。

支持同一文件内更新(覆盖原内容)或生成新版本(如 flowchart_v2.md)。


# 附录1 可生成图类型

## 一、流程图类

### 1. Flowchart(流程图)
- **用途**：展示流程、算法、决策路径。由**节点**(几何形状)和**边**(箭头/连线)组成。
- **基本语法**：
  ```
  flowchart LR
    A[开始] --> B{判断}
    B -->|是| C[结束]
    B -->|否| A
  ```
- **文件**：`flowchart.md`



## 二、软件工程与架构类

### 2. Architecture Diagram(架构图)— v11.1.0+
- **用途**：展示云服务或 CI/CD 部署中服务与资源之间的关系。服务(节点)通过边连接，相关服务可放入组中。
- **文件**：`architecture.md`

### 3. Block Diagram(块图)
- **用途**：用方块表示系统组件及其连接关系，适用于系统设计。
- **文件**：`block.md`

### 4. C4 Diagram(C4 模型图)— 实验性
- **用途**：C4 模型(Context/Container/Component/Code)的软件架构可视化。
- **注意**：实验性图表，语法可能变化。
- **文件**：`c4.md`

### 5. Class Diagram(类图)
- **用途**：UML 静态结构图，展示系统的类、属性、方法及对象间关系。
- **文件**：`classDiagram.md`

### 6. State Diagram(状态图)
- **用途**：描述系统的有限状态及状态间的转移，用于计算机科学及相关领域。
- **文件**：`stateDiagram.md`

### 7. Sequence Diagram(时序图)
- **用途**：交互图，展示进程/对象之间如何按时间顺序交互操作。
- **文件**：`sequenceDiagram.md`

### 8. ZenUML(时序图变体)
- **用途**：另一种时序图语法，展示进程间的交互顺序。
- **文件**：`zenuml.md`

### 9. Requirement Diagram(需求图)
- **用途**：可视化需求及其相互连接，遵循 SysML v1.6 规范。
- **文件**：`requirementDiagram.md`

### 10. Gitgraph Diagram(Git 分支图)
- **用途**：图形化展示 Git 提交记录和分支操作(commit、branch、merge 等)。
- **文件**：`gitgraph.md`

### 11. Packet Diagram(数据包图)— v11.0.0+
- **用途**：可视化网络数据包的结构和字段布局。
- **文件**：`packet.md`


## 三、项目管理与流程类

### 12. Gantt Diagram(甘特图)
- **用途**：项目进度管理，展示任务的开始/结束日期和时间线。
- **文件**：`gantt.md`

### 13. Kanban Diagram(看板图)
- **用途**：可视化任务在不同工作流阶段中的移动状态，适用于敏捷项目管理。
- **文件**：`kanban.md`

### 14. Timeline Diagram(时间线图)— 实验性
- **用途**：按时间顺序展示事件或里程碑。
- **注意**：实验性图表，图标集成部分仍在开发中。
- **文件**：`timeline.md`

### 15. User Journey Diagram(用户旅程图)
- **用途**：描述不同用户在系统/应用中完成特定任务的高级别步骤，展示当前工作流并发现改进点。
- **文件**：`userJourney.md`


## 四、数据分析与统计类

### 16. Pie Chart(饼图)
- **用途**：圆形统计图，通过扇形切片展示数值比例。
- **文件**：`pie.md`

### 17. XY Chart(XY 图表)
- **用途**：综合性图表模块，目前包含**柱状图**和**折线图**两种基础类型，用于双变量数据可视化。
- **文件**：`xyChart.md`

### 18. Quadrant Chart(象限图)— v11.0.0+
- **用途**：将数据点绘制在二维网格上，分为四个象限，用于模式识别和优先级排序(常用于商业、营销、风险管理)。
- **文件**：`quadrantChart.md`

### 19. Radar Diagram(雷达图)— v11.6.0+
- **用途**：以雷达形状展示多维度数据对比。
- **文件**：`radar.md`

### 20. Sankey Diagram(桑基图)— v10.3.0+
- **用途**：展示从一组数值到另一组数值的流动关系，常用于能量、流量、资金流向分析。
- **文件**：`sankey.md`


## 五、关系与组织类

### 21. Entity Relationship Diagram(ER 图)
- **用途**：实体关系模型，展示特定领域中感兴趣的事物(实体类型)及其之间的关系。
- **文件**：`entityRelationshipDiagram.md`

### 22. Venn Diagram(韦恩图)— v11.12.3+
- **用途**：用重叠的圆圈展示集合之间的关系(交集、并集、差集等)。
- **文件**：`venn.md`

### 23. TreeView Diagram(树形视图)— v11.14.0+
- **用途**：以树状结构展示层级数据。
- **文件**：`treeView.md`

### 24. Treemap Diagram(矩形树图)
- **用途**：将层级数据显示为一组嵌套矩形，每个分支用矩形表示，子分支用更小的矩形平铺。
- **文件**：`treemap.md`

### 25. Mindmap(思维导图)— 实验性
- **用途**：以中心主题发散出分支，用于头脑风暴和知识组织。
- **注意**：实验性图表，语法基本稳定，图标集成部分仍在开发中。
- **文件**：`mindmap.md`


## 六、商业与战略类

### 26. Wardley Map(沃德利地图)— v11.14.0+
- **用途**：商业战略的可视化表示，映射价值链和组件演化，帮助识别战略机会、依赖关系并指导技术决策。
- **文件**：`wardley.md`

### 27. Ishikawa Diagram(石川图/鱼骨图)— v11.12.3+
- **用途**：表示特定事件(或问题)的原因，也称因果图、鱼骨图。用于根因分析。
- **文件**：`ishikawa.md`

### 28. Event Modeling Diagram(事件建模图)— v\<MERMAID_RELEASE_VERSION>+
- **用途**：事件建模的可视化工具。
- **文件**：`eventmodeling.md`



## 快速参考

| 类别 | 图表类型 | 适用场景 | 最低版本 |
|------|---------|---------|---------|
| 流程图 | Flowchart | 流程、算法、决策 | - |
| 软件工程 | Architecture | 云/CI/CD 架构 | v11.1.0+ |
| 软件工程 | Block Diagram | 系统组件图 | - |
| 软件工程 | C4 Diagram | 软件架构模型 | 实验性 |
| 软件工程 | Class Diagram | UML 类结构 | - |
| 软件工程 | State Diagram | 有限状态机 | - |
| 软件工程 | Sequence Diagram | 交互时序 | - |
| 软件工程 | ZenUML | 交互时序(替代语法) | - |
| 软件工程 | Requirement Diagram | 需求管理 | - |
| 软件工程 | Gitgraph | Git 版本控制 | - |
| 软件工程 | Packet Diagram | 网络协议 | v11.0.0+ |
| 项目管理 | Gantt | 项目进度 | - |
| 项目管理 | Kanban | 任务看板 | - |
| 项目管理 | Timeline | 事件时间线 | 实验性 |
| 项目管理 | User Journey | 用户体验流程 | - |
| 数据分析 | Pie Chart | 比例分布 | - |
| 数据分析 | XY Chart | 柱状/折线图 | - |
| 数据分析 | Quadrant Chart | 四象限分析 | v11.0.0+ |
| 数据分析 | Radar Diagram | 多维对比 | v11.6.0+ |
| 数据分析 | Sankey Diagram | 流量/流向 | v10.3.0+ |
| 关系组织 | ER Diagram | 实体关系 | - |
| 关系组织 | Venn Diagram | 集合关系 | v11.12.3+ |
| 关系组织 | TreeView | 树形层级 | v11.14.0+ |
| 关系组织 | Treemap | 嵌套矩形 | - |
| 关系组织 | Mindmap | 思维导图 | 实验性 |
| 商业战略 | Wardley Map | 商业战略 | v11.14.0+ |
| 商业战略 | Ishikawa | 根因分析 | v11.12.3+ |
| 商业战略 | Event Modeling | 事件建模 | v\<MERMAID_RELEASE_VERSION>+ |



## 注意事项

1. **实验性图表**：C4 Diagram、Mindmap、Timeline 为实验性图表，语法和属性可能在后续版本中变化。
2. **版本要求**：部分图表有最低 Mermaid 版本要求(如上表所示)。

