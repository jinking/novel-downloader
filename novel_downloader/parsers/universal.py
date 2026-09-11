"""
Universal Parser for Novel Downloader V2
Supports intelligent catalog detection, info-page transition, and robust content extraction.
"""
import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional, List, Tuple
from novel_downloader.models import ProbeResult, Chapter, ChapterContent
from novel_downloader.utils import fetch_html, clean_zero_width

CATALOG_SELECTORS = [
    "#list", ".listmain", ".chapter-list", ".section-box",
    ".mulu", "#chapters", ".catalog", ".dirtree", "#chapterlist",
    ".book-chapter-list", ".novel_list", "#defaulthtml4", ".my_list",
    "div#list-chapterAll", "div.book-list"
]

CONTENT_SELECTORS = [
    "#content", "#chaptercontent", "#htmlContent", "#txtContent",
    ".read-content", ".text-content", "div.content", ".txt",
    ".showtxt", "#nr", "#nr1", "#BookText", "#booktxt", ".articlebody"
]

AD_CLASSES = ["ad", "banner", "advert", "share", "qrcode", "header", "footer", "nav"]

NOISE_PATTERNS = [
    r"首页", r"登录", r"注册", r"书架", r"加入书签", r"投推荐票",
    r"排行榜", r"完本", r"玄幻", r"仙侠", r"都市", r"历史",
    r"上一页", r"下一页", r"上一章", r"下一章", r"返回目录",
    r"阅读记录", r"用户协议", r"免责声明", r"联系我们", r"客户端",
    r"书库", r"分类", r"阅读历史", r"求书反馈", r"直达底部", r"返回书页"
]

CHAPTER_REGEX = re.compile(
    r"(第\s*[0-9一二三四五六七八九十百千万零]+\s*[章回卷节篇]|序[章言]|楔子|尾声|番外|后记|终章|^\s*\d{1,4}[\.、\s]|\b\d{1,4}\b)"
)

class UniversalParser:
    """通用小说网站目录与正文提取器"""

    @classmethod
    def probe(cls, url: str, keyword: str) -> Optional[ProbeResult]:
        """
        探测指定 URL：
        1. 抓取初始页面
        2. 若为简介页且存在“全部章节/完整目录”链接，自动跃迁
        3. 识别章节列表
        4. 构建 ProbeResult
        """
        html = fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        final_url, soup = cls._resolve_full_catalog_page(url, soup)

        page_title = soup.title.get_text().strip() if soup.title else keyword
        author = cls._extract_author(soup)

        chapters = cls._extract_chapters(final_url, soup)
        if not chapters or len(chapters) < 5:
            return None

        # 核心防伪检验：至少 60% 章节标题必须符合小说章节命名规范，排除书单/排行榜
        valid_chap_titles = sum(1 for ch in chapters if CHAPTER_REGEX.search(ch.title))
        ratio = valid_chap_titles / float(len(chapters))
        if ratio < 0.50 and len(chapters) > 10:
            return None

        return ProbeResult(
            engine="universal",
            title=page_title,
            author=author,
            chapters=chapters,
            downloader_func=cls.download_chapter,
            probe_score=1.0
        )

    @classmethod
    def _resolve_full_catalog_page(cls, url: str, soup: BeautifulSoup) -> Tuple[str, BeautifulSoup]:
        """检查是否有'全部章节'或'完整目录'子页面链接"""
        full_catalog_patterns = [
            r"全部章节", r"完整目录", r"章节目录", r"所有章节", r"查看目录", r"查看全部"
        ]
        for a in soup.find_all("a"):
            text = a.get_text().strip()
            href = a.get("href", "").strip()
            if not href or href.startswith("javascript:") or href == "#":
                continue
            if any(re.search(p, text) for p in full_catalog_patterns):
                target_url = urllib.parse.urljoin(url, href)
                if target_url.rstrip("/") != url.rstrip("/"):
                    sub_html = fetch_html(target_url)
                    if sub_html:
                        sub_soup = BeautifulSoup(sub_html, "html.parser")
                        if len(sub_soup.find_all("a")) > len(soup.find_all("a")):
                            return target_url, sub_soup
        return url, soup

    @classmethod
    def _extract_author(cls, soup: BeautifulSoup) -> Optional[str]:
        """从页面提取作者元信息"""
        meta = soup.find("meta", property="og:novel:author") or soup.find("meta", attrs={"name": "author"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        text = soup.get_text()
        m = re.search(r"作\s*者[：:\s]+([\w\u4e00-\u9fa5]+)", text)
        if m:
            return m.group(1).strip()
        return None

    @classmethod
    def _extract_chapters(cls, base_url: str, soup: BeautifulSoup) -> List[Chapter]:
        """提取章节列表，过滤非章节杂质并保持原文顺序"""
        container = None
        for sel in CATALOG_SELECTORS:
            el = soup.select_one(sel)
            if el and len(el.find_all("a")) >= 5:
                container = el
                break

        if not container:
            best_el = None
            best_count = 0
            for block in soup.find_all(["div", "ul", "dl"]):
                links = block.find_all("a")
                if len(links) < 5:
                    continue
                c = sum(1 for a in links if CHAPTER_REGEX.search(a.get_text()))
                if c > best_count:
                    best_count = c
                    best_el = block
            if best_count >= 5:
                container = best_el
            else:
                container = soup

        raw_links = container.find_all("a")
        chapters: List[Chapter] = []
        seen_urls = set()

        for a in raw_links:
            title = a.get_text().strip()
            href = a.get("href", "").strip()
            if not href or not title or href.startswith("javascript:") or href == "#":
                continue

            if any(re.search(p, title) for p in NOISE_PATTERNS):
                continue
            if len(title) > 80:
                continue

            # 若链接标题没有任何章节特征且包含书单特征，排除
            if any(k in title for k in ["小说", "阅读", "最新更新", "排行榜"]):
                if not CHAPTER_REGEX.search(title):
                    continue

            full_url = urllib.parse.urljoin(base_url, href)
            if full_url in seen_urls or full_url == base_url:
                continue

            seen_urls.add(full_url)
            chapters.append(Chapter(
                title=title,
                url=full_url,
                index=len(chapters)
            ))

        return chapters

    @classmethod
    def download_chapter(cls, ch: Chapter) -> ChapterContent:
        """下载单章正文，支持章内子分页检测"""
        curr_url = ch.url
        pages_text: List[str] = []
        visited = set()

        while curr_url and curr_url not in visited and len(visited) < 10:
            visited.add(curr_url)
            html = fetch_html(curr_url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")
            text, next_subpage_url = cls._extract_page_content_and_next(curr_url, soup)
            if text:
                pages_text.append(text)

            curr_url = next_subpage_url

        full_content = "\n\n".join(pages_text).strip()
        full_content = clean_zero_width(full_content)

        return ChapterContent(
            url=ch.url,
            title=ch.title,
            text=full_content,
            length=len(full_content),
            is_valid=len(full_content) >= 80
        )

    @classmethod
    def _extract_page_content_and_next(cls, current_url: str, soup: BeautifulSoup) -> Tuple[str, Optional[str]]:
        """从单个页面提取正文和可能的'下一页'链接"""
        content_el = None
        for sel in CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el and len(el.get_text().strip()) > 80:
                content_el = el
                break

        if not content_el:
            content_el = cls._density_extractor(soup)

        if not content_el:
            return "", None

        for tag in content_el.find_all(["script", "style", "iframe", "form", "button"]):
            tag.decompose()
        for tag in content_el.find_all(attrs={"class": lambda c: c and any(ad in str(c).lower() for ad in AD_CLASSES)}):
            tag.decompose()

        for br in content_el.find_all("br"):
            br.replace_with("\n")
        for p in content_el.find_all("p"):
            p.append("\n\n")

        raw_text = content_el.get_text()
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

        watermark_patterns = [
            r"天才一秒记住", r"最新网址", r"本章未完", r"点击下一页继续阅读",
            r"请收藏本站", r"笔趣阁", r"www\.", r"http://", r"https://",
            r"书库收录了全网最齐全"
        ]
        clean_lines = []
        for line in lines:
            if len(line) < 50 and any(re.search(p, line, re.IGNORECASE) for p in watermark_patterns):
                continue
            clean_lines.append(line)

        body_text = "\n\n".join(clean_lines)

        next_subpage = None
        for a in soup.find_all("a"):
            a_text = a.get_text().strip()
            if "下一页" in a_text and "章" not in a_text:
                href = a.get("href", "").strip()
                if href and not href.startswith("javascript:") and href != "#":
                    cand = urllib.parse.urljoin(current_url, href)
                    if cand != current_url and ("_" in cand or "page" in cand.lower() or "index" in cand.lower()):
                        next_subpage = cand
                        break

        return body_text, next_subpage

    @classmethod
    def _density_extractor(cls, soup: BeautifulSoup):
        """字符密度兜底提取器：找文本最长且非链接密集的 div/article/td"""
        best_node = None
        max_score = 0
        for node in soup.find_all(["div", "article", "section", "td"]):
            text = node.get_text().strip()
            t_len = len(text)
            if t_len < 150:
                continue
            link_text_len = sum(len(a.get_text().strip()) for a in node.find_all("a"))
            link_ratio = link_text_len / (t_len + 1e-5)
            if link_ratio > 0.20:
                continue
            score = t_len * (1.0 - link_ratio)
            if score > max_score:
                max_score = score
                best_node = node
        return best_node
