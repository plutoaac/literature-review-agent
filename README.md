# Literature Review Agent

科研文献综述自动生成 Agent 课程设计项目。用户输入研究主题后，系统自动检索论文、筛选排序、结构化分析，并生成可导出的 Markdown 综述。

## 功能

- 研究主题理解与检索式扩展
- 学术文献检索：Semantic Scholar + arXiv
- 轻量启发式文献排序：关键词匹配、引用数、年份、来源权重
- 论文摘要结构化分析
- 文献分类与对比
- 综述大纲生成
- 综述正文生成
- 引用编号校验
- Markdown 导出

## 界面展示

### 工作台首页

![工作台首页](docs/images/workspace-home.png)

### 任务执行进度

![任务执行进度](docs/images/task-progress.png)

### 综述生成结果

![综述生成结果](docs/images/review-result.png)

## 技术栈

### 后端

- Python 3.10+
- FastAPI
- SQLAlchemy + MySQL
- DeepSeek 或 Minimax API
- httpx / arxiv

### 前端

- Vue 3
- Vite
- Element Plus
- Axios

## 设计说明

本项目面向课程设计演示，重点是流程完整、依赖轻、可解释。

- 数据库固定使用 MySQL，不切 SQLite。
- 不需要 torch、sentence-transformers 或 CUDA。
- 生成能力通过外部 LLM API 完成。
- 文献排序不依赖 embedding API，避免 DeepSeek chat 模型没有 embeddings endpoint 时静默降级导致结果不可解释。
- 当前工作流是项目内自定义 Agent 串联，便于课程设计讲解和调试。

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 5.7+ 或 8.0+
- DeepSeek API Key 或 Minimax API Key

### 2. 后端安装

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 MySQL

确保 MySQL 服务运行，并创建数据库：

```sql
CREATE DATABASE literature_review CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

复制环境变量文件：

```bash
cp .env.example .env
```

编辑 `backend/.env`：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

DATABASE_URL=mysql+pymysql://user:password@localhost:3306/literature_review
```

如果使用 Minimax：

```env
LLM_PROVIDER=minimax
MINIMAX_API_KEY=your_minimax_api_key_here
MINIMAX_BASE_URL=your_openai_compatible_base_url
MINIMAX_MODEL=your_model_name
```

### 4. 启动后端

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000/docs` 查看 API 文档。

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 Vite 输出的本地地址。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks/{id}` | 获取任务状态 |
| POST | `/api/tasks/{id}/run` | 启动任务 |
| GET | `/api/tasks/{id}/result` | 获取结果 |
| GET | `/api/tasks/{id}/export` | 导出 Markdown |

## 项目结构

```text
literature-review-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── workflow.py
│   │   ├── api/
│   │   ├── agents/
│   │   ├── db/
│   │   └── services/
│   └── requirements.txt
├── frontend/
│   └── src/
├── README.md
└── SETUP.md
```
