"""
文献分类 Agent（OrganizeAgent）

职责：调用 LLM 将论文按研究方向分类，生成对比表和主题总结。

输出内容：
1. categories（文献分类）：将论文按研究主题分组，每组包含名称、说明和论文编号
2. comparison_table（对比表）：表格形式对比各论文的方法和贡献
3. theme_summary（主题总结）：总结整体研究趋势和主要发现

这一步的输出会传递给下游的 OutlineAgent，用于生成综述大纲。
"""

import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError
from app.utils.json_parser import JsonExtractionError, extract_json_object

logger = logging.getLogger(__name__)


class OrganizeAgent:
    """文献分类 Agent：将论文按研究方向分组并生成对比表"""

    def __init__(self, llm=None):
        """
        Args:
            llm: LLM 客户端实例（可选，默认从工厂函数创建）
        """
        self.llm = llm or get_llm_client()

    async def run(self, analyses: List[Dict], output_language: str) -> Dict:
        """
        执行文献分类

        Args:
            analyses: 论文分析结果列表（来自 ReadAgent）
            output_language: 输出语言（"zh" 或 "en"）

        Returns:
            包含 categories、comparison_table、theme_summary 的字典
        """
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
        """
        构建文献分类的 LLM 提示词

        将每篇论文的关键信息（编号、标题、分类、方法、贡献）格式化为文本，
        供 LLM 进行分类和对比。
        """
        lang_instruction = (
            "请用中文回答" if output_language == "zh" else "Please answer in English"
        )

        # 将论文信息格式化为简洁的文本列表
        papers_text = []
        for a in analyses:
            paper_idx = a.get("paper_index", "?")
            title = a.get("title", "Untitled")[:100]      # 截断过长标题
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
        """解析 LLM 返回的 JSON 响应"""
        try:
            return extract_json_object(response)
        except JsonExtractionError as e:
            logger.warning(f"Failed to parse organize response: {e}")
            return {"categories": [], "comparison_table": [], "theme_summary": ""}

    def _fallback_organize(self, analyses: List[Dict]) -> Dict:
        """
        Fallback 策略：基于论文自带的 category 字段进行简单分组

        不调用 LLM，直接使用 ReadAgent 分析时生成的 category 字段进行聚合。
        """
        # 按 category 字段分组
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
