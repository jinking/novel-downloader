"""
DuckDuckGo Lite 搜索驱动：纯 HTTP POST/GET，0 JS，100% 免验证码
"""
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import List
from novel_downloader.discovery.providers.base import SearchProvider
from novel_downloader.models import SearchResult

class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        results = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            rank = 1
            for td in soup.select("td a.result-link"):
                href = td.get("href", "")
                title = td.get_text().strip()
                if href.startswith("http") and not any(k in href for k in ["duckduckgo.com", "baidu.com"]):
                    results.append(SearchResult(
                        provider=self.name,
                        query=query,
                        title=title,
                        url=href,
                        rank=rank
                    ))
                    rank += 1
                    if len(results) >= limit:
                        break
        except Exception:
            pass
        return results
