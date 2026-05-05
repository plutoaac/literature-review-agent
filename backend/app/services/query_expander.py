"""
学术查询扩展模块

功能：将中文学术术语翻译为英文，扩展搜索查询的覆盖面。

主要场景：
- 用户输入"透明物体深度补全"→ 扩展为 "transparent object depth completion" 等英文查询
- 用户输入"大语言模型"→ 扩展为 "large language model"、"LLM"

扩展策略：
1. 精确匹配：检查查询是否包含预定义的中文学术短语，替换为对应的英文术语
2. 模糊翻译：遍历所有中文学术短语，提取匹配部分的英文翻译
3. 变体生成：为翻译结果添加 "survey"、"review" 等后缀，增加检索覆盖率
4. 去重：确保扩展后的查询列表无重复

注意：DOMAIN_TRANSLATIONS 字典是硬编码的，仅覆盖课程设计相关的学术领域。
生产环境应接入翻译 API 或使用更完整的术语表。
"""

import re
from typing import Iterable, List


# 中文学术术语 → 英文翻译映射表
# 键：中文学术短语；值：对应的英文查询列表
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

ENGLISH_ALIASES = {
    "retrieval augmented generation": [
        "retrieval augmented generation",
        "retrieval-augmented generation",
        "retrieval augmented language models",
        "retrieval augmented generation large language models",
        "knowledge intensive NLP retrieval augmented generation",
        "RAG large language models",
    ],
    "rag": [
        "retrieval augmented generation",
        "retrieval-augmented generation",
        "retrieval augmented language models",
        "RAG large language models",
    ],
    "multimodal large language models": [
        "multimodal large language models",
        "large multimodal models",
        "multimodal language models",
        "vision language models",
        "multimodal LLM",
        "MLLM",
    ],
}


def expand_academic_queries(queries: Iterable[str], max_queries: int = 12) -> List[str]:
    """
    扩展学术查询列表

    Args:
        queries: 原始查询列表（可能包含中文）
        max_queries: 最大返回查询数

    Returns:
        扩展后的英文查询列表（去重，最多 max_queries 条）
    """
    expanded: List[str] = []

    for query in queries:
        query = (query or "").strip()
        if not query:
            continue
        # 保留原始查询
        _append_unique(expanded, query)

        normalized_query = _normalize_english(query)
        for phrase, aliases in ENGLISH_ALIASES.items():
            if phrase == normalized_query or phrase in normalized_query:
                for alias in aliases:
                    _append_unique(expanded, alias)

        # 精确匹配：如果查询包含预定义的中文学术短语，添加对应的英文翻译
        for zh_phrase, english_queries in DOMAIN_TRANSLATIONS.items():
            if zh_phrase in query:
                for english_query in english_queries:
                    _append_unique(expanded, english_query)

        # 如果查询仍包含中文字符，尝试翻译
        if _contains_chinese(query):
            translated = _translate_by_terms(query)
            if translated:
                _append_unique(expanded, translated)
                # 生成变体：添加 survey/review 后缀（综述类论文通常更全面）
                _append_unique(expanded, f"{translated} survey")
                _append_unique(expanded, f"{translated} review")
        else:
            # 英文查询：规范化空白字符后保留
            normalized = re.sub(r"\s+", " ", query).strip()
            if normalized:
                _append_unique(expanded, normalized)

    return expanded[:max_queries]


def _translate_by_terms(query: str) -> str:
    """
    按术语翻译：遍历 DOMAIN_TRANSLATIONS，提取查询中匹配的中文学术短语的英文翻译

    例如："透明物体深度估计方法" → 匹配 "透明物体" 和 "深度估计" → "transparent object depth estimation"
    """
    english_terms: List[str] = []
    for zh_phrase, translations in DOMAIN_TRANSLATIONS.items():
        if zh_phrase in query:
            english_terms.append(translations[0])  # 取第一个翻译结果

    if not english_terms:
        return ""

    # 去重并拼接（保持顺序）
    return " ".join(dict.fromkeys(" ".join(english_terms).split()))


def _contains_chinese(text: str) -> bool:
    """检测文本是否包含中文字符"""
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _normalize_english(text: str) -> str:
    text = re.sub(r"[-_/]+", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _append_unique(items: List[str], value: str):
    """
    向列表追加去重项（忽略大小写和多余空白）

    Args:
        items: 目标列表
        value: 待追加的值
    """
    normalized = re.sub(r"\s+", " ", value or "").strip()
    if not normalized:
        return

    # 构建已存在项的小写集合，用于去重判断
    existing = {item.lower() for item in items}
    if normalized.lower() not in existing:
        items.append(normalized)
