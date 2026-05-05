# 科研文献综述 Agent 项目讲解

## 项目定位

这是一个面向课程设计和作品集展示的轻量级 AI 应用。用户输入研究主题后，系统自动完成学术文献检索、相关性排序、论文摘要阅读、结构化归纳、综述撰写和引用校验，最终输出可导出的 Markdown 综述。

项目的核心价值不是简单调用大模型，而是把外部文献数据源、任务编排、数据库持久化、前端可视化和 LLM 生成能力串成一个可演示的闭环。

## 架构概览

```text
Vue 工作台
  |
FastAPI API
  |
MySQL 任务与结果持久化
  |
ReviewWorkflow
  |
Query -> Search -> Rank -> Read -> Organize -> Outline -> RAG -> Write -> Citation
  |
DeepSeek / Minimax API + arXiv / OpenAlex / Semantic Scholar
```

## Agent 流程

1. QueryAgent：根据研究主题扩展关键词和检索式。
2. SearchAgent：优先从 arXiv 检索论文，并使用 OpenAlex / Semantic Scholar 补充结果。
3. RankAgent：按关键词匹配、引用数、年份和来源权重排序。
4. ReadAgent：并发分析论文摘要，抽取问题、方法、贡献、局限和数据集。
5. OrganizeAgent：把论文按研究方向分组，生成对比表和主题总结。
6. OutlineAgent：根据分类结果生成综述大纲。
7. LightweightRAG：把论文摘要和结构化分析切成证据片段，按大纲章节召回相关 evidence。
8. WriteAgent：基于召回证据生成完整综述正文。
9. CitationAgent：校验正文引用编号是否对应真实论文。

## 技术亮点

- 轻依赖：不使用 torch、sentence-transformers 或 CUDA，适合普通服务器部署。
- MySQL 持久化：任务、论文和结果可追踪，便于课堂演示和后续扩展。
- 配置化 LLM：支持 DeepSeek 和 Minimax 的 OpenAI-compatible Chat API。
- 检索增强生成：先检索真实论文，再基于文献信息生成综述，降低凭空生成风险。
- 轻量 RAG 证据链：不依赖本地 embedding，用关键词召回把 evidence 与综述章节绑定。
- 可解释排序：用关键词、引用量、年份和来源权重打分，便于向老师或面试官说明。
- 后台任务执行：前端创建任务后轮询状态，用户能看到 Agent 阶段进度。
- 鲁棒性处理：LLM 调用有重试，JSON 输出支持 Markdown 包裹和前后说明文本。

## 面试可以怎么讲

可以这样介绍：

> 我做了一个科研文献综述自动生成 Agent。它不是单纯把用户问题发给大模型，而是先通过 arXiv、OpenAlex 和 Semantic Scholar 检索真实论文，再做轻量相关性排序和结构化阅读，然后构建 RAG 证据片段库，按综述章节召回 evidence 后再生成正文，最后做引用校验。后端用 FastAPI 和 MySQL，前端用 Vue3 和 Element Plus，LLM 接 DeepSeek 或 Minimax。项目重点是完整 AI 应用闭环和可解释的工程实现。

如果面试官问为什么不用向量模型，可以回答：

> 课程设计目标是轻量部署，用户机器不希望安装 torch 或 CUDA。所以我没有强依赖本地 embedding，而是用了可解释的启发式排序。这样部署更稳定，也避免外部 chat 模型没有 embeddings endpoint 时出现不可控降级。后续如果条件允许，可以把 Minimax embedding 或其他向量服务作为可选模块接入。

如果面试官问 RAG 在哪里，可以回答：

> 本项目的 RAG 不是重型向量库版本，而是轻量 evidence-based RAG。系统先从真实论文中抽取标题、摘要、研究问题、方法、贡献和局限等证据片段；写作前根据综述大纲的每个章节做关键词召回，把最相关的 evidence 放进 prompt；生成时要求优先依据这些证据，并且引用必须使用已有 paper_id。这样可以在不安装 torch 和向量数据库的情况下体现检索增强生成。

如果面试官问 Agent 体现在哪里，可以回答：

> 我把任务拆成多个职责明确的 Agent：Query 负责检索式扩展，Search 负责数据获取，Rank 负责筛选排序，Read 负责结构化阅读，Organize 负责归纳分类，Outline 和 Write 负责生成内容，Citation 负责校验引用。每个 Agent 输入输出明确，便于调试和替换。

## 当前边界

- arXiv、OpenAlex 和 Semantic Scholar 覆盖面有限，不能完全等价于人工检索全部数据库。
- Google Scholar 没有官方稳定 API，直接爬取有封禁和合规风险，因此当前没有强接。
- 论文分析主要基于标题和摘要，没有解析 PDF 全文。
- 生成结果仍需人工校对，尤其是引用表达和学术细节。

## 后续优化路线

- 接入 PDF 下载与正文解析，支持更细粒度的证据抽取。
- 增加任务历史列表、复跑、删除和结果对比。
- 加入可选向量检索模块，用外部 embedding 服务提升排序质量。
- 引入 Celery 或 RQ，把后台任务从 FastAPI 进程中拆出去。
- 增加用户登录和 API key 管理，支持多人课程演示。
- 为核心服务补充单元测试和端到端演示脚本。
