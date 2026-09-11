"""
Discovery Engine: 统筹内置专用源、DuckDuckGo 及 Google 驱动
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from novel_downloader.discovery.query_builder import QueryBuilder
from novel_downloader.discovery.pool import CandidatePool
from novel_downloader.discovery.providers.builtin import BuiltinSiteProvider
from novel_downloader.discovery.providers.duckduckgo import DuckDuckGoProvider
from novel_downloader.discovery.providers.google import GoogleProvider
from novel_downloader.models import SearchResult

class DiscoveryEngine:
    def __init__(self, name: str, author: Optional[str] = None):
        self.name = name
        self.author = author
        self.pool = CandidatePool(novel_name=name, author=author)
        self.providers = [
            BuiltinSiteProvider(),
            DuckDuckGoProvider(),
            GoogleProvider()
        ]

    def discover_candidates(self, deep: bool = False) -> CandidatePool:
        queries = QueryBuilder.build_queries(self.name, self.author, deep=deep)
        
        # 多词路并发检索
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_task = {}
            for q in queries:
                for provider in self.providers:
                    # 避免对 Google 或 Builtin 滥发过多重复查询
                    if provider.name == "builtin" and q != queries[0]:
                        continue
                    if provider.name == "google" and not deep and q != queries[0]:
                        continue
                    future_to_task[executor.submit(provider.search, q, 8)] = (provider.name, q)

            for future in as_completed(future_to_task):
                prov_name, query = future_to_task[future]
                try:
                    res: List[SearchResult] = future.result()
                    if res:
                        self.pool.add_search_results(res)
                except Exception:
                    pass

        return self.pool
