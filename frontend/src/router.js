/**
 * Vue Router 路由配置
 *
 * 定义前端页面路由：
 * - /                → Home.vue（任务创建页面）
 * - /result/:taskId  → Result.vue（结果展示页面，taskId 为动态路由参数）
 *
 * 使用 HTML5 History 模式（无 # 号），需要后端配合：
 * 后端对所有非 /api 路径返回 index.html，由 Vue Router 接管前端路由。
 */

import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import Result from './views/Result.vue'

// 路由表
const routes = [
  {
    path: '/',               // 首页：任务创建表单
    name: 'Home',
    component: Home
  },
  {
    path: '/result/:taskId', // 结果页：taskId 为动态参数（UUID）
    name: 'Result',
    component: Result,
    props: true              // 将路由参数作为组件 props 传递（等价于 defineProps({ taskId })）
  },
  {
    path: '/:pathMatch(.*)*', // 404 兜底路由：匹配所有未定义的路径
    name: 'NotFound',
    redirect: '/'            // 重定向到首页
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),  // HTML5 History 模式
  routes
})

export default router
