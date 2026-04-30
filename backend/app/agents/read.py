import asyncio
import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError
from app.utils.json_parser import JsonExtractionError, extract_json_object

logger = logging.getLogger(__name__)


class ReadAgent:
    def __init__(self, max_concurrency: int = 4):
        self.llm = get_llm_client()
        self.max_concurrency = max_concurrency

    async def run(self, ranked_papers: List[Dict], output_language: str) -> List[Dict]:
        logger.info(f"ReadAgent: Analyzing {len(ranked_papers)} papers")

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def analyze_with_limit(paper: Dict) -> Dict:
            async with semaphore:
                return await self._analyze_paper(paper, output_language)

        analyses = await asyncio.gather(
            *[analyze_with_limit(paper) for paper in ranked_papers]
        )

        logger.info(f"ReadAgent: Completed {len(analyses)} analyses")
        return list(analyses)

    async def _analyze_paper(self, paper: Dict, output_language: str) -> Dict:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "") or "No abstract available"

        prompt = self._build_prompt(title, abstract, output_language)

        try:
            response = await self.llm.complete([
                {"role": "user", "content": prompt}
            ])

            result = self._parse_response(response)
            return {
                **paper,
                "problem": result.get("problem"),
                "method": result.get("method"),
                "contribution": result.get("contribution"),
                "limitation": result.get("limitation"),
                "dataset": result.get("dataset"),
                "category": result.get("category")
            }
        except LLMProviderError as e:
            logger.warning(f"ReadAgent LLM error for paper '{title}': {e}")
            return self._fallback_analysis(paper)

    def _build_prompt(self, title: str, abstract: str, output_language: str) -> str:
        lang_instruction = (
            "请用中文回答" if output_language == "zh" else "Please answer in English"
        )

        return f"""{lang_instruction}

你是一个学术论文分析助手。请分析以下论文，提取结构化信息。

论文标题：{title}

摘要：
{abstract}

请提取以下信息并用JSON格式输出：

1. **研究问题**（problem）：这篇论文要解决什么问题？
2. **使用方法**（method）：论文采用了什么方法或技术？
3. **主要贡献**（contribution）：论文的主要贡献是什么？
4. **局限性**（limitation）：论文有什么局限性？
5. **数据集**（dataset）：论文使用了什么数据集？（如果没有则写"N/A"）
6. **分类**（category）：这篇论文属于哪个研究方向？（如：模型架构、训练方法、应用场景等）

请用JSON格式输出：
{{
    "problem": "...",
    "method": "...",
    "contribution": "...",
    "limitation": "...",
    "dataset": "...",
    "category": "..."
}}

只输出JSON，不要有其他内容。
"""

    def _parse_response(self, response: str) -> Dict:
        try:
            return extract_json_object(response)
        except JsonExtractionError as e:
            logger.warning(f"Failed to parse analysis response: {e}")
            return {}

    def _fallback_analysis(self, paper: Dict) -> Dict:
        return {
            **paper,
            "problem": "N/A",
            "method": "N/A",
            "contribution": paper.get("title", "N/A"),
            "limitation": "N/A",
            "dataset": "N/A",
            "category": "General"
        }
