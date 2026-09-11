"""
Yandex Search Provider: 独立互联网索引发现补充
"""
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import List
from novel_downloader.discovery.providers.base import SearchProvider
from novel_downloader.models import SearchResult

class YandexProvider(SearchProvider):
    name = "yandex"

    def search(self, query: str, limit: int = 8) -> List[SearchResult]:
        url = f"https://yandex.com/search/?text={urllib.parse.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        results = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # 检测是否存在验证码或阻断
            if "smartcaptcha" in html.lower() or "showcaptcha" in html.lower():
                raise RuntimeError("Yandex SmartCaptcha triggered (human verification required)")

            soup = BeautifulSoup(html, "html.parser")
            rank = 1
            # 解析 Yandex 典型搜索结果节点
            items = soup.select("li.serp-item, div.organic, div.VanillaReact")
            for item in items:
                link_el = item.select_one("a.OrganicTitle-Link, h2 a, a.link")
                if not link_el:
                    continue
                href = link_el.get("href", "")
                title = link_el.get_text().strip()
                if not href or not title or not href.startswith("http") or "yandex" in href:
                    continue

                snippet_el = item.select_one("div.OrganicText, div.text-container")
                snippet = snippet_el.get_text().strip() if snippet_el else None

                results.append(SearchResult(
                    provider=self.name,
                    query=query,
                    title=title,
                    url=href,
                    snippet=snippet,
                    rank=rank
                ))
                rank += 1
                if len(results) >= limit:
                    break
        except Exception as e:
            # 向上重新抛出供 Engine 记录 FailureRecord，同时保证被 Engine 妥善隔离
            raise e

        return results
