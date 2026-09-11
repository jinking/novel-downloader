from novel_downloader.discovery.pool import CandidatePool
from novel_downloader.models import SearchResult

def test_candidate_pool_deduplication_and_ranking():
    pool = CandidatePool("诛仙", "萧鼎")
    results = [
        SearchResult(provider="google", query="q1", title="《诛仙》 萧鼎 目录", url="https://example.com/book/1?utm_source=test", rank=1),
        SearchResult(provider="yandex", query="q2", title="《诛仙》 全本在线阅读", url="https://example.com/book/1", rank=2),
        SearchResult(provider="duckduckgo", query="q3", title="起点付费站", url="https://qidian.com/book/2019", rank=3)
    ]
    pool.add_search_results(results)

    # 验证去重及黑名单过滤 (qidian.com 被剔除)
    assert pool.count() == 1

    ranked = pool.rank_candidates()
    assert len(ranked) == 1
    # 命中多引擎 + 命中书名和作者，得分应高于基础分 50
    assert ranked[0].discovery_score >= 90.0
    assert len(ranked[0].discovered_by) == 2
