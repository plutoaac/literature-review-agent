"""
JSON 解析工具单元测试

测试 extract_json_object() 函数的各种输入场景：
- 标准 JSON 对象
- Markdown 代码块包裹
- 前后有多余文字
- 空输入 / 无效输入
"""

import pytest
from app.utils.json_parser import extract_json_object, JsonExtractionError


class TestExtractJsonObject:
    """测试 JSON 对象提取功能"""

    def test_standard_json(self):
        """标准 JSON 对象：直接解析"""
        result = extract_json_object('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_json_with_markdown_fence(self):
        """Markdown 代码块包裹：提取代码块内容"""
        text = '```json\n{"search_queries": ["query1", "query2"]}\n```'
        result = extract_json_object(text)
        assert result == {"search_queries": ["query1", "query2"]}

    def test_json_with_prefix_text(self):
        """前缀文字：跳过非 JSON 内容"""
        text = '以下是结果：\n{"problem": "test problem"}'
        result = extract_json_object(text)
        assert result == {"problem": "test problem"}

    def test_json_with_suffix_text(self):
        """后缀文字：只解析第一个 JSON 对象"""
        text = '{"method": "deep learning"} 希望对你有帮助'
        result = extract_json_object(text)
        assert result == {"method": "deep learning"}

    def test_json_with_surrounding_text(self):
        """前后都有文字：正确提取中间的 JSON"""
        text = '根据分析，结果如下：\n{"categories": [1, 2, 3]}\n以上是分类结果。'
        result = extract_json_object(text)
        assert result == {"categories": [1, 2, 3]}

    def test_nested_json(self):
        """嵌套 JSON 对象：正确解析"""
        text = '{"outline": {"1. 引言": {"1.1 背景": null}}}'
        result = extract_json_object(text)
        assert "outline" in result
        assert "1. 引言" in result["outline"]

    def test_empty_input_raises_error(self):
        """空输入：抛出 JsonExtractionError"""
        with pytest.raises(JsonExtractionError, match="empty response"):
            extract_json_object("")

    def test_none_input_raises_error(self):
        """None 输入：抛出 JsonExtractionError"""
        with pytest.raises(JsonExtractionError, match="empty response"):
            extract_json_object(None)

    def test_no_json_raises_error(self):
        """无 JSON 内容：抛出 JsonExtractionError"""
        with pytest.raises(JsonExtractionError, match="no JSON object found"):
            extract_json_object("这是一段纯文本，没有JSON")

    def test_json_array_not_accepted(self):
        """JSON 数组（非对象）：应抛出异常"""
        with pytest.raises(JsonExtractionError, match="no JSON object found"):
            extract_json_object('[1, 2, 3]')

    def test_markdown_fence_without_json_label(self):
        """无 json 标签的代码块：也能提取"""
        text = '```\n{"key": "value"}\n```'
        result = extract_json_object(text)
        assert result == {"key": "value"}
