"""
Markdown 导出服务模块

将综述结果导出为 Markdown 文件，包含以下章节：
1. 论文列表（表格形式）
2. 文献分析（表格形式）
3. 综述大纲（层级列表）
4. 综述正文（Markdown 格式）
5. RAG 证据链（按章节组织）
6. 参考文献列表
7. 引用校验报告

导出的 Markdown 文件可直接用于学术写作或进一步编辑。
"""

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MarkdownExporter:
    """Markdown 导出器：将综述结果格式化为完整的 Markdown 文档"""

    def export(
        self,
        topic: str,
        papers: List[Dict],
        analyses: List[Dict],
        outline: Optional[Dict],
        content: Optional[str],
        valid_citations: List[str],
        citation_report: str,
        rag_evidence: Optional[List[Dict]] = None
    ) -> str:
        """
        导出完整的 Markdown 综述文档

        Args:
            topic: 研究主题
            papers: 论文列表
            analyses: 论文分析列表
            outline: 综述大纲
            content: 综述正文
            valid_citations: 有效引用列表
            citation_report: 引用校验报告
            rag_evidence: RAG 证据链

        Returns:
            Markdown 格式的完整文档
        """
        sections = []

        # 标题
        sections.append(f"# {topic} 研究综述\n")

        # 论文列表
        sections.append("## 论文列表\n")
        sections.append(self._render_paper_table(papers))

        # 文献分析
        sections.append("\n## 文献分析\n")
        sections.append(self._render_analysis_table(analyses))

        # 综述大纲
        sections.append("\n## 综述大纲\n")
        if outline:
            sections.append(self._render_outline(outline))

        # 综述正文
        sections.append("\n## 综述正文\n")
        if content:
            sections.append(content)

        # RAG 证据链
        sections.append("\n## RAG 证据链\n")
        sections.append(self._render_rag_evidence(rag_evidence or []))

        # 参考文献
        sections.append("\n## 参考文献\n")
        sections.append(self._generate_reference_list(papers))

        # 引用校验报告
        sections.append("\n## 引用校验报告\n")
        sections.append(citation_report)

        return "\n".join(sections)

    def _render_paper_table(self, papers: List[Dict]) -> str:
        """
        渲染论文列表为 Markdown 表格

        表格列：# | 标题 | 作者 | 年份 | 来源 | 引用数
        """
        if not papers:
            return "*暂无论文数据*"

        header = "| # | 标题 | 作者 | 年份 | 来源 | 引用数 |\n"
        header += "|----|------|------|------|------|--------|\n"

        rows = []
        for p in sorted(papers, key=lambda x: x.get("paper_index", 0)):
            # 作者：最多显示 3 位，超过加 "et al."
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            if not authors:
                authors = "Unknown"

            # 标题截断到 50 字符
            title = p.get("title", "Untitled")[:50]
            year = p.get("year", "N/A")
            source = p.get("source", "N/A")
            citations = p.get("citation_count", 0)
            paper_idx = p.get("paper_index", "?")

            rows.append(f"| [{paper_idx}] | {title}... | {authors} | {year} | {source} | {citations} |")

        return header + "\n".join(rows)

    def _render_analysis_table(self, analyses: List[Dict]) -> str:
        """
        渲染论文分析为 Markdown 表格

        表格列：# | 研究问题 | 方法 | 贡献 | 局限性 | 分类
        """
        if not analyses:
            return "*暂无分析数据*"

        header = "| # | 研究问题 | 方法 | 贡献 | 局限性 | 分类 |\n"
        header += "|----|----------|------|------|--------|------|\n"

        rows = []
        for a in sorted(analyses, key=lambda x: x.get("paper_index", 0)):
            paper_idx = a.get("paper_index", "?")
            # 各字段截断到 30 字符
            problem = (a.get("problem") or "N/A")[:30]
            method = (a.get("method") or "N/A")[:30]
            contribution = (a.get("contribution") or "N/A")[:30]
            limitation = (a.get("limitation") or "N/A")[:30]
            category = a.get("category") or "N/A"

            rows.append(f"| [{paper_idx}] | {problem}... | {method}... | {contribution}... | {limitation}... | {category} |")

        return header + "\n".join(rows)

    def _render_outline(self, outline: Dict) -> str:
        """
        渲染大纲为缩进列表

        格式：
        1. 引言
           1. 研究背景
           2. 研究意义
        2. 论文分类分析
        """
        lines = []

        def render_level(d: Dict, prefix: str = ""):
            for i, (key, value) in enumerate(d.items(), 1):
                lines.append(f"{prefix}{i}. {key}")
                if isinstance(value, dict):
                    render_level(value, prefix + "   ")

        render_level(outline)
        return "\n".join(lines)

    def _generate_reference_list(self, papers: List[Dict]) -> str:
        """
        生成参考文献列表

        格式：[编号] 标题 - 作者, 年份
        """
        lines = []

        for p in sorted(papers, key=lambda x: x.get("paper_index", 0)):
            paper_idx = p.get("paper_index", "?")
            title = p.get("title", "Untitled")
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            if not authors:
                authors = "Unknown"
            year = p.get("year", "N/A")
            url = p.get("url", "")

            lines.append(f"[{paper_idx}] {title} - {authors}, {year}")

        return "\n".join(lines) if lines else "*暂无参考文献*"

    def _render_rag_evidence(self, rag_evidence: List[Dict]) -> str:
        """
        渲染 RAG 证据链

        格式：
        ### 章节标题
        - **paper_id / section / 标题**：证据文本
        """
        if not rag_evidence:
            return "*暂无 RAG 证据链*"

        sections = []
        for section in rag_evidence:
            sections.append(f"### {section.get('section', '未命名章节')}")
            for item in section.get("evidence", []):
                paper_id = item.get("paper_id", "paper_?")
                title = item.get("title", "Untitled")
                chunk_type = item.get("section", "evidence")
                text = item.get("text", "")
                sections.append(f"- **{paper_id} / {chunk_type} / {title}**：{text}")

        return "\n".join(sections)


def get_exporter() -> MarkdownExporter:
    """工厂函数：获取导出器实例"""
    return MarkdownExporter()
