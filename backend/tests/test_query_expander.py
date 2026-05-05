"""
查询扩展模块单元测试

测试 expand_academic_queries() 的功能：
- 中文学术术语翻译
- 查询去重
- 变体生成
"""

import pytest
from app.services.query_expander import expand_academic_queries, _translate_by_terms, _contains_chinese


class TestContainsChinese:
    """测试中文检测"""

    def test_chinese_text(self):
        assert _contains_chinese("深度学习") == True

    def test_english_text(self):
        assert _contains_chinese("deep learning") == False

    def test_mixed_text(self):
        assert _contains_chinese("深度 learning") == True

    def test_empty_text(self):
        assert _contains_chinese("") == False


class TestTranslateByTerms:
    """测试术语翻译"""

    def test_known_term(self):
        """已知术语：应返回英文翻译"""
        result = _translate_by_terms("透明物体深度补全")
        assert "transparent" in result.lower()

    def test_unknown_term(self):
        """未知术语：应返回空字符串"""
        result = _translate_by_terms("量子计算")
        assert result == ""


class TestExpandAcademicQueries:
    """测试查询扩展"""

    def test_chinese_query_expanded(self):
        """中文查询：应扩展为英文"""
        queries = ["透明物体深度补全"]
        result = expand_academic_queries(queries)
        assert len(result) > 1
        # 应包含英文翻译
        has_english = any("transparent" in q.lower() for q in result)
        assert has_english

    def test_english_query_preserved(self):
        """英文查询：应保留原始查询"""
        queries = ["deep learning for NLP"]
        result = expand_academic_queries(queries)
        assert "deep learning for NLP" in result

    def test_duplicates_removed(self):
        """重复查询：应去重"""
        queries = ["deep learning", "deep learning"]
        result = expand_academic_queries(queries)
        # 去重后不应有两个完全相同的查询
        assert len(result) == len(set(result))

    def test_max_queries_respected(self):
        """最大查询数限制"""
        queries = ["透明物体深度补全", "大语言模型", "检索增强生成"]
        result = expand_academic_queries(queries, max_queries=5)
        assert len(result) <= 5

    def test_empty_queries(self):
        """空查询列表：应返回空列表"""
        result = expand_academic_queries([])
        assert result == []

    def test_known_domain_terms(self):
        """已知领域术语：应有对应翻译"""
        queries = ["大语言模型"]
        result = expand_academic_queries(queries)
        has_llm = any("large language model" in q.lower() or "llm" in q.lower() for q in result)
        assert has_llm
