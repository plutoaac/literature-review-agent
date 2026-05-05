<!--
  Result.vue — 综述结果展示页面

  页面结构：
  1. 顶部导航栏：任务 ID + 状态标签 + 返回按钮
  2. 任务进度面板：步骤条 + 进度条 + 错误提示
  3. 统计卡片（任务完成后显示）：论文数、分析数、RAG 证据数、引用数
  4. 内容面板（Tab 切换）：
     - 综述正文：Markdown 渲染（标题 + 段落 + 引用高亮）
     - RAG 证据链：按章节展示召回的证据片段
     - 论文证据：论文列表表格（可展开查看摘要）
     - 结构化分析：论文分析结果表格
     - 引用校验：有效/无效引用报告

  轮询机制：
  - 页面加载后每 3 秒轮询 getTaskStatus API
  - 任务完成/失败后停止轮询
  - 完成后自动获取结果数据
-->
<template>
  <div class="result-page">
    <!-- ========== 顶部导航栏 ========== -->
    <header class="result-topbar">
      <div>
        <span class="eyebrow">Review task</span>
        <h1>综述生成结果</h1>
        <p>Task ID: {{ taskId }}</p>
      </div>
      <div class="topbar-actions">
        <!-- 状态标签（pending=信息, running=警告, completed=成功, failed=危险） -->
        <el-tag :type="statusType" size="large">{{ statusText }}</el-tag>
        <el-button @click="goHome">
          <el-icon><House /></el-icon>
          返回工作台
        </el-button>
      </div>
    </header>

    <main class="result-layout">
      <!-- ========== 任务进度面板 ========== -->
      <section class="status-panel">
        <div class="phase-head">
          <div>
            <h2>{{ status === 'completed' ? '任务已完成' : '任务进度' }}</h2>
            <p v-if="currentPhase">当前阶段：{{ currentPhase }}</p>
            <p v-else>等待后端工作流更新状态</p>
          </div>
          <!-- 手动刷新按钮（非完成状态时显示） -->
          <el-button v-if="status !== 'completed'" type="primary" plain @click="refreshStatus">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <!-- 步骤条：展示 8 个 Agent 阶段 -->
        <el-steps :active="activeStep" finish-status="success" process-status="process" align-center>
          <el-step v-for="step in phaseSteps" :key="step.key" :title="step.label" />
        </el-steps>

        <!-- 进度条 -->
        <el-progress
          :percentage="progress"
          :status="progressStatus"
          :stroke-width="14"
          class="phase-progress"
        />

        <!-- 错误提示（任务失败时显示） -->
        <el-alert
          v-if="errorMessage"
          type="error"
          :title="errorMessage"
          :closable="false"
          show-icon
          class="error-alert"
        />
      </section>

      <!-- ========== 统计卡片（任务完成后显示） ========== -->
      <section v-if="status === 'completed' && result" class="summary-grid">
        <div v-for="card in summaryCards" :key="card.label" class="metric-card">
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <p>{{ card.detail }}</p>
        </div>
      </section>

      <!-- ========== 内容面板（Tab 切换） ========== -->
      <section v-if="status === 'completed' && result" class="content-panel">
        <div class="panel-toolbar">
          <div>
            <h2>交付内容</h2>
            <p>正文、RAG 证据链、证据论文、结构化分析与引用校验</p>
          </div>
          <!-- 导出 Markdown 按钮 -->
          <el-button type="primary" @click="handleExport" :loading="exporting">
            <el-icon><Download /></el-icon>
            导出 Markdown
          </el-button>
        </div>

        <el-tabs v-model="activeTab" class="result-tabs">
          <!-- ===== Tab 1：综述正文 ===== -->
          <el-tab-pane label="综述正文" name="content">
            <article class="document-view" v-html="renderedContent">
            </article>
          </el-tab-pane>

          <!-- ===== Tab 2：RAG 证据链 ===== -->
          <el-tab-pane label="RAG 证据链" name="rag">
            <!-- RAG 概览统计 -->
            <div class="rag-overview">
              <div>
                <span>召回章节</span>
                <strong>{{ ragEvidence.length }}</strong>
              </div>
              <div>
                <span>证据片段</span>
                <strong>{{ ragEvidenceCount }}</strong>
              </div>
              <div>
                <span>生成策略</span>
                <strong>Evidence-first</strong>
              </div>
            </div>

            <!-- 空状态 -->
            <el-empty
              v-if="ragEvidence.length === 0"
              description="暂无 RAG 证据链"
            />

            <!-- 证据列表（按章节组织） -->
            <div v-else class="rag-list">
              <section
                v-for="section in ragEvidence"
                :key="section.section"
                class="rag-section"
              >
                <div class="rag-section-head">
                  <div>
                    <span class="rag-label">Review section</span>
                    <h3>{{ section.section }}</h3>
                  </div>
                  <el-tag effect="plain">{{ section.evidence?.length || 0 }} 条证据</el-tag>
                </div>

                <!-- 证据卡片网格 -->
                <div class="rag-evidence-grid">
                  <article
                    v-for="item in section.evidence"
                    :key="item.chunk_id"
                    class="rag-evidence-card"
                  >
                    <div class="evidence-meta">
                      <el-tag size="small" type="success" effect="plain">
                        {{ item.paper_id }}
                      </el-tag>
                      <el-tag size="small" type="info" effect="plain">
                        {{ formatEvidenceSection(item.section) }}
                      </el-tag>
                      <span>{{ formatScore(item.score) }}</span>
                    </div>
                    <h4>{{ item.title }}</h4>
                    <p>{{ item.text }}</p>
                  </article>
                </div>
              </section>
            </div>
          </el-tab-pane>

          <!-- ===== Tab 3：论文证据 ===== -->
          <el-tab-pane label="论文证据" name="papers">
            <!-- 来源统计 -->
            <div class="source-strip">
              <div v-for="item in sourceSummary" :key="item.source">
                <span>{{ formatSource(item.source) }}</span>
                <strong>{{ item.count }}</strong>
              </div>
            </div>

            <!-- 论文列表表格（可展开查看摘要） -->
            <el-table :data="result.papers" stripe class="paper-table">
              <!-- 展开行：显示论文摘要 -->
              <el-table-column type="expand">
                <template #default="{ row }">
                  <div class="abstract-box">
                    <strong>摘要</strong>
                    <p>{{ row.abstract || 'No abstract available.' }}</p>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="paper_index" label="#" width="56" />
              <el-table-column prop="title" label="标题" min-width="280" show-overflow-tooltip />
              <el-table-column label="来源" width="150">
                <template #default="{ row }">
                  <el-tag :type="sourceTagType(row.source)" effect="plain">
                    {{ formatSource(row.source) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="year" label="年份" width="80" />
              <el-table-column prop="citation_count" label="引用" width="90" />
              <el-table-column label="相关度" width="110">
                <template #default="{ row }">
                  {{ formatScore(row.relevance_score) }}
                </template>
              </el-table-column>
              <!-- 链接列：打开论文原始页面 -->
              <el-table-column label="链接" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.url"
                    size="small"
                    link
                    type="primary"
                    @click="openPaper(row.url)"
                  >
                    <el-icon><Link /></el-icon>
                    打开
                  </el-button>
                  <span v-else class="muted">无</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ===== Tab 4：结构化分析 ===== -->
          <el-tab-pane label="结构化分析" name="analysis">
            <el-table :data="result.analyses" stripe class="analysis-table">
              <el-table-column prop="paper_index" label="#" width="56" />
              <el-table-column prop="title" label="论文" min-width="220" show-overflow-tooltip />
              <el-table-column prop="problem" label="研究问题" min-width="220" show-overflow-tooltip />
              <el-table-column prop="method" label="方法" min-width="180" show-overflow-tooltip />
              <el-table-column label="分类" width="150">
                <template #default="{ row }">
                  <el-tag effect="plain">{{ row.category || 'General' }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ===== Tab 5：引用校验 ===== -->
          <el-tab-pane label="引用校验" name="citations">
            <!-- 全部有效时显示成功提示 -->
            <el-alert
              v-if="result.invalid_citations && result.invalid_citations.length === 0"
              type="success"
              title="所有引用均有效"
              :closable="false"
              show-icon
              class="citation-alert"
            />
            <!-- 存在无效引用时显示警告 -->
            <el-alert
              v-else-if="result.invalid_citations && result.invalid_citations.length > 0"
              type="warning"
              :title="`存在 ${result.invalid_citations.length} 个无效引用`"
              :closable="false"
              show-icon
              class="citation-alert"
            />
            <!-- 引用校验报告 -->
            <pre class="citation-report">{{ result.citation_report }}</pre>
          </el-tab-pane>
        </el-tabs>
      </section>
    </main>
  </div>
</template>

<script setup>
/**
 * 组合式 API：任务状态轮询 + 结果展示 + Markdown 导出
 *
 * 核心逻辑：
 * 1. 页面加载后启动轮询（每 3 秒查询任务状态）
 * 2. 任务完成后自动获取结果数据并停止轮询
 * 3. 用户可切换 Tab 查看不同维度的结果
 * 4. 支持导出 Markdown 文件到本地
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { getTaskStatus, getTaskResult, exportMarkdown } from '../api.js'

// 配置 marked：启用 GFM（GitHub Flavored Markdown）
marked.setOptions({
  gfm: true,
  breaks: true
})

// 接收路由参数（taskId 通过 props: true 自动传入）
const props = defineProps({
  taskId: {
    type: String,
    required: true
  }
})

const router = useRouter()

// ========== 响应式状态 ==========
const status = ref('pending')        // 任务状态：pending/running/completed/failed
const currentPhase = ref('')         // 当前执行阶段名称
const progress = ref(0)              // 进度百分比（0~100）
const errorMessage = ref('')         // 错误信息（任务失败时）
const result = ref(null)             // 综述结果数据
const activeTab = ref('content')     // 当前激活的 Tab
const exporting = ref(false)         // 导出加载状态

let pollInterval = null              // 轮询定时器（非响应式，不需要在模板中使用）
let pollAttempts = 0                 // 轮询尝试次数（用于退避策略）
const MAX_POLL_INTERVAL = 15000      // 最大轮询间隔（15 秒）

// 8 个 Agent 阶段定义（与步骤条对应）
const phaseSteps = [
  { key: 'QueryAgent', label: 'Query' },
  { key: 'SearchAgent', label: 'Search' },
  { key: 'RankAgent', label: 'Rank' },
  { key: 'ReadAgent', label: 'Read' },
  { key: 'OrganizeAgent', label: 'Organize' },
  { key: 'OutlineAgent', label: 'Outline' },
  { key: 'WriteAgent', label: 'Write' },
  { key: 'CitationCheckAgent', label: 'Citation' }
]

// ========== 计算属性 ==========
/** 状态文本映射 */
const statusText = computed(() => {
  const map = {
    'pending': '等待开始',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status.value] || status.value
})

/** 状态标签类型映射（Element Plus tag type） */
const statusType = computed(() => {
  const map = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status.value] || 'info'
})

/** 进度条状态（失败=异常, 完成=成功, 其他=默认） */
const progressStatus = computed(() => {
  if (status.value === 'failed') return 'exception'
  if (status.value === 'completed') return 'success'
  return null
})

/** 当前激活的步骤索引（用于 el-steps 组件） */
const activeStep = computed(() => {
  if (status.value === 'completed') return phaseSteps.length  // 完成时全部高亮
  const index = phaseSteps.findIndex((step) => step.key === currentPhase.value)
  return index >= 0 ? index : 0
})

/** 论文来源统计（Semantic Scholar vs arXiv） */
const sourceSummary = computed(() => {
  const counts = {}
  const papers = result.value?.papers || []
  papers.forEach((paper) => {
    const source = paper.source || 'unknown'
    counts[source] = (counts[source] || 0) + 1
  })
  return Object.entries(counts).map(([source, count]) => ({ source, count }))
})

/** RAG 证据链数据 */
const ragEvidence = computed(() => result.value?.rag_evidence || [])

/** RAG 证据片段总数 */
const ragEvidenceCount = computed(() => {
  return ragEvidence.value.reduce((total, section) => {
    return total + (section.evidence?.length || 0)
  }, 0)
})

/** 统计卡片数据 */
const summaryCards = computed(() => {
  const papers = result.value?.papers || []
  const analyses = result.value?.analyses || []
  const valid = result.value?.valid_citations || []
  const invalid = result.value?.invalid_citations || []
  return [
    {
      label: '论文证据',
      value: papers.length,
      detail: `${sourceSummary.value.length || 0} 个来源`
    },
    {
      label: '结构化分析',
      value: analyses.length,
      detail: '问题、方法、贡献'
    },
    {
      label: 'RAG 证据',
      value: ragEvidenceCount.value,
      detail: `${ragEvidence.value.length || 0} 个章节召回`
    },
    {
      label: '有效引用',
      value: valid.length,
      detail: invalid.length ? `${invalid.length} 个待核查` : '引用校验通过'
    }
  ]
})

/**
 * 综述正文渲染：使用 marked 库解析 Markdown
 *
 * 使用 marked 库替代手写解析器，支持完整的 Markdown 语法：
 * - 标题（h1-h6）
 * - 粗体/斜体
 * - 列表（有序/无序）
 * - 链接
 * - 代码块
 * - 引用块
 *
 * 引用标记 [paper_X] 通过 post-processing 转为高亮 span
 */
const renderedContent = computed(() => {
  if (!result.value || !result.value.content) return ''

  // 使用 marked 解析 Markdown 为 HTML
  let html = marked(result.value.content)

  // 后处理：将 [paper_X] 引用标记转为绿色高亮
  html = html.replace(
    /\[paper_(\d+)\]/g,
    '<span class="citation">[$1]</span>'
  )

  return html
})

// ========== 格式化工具函数 ==========

/** 来源名称格式化 */
const formatSource = (source) => {
  const map = {
    semantic_scholar: 'Semantic Scholar',
    arxiv: 'arXiv'
  }
  return map[source] || source || 'Unknown'
}

/** 来源标签颜色 */
const sourceTagType = (source) => {
  if (source === 'semantic_scholar') return 'success'
  if (source === 'arxiv') return 'info'
  return 'warning'
}

/** 评分格式化（保留 3 位小数） */
const formatScore = (score) => {
  if (score === null || score === undefined) return '-'
  return Number(score).toFixed(3)
}

/** RAG 证据 section 类型中文映射 */
const formatEvidenceSection = (section) => {
  const map = {
    abstract: '摘要',
    problem: '问题',
    method: '方法',
    contribution: '贡献',
    limitation: '局限'
  }
  return map[section] || section || '证据'
}

// ========== 数据获取 ==========

/** 获取任务状态（轮询调用） */
const fetchStatus = async () => {
  try {
    const response = await getTaskStatus(props.taskId)
    const data = response.data

    status.value = data.status
    currentPhase.value = data.current_phase || ''
    progress.value = data.progress || 0
    errorMessage.value = data.error_message || ''

    // 任务完成：获取结果并停止轮询
    if (status.value === 'completed') {
      await fetchResult()
      stopPolling()
    } else if (status.value === 'failed') {
      stopPolling()
    }
  } catch (error) {
    console.error('获取状态失败:', error)
    ElMessage.error('获取任务状态失败')
  }
}

/** 获取综述结果（任务完成后调用） */
const fetchResult = async () => {
  try {
    const response = await getTaskResult(props.taskId)
    result.value = response.data
  } catch (error) {
    console.error('获取结果失败:', error)
    ElMessage.error('获取任务结果失败')
  }
}

/** 导出 Markdown 文件（创建 Blob → 触发下载） */
const handleExport = async () => {
  exporting.value = true
  try {
    const response = await exportMarkdown(props.taskId)
    const content = response.data.content
    const filename = response.data.filename

    // 创建 Blob 并触发浏览器下载
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)  // 释放内存

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

/** 在新标签页打开论文链接 */
const openPaper = (url) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

/** 返回首页 */
const goHome = () => {
  router.push('/')
}

// ========== 轮询控制 ==========

/** 启动轮询（立即查询一次，然后递增间隔轮询） */
const startPolling = () => {
  fetchStatus()
  scheduleNextPoll()
}

/** 调度下一次轮询（指数退避：3s → 5s → 8s → 13s → 15s 封顶） */
const scheduleNextPoll = () => {
  pollAttempts++
  // 退避公式：min(3 * 1.6^(attempts-1), 15) 秒
  const interval = Math.min(3000 * Math.pow(1.6, pollAttempts - 1), MAX_POLL_INTERVAL)
  pollInterval = setTimeout(() => {
    fetchStatus()
    // 如果任务仍在运行，继续调度下一次
    if (status.value === 'running' || status.value === 'pending') {
      scheduleNextPoll()
    }
  }, interval)
}

/** 停止轮询 */
const stopPolling = () => {
  if (pollInterval) {
    clearTimeout(pollInterval)
    pollInterval = null
  }
  pollAttempts = 0  // 重置尝试次数
}

/** 手动刷新状态 */
const refreshStatus = () => {
  fetchStatus()
}

// ========== 生命周期钩子 ==========

// 页面挂载后启动轮询
onMounted(() => {
  startPolling()
})

// 页面卸载前停止轮询（防止内存泄漏）
onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
/* ========== 页面整体 ========== */
.result-page {
  min-height: 100vh;
  padding: 28px;
  background:
    linear-gradient(180deg, rgba(224, 242, 254, 0.5), rgba(248, 250, 252, 0) 280px),
    #f6f8fb;
  color: #172033;
}

/* ========== 顶部导航栏 ========== */
.result-topbar {
  max-width: 1220px;
  margin: 0 auto 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.eyebrow {
  display: block;
  margin-bottom: 6px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.result-topbar h1 {
  margin: 0;
  color: #111827;
  font-size: 26px;
}

.result-topbar p {
  margin: 6px 0 0;
  color: #667085;
  font-size: 13px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ========== 主内容区 ========== */
.result-layout {
  max-width: 1220px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.status-panel,
.content-panel,
.metric-card {
  background: #fff;
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
}

.status-panel,
.content-panel {
  padding: 22px;
}

/* ========== 进度面板 ========== */
.phase-head,
.panel-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.phase-head h2,
.panel-toolbar h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.phase-head p,
.panel-toolbar p {
  margin: 6px 0 0;
  color: #667085;
  font-size: 13px;
}

.phase-progress {
  margin-top: 18px;
}

.error-alert {
  margin-top: 16px;
}

/* ========== 统计卡片 ========== */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px;
}

.metric-card span {
  display: block;
  color: #667085;
  font-size: 13px;
  margin-bottom: 8px;
}

.metric-card strong {
  display: block;
  color: #111827;
  font-size: 26px;
  line-height: 1.1;
}

.metric-card p {
  margin: 8px 0 0;
  color: #667085;
  font-size: 13px;
}

/* ========== Tab 内容区 ========== */
.result-tabs {
  margin-top: 8px;
}

/* ========== 综述正文 ========== */
.document-view {
  max-height: 640px;
  overflow-y: auto;
  padding: 26px 30px;
  background: #fbfcfe;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  line-height: 1.85;
  font-size: 15px;
}

.document-view h1 {
  font-size: 24px;
  margin: 18px 0 12px;
  color: #111827;
}

.document-view h2 {
  font-size: 20px;
  margin: 18px 0 10px;
  color: #1f2937;
}

.document-view h3 {
  font-size: 16px;
  margin: 14px 0 8px;
  color: #344054;
}

.document-view p {
  margin: 9px 0;
  color: #344054;
  text-align: justify;
}

/* 引用标记样式（绿色高亮） */
.citation {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 5px;
  border-radius: 6px;
  background: #ecfdf5;
  color: #047857;
  font-weight: 700;
}

/* ========== RAG 证据链 ========== */
.source-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.rag-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.rag-overview div,
.rag-section,
.rag-evidence-card {
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  background: #fbfcfe;
}

.rag-overview div {
  padding: 14px 16px;
}

.rag-overview span,
.rag-label {
  display: block;
  color: #667085;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.rag-overview strong {
  display: block;
  margin-top: 6px;
  color: #111827;
  font-size: 22px;
}

.rag-list {
  display: grid;
  gap: 14px;
}

.rag-section {
  padding: 16px;
}

.rag-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}

.rag-section h3 {
  margin: 5px 0 0;
  color: #111827;
  font-size: 17px;
}

.rag-evidence-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.rag-evidence-card {
  padding: 14px;
}

.evidence-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 9px;
}

.evidence-meta span {
  color: #667085;
  font-size: 12px;
}

.rag-evidence-card h4 {
  margin: 0 0 8px;
  color: #111827;
  font-size: 14px;
  line-height: 1.45;
}

.rag-evidence-card p {
  margin: 0;
  color: #475467;
  line-height: 1.65;
  font-size: 13px;
}

/* ========== 论文来源统计 ========== */
.source-strip div {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  background: #fbfcfe;
}

.source-strip span {
  color: #667085;
  font-size: 13px;
}

.source-strip strong {
  color: #111827;
}

/* ========== 表格 ========== */
.paper-table,
.analysis-table {
  width: 100%;
}

.abstract-box {
  padding: 12px 18px;
  color: #344054;
  line-height: 1.7;
}

.abstract-box strong {
  display: block;
  margin-bottom: 6px;
  color: #111827;
}

.abstract-box p {
  margin: 0;
}

.muted {
  color: #98a2b3;
}

/* ========== 引用校验 ========== */
.citation-alert {
  margin-bottom: 14px;
}

.citation-report {
  margin: 0;
  background: #fbfcfe;
  border: 1px solid #edf1f7;
  padding: 16px;
  border-radius: 8px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.65;
  color: #344054;
}

/* ========== 响应式布局 ========== */
@media (max-width: 960px) {
  .result-page {
    padding: 18px;
  }

  .result-topbar,
  .phase-head,
  .panel-toolbar {
    flex-direction: column;
  }

  .topbar-actions {
    width: 100%;
    justify-content: space-between;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .rag-overview,
  .rag-evidence-grid {
    grid-template-columns: 1fr;
  }

  .document-view {
    padding: 18px;
  }
}

@media (max-width: 620px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
