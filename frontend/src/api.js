/**
 * API 请求封装模块
 *
 * 基于 axios 封装后端 API 调用，提供以下功能：
 * 1. 统一的 baseURL 配置（/api 前缀，由 Vite 代理转发到后端）
 * 2. 5 分钟超时（适配 LLM 长时间任务）
 * 3. 响应错误拦截器（统一日志记录）
 * 4. 导出各接口的命名函数（createTask、getTaskStatus 等）
 *
 * 接口列表：
 * - POST /api/tasks          — 创建综述任务
 * - GET  /api/tasks/{id}     — 查询任务状态
 * - POST /api/tasks/{id}/run — 启动任务执行
 * - GET  /api/tasks/{id}/result — 获取综述结果
 * - GET  /api/tasks/{id}/export — 导出 Markdown
 */

import axios from 'axios'

// 创建 axios 实例，配置基础路径和超时
const api = axios.create({
  baseURL: '/api',       // 所有请求自动添加 /api 前缀，由 Vite 代理转发到后端 8000 端口
  timeout: 300000        // 5 分钟超时（LLM 任务可能需要较长时间）
})

// 响应拦截器：统一处理错误
api.interceptors.response.use(
  response => response,  // 成功响应直接返回
  error => {
    console.error('API Error:', error)  // 记录错误日志
    return Promise.reject(error)        // 继续抛出，由调用方处理
  }
)

/**
 * 创建综述任务
 * @param {Object} data - 任务参数 { topic, year_from, year_to, paper_limit, language }
 * @returns {Promise} 包含 task_id 的响应
 */
export const createTask = (data) => {
  return api.post('/tasks', data)
}

/**
 * 查询任务状态
 * @param {string} taskId - 任务 UUID
 * @returns {Promise} 包含 status、progress、current_phase 的响应
 */
export const getTaskStatus = (taskId) => {
  return api.get(`/tasks/${taskId}`)
}

/**
 * 启动任务执行（后台异步运行）
 * @param {string} taskId - 任务 UUID
 * @returns {Promise} 包含 message 的响应
 */
export const runTask = (taskId) => {
  return api.post(`/tasks/${taskId}/run`)
}

/**
 * 获取综述结果（任务完成后调用）
 * @param {string} taskId - 任务 UUID
 * @returns {Promise} 包含 papers、analyses、content、rag_evidence 等的完整结果
 */
export const getTaskResult = (taskId) => {
  return api.get(`/tasks/${taskId}/result`)
}

/**
 * 导出 Markdown 文件
 * @param {string} taskId - 任务 UUID
 * @returns {Promise} 包含 content（Markdown 文本）和 filename 的响应
 */
export const exportMarkdown = (taskId) => {
  return api.get(`/tasks/${taskId}/export`)
}

// 默认导出 axios 实例（可用于自定义请求）
export default api
