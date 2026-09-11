"""
Built-in Specialized Site Search Provider
Directly probes known resilient novel archives (Haimashu, Czbooks, 8xsk, etc.)
"""
import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import List
from novel_downloader.discovery.providers.base import SearchProvider
from novel_downloader.models import SearchResult
from novel_downloader.utils import fetch_html

class BuiltinSiteProvider(SearchProvider):
    name = "builtin"

    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        results: List[SearchResult] = []
        clean_name = query.split()[0] if query else ""
        if not clean_name:
            return results

        # 1. 小说狂人 (czbooks.net)
        try:
            cz_url = f"https://czbooks.net/s/{urllib.parse.quote(clean_name)}"
            cz_html = fetch_html(cz_url)
            if cz_html:
                soup = BeautifulSoup(cz_html, "html.parser")
                for a in soup.select("ul.novel-item-list a, div.novel-item a"):
                    title = a.get_text().strip()
                    href = a.get("href", "")
                    if clean_name in title and "/n/" in href:
                        f_url = "https:" + href if href.startswith("//") else (href if href.startswith("http") else f"https://czbooks.net{href}")
                        results.append(SearchResult(
                            provider=self.name,
                            query=query,
                            title=title,
                            url=f_url,
                            rank=1
                        ))
                        break
        except Exception:
            pass

        # 2. 海马读书网 (haimashu.com)
        try:
            hm_url = f"https://www.haimashu.com/search/{urllib.parse.quote(clean_name)}"
            hm_html = fetch_html(hm_url)
            if hm_html:
                soup = BeautifulSoup(hm_html, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    title = a.get_text().strip()
                    if "/book/" in href and clean_name in title:
                        m = re.search(r"/book/(\d+)", href)
                        if m:
                            results.append(SearchResult(
                                provider=self.name,
                                query=query,
                                title=title,
                                url=f"https://www.haimashu.com/book/{m.group(1)}",
                                rank=1
                            ))
                            break
        except Exception:
            pass

        # 3. 八叉书库 (8xsk.com)
        try:
            bx_url = f"https://www.8xsk.com/search/?searchkey={urllib.parse.quote(clean_name)}"
            bx_html = fetch_html(bx_url, headers={"Cookie": "age18_ok=1"})
            if bx_html:
                soup = BeautifulSoup(bx_html, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    title = a.get_text().strip()
                    if "/book/" in href and clean_name in title:
                        m = re.search(r"/book/(\d+)", href)
                        if m:
                            results.append(SearchResult(
                                provider=self.name,
                                query=query,
                                title=title,
                                url=f"https://www.8xsk.com/book/{m.group(1)}.html",
                                rank=1
                            ))
                            break
        except Exception:
            pass

        return results[:limit]
