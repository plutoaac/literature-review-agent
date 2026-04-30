import re
from typing import Iterable, List


DOMAIN_TRANSLATIONS = {
    "透明物体深度补全": [
        "transparent object depth completion",
        "depth completion for transparent objects",
        "transparent object depth estimation",
        "transparent object reconstruction depth",
        "ClearGrasp transparent object depth",
        "TransCG transparent object depth completion",
    ],
    "透明物体": ["transparent object", "transparent objects"],
    "深度补全": ["depth completion", "depth inpainting"],
    "深度估计": ["depth estimation"],
    "机器人抓取": ["robotic grasping", "robot grasping"],
    "三维重建": ["3D reconstruction", "three-dimensional reconstruction"],
    "多模态": ["multimodal", "multi-modal"],
    "大语言模型": ["large language model", "LLM"],
    "检索增强生成": ["retrieval augmented generation", "RAG"],
}


def expand_academic_queries(queries: Iterable[str], max_queries: int = 12) -> List[str]:
    expanded: List[str] = []

    for query in queries:
        query = (query or "").strip()
        if not query:
            continue
        _append_unique(expanded, query)

        for zh_phrase, english_queries in DOMAIN_TRANSLATIONS.items():
            if zh_phrase in query:
                for english_query in english_queries:
                    _append_unique(expanded, english_query)

        if _contains_chinese(query):
            translated = _translate_by_terms(query)
            if translated:
                _append_unique(expanded, translated)
                _append_unique(expanded, f"{translated} survey")
                _append_unique(expanded, f"{translated} review")
        else:
            normalized = re.sub(r"\s+", " ", query).strip()
            if normalized:
                _append_unique(expanded, normalized)

    return expanded[:max_queries]


def _translate_by_terms(query: str) -> str:
    english_terms: List[str] = []
    for zh_phrase, translations in DOMAIN_TRANSLATIONS.items():
        if zh_phrase in query:
            english_terms.append(translations[0])

    if not english_terms:
        return ""

    return " ".join(dict.fromkeys(" ".join(english_terms).split()))


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _append_unique(items: List[str], value: str):
    normalized = re.sub(r"\s+", " ", value or "").strip()
    if not normalized:
        return

    existing = {item.lower() for item in items}
    if normalized.lower() not in existing:
        items.append(normalized)
