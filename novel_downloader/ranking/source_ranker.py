"""
Source Ranker for Novel Downloader V2
Ranks candidate sources based on multi-dimensional quality scores.
"""
from typing import List, Tuple, Optional
from novel_downloader.models import Candidate, ProbeResult, ValidationResult

class SourceRanker:
    @classmethod
    def rank(cls, evaluated: List[Tuple[Candidate, ProbeResult, ValidationResult]]) -> List[Tuple[Candidate, ProbeResult, ValidationResult]]:
        """
        排序逻辑：
        1. 达标者 (is_qualified == True) 排在未达标者前面
        2. 达标源按总评分降序排列
        3. 总分相近时（差距<=3分），章节数多且稳定的排前
        """
        def sort_key(item: Tuple[Candidate, ProbeResult, ValidationResult]):
            cand, probe, val = item
            qualified_flag = 1 if val.is_qualified else 0
            score = val.total_score
            ch_count = len(probe.chapters)
            return (qualified_flag, score, ch_count)

        return sorted(evaluated, key=sort_key, reverse=True)

    @classmethod
    def pick_best(cls, evaluated: List[Tuple[Candidate, ProbeResult, ValidationResult]]) -> Optional[Tuple[Candidate, ProbeResult, ValidationResult]]:
        ranked = cls.rank(evaluated)
        if not ranked:
            return None
        best = ranked[0]
        # 即使最高分也需要是合格的，除非强制容灾
        if best[2].is_qualified:
            return best
        return None
