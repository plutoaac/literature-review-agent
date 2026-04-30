<template>
  <div class="result-page">
    <header class="result-topbar">
      <div>
        <span class="eyebrow">Review task</span>
        <h1>综述生成结果</h1>
        <p>Task ID: {{ taskId }}</p>
      </div>
      <div class="topbar-actions">
        <el-tag :type="statusType" size="large">{{ statusText }}</el-tag>
        <el-button @click="goHome">
          <el-icon><House /></el-icon>
          返回工作台
        </el-button>
      </div>
    </header>

    <main class="result-layout">
      <section class="status-panel">
        <div class="phase-head">
          <div>
            <h2>{{ status === 'completed' ? '任务已完成' : '任务进度' }}</h2>
            <p v-if="currentPhase">当前阶段：{{ currentPhase }}</p>
            <p v-else>等待后端工作流更新状态</p>
          </div>
          <el-button v-if="status !== 'completed'" type="primary" plain @click="refreshStatus">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <el-steps :active="activeStep" finish-status="success" process-status="process" align-center>
          <el-step v-for="step in phaseSteps" :key="step.key" :title="step.label" />
        </el-steps>

        <el-progress
          :percentage="progress"
          :status="progressStatus"
          :stroke-width="14"
          class="phase-progress"
        />

        <el-alert
          v-if="errorMessage"
          type="error"
          :title="errorMessage"
          :closable="false"
          show-icon
          class="error-alert"
        />
      </section>

      <section v-if="status === 'completed' && result" class="summary-grid">
        <div v-for="card in summaryCards" :key="card.label" class="metric-card">
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <p>{{ card.detail }}</p>
        </div>
      </section>

      <section v-if="status === 'completed' && result" class="content-panel">
        <div class="panel-toolbar">
          <div>
            <h2>交付内容</h2>
            <p>正文、证据论文、结构化分析与引用校验</p>
          </div>
          <el-button type="primary" @click="handleExport" :loading="exporting">
            <el-icon><Download /></el-icon>
            导出 Markdown
          </el-button>
        </div>

        <el-tabs v-model="activeTab" class="result-tabs">
          <el-tab-pane label="综述正文" name="content">
            <article class="document-view">
              <template v-for="(block, index) in renderedBlocks" :key="index">
                <component
                  v-if="block.type === 'heading'"
                  :is="block.tag"
                >
                  {{ block.text }}
                </component>
                <p v-else>
                  <template v-for="(part, partIndex) in block.parts" :key="partIndex">
                    <span v-if="part.type === 'citation'" class="citation">[{{ part.text }}]</span>
                    <span v-else>{{ part.text }}</span>
                  </template>
                </p>
              </template>
            </article>
          </el-tab-pane>

          <el-tab-pane label="论文证据" name="papers">
            <div class="source-strip">
              <div v-for="item in sourceSummary" :key="item.source">
                <span>{{ formatSource(item.source) }}</span>
                <strong>{{ item.count }}</strong>
              </div>
            </div>

            <el-table :data="result.papers" stripe class="paper-table">
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

          <el-tab-pane label="引用校验" name="citations">
            <el-alert
              v-if="result.invalid_citations && result.invalid_citations.length === 0"
              type="success"
              title="所有引用均有效"
              :closable="false"
              show-icon
              class="citation-alert"
            />
            <el-alert
              v-else-if="result.invalid_citations && result.invalid_citations.length > 0"
              type="warning"
              :title="`存在 ${result.invalid_citations.length} 个无效引用`"
              :closable="false"
              show-icon
              class="citation-alert"
            />
            <pre class="citation-report">{{ result.citation_report }}</pre>
          </el-tab-pane>
        </el-tabs>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTaskStatus, getTaskResult, exportMarkdown } from '../api.js'

const props = defineProps({
  taskId: {
    type: String,
    required: true
  }
})

const router = useRouter()

const status = ref('pending')
const currentPhase = ref('')
const progress = ref(0)
const errorMessage = ref('')
const result = ref(null)
const activeTab = ref('content')
const exporting = ref(false)

let pollInterval = null

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

const statusText = computed(() => {
  const map = {
    'pending': '等待开始',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status.value] || status.value
})

const statusType = computed(() => {
  const map = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status.value] || 'info'
})

const progressStatus = computed(() => {
  if (status.value === 'failed') return 'exception'
  if (status.value === 'completed') return 'success'
  return null
})

const activeStep = computed(() => {
  if (status.value === 'completed') return phaseSteps.length
  const index = phaseSteps.findIndex((step) => step.key === currentPhase.value)
  return index >= 0 ? index : 0
})

const sourceSummary = computed(() => {
  const counts = {}
  const papers = result.value?.papers || []
  papers.forEach((paper) => {
    const source = paper.source || 'unknown'
    counts[source] = (counts[source] || 0) + 1
  })
  return Object.entries(counts).map(([source, count]) => ({ source, count }))
})

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
      label: '有效引用',
      value: valid.length,
      detail: invalid.length ? `${invalid.length} 个待核查` : '引用校验通过'
    },
    {
      label: '任务状态',
      value: statusText.value,
      detail: currentPhase.value || 'Done'
    }
  ]
})

const renderedBlocks = computed(() => {
  if (!result.value || !result.value.content) return []

  const blocks = []
  const paragraphLines = []

  const pushParagraph = () => {
    if (!paragraphLines.length) return
    blocks.push({
      type: 'paragraph',
      parts: parseInline(paragraphLines.join(' '))
    })
    paragraphLines.length = 0
  }

  result.value.content.split(/\r?\n/).forEach((line) => {
    const trimmed = line.trim()
    if (!trimmed) {
      pushParagraph()
      return
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      pushParagraph()
      blocks.push({
        type: 'heading',
        tag: `h${heading[1].length}`,
        text: heading[2]
      })
      return
    }

    paragraphLines.push(trimmed)
  })

  pushParagraph()
  return blocks
})

const parseInline = (text) => {
  const parts = []
  const citationPattern = /\[paper_(\d+)\]/g
  let cursor = 0
  let match

  while ((match = citationPattern.exec(text)) !== null) {
    if (match.index > cursor) {
      parts.push({ type: 'text', text: text.slice(cursor, match.index) })
    }
    parts.push({ type: 'citation', text: match[1] })
    cursor = match.index + match[0].length
  }

  if (cursor < text.length) {
    parts.push({ type: 'text', text: text.slice(cursor) })
  }

  return parts
}

const formatSource = (source) => {
  const map = {
    semantic_scholar: 'Semantic Scholar',
    arxiv: 'arXiv'
  }
  return map[source] || source || 'Unknown'
}

const sourceTagType = (source) => {
  if (source === 'semantic_scholar') return 'success'
  if (source === 'arxiv') return 'info'
  return 'warning'
}

const formatScore = (score) => {
  if (score === null || score === undefined) return '-'
  return Number(score).toFixed(3)
}

const fetchStatus = async () => {
  try {
    const response = await getTaskStatus(props.taskId)
    const data = response.data

    status.value = data.status
    currentPhase.value = data.current_phase || ''
    progress.value = data.progress || 0
    errorMessage.value = data.error_message || ''

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

const fetchResult = async () => {
  try {
    const response = await getTaskResult(props.taskId)
    result.value = response.data
  } catch (error) {
    console.error('获取结果失败:', error)
    ElMessage.error('获取任务结果失败')
  }
}

const handleExport = async () => {
  exporting.value = true
  try {
    const response = await exportMarkdown(props.taskId)
    const content = response.data.content
    const filename = response.data.filename

    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const openPaper = (url) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

const goHome = () => {
  router.push('/')
}

const startPolling = () => {
  fetchStatus()
  pollInterval = setInterval(fetchStatus, 3000)
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const refreshStatus = () => {
  fetchStatus()
}

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.result-page {
  min-height: 100vh;
  padding: 28px;
  background:
    linear-gradient(180deg, rgba(224, 242, 254, 0.5), rgba(248, 250, 252, 0) 280px),
    #f6f8fb;
  color: #172033;
}

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

.result-tabs {
  margin-top: 8px;
}

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

.source-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

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
