import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000
})

api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const createTask = (data) => {
  return api.post('/tasks', data)
}

export const getTaskStatus = (taskId) => {
  return api.get(`/tasks/${taskId}`)
}

export const runTask = (taskId) => {
  return api.post(`/tasks/${taskId}/run`)
}

export const getTaskResult = (taskId) => {
  return api.get(`/tasks/${taskId}/result`)
}

export const exportMarkdown = (taskId) => {
  return api.get(`/tasks/${taskId}/export`)
}

export default api
