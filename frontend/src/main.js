/**
 * Vue 应用入口文件
 *
 * 职责：
 * 1. 创建 Vue 应用实例
 * 2. 注册全局插件（Element Plus UI 组件库、Vue Router 路由）
 * 3. 注册 Element Plus 图标组件（全局可用）
 * 4. 挂载到 DOM 的 #app 元素
 */

import { createApp } from 'vue'
import ElementPlus from 'element-plus'           // Element Plus UI 组件库（按钮、表单、表格等）
import 'element-plus/dist/index.css'              // Element Plus 全局样式
import * as ElementPlusIconsVue from '@element-plus/icons-vue'  // Element Plus 图标库
import App from './App.vue'                       // 根组件
import router from './router'                     // 路由配置

// 创建 Vue 应用实例
const app = createApp(App)

// 全局注册所有 Element Plus 图标组件（100+ 个）
// 注册后可在任意模板中通过 <el-icon><Search /></el-icon> 使用
// 注意：这会增加打包体积，生产环境建议按需引入
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册插件
app.use(ElementPlus)  // Element Plus UI 组件库
app.use(router)       // Vue Router 路由

// 挂载到 DOM
app.mount('#app')
