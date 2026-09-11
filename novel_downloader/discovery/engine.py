"""
Discovery Engine: 统筹内置专用源、Google、Yandex 及 DuckDuckGo 检索
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from novel_downloader.discovery.query_builder import QueryBuilder
from novel_downloader.discovery.pool import CandidatePool
from novel_downloader.discovery.providers.builtin import BuiltinSiteProvider
from novel_downloader.discovery.providers.google import GoogleProvider
from novel_downloader.discovery.providers.yandex import YandexProvider
from novel_downloader.discovery.providers.duckduckgo import DuckDuckGoProvider
from novel_downloader.models import SearchResult, FailureRecord

class DiscoveryEngine:
    def __init__(self, name: str, author: Optional[str] = None):
        self.name = name
        self.author = author
        self.pool = CandidatePool(novel_name=name, author=author)
        self.providers = [
            BuiltinSiteProvider(),
            GoogleProvider(),
            YandexProvider(),
            DuckDuckGoProvider()
        ]
        self.provider_failures: List[FailureRecord] = []

    def discover_candidates(self, deep: bool = False) -> CandidatePool:
        queries = QueryBuilder.build_queries(self.name, self.author, deep=deep)
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_task = {}
            for q in queries:
                for provider in self.providers:
                    # 规则防风控：builtin 与 google/yandex 不滥发重复 query
                    if provider.name == "builtin" and q != queries[0]:
                        continue
                    if provider.name in ("google", "yandex") and not deep and q != queries[0]:
                        continue
                    future_to_task[executor.submit(provider.search, q, 8)] = (provider.name, q)

            for future in as_completed(future_to_task):
                prov_name, query = future_to_task[future]
                try:
                    res: List[SearchResult] = future.result()
                    if res:
                        self.pool.add_search_results(res)
                except Exception as e:
                    fail = FailureRecord(
                        stage="discovery",
                        target=prov_name,
                        reason=f"Provider 检索异常: {str(e)}",
                        details=f"query='{query}'"
                    )
                    self.provider_failures.append(fail)

        return self.pool

    def get_failures(self) -> List[FailureRecord]:
        return list(self.provider_failures)
