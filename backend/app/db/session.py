"""
数据库会话管理模块

负责：
1. 创建 SQLAlchemy 引擎（Engine）：管理数据库连接池
2. 创建会话工厂（SessionLocal）：每次请求创建一个数据库会话
3. 初始化数据库表结构（init_db）：根据 ORM 模型自动建表
4. 提供依赖注入函数（get_db）：FastAPI 路由中通过 Depends(get_db) 获取会话
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings
from app.db.models import Base

# 读取数据库配置
settings = get_settings()

# 创建 SQLAlchemy 引擎
# pool_pre_ping=True：每次从连接池取连接时先 ping 一下，自动剔除断开的连接
# pool_recycle=3600：连接最大存活时间 1 小时，避免 MySQL 默认 8 小时超时导致连接失效
# echo=False：不打印 SQL 语句（生产环境建议关闭，开发时可设为 True）
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# 创建会话工厂
# autocommit=False：不自动提交事务（需要手动 db.commit()）
# autoflush=False：不自动 flush（需要手动 db.flush() 或 db.commit()）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    初始化数据库表结构

    根据 Base 中定义的所有 ORM 模型，在数据库中创建对应的表（如果不存在）。
    注意：此方法只能创建新表，不会修改已有表结构（如添加列）。
    如需修改表结构，应使用 Alembic 迁移工具。
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    数据库会话依赖注入函数（FastAPI 专用）

    使用方式：
        @router.get("/example")
        async def example(db: Session = Depends(get_db)):
            result = db.query(Task).all()

    工作原理：
    1. 创建一个新的数据库会话
    2. 通过 yield 将会话提供给路由函数
    3. 路由函数执行完毕后（无论成功或异常），在 finally 中关闭会话

    这种模式确保每次请求使用独立的会话，避免连接泄漏。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
