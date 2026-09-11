"""
Parser Router for Novel Downloader V2
Routes URLs to specialized adapters or the universal parser.
"""
from typing import Optional
from novel_downloader.models import ProbeResult
from novel_downloader.parsers.adapters.specialized import (
    HaimashuAdapter,
    B8xskAdapter,
    B111bzAdapter,
    CzbooksAdapter
)
from novel_downloader.parsers.universal import UniversalParser

class ParserRouter:
    @classmethod
    def probe(cls, url: str, keyword: str) -> Optional[ProbeResult]:
        url_lower = url.lower()
        
        # 1. 专有适配器路由
        if "haimashu.com" in url_lower:
            res = HaimashuAdapter.probe(url, keyword)
            if res:
                return res
        elif "8xsk.com" in url_lower:
            res = B8xskAdapter.probe(url, keyword)
            if res:
                return res
        elif "111bz.cc" in url_lower or "111bz." in url_lower:
            res = B111bzAdapter.probe(url, keyword)
            if res:
                return res
        elif "czbooks.net" in url_lower:
            res = CzbooksAdapter.probe(url, keyword)
            if res:
                return res
                
        # 2. 通用解析器探测与兜底
        return UniversalParser.probe(url, keyword)
