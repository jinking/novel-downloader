from novel_downloader.ranking.source_ranker import SourceRanker
from novel_downloader.models import Candidate, ProbeResult, ValidationResult, Chapter

def test_source_ranker_prefers_qualified_over_more_chapters():
    # Candidate A: 章节数多 (1800章)，但未达标 (score 55, qualified=False)
    cand_a = Candidate(url="https://site-a.com", domain="site-a.com")
    probe_a = ProbeResult(
        engine="universal",
        title="测试书",
        chapters=[Chapter(title=f"第{i}章", url=f"https://site-a.com/{i}", index=i) for i in range(1800)],
        downloader_func=lambda ch: None
    )
    val_a = ValidationResult(total_score=55.0, is_qualified=False, reasons=["正文截断"])

    # Candidate B: 章节数稍少 (1300章)，但完全达标 (score 78, qualified=True)
    cand_b = Candidate(url="https://site-b.com", domain="site-b.com")
    probe_b = ProbeResult(
        engine="universal",
        title="测试书",
        chapters=[Chapter(title=f"第{i}章", url=f"https://site-b.com/{i}", index=i) for i in range(1300)],
        downloader_func=lambda ch: None
    )
    val_b = ValidationResult(total_score=78.0, is_qualified=True)

    evaluated = [(cand_a, probe_a, val_a), (cand_b, probe_b, val_b)]

    ranked = SourceRanker.rank(evaluated)
    assert ranked[0][0].domain == "site-b.com"
    assert ranked[0][2].is_qualified is True

    best = SourceRanker.pick_best(evaluated)
    assert best is not None
    assert best[0].domain == "site-b.com"
    assert best[2].is_qualified is True

def test_source_ranker_pick_best_returns_none_when_all_unqualified():
    cand_a = Candidate(url="https://site-a.com", domain="site-a.com")
    probe_a = ProbeResult(
        engine="universal",
        title="测试书",
        chapters=[Chapter(title="第1章", url="https://site-a.com/1")],
        downloader_func=lambda ch: None
    )
    val_a = ValidationResult(total_score=40.0, is_qualified=False)

    best = SourceRanker.pick_best([(cand_a, probe_a, val_a)])
    # 当没有合格源时，pick_best 坚决返回 None
    assert best is None
