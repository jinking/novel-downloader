"""
Google Search Provider: 通过本地 OpenCLI 受信任 Chrome 浏览器驱动
"""
import json
import subprocess
import urllib.parse
from typing import List
from novel_downloader.discovery.providers.base import SearchProvider
from novel_downloader.models import SearchResult

class GoogleProvider(SearchProvider):
    name = "google"

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        results = []
        try:
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            subprocess.run(["opencli", "browser", "default", "open", search_url],
                           capture_output=True, text=True, timeout=10)
            
            eval_js = """(function() {
              var res = [];
              var items = document.querySelectorAll('div.g, div[data-hveid]');
              for (var i = 0; i < items.length; i++) {
                var a = items[i].querySelector('a');
                var h3 = items[i].querySelector('h3');
                if (a && h3 && a.href.startsWith('http') && !a.href.includes('google.com')) {
                  res.push({ title: h3.textContent.trim(), url: a.href });
                }
              }
              return res.slice(0, 10);
            })()"""
            p = subprocess.run(["opencli", "browser", "default", "eval", eval_js],
                               capture_output=True, text=True, timeout=10)
            items = json.loads(p.stdout)
            for rank, it in enumerate(items, 1):
                results.append(SearchResult(
                    provider=self.name,
                    query=query,
                    title=it.get("title", ""),
                    url=it.get("url", ""),
                    rank=rank
                ))
                if len(results) >= limit:
                    break
        except Exception:
            pass
        return results
