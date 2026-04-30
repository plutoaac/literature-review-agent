<template>
  <div class="workspace">
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

      <div class="runtime-tags">
        <el-tag effect="plain" type="success">DeepSeek</el-tag>
        <el-tag effect="plain">Semantic Scholar</el-tag>
        <el-tag effect="plain" type="info">arXiv</el-tag>
      </div>
    </header>

    <main class="workspace-grid">
      <section class="task-panel">
        <div class="section-heading">
          <div>
            <span class="eyebrow">Task setup</span>
            <h2>创建综述任务</h2>
            <p>输入研究主题后，系统会自动扩展检索词、筛选论文并生成综述。</p>
          </div>
        </div>

        <div class="capability-strip">
          <div v-for="item in capabilities" :key="item.title" class="capability-card">
            <el-icon><component :is="item.icon" /></el-icon>
            <div>
              <strong>{{ item.title }}</strong>
              <span>{{ item.desc }}</span>
            </div>
          </div>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          class="task-form"
        >
          <el-form-item label="研究主题" prop="topic">
            <el-input
              v-model="form.topic"
              placeholder="例如：Retrieval Augmented Generation for Question Answering"
              :disabled="loading"
              clearable
            />
          </el-form-item>

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

      <aside class="insight-panel">
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
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createTask, runTask } from '../api.js'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const examples = [
  'Retrieval Augmented Generation',
  'LLM Hallucination Detection',
  'Multimodal Large Language Models'
]

const languageOptions = [
  { label: '中文', value: 'zh' },
  { label: 'English', value: 'en' }
]

const paperPresets = [5, 10, 15, 20, 30]

const capabilities = [
  { icon: 'Search', title: '双源检索', desc: '覆盖论文摘要与引用信息' },
  { icon: 'DataAnalysis', title: '相关性排序', desc: '关键词、引用数与年份综合评分' },
  { icon: 'Document', title: '引用校验', desc: '约束生成内容只引用候选论文' }
]

const pipeline = [
  { index: '01', name: 'Query', desc: '扩展主题关键词与检索式' },
  { index: '02', name: 'Search', desc: '检索并合并学术论文' },
  { index: '03', name: 'Rank', desc: '按相关性与影响力排序' },
  { index: '04', name: 'Read', desc: '抽取问题、方法和贡献' },
  { index: '05', name: 'Write', desc: '生成综述并校验引用' }
]

const sourceCards = [
  { name: '文献来源', value: '2', desc: 'Semantic Scholar + arXiv' },
  { name: '生成模型', value: 'DeepSeek', desc: 'OpenAI-compatible Chat API' },
  { name: '存储状态', value: 'Enabled', desc: '任务、论文与结果持久化' },
  { name: '排序方式', value: 'Hybrid', desc: '轻量可解释评分策略' }
]

const form = reactive({
  topic: '',
  yearRange: ['2020', '2024'],
  paperLimit: 10,
  language: 'zh'
})

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

const useExample = (topic) => {
  form.topic = topic
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true

    try {
      const [yearFrom, yearTo] = form.yearRange

      const taskData = {
        topic: form.topic,
        year_from: parseInt(yearFrom),
        year_to: parseInt(yearTo),
        paper_limit: form.paperLimit,
        language: form.language
      }

      const response = await createTask(taskData)
      const taskId = response.data.task_id

      ElMessage.success('任务已创建，正在启动工作流')

      await runTask(taskId)

      router.push(`/result/${taskId}`)
    } catch (error) {
      console.error('创建任务失败:', error)
      const message = error?.response?.data?.detail || '创建任务失败，请检查后端服务和配置'
      ElMessage.error(message)
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.workspace {
  min-height: 100vh;
  padding: 28px;
  background:
    linear-gradient(rgba(15, 118, 110, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.035) 1px, transparent 1px),
    linear-gradient(180deg, #eef8fb 0, #f7f9fc 310px, #f7f9fc 100%);
  background-size: 28px 28px, 28px 28px, auto;
  color: #172033;
}

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
