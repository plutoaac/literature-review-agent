import math
import re
from typing import Any, Dict, List


class LightweightRAG:
    """Keyword-based evidence retrieval without local embedding dependencies."""

    SECTION_WEIGHTS = {
        "contribution": 1.4,
        "method": 1.2,
        "problem": 1.1,
        "abstract": 1.0,
        "limitation": 0.8,
    }

    def build_evidence_pack(
        self,
        outline: Dict[str, Any] | None,
        analyses: List[Dict[str, Any]],
        topic: str,
        top_k: int = 6,
        max_sections: int = 8,
    ) -> List[Dict[str, Any]]:
        chunks = self.build_chunks(analyses)
        headings = self._flatten_outline(outline) or [topic]

        evidence_pack = []
        for heading in headings[:max_sections]:
            query = f"{topic} {heading}"
            evidence = self.retrieve(query=query, chunks=chunks, top_k=top_k)
            if evidence:
                evidence_pack.append(
                    {
                        "section": heading,
                        "query": query,
                        "evidence": evidence,
                    }
                )

        return evidence_pack

    def build_chunks(self, analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        for analysis in analyses:
            paper_index = analysis.get("paper_index", "?")
            paper_id = f"paper_{paper_index}"
            title = analysis.get("title") or "Untitled"

            fields = [
                ("abstract", analysis.get("abstract")),
                ("problem", analysis.get("problem")),
                ("method", analysis.get("method")),
                ("contribution", analysis.get("contribution")),
                ("limitation", analysis.get("limitation")),
            ]

            for section, text in fields:
                text = (text or "").strip()
                if not text or text.upper() == "N/A":
                    continue
                chunks.append(
                    {
                        "chunk_id": f"{paper_id}_{section}",
                        "paper_id": paper_id,
                        "paper_index": paper_index,
                        "title": title,
                        "source": analysis.get("source"),
                        "year": analysis.get("year"),
                        "section": section,
                        "text": text[:900],
                        "score": 0.0,
                    }
                )

        return chunks

    def retrieve(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 6,
    ) -> List[Dict[str, Any]]:
        query_terms = set(self._tokenize(query))
        if not query_terms:
            return chunks[:top_k]

        scored = []
        for chunk in chunks:
            text = f"{chunk.get('title', '')} {chunk.get('section', '')} {chunk.get('text', '')}"
            terms = set(self._tokenize(text))
            if not terms:
                continue

            overlap = query_terms & terms
            title_terms = set(self._tokenize(chunk.get("title") or ""))
            title_overlap = query_terms & title_terms

            score = (
                len(overlap) / math.sqrt(len(terms))
                + len(title_overlap) * 0.35
                + self.SECTION_WEIGHTS.get(chunk.get("section"), 1.0) * 0.2
            )

            if score <= 0:
                continue

            item = dict(chunk)
            item["score"] = round(score, 4)
            scored.append(item)

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def format_for_prompt(self, evidence_pack: List[Dict[str, Any]]) -> str:
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
        return [
            token.lower()
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*|[\u4e00-\u9fff]", text or "")
            if len(token.strip()) > 1 or "\u4e00" <= token <= "\u9fff"
        ]


def get_rag_service() -> LightweightRAG:
    return LightweightRAG()
