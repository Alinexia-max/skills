---
name: web-frontend-coder
description: Web前端编码指南，适用于 Vue3 + TypeScript + Vite5 + Ant Design Vue 4 项目。当需要编写、修改Vue页面、组件、API层、Pinia Store、路由配置等前端代码时触发。绑定Agent：web-frontend-coder。
allowed-tools: 
disable: false
---

# Web 前端编码指南（Vue3 + TS + Ant Design Vue 4）

## 技术栈

| 项目 | 版本/选型 |
|------|----------|
| 框架 | Vue 3.4 + Composition API |
| 语言 | TypeScript 5 |
| 构建 | Vite 5 |
| UI | Ant Design Vue 4.2 |
| 图标 | @ant-design/icons-vue |
| 状态管理 | Pinia（Options API 风格） |
| 路由 | Vue Router 4（Hash 模式） |
| HTTP | Axios 1.6（封装在 `src/lib/axios.ts`） |
| 国际化 | vue-i18n 9（Composition API） |
| 样式 | Less |
| 图表 | ECharts 5.4 |
| 加密 | sm-crypto（SM4/AES） |
| 工具库 | lodash、dayjs、decimal.js |

## 项目目录结构

```
src/
├── api/           # API 层，按模块分文件
│   └── {system|support|business}/
│       └── {entity}-api.ts      # 导出命名对象（如 employeeApi）
├── assets/        # 静态资源
├── components/    # 公共组件
├── config/        # 项目配置
├── constants/     # 常量
├── directives/    # 自定义指令（如 v-privilege）
├── i18n/          # 国际化语言包
│   └── lang/{zh-CN|en-US}/
├── layout/        # 布局组件
├── lib/           # 工具库（axios.ts 在此）
├── plugins/       # 插件
├── router/        # 路由配置
├── store/         # Pinia Store
├── theme/         # 主题配置
├── types/         # TypeScript 类型声明
├── utils/         # 工具函数
└── views/         # 页面，按模块分目录
```

## 编码规范

### Vue 组件
- 使用 `<script setup lang="ts">` Composition API 写法
- 文件名：大驼峰，如 `EmployeeList.vue`、`RoleFormModal.vue`
- 模板内使用 Ant Design Vue 4 组件（`a-button`、`a-table`、`a-modal` 等）
- 样式使用 `<style lang="less" scoped>`
- 组件命名使用多词，避免与 HTML 原生元素冲突

### API 层
- 每个实体一个 API 文件，如 `employee-api.ts`
- 导出命名对象：`export const employeeApi = { ... }`
- 统一通过 `src/lib/axios.ts` 发请求
- 方法命名：`queryList`、`queryDetail`、`add`、`update`、`delete`

### Pinia Store
- 使用 Options API 风格（`defineStore('id', { state, getters, actions })`）
- Store 文件命名：`useXxxStore`，如 `useUserStore`

### 路由
- Hash 模式
- 动态路由：登录后根据后端返回 `menuList` 构建

### 国际化
- 使用 vue-i18n Composition API（`useI18n()`）
- 语言包在 `src/i18n/lang/{zh-CN|en-US}/`

### 权限
- 功能点权限用 `v-privilege` 指令
- 也可用 `$privilege` 方法
- 超级管理员跳过权限检查

### API 路径别名
- `@/` → `src/`（已在 vite.config.ts 和 tsconfig.json 配置）
- import 时使用 `import Xxx from '@/xxx/xxx'`

## 常用脚本

```bash
npm run dev          # 开发服务器（mode=development）
npm run localhost    # 本地联调（mode=localhost）
npm run build:prod   # 生产构建
npm run build:test   # 测试环境构建
```

## 开发约束

- 不要手动修改 `node_modules`
- 样式变量在 theme/ 中统一管理，不要在各组件中硬编码色值
- API 请求统一走 axios.ts 封装，不要直接使用 `fetch` 或裸 `axios`
- 列表页使用 `a-table` + 分页组件
