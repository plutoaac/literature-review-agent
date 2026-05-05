"""
轻量相关性评分器单元测试

测试 LightweightRelevanceScorer 的各维度评分：
- 关键词匹配（标题 + 摘要）
- 引用数评分（log 平滑）
- 年份新鲜度（线性衰减）
- 来源权重
- 综合评分
"""

import pytest
from app.services.embedding import LightweightRelevanceScorer


@pytest.fixture
def scorer():
    """创建评分器实例"""
    return LightweightRelevanceScorer()


class TestTokenization:
    """测试分词功能"""

    def test_english_tokenization(self, scorer):
        """英文分词：提取单词并转小写"""
        tokens = scorer._tokens("Deep Learning for NLP")
        assert "deep" in tokens
        assert "learning" in tokens
        assert "nlp" in tokens

    def test_chinese_tokenization(self, scorer):
        """中文分词：逐字提取"""
        tokens = scorer._tokens("深度学习")
        assert "深" in tokens
        assert "度" in tokens

    def test_stopwords_filtered(self, scorer):
        """停用词过滤：常见词被移除"""
        tokens = scorer._tokens("a study of the deep learning")
        assert "a" not in tokens
        assert "the" not in tokens
        assert "of" not in tokens
        assert "deep" in tokens

    def test_empty_text(self, scorer):
        """空文本：返回空集合"""
        tokens = scorer._tokens("")
        assert len(tokens) == 0


class TestOverlapScore:
    """测试关键词重叠评分"""

    def test_full_overlap(self, scorer):
        """完全重叠：评分应为 1.0"""
        topic = {"deep", "learning"}
        candidate = {"deep", "learning", "nlp"}
        score = scorer._overlap(topic, candidate)
        assert score == 1.0

    def test_partial_overlap(self, scorer):
        """部分重叠：评分应为 0.5"""
        topic = {"deep", "learning"}
        candidate = {"deep", "nlp"}
        score = scorer._overlap(topic, candidate)
        assert score == 0.5

    def test_no_overlap(self, scorer):
        """无重叠：评分应为 0.0"""
        topic = {"deep", "learning"}
        candidate = {"computer", "vision"}
        score = scorer._overlap(topic, candidate)
        assert score == 0.0

    def test_empty_topic(self, scorer):
        """空主题：评分应为 0.0"""
        score = scorer._overlap(set(), {"some", "tokens"})
        assert score == 0.0


class TestCitationScore:
    """测试引用数评分"""

    def test_zero_citations(self, scorer):
        """0 引用：评分应为 0.0"""
        assert scorer._citation_score(0) == 0.0

    def test_high_citations(self, scorer):
        """高引用（5000）：评分应接近 1.0"""
        score = scorer._citation_score(5000)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_medium_citations(self, scorer):
        """中等引用（100）：评分应在 0.5-0.8 之间"""
        score = scorer._citation_score(100)
        assert 0.5 < score < 0.8

    def test_negative_citations(self, scorer):
        """负引用数：应视为 0"""
        assert scorer._citation_score(-10) == 0.0

    def test_invalid_citation_count(self, scorer):
        """无效引用数：应返回 0.0"""
        assert scorer._citation_score("invalid") == 0.0


class TestYearScore:
    """测试年份新鲜度评分"""

    def test_current_year(self, scorer):
        """当前年份：评分应接近 1.0"""
        from datetime import datetime
        current_year = datetime.utcnow().year
        score = scorer._year_score(current_year)
        assert score > 0.9

    def test_12_years_ago(self, scorer):
        """12 年前：评分应接近 0.0"""
        from datetime import datetime
        current_year = datetime.utcnow().year
        score = scorer._year_score(current_year - 12)
        assert score == pytest.approx(0.0, abs=0.1)

    def test_invalid_year(self, scorer):
        """无效年份：评分应为 0.0"""
        assert scorer._year_score("invalid") == 0.0


class TestFullScore:
    """测试综合评分"""

    def test_relevant_paper_scores_high(self, scorer):
        """高相关性论文：评分应 > 0.5"""
        paper = {
            "title": "Deep Learning for Natural Language Processing",
            "abstract": "This paper presents deep learning methods for NLP tasks.",
            "citation_count": 100,
            "year": 2023,
            "source": "semantic_scholar"
        }
        score = scorer.score(paper, "deep learning NLP")
        assert score > 0.5

    def test_irrelevant_paper_scores_low(self, scorer):
        """低相关性论文：评分应 < 0.3"""
        paper = {
            "title": "Cooking Recipes for Beginners",
            "abstract": "A guide to making delicious meals at home.",
            "citation_count": 0,
            "year": 2020,
            "source": "arxiv"
        }
        score = scorer.score(paper, "deep learning")
        assert score < 0.3

    def test_score_range(self, scorer):
        """评分范围：应在 [0, 1] 之间"""
        paper = {
            "title": "Test Paper",
            "abstract": "Test abstract",
            "citation_count": 50,
            "year": 2022,
            "source": "arxiv"
        }
        score = scorer.score(paper, "test topic")
        assert 0.0 <= score <= 1.0
