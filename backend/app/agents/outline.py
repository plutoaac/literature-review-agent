import logging
from typing import Dict, List
from app.services.llm import get_llm_client, LLMProviderError
from app.utils.json_parser import JsonExtractionError, extract_json_object

logger = logging.getLogger(__name__)


class OutlineAgent:
    def __init__(self):
        self.llm = get_llm_client()

    async def run(
        self,
        categories: List[Dict],
        topic: str,
        output_language: str
    ) -> Dict:
        logger.info(f"OutlineAgent: Generating outline for topic '{topic}'")

        prompt = self._build_prompt(categories, topic, output_language)

        try:
            response = await self.llm.complete([
                {"role": "user", "content": prompt}
            ])

            outline = self._parse_response(response)
            logger.info("OutlineAgent: Outline generated successfully")
            return outline
        except LLMProviderError as e:
            logger.error(f"OutlineAgent LLM error: {e}")
            return self._fallback_outline(topic)

    def _build_prompt(
        self,
        categories: List[Dict],
        topic: str,
        output_language: str
    ) -> str:
        lang_instruction = (
            "请用中文回答" if output_language == "zh" else "Please answer in English"
        )

        categories_text = "\n".join([
            f"- {c['name']}: {c.get('description', '')} (包含论文 {c['paper_indices']})"
            for c in categories
        ])

        return f"""{lang_instruction}

你是一个学术综述大纲生成助手。请根据以下文献分类，为研究主题生成综述大纲。

研究主题：{topic}

文献分类：
{categories_text}

请生成一个层级结构的综述大纲，包含：
- 引言部分
- 各分类的主要内容
- 总结和未来方向

请用JSON格式输出，键是大纲标题，值是子章节（如果有）：
{{
    "1. 引言": {{
        "1.1 研究背景": null,
        "1.2 研究意义": null
    }},
    "2. [分类名称]": {{
        "2.1 技术方法": null,
        "2.2 应用场景": null
    }},
    "3. 总结与展望": {{
        "3.1 主要贡献总结": null,
        "3.2 未来研究方向": null
    }}
}}

只输出JSON，不要有其他内容。
"""

    def _parse_response(self, response: str) -> Dict:
        try:
            return extract_json_object(response)
        except JsonExtractionError as e:
            logger.warning(f"Failed to parse outline response: {e}")
            return {}

    def _fallback_outline(self, topic: str) -> Dict:
        return {
            "1. 引言": {
                "1.1 研究背景": None,
                "1.2 研究意义": None
            },
            "2. 论文分类分析": {
                "2.1 主流方法": None,
                "2.2 技术对比": None
            },
            "3. 总结与展望": {
                "3.1 主要发现": None,
                "3.2 未来方向": None
            }
        }
