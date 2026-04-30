# 环境配置教程

## 1. Python

推荐 Python 3.10 或更高版本。

```bash
python --version
cd literature-review-agent/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

本项目不需要安装 torch、sentence-transformers 或 CUDA。

## 2. MySQL

本项目使用 MySQL 作为正式数据库。

### Ubuntu

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

### 创建数据库

```bash
mysql -u root -p
```

```sql
CREATE DATABASE literature_review CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'literature_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON literature_review.* TO 'literature_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

`.env` 中的连接串示例：

```env
DATABASE_URL=mysql+pymysql://literature_user:your_password@localhost:3306/literature_review
```

## 3. LLM API

复制配置文件：

```bash
cd backend
cp .env.example .env
```

### DeepSeek

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### Minimax

Minimax 按 OpenAI-compatible chat 接口配置：

```env
LLM_PROVIDER=minimax
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_BASE_URL=your_openai_compatible_base_url
MINIMAX_MODEL=your_model_name
```

如果 Minimax 后台给出的地址不是 OpenAI-compatible `/chat/completions` 形式，需要把 `MINIMAX_BASE_URL` 改成兼容网关地址。

## 4. 启动后端

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://localhost:8000/health
```

## 5. 启动前端

前端需要 Node.js 18+。服务器默认 Node 10 无法构建 Vite 5 项目。

```bash
node --version
cd frontend
npm install
npm run dev
```

## 6. 常见问题

### 数据库连接失败

检查 MySQL 是否运行、数据库是否创建、用户名密码是否和 `DATABASE_URL` 一致。

### LLM 调用失败

检查 API Key、模型名、Base URL、账户余额和服务器网络。

### 前端构建失败

如果看到 Vite 或 Node 版本错误，升级到 Node.js 18+ 后重新执行：

```bash
cd frontend
npm install
npm run build
```

### 文献排序为什么不用 embedding

用户要求轻依赖且不下载 torch。本项目使用关键词匹配、引用数、年份和来源权重做可解释排序；这对课程设计演示更稳定，也不会依赖某个聊天模型是否提供 embedding endpoint。
