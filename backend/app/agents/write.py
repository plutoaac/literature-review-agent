"""
综述正文写作 Agent（WriteAgent）

职责：调用 LLM 根据大纲、论文信息和 RAG 证据片段，撰写完整的学术综述正文。

关键设计：
1. 引用约束：提示词中明确列出所有合法的 paper_id，禁止 LLM 编造引用
2. RAG 证据优先：要求 LLM 优先依据 RAG 证据片段进行总结，不足时做谨慎概括
3. 引用格式：统一使用 [paper_X] 格式，便于下游 CitationCheckAgent 校验
"""

import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError
from app.services.rag import get_rag_service

logger = logging.getLogger(__name__)


class WriteAgent:
    """综述正文写作 Agent：基于大纲和证据生成完整的学术综述"""

    def __init__(self, llm=None, rag_service=None):
        """
        Args:
            llm: LLM 客户端实例（可选，默认从工厂函数创建）
            rag_service: RAG 服务实例（可选，默认从工厂函数创建）
        """
        self.llm = llm or get_llm_client()
        self.rag_service = rag_service or get_rag_service()

    async def run(
        self,
        outline: Dict,
        categories: List[Dict],
        ranked_papers: List[Dict],
        rag_evidence: List[Dict],
        output_language: str
    ) -> str:
        """
        生成综述正文

        Args:
            outline: 综述大纲（嵌套字典）
            categories: 文献分类列表
            ranked_papers: 排序后的论文列表
            rag_evidence: RAG 证据片段（按章节组织）
            output_language: 输出语言

        Returns:
            Markdown 格式的综述正文
        """
        logger.info("WriteAgent: Generating review content")

        # 构建合法引用 ID 列表（如 ["paper_1", "paper_2", ...]）
        valid_ids = [f"paper_{p.get('paper_index', i+1)}" for i, p in enumerate(ranked_papers)]

        prompt = self._build_prompt(
            outline,
            categories,
            ranked_papers,
            valid_ids,
            rag_evidence,
            output_language
        )

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
        rag_evidence: List[Dict],
        output_language: str
    ) -> str:
        """
        构建综述写作的 LLM 提示词

        提示词结构：
        1. 语言指令 + 角色设定
        2. 引用约束（5 条规则，防止幻觉引用）
        3. 综述大纲
        4. 可引用的文献列表（含标题、作者、年份、摘要）
        5. RAG 证据片段
        6. 写作要求
        """
        lang_instruction = (
            "请用中文撰写" if output_language == "zh" else "Please write in English"
        )

        # 将大纲格式化为层级文本
        outline_text = self._format_outline(outline)

        # 格式化论文信息（每篇论文一行，含编号、标题、作者、年份、摘要前 200 字）
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

        # 将 RAG 证据格式化为 LLM 可读的文本
        evidence_text = self.rag_service.format_for_prompt(rag_evidence)

        return f"""{lang_instruction}

你是一个学术综述写作助手。请根据以下大纲、文献信息和 RAG 证据片段，撰写一篇完整的学术综述。

**重要约束**：
1. 只能使用以下 paper_id 进行引用：{valid_ids}
2. 禁止凭空创造任何不存在的引用
3. 引用格式：[paper_1]、[paper_2] 等
4. 每个引用都必须是真实存在于下方文献列表中的论文
5. 优先依据 RAG 证据片段进行总结；证据不足时可以做谨慎概括，但不能编造具体实验结论

---

综述大纲：
{outline_text}

---

可引用的文献列表：
{papers_info_text}

---

RAG 证据片段：
{evidence_text}

---

请撰写综述正文，遵循以下要求：
1. 严格按照上述大纲结构
2. 在适当位置使用文献引用，格式为 [paper_X]
3. 每段话尽量综合多篇文献的内容，并优先覆盖上方证据片段
4. 语言要学术化、连贯
5. 不要列出参考文献（在最后单独生成）

直接输出综述正文，不要有其他内容。
"""

    def _format_outline(self, outline: Dict, prefix: str = "") -> str:
        """
        递归格式化大纲为缩进文本

        例如：
        1. 引言
          1.1 研究背景
          1.2 研究意义
        2. 论文分类分析
        """
        lines = []
        for key, value in outline.items():
            lines.append(f"{prefix}{key}")
            if isinstance(value, dict):
                lines.append(self._format_outline(value, prefix + "  "))
        return "\n".join(lines)

    def _fallback_content(self, outline: Dict, ranked_papers: List[Dict]) -> str:
        """
        Fallback 策略：LLM 调用失败时，生成基础的综述框架

        只包含引言和参考文献列表，正文内容为空，用户可在此基础上手动补充。
        """
        content = ["# 研究综述\n"]

        content.append("## 引言\n")
        content.append(f"本综述基于 {len(ranked_papers)} 篇相关论文，对研究主题进行了系统分析。\n")

        # 列出前 5 篇论文作为示例引用
        for i, p in enumerate(ranked_papers[:5], 1):
            title = p.get("title", "Untitled")
            content.append(f"[paper_{p.get('paper_index', i)}] {title} ...\n")

        content.append("\n## 参考文献\n")
        for p in ranked_papers:
            title = p.get("title", "Untitled")
            content.append(f"[paper_{p.get('paper_index', '?')}] {title}\n")

        return "".join(content)
