import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError

logger = logging.getLogger(__name__)


class WriteAgent:
    def __init__(self):
        self.llm = get_llm_client()

    async def run(
        self,
        outline: Dict,
        categories: List[Dict],
        ranked_papers: List[Dict],
        output_language: str
    ) -> str:
        logger.info("WriteAgent: Generating review content")

        valid_ids = [f"paper_{p.get('paper_index', i+1)}" for i, p in enumerate(ranked_papers)]

        prompt = self._build_prompt(outline, categories, ranked_papers, valid_ids, output_language)

        try:
            content = await self.llm.complete([
                {"role": "user", "content": prompt}
            ])

            logger.info(f"WriteAgent: Generated {len(content)} characters")
            return content
        except LLMProviderError as e:
            logger.error(f"WriteAgent LLM error: {e}")
            return self._fallback_content(outline, ranked_papers)

    def _build_prompt(
        self,
        outline: Dict,
        categories: List[Dict],
        ranked_papers: List[Dict],
        valid_ids: List[str],
        output_language: str
    ) -> str:
        lang_instruction = (
            "请用中文撰写" if output_language == "zh" else "Please write in English"
        )

        outline_text = self._format_outline(outline)

        papers_info = []
        for p in ranked_papers:
            idx = p.get("paper_index", "?")
            title = p.get("title", "Untitled")
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            year = p.get("year", "N/A")
            abstract = (p.get("abstract") or "No abstract")[:200]

            papers_info.append(f"[{idx}] {title} - {authors}, {year}\n   Abstract: {abstract}...")

        papers_info_text = "\n\n".join(papers_info)

        return f"""{lang_instruction}

你是一个学术综述写作助手。请根据以下大纲和文献信息，撰写一篇完整的学术综述。

**重要约束**：
1. 只能使用以下 paper_id 进行引用：{valid_ids}
2. 禁止凭空创造任何不存在的引用
3. 引用格式：[paper_1]、[paper_2] 等
4. 每个引用都必须是真实存在于下方文献列表中的论文

---

综述大纲：
{outline_text}

---

可引用的文献列表：
{papers_info_text}

---

请撰写综述正文，遵循以下要求：
1. 严格按照上述大纲结构
2. 在适当位置使用文献引用，格式为 [paper_X]
3. 每段话尽量综合多篇文献的内容
4. 语言要学术化、连贯
5. 不要列出参考文献（在最后单独生成）

直接输出综述正文，不要有其他内容。
"""

    def _format_outline(self, outline: Dict, prefix: str = "") -> str:
        lines = []
        for key, value in outline.items():
            lines.append(f"{prefix}{key}")
            if isinstance(value, dict):
                lines.append(self._format_outline(value, prefix + "  "))
        return "\n".join(lines)

    def _fallback_content(self, outline: Dict, ranked_papers: List[Dict]) -> str:
        content = ["# 研究综述\n"]

        content.append("## 引言\n")
        content.append(f"本综述基于 {len(ranked_papers)} 篇相关论文，对研究主题进行了系统分析。\n")

        for i, p in enumerate(ranked_papers[:5], 1):
            title = p.get("title", "Untitled")
            content.append(f"[paper_{p.get('paper_index', i)}] {title} ...\n")

        content.append("\n## 参考文献\n")
        for p in ranked_papers:
            title = p.get("title", "Untitled")
            content.append(f"[paper_{p.get('paper_index', '?')}] {title}\n")

        return "".join(content)
