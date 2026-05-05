"""
轻量级 RAG（检索增强生成）服务模块

本模块实现了基于关键词匹配的轻量 RAG 证据召回机制，不依赖向量模型或向量数据库。

RAG 工作流程：
1. build_chunks()：将论文分析结果拆分为证据片段（按 section 类型）
2. build_evidence_pack()：针对综述大纲的每个章节，召回最相关的证据片段
3. format_for_prompt()：将证据格式化为 LLM 可读的文本

证据片段结构：
{
    "chunk_id": "paper_1_method",
    "paper_id": "paper_1",
    "section": "method",        # abstract/problem/method/contribution/limitation
    "text": "论文方法的文本片段",
    "score": 3.14               # 相关性评分
}

设计考量：
- 使用关键词匹配而非 embedding，避免依赖本地向量模型
- 按 section 类型加权（贡献 > 方法 > 问题 > 摘要 > 局限性）
- 适合课程设计部署环境（无需 GPU、无需向量数据库）
"""

import math
import re
from typing import Any, Dict, List


class LightweightRAG:
    """
    轻量级 RAG 服务：基于关键词匹配的证据召回

    核心思想：将论文分析结果拆分为小的证据片段（chunks），
    然后针对综述的每个章节，通过关键词匹配召回最相关的片段。
    """

    # section 类型权重：贡献和方法通常更重要，局限性相对次要
    SECTION_WEIGHTS = {
        "contribution": 1.4,   # 主要贡献：最高权重
        "method": 1.2,         # 使用方法
        "problem": 1.1,        # 研究问题
        "abstract": 1.0,       # 摘要：基准权重
        "limitation": 0.8,     # 局限性：最低权重
    }

    def build_evidence_pack(
        self,
        outline: Dict[str, Any] | None,
        analyses: List[Dict[str, Any]],
        topic: str,
        top_k: int = 6,
        max_sections: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        构建 RAG 证据包：为综述大纲的每个章节召回相关证据

        Args:
            outline: 综述大纲（嵌套字典结构）
            analyses: 论文分析结果列表
            topic: 研究主题
            top_k: 每个章节最多召回的证据数
            max_sections: 最多处理的大纲章节数

        Returns:
            证据包列表，每个元素包含 section、query、evidence
        """
        # 将论文分析拆分为证据片段
        chunks = self.build_chunks(analyses)
        # 将大纲展平为章节标题列表
        headings = self._flatten_outline(outline) or [topic]

        evidence_pack = []
        # 遍历大纲的前 max_sections 个章节
        for heading in headings[:max_sections]:
            # 构建检索查询：主题 + 章节标题
            query = f"{topic} {heading}"
            # 从证据片段中召回 top_k 个最相关的
            evidence = self.retrieve(query=query, chunks=chunks, top_k=top_k)
            if evidence:
                evidence_pack.append(
                    {
                        "section": heading,   # 章节标题
                        "query": query,       # 检索查询
                        "evidence": evidence, # 召回的证据片段列表
                    }
                )

        return evidence_pack

    def build_chunks(self, analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将论文分析结果拆分为证据片段

        每篇论文的每个 section（abstract/problem/method/contribution/limitation）
        作为一个独立的证据片段，方便后续按章节召回。

        Args:
            analyses: 论文分析结果列表

        Returns:
            证据片段列表
        """
        chunks = []
        for analysis in analyses:
            paper_index = analysis.get("paper_index", "?")
            paper_id = f"paper_{paper_index}"
            title = analysis.get("title") or "Untitled"

            # 定义要提取的 section 类型及其对应字段
            fields = [
                ("abstract", analysis.get("abstract")),
                ("problem", analysis.get("problem")),
                ("method", analysis.get("method")),
                ("contribution", analysis.get("contribution")),
                ("limitation", analysis.get("limitation")),
            ]

            for section, text in fields:
                text = (text or "").strip()
                # 跳过空文本和 N/A 占位符
                if not text or text.upper() == "N/A":
                    continue
                chunks.append(
                    {
                        "chunk_id": f"{paper_id}_{section}",  # 唯一标识
                        "paper_id": paper_id,                  # 关联的论文 ID
                        "paper_index": paper_index,            # 论文编号
                        "title": title,                        # 论文标题
                        "source": analysis.get("source"),      # 来源
                        "year": analysis.get("year"),          # 年份
                        "section": section,                    # section 类型
                        "text": text[:900],                    # 截断过长文本（避免 LLM 上下文溢出）
                        "score": 0.0,                          # 初始评分（召回时计算）
                    }
                )

        return chunks

    def retrieve(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        基于关键词匹配召回最相关的证据片段

        评分公式：
        score = (query 与 chunk 的词重叠数) / sqrt(chunk 的词数)
              + (query 与 chunk 标题的词重叠数) * 0.35
              + section 类型权重 * 0.2

        Args:
            query: 检索查询（如 "深度补全 2.1 技术方法"）
            chunks: 所有证据片段
            top_k: 返回数量上限

        Returns:
            按评分降序排列的 top_k 个证据片段
        """
        query_terms = set(self._tokenize(query))
        if not query_terms:
            return chunks[:top_k]

        scored = []
        for chunk in chunks:
            # 拼接 chunk 的所有文本用于匹配
            text = f"{chunk.get('title', '')} {chunk.get('section', '')} {chunk.get('text', '')}"
            terms = set(self._tokenize(text))
            if not terms:
                continue

            # 计算词重叠
            overlap = query_terms & terms
            # 额外计算标题匹配（标题匹配更有价值）
            title_terms = set(self._tokenize(chunk.get("title") or ""))
            title_overlap = query_terms & title_terms

            # 综合评分
            score = (
                len(overlap) / math.sqrt(len(terms))    # 主评分：重叠词数 / sqrt(chunk词数)
                + len(title_overlap) * 0.35              # 标题匹配加分
                + self.SECTION_WEIGHTS.get(chunk.get("section"), 1.0) * 0.2  # section 类型加分
            )

            if score <= 0:
                continue

            item = dict(chunk)
            item["score"] = round(score, 4)
            scored.append(item)

        # 按评分降序排列，取 top_k
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def format_for_prompt(self, evidence_pack: List[Dict[str, Any]]) -> str:
        """
        将证据包格式化为 LLM 可读的文本

        格式：
        Section: 1.1 研究背景
        - paper_1 | method | 论文标题 | Evidence: 方法描述...
        - paper_2 | contribution | 论文标题 | Evidence: 贡献描述...

        Args:
            evidence_pack: 证据包列表

        Returns:
            格式化的文本字符串
        """
        if not evidence_pack:
            return "No retrieved evidence available."

        lines = []
        for section in evidence_pack:
            lines.append(f"Section: {section.get('section')}")
            for item in section.get("evidence", []):
                lines.append(
                    "- "
                    f"{item.get('paper_id')} | {item.get('section')} | "
                    f"{item.get('title')} | Evidence: {item.get('text')}"
                )
            lines.append("")

        return "\n".join(lines).strip()

    def _flatten_outline(self, outline: Dict[str, Any] | None) -> List[str]:
        """
        递归展平大纲为章节标题列表

        输入：{"1. 引言": {"1.1 背景": null}, "2. 方法": null}
        输出：["1. 引言", "1.1 背景", "2. 方法"]
        """
        if not outline:
            return []

        headings = []

        def walk(node: Dict[str, Any]):
            for key, value in node.items():
                headings.append(str(key))
                if isinstance(value, dict):
                    walk(value)

        walk(outline)
        return headings

    def _tokenize(self, text: str) -> List[str]:
        """
        文本分词：提取英文单词和中文字符，转小写

        规则：
        - 英文：匹配 2+ 字符的单词（如 "depth"、"completion"）
        - 中文：逐字匹配
        - 过滤单字符英文（如 "a"、"I"）
        """
        return [
            token.lower()
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*|[\u4e00-\u9fff]", text or "")
            if len(token.strip()) > 1 or "\u4e00" <= token <= "\u9fff"
        ]


def get_rag_service() -> LightweightRAG:
    """工厂函数：获取 RAG 服务实例"""
    return LightweightRAG()
