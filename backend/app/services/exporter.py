import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MarkdownExporter:
    def export(
        self,
        topic: str,
        papers: List[Dict],
        analyses: List[Dict],
        outline: Optional[Dict],
        content: Optional[str],
        valid_citations: List[str],
        citation_report: str
    ) -> str:
        sections = []

        sections.append(f"# {topic} 研究综述\n")

        sections.append("## 论文列表\n")
        sections.append(self._render_paper_table(papers))

        sections.append("\n## 文献分析\n")
        sections.append(self._render_analysis_table(analyses))

        sections.append("\n## 综述大纲\n")
        if outline:
            sections.append(self._render_outline(outline))

        sections.append("\n## 综述正文\n")
        if content:
            sections.append(content)

        sections.append("\n## 参考文献\n")
        sections.append(self._generate_reference_list(papers))

        sections.append("\n## 引用校验报告\n")
        sections.append(citation_report)

        return "\n".join(sections)

    def _render_paper_table(self, papers: List[Dict]) -> str:
        if not papers:
            return "*暂无论文数据*"

        header = "| # | 标题 | 作者 | 年份 | 来源 | 引用数 |\n"
        header += "|----|------|------|------|------|--------|\n"

        rows = []
        for p in sorted(papers, key=lambda x: x.get("paper_index", 0)):
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            if not authors:
                authors = "Unknown"

            title = p.get("title", "Untitled")[:50]
            year = p.get("year", "N/A")
            source = p.get("source", "N/A")
            citations = p.get("citation_count", 0)
            paper_idx = p.get("paper_index", "?")

            rows.append(f"| [{paper_idx}] | {title}... | {authors} | {year} | {source} | {citations} |")

        return header + "\n".join(rows)

    def _render_analysis_table(self, analyses: List[Dict]) -> str:
        if not analyses:
            return "*暂无分析数据*"

        header = "| # | 研究问题 | 方法 | 贡献 | 局限性 | 分类 |\n"
        header += "|----|----------|------|------|--------|------|\n"

        rows = []
        for a in sorted(analyses, key=lambda x: x.get("paper_index", 0)):
            paper_idx = a.get("paper_index", "?")
            problem = (a.get("problem") or "N/A")[:30]
            method = (a.get("method") or "N/A")[:30]
            contribution = (a.get("contribution") or "N/A")[:30]
            limitation = (a.get("limitation") or "N/A")[:30]
            category = a.get("category") or "N/A"

            rows.append(f"| [{paper_idx}] | {problem}... | {method}... | {contribution}... | {limitation}... | {category} |")

        return header + "\n".join(rows)

    def _render_outline(self, outline: Dict) -> str:
        lines = []

        def render_level(d: Dict, prefix: str = ""):
            for i, (key, value) in enumerate(d.items(), 1):
                lines.append(f"{prefix}{i}. {key}")
                if isinstance(value, dict):
                    render_level(value, prefix + "   ")

        render_level(outline)
        return "\n".join(lines)

    def _generate_reference_list(self, papers: List[Dict]) -> str:
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


def get_exporter() -> MarkdownExporter:
    return MarkdownExporter()
