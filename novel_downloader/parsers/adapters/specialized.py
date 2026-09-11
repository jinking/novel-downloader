"""
Built-in Specialized Adapters (AES, Base64, Sub-page pagination, etc.)
"""
import re
import base64
import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional, List, Tuple
from novel_downloader.models import Candidate, ProbeResult, Chapter, ChapterContent
from novel_downloader.utils import fetch_html, clean_zero_width, decrypt_aes_cbc, MOBILE_HEADERS

# 1. 海马读书网 (haimashu.com) - AES-128-CBC
class HaimashuAdapter:
    BASE_URL = "https://www.haimashu.com"

    @classmethod
    def probe(cls, url: str, keyword: str) -> Optional[ProbeResult]:
        m = re.search(r"/book/(\d+)", url)
        if not m:
            return None
        bid = m.group(1)
        first_cat = f"{cls.BASE_URL}/book/{bid}/catalog/"
        html = fetch_html(first_cat)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        max_p = 1
        for a in soup.find_all("a"):
            m_p = re.search(rf"/book/{bid}/catalog/(\d+)\.html", a.get("href", ""))
            if m_p and int(m_p.group(1)) > max_p:
                max_p = int(m_p.group(1))

        chapters: List[Chapter] = []
        seen = set()
        for p in range(1, max_p + 1):
            p_url = f"{cls.BASE_URL}/book/{bid}/catalog/{p}.html" if p > 1 else first_cat
            p_html = fetch_html(p_url) if p > 1 else html
            p_soup = BeautifulSoup(p_html, "html.parser")
            for a in p_soup.find_all("a", class_="g"):
                b64 = None
                t_val = None
                for k, v in a.attrs.items():
                    if isinstance(v, str) and v.startswith("L2Jvb2s"): b64 = v
                    elif isinstance(v, str) and "分卷阅读" in v: t_val = v
                if b64:
                    real = base64.b64decode(b64).decode("utf-8")
                    f_url = real if real.startswith("http") else cls.BASE_URL + real
                    if f_url not in seen:
                        seen.add(f_url)
                        chapters.append(Chapter(title=t_val or a.get_text().strip(), url=f_url, index=len(chapters)))

        if chapters:
            return ProbeResult(
                engine="haimashu",
                title=soup.title.get_text().strip() if soup.title else keyword,
                chapters=chapters,
                downloader_func=cls.download_chapter
            )
        return None

    @classmethod
    def download_chapter(cls, ch: Chapter) -> ChapterContent:
        html = fetch_html(ch.url)
        if not html:
            return ChapterContent(url=ch.url, title=ch.title, text="", is_valid=False)
        m = re.search(r"\.html\(d\([\"\'](.*?)[\"\'],\s*[\"\'](.*?)[\"\']\)\)", html)
        if m:
            text = decrypt_aes_cbc(m.group(1), m.group(2))
            text = clean_zero_width(text)
            return ChapterContent(url=ch.url, title=ch.title, text=text, length=len(text), is_valid=bool(text))
        return ChapterContent(url=ch.url, title=ch.title, text="", is_valid=False)

# 2. 八叉书库 (8xsk.com) - 18+ Cookie & Base64
class B8xskAdapter:
    BASE_URL = "https://www.8xsk.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": "age18_ok=1"
    }

    @classmethod
    def probe(cls, url: str, keyword: str) -> Optional[ProbeResult]:
        m = re.search(r"/book/(\d+)", url)
        if not m:
            return None
        bid = m.group(1)
        html = fetch_html(f"{cls.BASE_URL}/book/{bid}.html", headers=cls.HEADERS)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        chapters: List[Chapter] = []
        seen = set()
        for a in soup.find_all("a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if not href or not title: continue
            if f"/read/{bid}_" in href:
                f_url = urllib.parse.urljoin(cls.BASE_URL, href)
                if f_url not in seen:
                    seen.add(f_url)
                    chapters.append(Chapter(title=title, url=f_url, index=len(chapters)))

        if chapters:
            return ProbeResult(
                engine="8xsk",
                title=soup.title.get_text().strip() if soup.title else keyword,
                chapters=chapters,
                downloader_func=cls.download_chapter
            )
        return None

    @classmethod
    def download_chapter(cls, ch: Chapter) -> ChapterContent:
        html = fetch_html(ch.url, headers=cls.HEADERS)
        if not html:
            return ChapterContent(url=ch.url, title=ch.title, text="", is_valid=False)
        m = re.search(r"window\.atob\([\"\'](.*?)[\"\']\)", html)
        if m:
            text = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            clean = "\n\n".join(lines)
            return ChapterContent(url=ch.url, title=ch.title, text=clean, length=len(clean), is_valid=bool(clean))
        return ChapterContent(url=ch.url, title=ch.title, text="", is_valid=False)

# 3. 第一版主 (111bz.cc) - 移动端多子页无缝递归
class B111bzAdapter:
    MOBILE_BASE = "https://m.111bz.cc"

    @classmethod
    def probe(cls, url: str, keyword: str) -> Optional[ProbeResult]:
        m = re.search(r"/(9_\d+)", url)
        if not m:
            return None
        bid = m.group(1)
        html = fetch_html(f"https://www.111bz.cc/{bid}/", encoding="gbk")
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        chapters: List[Chapter] = []
        seen = set()
        for a in soup.find_all("a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if not href or not href.endswith(".html") or not title: continue
            m_url = href.replace("www.111bz.cc", "m.111bz.cc") if href.startswith("http") else f"{cls.MOBILE_BASE}{href}"
            if m_url not in seen:
                seen.add(m_url)
                chapters.append(Chapter(title=title, url=m_url, index=len(chapters)))

        if chapters:
            return ProbeResult(
                engine="111bz",
                title=soup.title.get_text().strip() if soup.title else keyword,
                chapters=chapters,
                downloader_func=cls.download_chapter
            )
        return None

    @classmethod
    def download_chapter(cls, ch: Chapter) -> ChapterContent:
        curr = ch.url
        pages = []
        while curr:
            html = fetch_html(curr, headers=MOBILE_HEADERS, encoding="gbk")
            if not html: break
            soup = BeautifulSoup(html, "html.parser")
            nr = soup.find("div", id="nr1")
            if nr:
                for tag in nr.find_all(["script", "style", "a"]): tag.decompose()
                lines = [l.strip() for l in nr.get_text("\n").split("\n") if l.strip()]
                clean = [l for l in lines if not any(k in l for k in ["阅读地址", "111bz", "书友群"])]
                if clean: pages.append("\n\n".join(clean))
            next_p = None
            for a in soup.find_all("a"):
                if "下一页" in a.get_text():
                    h = a.get("href", "")
                    if h and "_" in h and h.endswith(".html"):
                        next_p = f"{cls.MOBILE_BASE}{h}" if h.startswith("/") else h
                        break
            curr = next_p
        full_text = "\n\n".join(pages)
        return ChapterContent(url=ch.url, title=ch.title, text=full_text, length=len(full_text), is_valid=bool(full_text))

# 4. 小说狂人 (czbooks.net)
class CzbooksAdapter:
    BASE_URL = "https://czbooks.net"

    @classmethod
    def probe(cls, url: str, keyword: str) -> Optional[ProbeResult]:
        m = re.search(r"/n/([a-z0-9]+)", url)
        if not m:
            return None
        slug = m.group(1)
        html = fetch_html(f"{cls.BASE_URL}/n/{slug}")
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        chapters: List[Chapter] = []
        seen = set()
        for a in soup.select("ul.chapter-list a, li a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if not href or f"/n/{slug}/" not in href: continue
            f_url = "https:" + href if href.startswith("//") else href
            if f_url not in seen:
                seen.add(f_url)
                chapters.append(Chapter(title=title, url=f_url, index=len(chapters)))

        if chapters:
            return ProbeResult(
                engine="czbooks",
                title=soup.title.get_text().strip() if soup.title else keyword,
                chapters=chapters,
                downloader_func=cls.download_chapter
            )
        return None

    @classmethod
    def download_chapter(cls, ch: Chapter) -> ChapterContent:
        html = fetch_html(ch.url)
        if not html:
            return ChapterContent(url=ch.url, title=ch.title, text="", is_valid=False)
        soup = BeautifulSoup(html, "html.parser")
        c = soup.select_one("div.content")
        if not c:
            return ChapterContent(url=ch.url, title=ch.title, text="", is_valid=False)
        for tag in c.find_all(["script", "style", "a"]): tag.decompose()
        lines = [l.strip() for l in c.get_text("\n").split("\n") if l.strip()]
        full_text = "\n\n".join(lines)
        return ChapterContent(url=ch.url, title=ch.title, text=full_text, length=len(full_text), is_valid=bool(full_text))
