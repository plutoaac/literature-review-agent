from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "deepseek"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    minimax_api_key: str = ""
    minimax_base_url: str = ""
    minimax_model: str = ""

    database_url: str = "mysql+pymysql://root:password@localhost:3306/literature_review"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
