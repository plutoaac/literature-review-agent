"""
FastAPI 应用入口模块

本模块是文献综述生成系统的后端入口，负责：
1. 创建 FastAPI 应用实例并配置中间件（CORS 跨域支持）
2. 注册 API 路由
3. 在启动时初始化数据库表结构
4. 提供前端静态文件托管（SPA 单页应用支持）
5. 提供健康检查接口
"""

import logging
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.db.session import init_db
from app.api.routes import router

# 配置日志格式，输出到标准输出（stdout），方便容器化部署时收集日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 读取全局配置（从 .env 文件或环境变量加载）
settings = get_settings()

# 前端构建产物目录：backend/app/main.py -> backend/ -> literature-review-agent/ -> frontend/dist
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# 创建 FastAPI 应用实例，自动生成 OpenAPI 文档（访问 /docs 查看）
app = FastAPI(
    title="Literature Review Agent",
    description="AI-powered academic literature review generation system",
    version="1.0.0"
)

# CORS 中间件：允许前端跨域访问后端 API
# allow_origins=["*"] 表示允许所有来源（开发阶段使用，生产环境应限制为具体域名）
# allow_credentials=True 允许携带 Cookie 等凭证信息
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由（所有以 /api/tasks 开头的接口）
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """
    应用启动事件：自动创建数据库表结构

    如果数据库连接失败，应用仍会启动，但数据库相关操作会报错。
    这样做是为了让应用至少能响应健康检查请求，方便运维排查问题。
    """
    logger.info("Initializing database...")
    try:
        init_db()  # 根据 ORM 模型自动创建所有表（如果不存在）
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Application will continue but database operations may fail")


@app.get("/")
async def root():
    """
    根路径：优先返回前端 index.html（SPA 单页应用入口）
    如果前端未构建，则返回 JSON 格式的系统信息
    """
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Literature Review Agent",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """
    健康检查接口：供负载均衡器或监控系统调用，判断服务是否存活
    注意：此处不检查数据库连接状态，仅表示 FastAPI 进程正常运行
    """
    return {"status": "healthy"}


# 挂载前端静态资源目录（JS/CSS/图片等），路径 /assets -> frontend/dist/assets
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


@app.get("/{full_path:path}")
async def frontend_fallback(full_path: str):
    """
    前端路由兜底：Vue Router 使用 history 模式，刷新页面时需要后端返回 index.html

    工作原理：
    - 如果请求路径以 api/ 开头，说明是不存在的 API 接口，返回 404
    - 否则返回前端 index.html，让 Vue Router 处理前端路由
    """
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Literature Review Agent",
        "version": "1.0.0",
        "status": "running"
    }


# 直接运行此文件时启动 uvicorn 开发服务器（监听所有网卡，端口 8000）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
