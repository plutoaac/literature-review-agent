"""
LLM 响应 JSON 解析工具模块

解决的问题：
LLM 返回的文本不一定是标准 JSON，可能包含：
- Markdown 代码块包裹（```json ... ```）
- 前后有多余文字（如 "以下是JSON输出："）
- 嵌套在其他文本中

本模块提供 extract_json_object() 函数，从 LLM 响应中提取第一个有效的 JSON 对象。

解析策略（按优先级）：
1. 尝试直接解析整个文本为 JSON
2. 尝试提取 Markdown 代码块中的内容
3. 逐字符扫描，找到第一个 { 后使用 raw_decode 解析
"""

import json
import re
from typing import Any, Dict


class JsonExtractionError(ValueError):
    """当 LLM 响应中找不到有效的 JSON 对象时抛出"""
    pass


def extract_json_object(text: str) -> Dict[str, Any]:
    """
    从 LLM 响应文本中提取第一个 JSON 对象

    Args:
        text: LLM 返回的原始文本

    Returns:
        解析后的 Python 字典

    Raises:
        JsonExtractionError: 当文本中找不到有效的 JSON 对象时

    示例：
        >>> extract_json_object('{"key": "value"}')
        {'key': 'value'}
        >>> extract_json_object('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
        >>> extract_json_object('以下是结果：{"key": "value"} 希望对你有帮助')
        {'key': 'value'}
    """
    if not text or not text.strip():
        raise JsonExtractionError("empty response")

    # 候选文本列表：原始文本 + Markdown 代码块中的内容
    candidates = [text.strip(), *_extract_fenced_blocks(text)]
    decoder = json.JSONDecoder()

    for candidate in candidates:
        candidate = candidate.strip()

        # 策略 1：尝试直接解析整个候选文本
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 策略 2：逐字符扫描，找到第一个 { 后使用 raw_decode
        # raw_decode 会从指定位置开始解析，忽略前面的非 JSON 内容
        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    raise JsonExtractionError("no JSON object found")


def _extract_fenced_blocks(text: str) -> list[str]:
    """
    提取 Markdown 代码块中的内容

    匹配 ```json ... ``` 或 ``` ... ``` 格式的代码块

    Args:
        text: 包含 Markdown 代码块的文本

    Returns:
        代码块内容列表（去除了 ``` 标记）
    """
    pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
    return [match.group(1).strip() for match in pattern.finditer(text)]
