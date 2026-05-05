"""
RAG 服务单元测试

测试 LightweightRAG 的核心功能：
- 证据片段构建（build_chunks）
- 证据召回（retrieve）
- 大纲展平（_flatten_outline）
- 提示词格式化（format_for_prompt）
"""

import pytest
from app.services.rag import LightweightRAG


@pytest.fixture
def rag():
    """创建 RAG 服务实例"""
    return LightweightRAG()


@pytest.fixture
def sample_analyses():
    """示例论文分析数据"""
    return [
        {
            "paper_index": 1,
            "title": "Deep Learning for NLP",
            "abstract": "This paper reviews deep learning methods.",
            "problem": "NLP tasks require feature engineering.",
            "method": "Transformer architecture",
            "contribution": "State-of-the-art results on GLUE benchmark.",
            "limitation": "Requires large training data.",
            "source": "semantic_scholar",
            "year": 2023
        },
        {
            "paper_index": 2,
            "title": "Attention Is All You Need",
            "abstract": "Proposed the Transformer model.",
            "problem": "RNNs are slow to train.",
            "method": "Self-attention mechanism",
            "contribution": "Introduced Transformer architecture.",
            "limitation": "Quadratic complexity with sequence length.",
            "source": "arxiv",
            "year": 2017
        }
    ]


class TestBuildChunks:
    """测试证据片段构建"""

    def test_chunks_created(self, rag, sample_analyses):
        """正常数据：应创建多个证据片段"""
        chunks = rag.build_chunks(sample_analyses)
        assert len(chunks) > 0

    def test_chunk_has_required_fields(self, rag, sample_analyses):
        """每个片段应包含必要字段"""
        chunks = rag.build_chunks(sample_analyses)
        chunk = chunks[0]
        assert "chunk_id" in chunk
        assert "paper_id" in chunk
        assert "section" in chunk
        assert "text" in chunk

    def test_na_values_skipped(self, rag):
        """N/A 值应被跳过"""
        analyses = [{
            "paper_index": 1,
            "title": "Test Paper",
            "abstract": "Test abstract",
            "problem": "N/A",
            "method": "N/A",
            "contribution": "Real contribution.",
            "limitation": "N/A",
            "source": "arxiv",
            "year": 2023
        }]
        chunks = rag.build_chunks(analyses)
        sections = [c["section"] for c in chunks]
        assert "problem" not in sections
        assert "method" not in sections
        assert "contribution" in sections

    def test_text_truncated(self, rag):
        """过长文本应被截断到 900 字符"""
        analyses = [{
            "paper_index": 1,
            "title": "Test",
            "abstract": "A" * 2000,  # 超长摘要
            "problem": None,
            "method": None,
            "contribution": None,
            "limitation": None,
            "source": "arxiv",
            "year": 2023
        }]
        chunks = rag.build_chunks(analyses)
        for chunk in chunks:
            assert len(chunk["text"]) <= 900


class TestRetrieve:
    """测试证据召回"""

    def test_returns_top_k(self, rag, sample_analyses):
        """应返回 top_k 个结果"""
        chunks = rag.build_chunks(sample_analyses)
        results = rag.retrieve("deep learning", chunks, top_k=3)
        assert len(results) <= 3

    def test_relevant_chunks_ranked_higher(self, rag, sample_analyses):
        """相关片段应排在前面"""
        chunks = rag.build_chunks(sample_analyses)
        results = rag.retrieve("Transformer attention", chunks, top_k=5)
        if len(results) >= 2:
            # 第一个结果的评分应 >= 第二个
            assert results[0]["score"] >= results[1]["score"]

    def test_empty_query(self, rag, sample_analyses):
        """空查询：返回前 top_k 个片段"""
        chunks = rag.build_chunks(sample_analyses)
        results = rag.retrieve("", chunks, top_k=2)
        assert len(results) <= 2


class TestFlattenOutline:
    """测试大纲展平"""

    def test_simple_outline(self, rag):
        """简单大纲：正确展平"""
        outline = {
            "1. 引言": {"1.1 背景": None, "1.2 意义": None},
            "2. 方法": None
        }
        headings = rag._flatten_outline(outline)
        assert "1. 引言" in headings
        assert "1.1 背景" in headings
        assert "2. 方法" in headings

    def test_none_outline(self, rag):
        """None 大纲：返回空列表"""
        assert rag._flatten_outline(None) == []

    def test_empty_outline(self, rag):
        """空大纲：返回空列表"""
        assert rag._flatten_outline({}) == []


class TestFormatForPrompt:
    """测试提示词格式化"""

    def test_normal_formatting(self, rag):
        """正常数据：格式化为可读文本"""
        evidence_pack = [
            {
                "section": "2.1 技术方法",
                "evidence": [
                    {"paper_id": "paper_1", "section": "method", "title": "Test", "text": "Method description"}
                ]
            }
        ]
        result = rag.format_for_prompt(evidence_pack)
        assert "2.1 技术方法" in result
        assert "paper_1" in result

    def test_empty_pack(self, rag):
        """空证据包：返回默认消息"""
        result = rag.format_for_prompt([])
        assert "No retrieved evidence" in result


class TestBuildEvidencePack:
    """测试完整证据包构建"""

    def test_evidence_pack_structure(self, rag, sample_analyses):
        """证据包应包含 section、query、evidence 字段"""
        outline = {"1. 引言": None, "2. 方法": None}
        pack = rag.build_evidence_pack(outline, sample_analyses, "deep learning")
        if pack:
            assert "section" in pack[0]
            assert "query" in pack[0]
            assert "evidence" in pack[0]
