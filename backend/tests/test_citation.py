"""
引用校验 Agent 单元测试

测试 CitationCheckAgent 的核心功能：
- 有效引用识别
- 无效引用（幻觉引用）检测
- 引用报告生成
"""

import pytest
from app.agents.citation import CitationCheckAgent


@pytest.fixture
def agent():
    """创建引用校验 Agent 实例"""
    return CitationCheckAgent()


class TestCitationCheck:
    """测试引用校验功能"""

    def test_valid_citations(self, agent):
        """全部有效引用：invalid_citations 应为空"""
        content = "根据研究 [paper_1] 和 [paper_2] 的结果..."
        valid_ids = ["paper_1", "paper_2"]
        result = agent.run(content, valid_ids)
        assert len(result["valid_citations"]) == 2
        assert len(result["invalid_citations"]) == 0

    def test_invalid_citations(self, agent):
        """存在幻觉引用：应被检测出来"""
        content = "根据 [paper_1] 和 [paper_99] 的研究..."  # paper_99 不存在
        valid_ids = ["paper_1", "paper_2"]
        result = agent.run(content, valid_ids)
        assert "paper_1" in result["valid_citations"]
        assert "paper_99" in result["invalid_citations"]

    def test_duplicate_citations_deduplicated(self, agent):
        """重复引用：应去重"""
        content = "[paper_1] 提出了方法，[paper_1] 证实了效果。"
        valid_ids = ["paper_1"]
        result = agent.run(content, valid_ids)
        assert result["valid_citations"].count("paper_1") == 1

    def test_no_citations(self, agent):
        """无引用：两个列表都应为空"""
        content = "这是一段没有引用的文字。"
        valid_ids = ["paper_1"]
        result = agent.run(content, valid_ids)
        assert len(result["valid_citations"]) == 0
        assert len(result["invalid_citations"]) == 0

    def test_mixed_citations(self, agent):
        """混合引用：正确分类"""
        content = "[paper_1] 和 [paper_3] 是有效的，[paper_99] 是幻觉。"
        valid_ids = ["paper_1", "paper_2", "paper_3"]
        result = agent.run(content, valid_ids)
        assert "paper_1" in result["valid_citations"]
        assert "paper_3" in result["valid_citations"]
        assert "paper_99" in result["invalid_citations"]

    def test_report_generated(self, agent):
        """报告应包含必要信息"""
        content = "[paper_1] 的研究。"
        valid_ids = ["paper_1"]
        result = agent.run(content, valid_ids)
        report = result["citation_report"]
        assert "引用校验报告" in report
        assert "总引用数" in report
        assert "有效引用" in report

    def test_all_valid_report(self, agent):
        """全部有效时报告应显示成功信息"""
        content = "[paper_1] 的研究。"
        valid_ids = ["paper_1"]
        result = agent.run(content, valid_ids)
        assert "所有引用均有效" in result["citation_report"]

    def test_has_invalid_report(self, agent):
        """存在无效引用时报告应列出无效引用"""
        content = "[paper_1] 和 [paper_99] 的研究。"
        valid_ids = ["paper_1"]
        result = agent.run(content, valid_ids)
        report = result["citation_report"]
        assert "paper_99" in report
        assert "不存在于文献列表中" in report
