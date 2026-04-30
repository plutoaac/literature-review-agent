import logging
import json
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError

logger = logging.getLogger(__name__)


class OrganizeAgent:
    def __init__(self):
        self.llm = get_llm_client()

    async def run(self, analyses: List[Dict], output_language: str) -> Dict:
        logger.info(f"OrganizeAgent: Organizing {len(analyses)} papers into categories")

        prompt = self._build_prompt(analyses, output_language)

        try:
            response = await self.llm.complete([
                {"role": "user", "content": prompt}
            ])

            result = self._parse_response(response)
            logger.info(f"OrganizeAgent: Created {len(result.get('categories', []))} categories")
            return result
        except LLMProviderError as e:
            logger.error(f"OrganizeAgent LLM error: {e}")
            return self._fallback_organize(analyses)

    def _build_prompt(self, analyses: List[Dict], output_language: str) -> str:
        lang_instruction = (
            "请用中文回答" if output_language == "zh" else "Please answer in English"
        )

        papers_text = []
        for a in analyses:
            paper_idx = a.get("paper_index", "?")
            title = a.get("title", "Untitled")[:100]
            category = a.get("category", "General")
            method = a.get("method", "N/A")[:100]
            contribution = a.get("contribution", "N/A")[:100]

            papers_text.append(f"[{paper_idx}] {title}")
            papers_text.append(f"   Category: {category}, Method: {method}, Contribution: {contribution}")

        papers_text = "\n".join(papers_text)

        return f"""{lang_instruction}

你是一个学术文献分类助手。请将以下论文按研究方向分类，并生成文献对比表。

论文列表：
{papers_text}

请完成以下任务：

1. **文献分类**（categories）：将论文按研究主题/方向分组，每个分类包含：
   - name: 分类名称
   - description: 分类说明
   - paper_indices: 属于该分类的论文编号列表

2. **文献对比表**（comparison_table）：生成一个表格对比各论文的方法和贡献

3. **主题总结**（theme_summary）：总结这些论文的整体研究趋势和主要发现

请用JSON格式输出：
{{
    "categories": [
        {{
            "name": "分类名称",
            "description": "分类说明",
            "paper_indices": [1, 3, 5]
        }}
    ],
    "comparison_table": [
        ["论文", "方法", "贡献"],
        ["[1]", "方法1", "贡献1"],
        ...
    ],
    "theme_summary": "主题总结..."
}}

只输出JSON，不要有其他内容。
"""

    def _parse_response(self, response: str) -> Dict:
        try:
            for line in response.strip().split('\n'):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    return json.loads(line)
            return json.loads(response.strip())
        except Exception as e:
            logger.warning(f"Failed to parse organize response: {e}")
            return {"categories": [], "comparison_table": [], "theme_summary": ""}

    def _fallback_organize(self, analyses: List[Dict]) -> Dict:
        categories = {}
        for a in analyses:
            cat = a.get("category", "General")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(a.get("paper_index", "?"))

        return {
            "categories": [
                {
                    "name": cat,
                    "description": f"关于{cat}的研究",
                    "paper_indices": indices
                }
                for cat, indices in categories.items()
            ],
            "comparison_table": [
                ["论文", "方法", "贡献"],
                *[[a.get("paper_index", "?"), a.get("method", "N/A")[:30], a.get("contribution", "N/A")[:30]]
                  for a in analyses]
            ],
            "theme_summary": "主题总结"
        }
