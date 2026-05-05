"""
LLM 客户端服务模块

封装 OpenAI 兼容的 LLM API 调用，支持 DeepSeek 和 Minimax 两个提供商。

核心特性：
1. 统一接口：DeepSeek 和 Minimax 都使用 OpenAI 兼容的 /chat/completions 接口
2. 自动重试：遇到 429（限流）或 5xx（服务端错误）时自动重试，指数退避
3. 配置校验：启动时检查 API Key、Base URL、Model 是否配置完整
4. 超时控制：单次请求 120 秒超时，避免长时间阻塞
"""

import logging
import asyncio
from typing import Dict, List

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProviderError(Exception):
    """LLM 服务异常：当 API 调用失败且重试耗尽时抛出"""
    pass


class OpenAICompatibleChatClient:
    """
    OpenAI 兼容的 LLM 聊天客户端

    支持所有兼容 OpenAI /chat/completions 接口的 LLM 服务（如 DeepSeek、Minimax）。
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
    ):
        """
        初始化 LLM 客户端

        Args:
            provider: 服务商标识（"deepseek" 或 "minimax"），用于日志和错误信息
            api_key: API 密钥
            base_url: API 基础地址（如 https://api.deepseek.com）
            model: 使用的模型名称（如 deepseek-chat）
        """
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")  # 移除末尾斜杠，避免拼接 URL 时出现双斜杠
        self.model = model

        # 校验必填配置项，缺失时抛出明确的错误信息
        missing = []
        if not self.api_key:
            missing.append(f"{provider.upper()}_API_KEY")
        if not self.base_url:
            missing.append(f"{provider.upper()}_BASE_URL")
        if not self.model:
            missing.append(f"{provider.upper()}_MODEL")
        if missing:
            raise LLMProviderError(
                f"Missing LLM configuration for {provider}: {', '.join(missing)}"
            )

    async def complete(self, messages: List[Dict], **kwargs) -> str:
        """
        调用 LLM 聊天补全接口

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            **kwargs: 可选参数
                - max_retries: 最大重试次数（默认 2）
                - temperature: 温度参数（默认 0.7）
                - max_tokens: 最大生成 token 数（默认 4096）

        Returns:
            LLM 生成的文本内容

        Raises:
            LLMProviderError: 当所有重试都失败时抛出
        """
        max_retries = kwargs.get("max_retries", 2)

        # 构建请求体（OpenAI 格式）
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        # 需要重试的 HTTP 状态码（限流 + 服务端错误）
        retry_statuses = {429, 500, 502, 503, 504}

        for attempt in range(max_retries + 1):
            try:
                # 每次请求创建新的 httpx 客户端（简单但非最优，适合课程设计）
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    # 提取 LLM 生成的文本（OpenAI 格式：choices[0].message.content）
                    return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code
                body = e.response.text[:300]  # 只取前 300 字符，避免日志过长
                logger.warning(
                    "%s API HTTP error %s on attempt %s/%s: %s",
                    self.provider,
                    status_code,
                    attempt + 1,
                    max_retries + 1,
                    body,
                )
                # 非重试状态码或已用完重试次数，直接抛出异常
                if status_code not in retry_statuses or attempt >= max_retries:
                    raise LLMProviderError(f"{self.provider} API error: {status_code}")
            except (httpx.TimeoutException, httpx.RequestError) as e:
                # 网络超时或连接错误，也进行重试
                last_error = e
                logger.warning(
                    "%s API request failed on attempt %s/%s: %s",
                    self.provider,
                    attempt + 1,
                    max_retries + 1,
                    e,
                )
                if attempt >= max_retries:
                    raise LLMProviderError(f"{self.provider} API error: {e}")
            except Exception as e:
                # 其他未知异常，不重试直接抛出
                logger.error("%s API error: %s", self.provider, e)
                raise LLMProviderError(f"{self.provider} API error: {e}")

            # 指数退避：等待 2^attempt 秒（1s, 2s, 4s），最大 8 秒
            await asyncio.sleep(min(2 ** attempt, 8))

        raise LLMProviderError(f"{self.provider} API error: {last_error}")


def get_llm_client() -> OpenAICompatibleChatClient:
    """
    工厂函数：根据配置创建对应的 LLM 客户端实例

    根据 settings.llm_provider 的值（"deepseek" 或 "minimax"）创建客户端。
    每次调用都会创建新实例（非单例），适用于 Agent 内部使用。

    Returns:
        配置好的 OpenAICompatibleChatClient 实例

    Raises:
        LLMProviderError: 不支持的 LLM 提供商
    """
    provider = (settings.llm_provider or "deepseek").lower()

    if provider == "deepseek":
        return OpenAICompatibleChatClient(
            provider="deepseek",
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )

    if provider == "minimax":
        return OpenAICompatibleChatClient(
            provider="minimax",
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
            model=settings.minimax_model,
        )

    raise LLMProviderError(
        f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. Use 'deepseek' or 'minimax'."
    )
