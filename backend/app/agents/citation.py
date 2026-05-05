"""
引用校验 Agent（CitationCheckAgent）

职责：校验综述正文中引用的 [paper_X] 编号是否真实存在于论文列表中。

工作原理：
1. 使用正则表达式提取综述中所有 [paper_X] 引用
2. 与实际论文的 paper_id 列表比对
3. 分类为有效引用和无效引用（幻觉引用）
4. 生成校验报告（总引用数、有效数、无效数、详细列表）

注意：这是同步 Agent（不需要 LLM 调用，纯正则匹配），因此 run() 不是 async。
"""

import re
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


class CitationCheckAgent:
    """引用校验 Agent：检测 LLM 生成的幻觉引用"""

    def run(self, content: str, valid_paper_ids: List[str]) -> Dict:
        """
        校验综述中的引用

        Args:
            content: 综述正文（Markdown 格式）
            valid_paper_ids: 合法的 paper_id 列表（如 ["paper_1", "paper_2"]）

        Returns:
            包含 valid_citations、invalid_citations、citation_report 的字典
        """
        logger.info("CitationCheckAgent: Checking citations")

        # 正则匹配所有 [paper_X] 格式的引用
        pattern = r'\[paper_(\d+)\]'
        found_indices = re.findall(pattern, content)

        # 构建合法 ID 集合（用于 O(1) 查找）
        valid_ids_set = set(valid_paper_ids)

        # 将提取的数字转为 paper_X 格式
        found_ids = [f"paper_{idx}" for idx in found_indices]

        # 分类有效/无效引用
        invalid = [fid for fid in found_ids if fid not in valid_ids_set]
        valid = [fid for fid in found_ids if fid in valid_ids_set]

        # 去重并保持顺序（dict.fromkeys 保序去重）
        unique_valid = list(dict.fromkeys(valid))
        unique_invalid = list(dict.fromkeys(invalid))

        # 生成校验报告
        report = self._generate_report(unique_valid, unique_invalid, content)

        logger.info(
            f"CitationCheckAgent: Found {len(unique_valid)} valid, "
            f"{len(unique_invalid)} invalid citations"
        )

        return {
            "valid_citations": unique_valid,
            "invalid_citations": unique_invalid,
            "citation_report": report
        }

    def _generate_report(
        self,
        valid: List[str],
        invalid: List[str],
        content: str
    ) -> str:
        """
        生成引用校验报告（纯文本格式）

        报告内容：
        - 总引用数、有效数、无效数
        - 无效引用列表（高亮显示）
        - 有效引用列表（最多显示 10 条）
        """
        lines = []
        lines.append(f"引用校验报告")
        lines.append(f"=" * 40)
        lines.append(f"总引用数：{len(valid) + len(invalid)}")
        lines.append(f"有效引用：{len(valid)}")
        lines.append(f"无效引用：{len(invalid)}")
        lines.append("")

        if invalid:
            lines.append("无效引用列表：")
            for inv in invalid:
                lines.append(f"  - {inv} (不存在于文献列表中)")
            lines.append("")
        else:
            lines.append("✓ 所有引用均有效")
            lines.append("")

        if valid:
            lines.append("有效引用列表：")
            for v in valid[:10]:  # 最多显示 10 条
                lines.append(f"  - {v}")
            if len(valid) > 10:
                lines.append(f"  ... 等共 {len(valid)} 处引用")

        return "\n".join(lines)
