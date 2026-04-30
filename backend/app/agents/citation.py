import re
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


class CitationCheckAgent:
    def run(self, content: str, valid_paper_ids: List[str]) -> Dict:
        logger.info("CitationCheckAgent: Checking citations")

        pattern = r'\[paper_(\d+)\]'
        found_indices = re.findall(pattern, content)

        valid_ids_set = set(valid_paper_ids)

        found_ids = [f"paper_{idx}" for idx in found_indices]

        invalid = [fid for fid in found_ids if fid not in valid_ids_set]
        valid = [fid for fid in found_ids if fid in valid_ids_set]

        unique_valid = list(dict.fromkeys(valid))
        unique_invalid = list(dict.fromkeys(invalid))

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
            for v in valid[:10]:
                lines.append(f"  - {v}")
            if len(valid) > 10:
                lines.append(f"  ... 等共 {len(valid)} 处引用")

        return "\n".join(lines)
