"""
应用配置管理模块

使用 pydantic-settings 从 .env 文件或环境变量自动加载配置。
配置项包括：
- LLM 服务提供商配置（DeepSeek / Minimax）
- 数据库连接串
- API 密钥等敏感信息

使用方式：
    settings = get_settings()
    print(settings.database_url)
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用配置类，继承自 pydantic BaseSettings

    配置项优先级：环境变量 > .env 文件 > 类中定义的默认值
    """

    # LLM 服务提供商，支持 "deepseek" 或 "minimax"
    llm_provider: str = "deepseek"

    # DeepSeek API 配置（国内大模型，性价比高）
    deepseek_api_key: str = ""                      # API 密钥，从 DeepSeek 控制台获取
    deepseek_base_url: str = "https://api.deepseek.com"  # API 基础地址
    deepseek_model: str = "deepseek-chat"            # 使用的模型名称

    # Minimax API 配置（兼容 OpenAI 接口格式）
    minimax_api_key: str = ""
    minimax_base_url: str = ""
    minimax_model: str = ""

    # MySQL 数据库连接串（格式：mysql+pymysql://用户名:密码@主机:端口/数据库名）
    database_url: str = "mysql+pymysql://root:password@localhost:3306/literature_review"

    class Config:
        # 从 .env 文件加载配置（相对于工作目录）
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 忽略 .env 中未在 Settings 中定义的字段（避免报错）
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置单例（使用 lru_cache 缓存，避免重复读取 .env 文件）

    Returns:
        Settings: 配置对象实例
    """
    return Settings()
