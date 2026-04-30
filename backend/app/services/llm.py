import logging
from typing import Dict, List

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProviderError(Exception):
    pass


class OpenAICompatibleChatClient:
    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

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

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            body = e.response.text[:300]
            logger.error("%s API HTTP error %s: %s", self.provider, e.response.status_code, body)
            raise LLMProviderError(f"{self.provider} API error: {e.response.status_code}")
        except Exception as e:
            logger.error("%s API error: %s", self.provider, e)
            raise LLMProviderError(f"{self.provider} API error: {e}")


def get_llm_client() -> OpenAICompatibleChatClient:
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
