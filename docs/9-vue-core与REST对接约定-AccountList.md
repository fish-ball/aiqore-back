# vue-core 与 REST 对接约定（AccountList 经验沉淀）

本文档基于 `AccountList` 页面重构过程整理，作为后续同类页面改造的统一执行规范。

## 目标与原则

- 前端页面优先使用 `vue-core` 组件模块（`data-view / dialog / api`），减少手写 `element-plus` 业务逻辑。
- REST 资源路径保持一致性，避免列表/详情/编辑/删除分裂成不同命名风格。
- 接口响应格式优先对齐 `vue-core` 默认处理，减少页面层额外兼容代码。
- 重构遵循“最小影响”原则：聚焦当前页面，不联动改动无关模块。

## 一、前端页面结构约定（ListView 优先）

### 1. 页面容器

- 列表页优先直接渲染一个 `ListView`，避免额外包裹头部卡片与重复控件。
- 推荐形态：
  - 模板仅保留：`<ListView v-bind="listViewOptions" />`
  - 所有配置集中在一个 `reactive` 对象中统一维护。

### 2. 配置组织

- 使用 `listViewOptions` 承载以下内容：
  - `title`
  - `model`
  - `options`
  - `fields`
  - `actions`
  - `editViewOptions`
- `fields/actions` 直接内嵌在 `listViewOptions`，不额外拆分中间变量（除非复用需求明确）。

### 3. 字段渲染简化

- 对于金额/时间等纯显示转换，优先使用默认 `type` + `filter`。
- 不优先使用 `type: 'render'`，除非存在复杂 VNode 结构或交互需求。

### 4. 新建/编辑能力

- 通过 `ListView.options` 启用能力，不额外手写弹窗：
  - `inlineEdit: true`
  - `canCreate / canEdit / canDelete`
- 表单结构通过 `editViewOptions.fields` 声明，保持与资源模型一致。

## 二、路由命名约定（页面语义化）

### 1. 组件命名

- 列表页组件使用 `XxxList.vue` 命名，例如：`AccountList.vue`。

### 2. 路由 path/name

- 列表路由使用单数资源语义（与后端资源对齐）：
  - `path: 'account'`
  - `name: 'admin-account-list'`
- 菜单 index、页面跳转、其他引用路径必须同步更新，避免遗留旧地址（如 `/accounts`）。

## 三、后端 REST 资源约定（与 vue-core 对齐）

### 1. 资源命名统一

- 同一资源必须统一单复数，本项目 `account` 已确定为单数资源：
  - 列表：`GET /api/trade/account`
  - 详情：`GET /api/trade/account/{id}`
  - 创建：`POST /api/trade/account`
  - 删除：`DELETE /api/trade/account/{id}`
  - 动作：`POST /api/trade/account/{id}/sync`

禁止出现 `account` 与 `accounts` 混用导致的 URL 拼接错误。

### 2. 列表分页与响应结构

- 为适配 `vue-core ListView` 默认行为，列表接口必须支持：
  - Query 参数：`page`、`page_size`
- 列表响应结构必须为：
  - `count`: 总数
  - `results`: 当前页数组

即：

```json
{
  "count": 100,
  "results": []
}
```

### 3. 单对象接口格式

- 当前项目约定：单对象接口沿用现有通用包裹结构（`code/data/message`）。
- 若未来需要切换为“直接返回对象本身”，必须先统一评估 `vue-core hooks` 与存量页面依赖，再整体迁移，不做局部临时兼容。

### 4. 删除语义

- 当前项目约定：账户删除使用**硬删除**（`db.delete + commit`）。
- 若未来改为软删除，需同步更新：
  - 列表过滤逻辑
  - 统计口径
  - 文档说明

## 四、AccountList 重构检查清单

每次改造类似页面时，至少核对以下项目：

1. 页面是否已收敛为单 `ListView` + `listViewOptions`。
2. `model` 是否与后端资源路径完全一致。
3. 列表接口是否支持 `page/page_size` 且返回 `count/results`。
4. 路由 `path/name`、菜单 `index`、页面内跳转是否全部同步。
5. `fields` 是否优先使用 `filter` 做轻量格式化。
6. 新建/编辑是否通过 `inlineEdit + editViewOptions` 实现。
7. 删除语义（硬删/软删）是否与当前约定一致。

## 五、后续执行建议

- 新页面重构时先定义“资源命名 + 路由命名 + 列表响应格式”，再写页面。
- 前后端联调时优先抓取浏览器请求 URL，对照资源命名排查问题。
- 每次完成一个页面迁移后，及时补文档，确保约定可追溯。
