<!--
  Home.vue — 任务创建页面（工作台首页）

  页面结构：
  1. 顶部导航栏：品牌标识 + 技术标签
  2. 主内容区（左右两栏布局）：
     - 左栏：任务创建表单（研究主题、年份、论文数、语言）
     - 右栏：Agent 执行链路可视化 + 数据源信息卡片

  交互流程：
  1. 用户填写表单 → 2. 点击"开始生成综述" → 3. 调用 createTask API → 4. 调用 runTask API → 5. 跳转到结果页
-->
<template>
  <div class="workspace">
    <!-- ========== 顶部导航栏 ========== -->
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">
          <el-icon><Document /></el-icon>
        </div>
        <div>
          <h1>科研文献综述生成工作台</h1>
          <p>AI 驱动的学术文献检索、分析与综述生成系统</p>
        </div>
      </div>

      <!-- 技术栈标签 -->
      <div class="runtime-tags">
        <el-tag effect="plain" type="success">DeepSeek</el-tag>
        <el-tag effect="plain">Semantic Scholar</el-tag>
        <el-tag effect="plain" type="success">OpenAlex</el-tag>
        <el-tag effect="plain" type="info">arXiv</el-tag>
      </div>
    </header>

    <!-- ========== 主内容区（左右两栏） ========== -->
    <main class="workspace-grid">
      <!-- ===== 左栏：任务创建面板 ===== -->
      <section class="task-panel">
        <div class="section-heading">
          <div>
            <span class="eyebrow">Task setup</span>
            <h2>创建综述任务</h2>
            <p>输入研究主题后，系统会自动扩展检索词、筛选论文并生成综述。</p>
          </div>
        </div>

        <!-- 功能亮点卡片（3 个） -->
        <div class="capability-strip">
          <div v-for="item in capabilities" :key="item.title" class="capability-card">
            <el-icon><component :is="item.icon" /></el-icon>
            <div>
              <strong>{{ item.title }}</strong>
              <span>{{ item.desc }}</span>
            </div>
          </div>
        </div>

        <!-- 任务创建表单 -->
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          class="task-form"
        >
          <!-- 研究主题输入 -->
          <el-form-item label="研究主题" prop="topic">
            <el-input
              v-model="form.topic"
              placeholder="例如：Retrieval Augmented Generation for Question Answering"
              :disabled="loading"
              clearable
            />
          </el-form-item>

          <!-- 示例主题按钮 -->
          <div class="examples">
            <span>示例主题</span>
            <el-button
              v-for="item in examples"
              :key="item"
              size="small"
              plain
              :disabled="loading"
              @click="useExample(item)"
            >
              {{ item }}
            </el-button>
          </div>

          <!-- 年份范围 + 输出语言（同行排列） -->
          <div class="form-row">
            <el-form-item label="年份范围" prop="yearRange">
              <el-date-picker
                v-model="form.yearRange"
                type="yearrange"
                range-separator="至"
                start-placeholder="开始年份"
                end-placeholder="结束年份"
                :disabled="loading"
                value-format="YYYY"
                style="width: 100%;"
              />
            </el-form-item>

            <el-form-item label="输出语言" prop="language">
              <el-segmented
                v-model="form.language"
                :options="languageOptions"
                :disabled="loading"
                block
              />
            </el-form-item>
          </div>

          <!-- 论文数量选择（预设按钮 + 数字输入框） -->
          <el-form-item label="论文数量" prop="paperLimit">
            <div class="paper-count-control">
              <div class="preset-grid">
                <button
                  v-for="count in paperPresets"
                  :key="count"
                  type="button"
                  class="preset-button"
                  :class="{ active: form.paperLimit === count }"
                  :disabled="loading"
                  @click="form.paperLimit = count"
                >
                  {{ count }}
                </button>
              </div>
              <el-input-number
                v-model="form.paperLimit"
                :min="5"
                :max="30"
                :step="5"
                step-strictly
                controls-position="right"
                :disabled="loading"
              />
            </div>
            <p class="field-hint">建议课堂演示选择 10-15 篇，速度和结果质量更均衡。</p>
          </el-form-item>

          <!-- 提交按钮 -->
          <div class="submit-row">
            <div class="submit-note">
              <strong>预计流程</strong>
              <span>检索、排序、阅读、组织、生成、校验</span>
            </div>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleSubmit"
            >
              <el-icon><Search /></el-icon>
              <span>{{ loading ? '任务创建中' : '开始生成综述' }}</span>
            </el-button>
          </div>
        </el-form>
      </section>

      <!-- ===== 右栏：信息面板 ===== -->
      <aside class="insight-panel">
        <!-- Agent 执行链路可视化 -->
        <section class="panel-block flow-panel">
          <div class="panel-title">
            <el-icon><Connection /></el-icon>
            <h3>Agent 执行链路</h3>
          </div>
          <div class="pipeline">
            <div v-for="step in pipeline" :key="step.name" class="pipeline-step">
              <div class="step-index">{{ step.index }}</div>
              <div>
                <strong>{{ step.name }}</strong>
                <p>{{ step.desc }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- 数据源和技术信息卡片 -->
        <section class="panel-block source-panel">
          <div class="panel-title">
            <el-icon><DataAnalysis /></el-icon>
            <h3>数据与质量控制</h3>
          </div>
          <div class="source-grid">
            <div v-for="item in sourceCards" :key="item.name" class="source-card">
              <span>{{ item.name }}</span>
              <strong>{{ item.value }}</strong>
              <p>{{ item.desc }}</p>
            </div>
          </div>
        </section>

        <!-- 历史任务记录 -->
        <section class="panel-block history-panel">
          <div class="panel-title history-title">
            <div class="history-title-main">
              <el-icon><Clock /></el-icon>
              <h3>历史任务</h3>
            </div>
            <el-button size="small" plain :loading="historyLoading" @click="loadHistory">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>

          <el-empty
            v-if="!historyLoading && historyTasks.length === 0"
            description="暂无历史任务"
          />

          <div v-else class="history-list">
            <button
              v-for="task in historyTasks"
              :key="task.task_id"
              type="button"
              class="history-item"
              @click="openHistoryTask(task.task_id)"
            >
              <div class="history-main">
                <strong>{{ task.topic }}</strong>
                <span>{{ formatDate(task.created_at) }} · {{ task.paper_limit }} 篇 · {{ task.language === 'zh' ? '中文' : 'English' }}</span>
              </div>
              <div class="history-side">
                <el-tag :type="historyStatusType(task.status)" effect="plain" size="small">
                  {{ historyStatusText(task.status) }}
                </el-tag>
                <span>{{ task.progress || 0 }}%</span>
              </div>
            </button>
          </div>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup>
/**
 * 组合式 API：使用 Vue 3 <script setup> 语法
 *
 * 状态管理：
 * - formRef: 表单引用（用于调用 validate 方法）
 * - loading: 加载状态（防止重复提交）
 * - form: 表单数据（响应式对象）
 * - rules: 表单验证规则
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createTask, runTask, getTaskHistory } from '../api.js'

const router = useRouter()
const formRef = ref(null)     // 表单 DOM 引用
const loading = ref(false)    // 提交加载状态
const historyTasks = ref([])
const historyLoading = ref(false)

// 示例主题列表
const examples = [
  'Retrieval Augmented Generation',
  'LLM Hallucination Detection',
  'Multimodal Large Language Models'
]

// 语言选项
const languageOptions = [
  { label: '中文', value: 'zh' },
  { label: 'English', value: 'en' }
]

// 论文数量预设值
const paperPresets = [5, 10, 15, 20, 30]

// 功能亮点数据
const capabilities = [
  { icon: 'Search', title: '双源检索', desc: '覆盖论文摘要与引用信息' },
  { icon: 'DataAnalysis', title: '相关性排序', desc: '关键词、引用数与年份综合评分' },
  { icon: 'Document', title: '引用校验', desc: '约束生成内容只引用候选论文' }
]

// Agent 执行链路步骤
const pipeline = [
  { index: '01', name: 'Query', desc: '扩展主题关键词与检索式' },
  { index: '02', name: 'Search', desc: '检索并合并学术论文' },
  { index: '03', name: 'Rank', desc: '按相关性与影响力排序' },
  { index: '04', name: 'Read', desc: '抽取问题、方法和贡献' },
  { index: '05', name: 'Write', desc: '生成综述并校验引用' }
]

// 数据源信息卡片
const sourceCards = [
  { name: '文献来源', value: '3', desc: 'arXiv + OpenAlex + Semantic Scholar' },
  { name: '生成模型', value: 'DeepSeek', desc: 'OpenAI-compatible Chat API' },
  { name: '存储状态', value: 'Enabled', desc: '任务、论文与结果持久化' },
  { name: '排序方式', value: 'Hybrid', desc: '轻量可解释评分策略' }
]

// 表单数据（响应式对象）
const form = reactive({
  topic: '',
  yearRange: ['2020', '2024'],  // 默认年份范围
  paperLimit: 10,               // 默认 10 篇
  language: 'zh'                // 默认中文
})

// 表单验证规则（Element Plus 自动校验）
const rules = {
  topic: [
    { required: true, message: '请输入研究主题', trigger: 'blur' },
    { min: 2, message: '主题长度至少2个字符', trigger: 'blur' }
  ],
  yearRange: [
    { required: true, message: '请选择年份范围', trigger: 'change' }
  ],
  paperLimit: [
    { required: true, message: '请选择论文数量', trigger: 'change' }
  ],
  language: [
    { required: true, message: '请选择输出语言', trigger: 'change' }
  ]
}

// 使用示例主题
const useExample = (topic) => {
  form.topic = topic
}

const loadHistory = async () => {
  historyLoading.value = true
  try {
    const response = await getTaskHistory(12)
    historyTasks.value = response.data || []
  } catch (error) {
    console.error('获取历史任务失败:', error)
    ElMessage.error('获取历史任务失败')
  } finally {
    historyLoading.value = false
  }
}

const openHistoryTask = (taskId) => {
  router.push(`/result/${taskId}`)
}

const historyStatusText = (status) => {
  const map = {
    pending: '等待',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const historyStatusType = (status) => {
  const map = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const formatDate = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * 提交表单：创建任务并启动工作流
 *
 * 流程：
 * 1. 表单验证 → 2. 调用 createTask API → 3. 调用 runTask API → 4. 跳转结果页
 */
const handleSubmit = async () => {
  if (!formRef.value) return

  // Element Plus 表单验证
  await formRef.value.validate(async (valid) => {
    if (!valid) return  // 验证失败，不继续

    loading.value = true

    try {
      // 解析年份范围
      const [yearFrom, yearTo] = form.yearRange

      // 构建请求参数
      const taskData = {
        topic: form.topic,
        year_from: parseInt(yearFrom),
        year_to: parseInt(yearTo),
        paper_limit: form.paperLimit,
        language: form.language
      }

      // 第一步：创建任务（获取 taskId）
      const response = await createTask(taskData)
      const taskId = response.data.task_id

      ElMessage.success('任务已创建，正在启动工作流')

      // 第二步：启动任务执行（后台异步运行）
      await runTask(taskId)

      // 第三步：跳转到结果页
      router.push(`/result/${taskId}`)
    } catch (error) {
      console.error('创建任务失败:', error)
      // 优先显示后端返回的错误信息
      const message = error?.response?.data?.detail || '创建任务失败，请检查后端服务和配置'
      ElMessage.error(message)
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
/* ========== 页面整体布局 ========== */
.workspace {
  min-height: 100vh;
  padding: 28px;
  /* 网格点背景 + 渐变底色 */
  background:
    linear-gradient(rgba(15, 118, 110, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.035) 1px, transparent 1px),
    linear-gradient(180deg, #eef8fb 0, #f7f9fc 310px, #f7f9fc 100%);
  background-size: 28px 28px, 28px 28px, auto;
  color: #172033;
}

/* ========== 顶部导航栏 ========== */
.topbar {
  max-width: 1180px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #0f766e;
  color: #fff;
  font-size: 24px;
  box-shadow: 0 12px 24px rgba(15, 118, 110, 0.18);
}

.brand h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  color: #111827;
}

.brand p {
  margin: 4px 0 0;
  color: #667085;
  font-size: 14px;
}

.runtime-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

/* ========== 主内容区（左右两栏） ========== */
.workspace-grid {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(340px, 0.75fr);
  gap: 20px;
  align-items: start;
}

.task-panel,
.panel-block {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
}

.task-panel {
  padding: 28px;
}

/* ========== 标题区域 ========== */
.section-heading {
  margin-bottom: 18px;
}

.eyebrow {
  display: block;
  margin-bottom: 6px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.section-heading h2,
.panel-title h3 {
  margin: 0;
  color: #111827;
}

.section-heading h2 {
  font-size: 22px;
}

.section-heading p {
  margin: 8px 0 0;
  color: #667085;
  font-size: 14px;
}

/* ========== 功能亮点卡片 ========== */
.capability-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

.capability-card {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid #e8eef6;
  border-radius: 8px;
  background: #fbfcfe;
}

.capability-card .el-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #ecfdf5;
  color: #047857;
  font-size: 17px;
}

.capability-card strong {
  display: block;
  color: #1f2937;
  font-size: 13px;
  margin-bottom: 3px;
}

.capability-card span {
  color: #667085;
  font-size: 12px;
  line-height: 1.45;
}

/* ========== 表单样式 ========== */
.task-form :deep(.el-form-item__label) {
  font-weight: 700;
  color: #344054;
}

.examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: -6px 0 20px;
}

.examples span {
  color: #667085;
  font-size: 13px;
}

.form-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 0.55fr);
  gap: 16px;
}

.paper-count-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 132px;
  gap: 14px;
  align-items: center;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.preset-button {
  height: 38px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #fff;
  color: #344054;
  font-weight: 700;
  cursor: pointer;
  transition: 0.16s ease;
}

.preset-button:hover,
.preset-button.active {
  border-color: #0f766e;
  background: #ecfdf5;
  color: #047857;
}

.preset-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.field-hint {
  margin: 8px 0 0;
  color: #98a2b3;
  font-size: 12px;
}

.submit-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
  padding-top: 18px;
  border-top: 1px solid #eef2f7;
}

.submit-note {
  display: grid;
  gap: 3px;
}

.submit-note strong {
  color: #344054;
  font-size: 13px;
}

.submit-note span {
  color: #667085;
  font-size: 12px;
}

.submit-row .el-button {
  min-width: 180px;
}

.submit-row .el-button :deep(span) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* ========== 右栏信息面板 ========== */
.insight-panel {
  display: grid;
  gap: 16px;
}

.panel-block {
  padding: 22px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.panel-title .el-icon {
  color: #0f766e;
  font-size: 20px;
}

/* ========== Agent 执行链路 ========== */
.pipeline {
  display: grid;
  gap: 14px;
}

.pipeline-step {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.step-index {
  width: 34px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #ecfdf5;
  color: #047857;
  font-size: 12px;
  font-weight: 800;
}

.pipeline-step strong {
  display: block;
  color: #1f2937;
  margin-bottom: 2px;
}

.pipeline-step p {
  margin: 0;
  color: #667085;
  font-size: 13px;
  line-height: 1.55;
}

/* ========== 数据源信息卡片 ========== */
.source-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.source-card {
  min-height: 104px;
  padding: 13px;
  border: 1px solid #e8eef6;
  border-radius: 8px;
  background: #fbfcfe;
}

.source-card span {
  display: block;
  color: #667085;
  font-size: 12px;
  margin-bottom: 8px;
}

.source-card strong {
  display: block;
  color: #111827;
  font-size: 18px;
  line-height: 1.15;
  margin-bottom: 8px;
}

.source-card p {
  margin: 0;
  color: #667085;
  font-size: 12px;
  line-height: 1.45;
}

/* ========== 历史任务记录 ========== */
.history-title {
  justify-content: space-between;
}

.history-title-main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-list {
  display: grid;
  gap: 10px;
}

.history-item {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid #e8eef6;
  border-radius: 8px;
  background: #fbfcfe;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.history-item:hover {
  border-color: #93c5fd;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.history-main {
  min-width: 0;
}

.history-main strong {
  display: block;
  overflow: hidden;
  color: #111827;
  font-size: 13px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-main span {
  display: block;
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
}

.history-side {
  display: grid;
  justify-items: end;
  gap: 5px;
}

.history-side > span {
  color: #667085;
  font-size: 12px;
}

/* ========== 响应式布局 ========== */
@media (max-width: 980px) {
  .workspace {
    padding: 18px;
  }

  .topbar,
  .workspace-grid,
  .form-row,
  .paper-count-control {
    grid-template-columns: 1fr;
  }

  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .runtime-tags {
    justify-content: flex-start;
  }

  .task-panel {
    padding: 20px;
  }

  .history-item {
    grid-template-columns: 1fr;
  }

  .history-side {
    justify-items: start;
  }
}

@media (max-width: 680px) {
  .capability-strip,
  .source-grid,
  .preset-grid {
    grid-template-columns: 1fr;
  }

  .submit-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
