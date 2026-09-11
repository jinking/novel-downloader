#!/usr/bin/env python3
"""
Novel Downloader - Universal Novel Scraper & Anti-Crawler Decryptor
Architecture:
  Level 1: Built-in Specialized Novel Engines (AES-128-CBC, Base64, multi-page, etc.)
  Level 2: Zero-Captcha Search Fallback (DuckDuckGo Lite HTTP API - 100% No Captcha)
  Level 3: Local Chrome Google Engine Fallback (Via OpenCLI with existing user trust profile)
  Universal Novel Parser: Adaptive directory & content extractor for any third-party novel site.
"""

import os
import sys
import time
import gzip
import re
import json
import base64
import hashlib
import unicodedata
import argparse
import subprocess
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

import urllib.error

# Ensure non-buffered stdout for real-time logs
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
}

def clean_zero_width(text):
    text = unicodedata.normalize("NFKC", text)
    zero_width = [
        "\u200b", "\u200c", "\u200d", "\u200e", "\u200f",
        "\ufeff", "\u00ad", "\u202a", "\u202b", "\u202c",
        "\u202d", "\u202e", "\u2060", "\u180e"
    ]
    for ch in zero_width:
        text = text.replace(ch, "")
    return text

def fetch_html(url, headers=None, retries=2, delay=0.2, encoding=None):
    if not headers:
        headers = HEADERS
    if url.startswith("//"):
        url = "https:" + url
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                final_url = resp.geturl()
                if "google.com" in final_url or "baidu.com" in final_url:
                    return ""
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip" or (len(raw) >= 2 and raw[:2] == b"\x1f\x8b"):
                    raw = gzip.decompress(raw)
                
                # 自动侦测 GBK / GB2312
                enc = encoding
                if not enc:
                    header_content = raw[:1024].lower()
                    if b"charset=gbk" in header_content or b"charset=\"gbk\"" in header_content or b"charset=gb2312" in header_content:
                        enc = "gbk"
                    else:
                        enc = "utf-8"
                return raw.decode(enc, errors="ignore")
        except urllib.error.HTTPError as he:
            if he.code in (403, 404, 410):
                return ""
            time.sleep(delay)
        except Exception:
            time.sleep(delay)
    return ""

def decrypt_haimashu_aes(cipher_b64, key_str):
    cipher_b64 = cipher_b64.replace(r"\/", "/")
    md5_hex = hashlib.md5(key_str.encode("utf-8")).hexdigest()
    iv = md5_hex[:16].encode("utf-8")
    key = md5_hex[16:].encode("utf-8")
    raw_cipher = base64.b64decode(cipher_b64)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(raw_cipher) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted.decode("utf-8", errors="ignore")

# ==================== Level 1: Specialized Adapters ==================== #

class HaimashuAdapter:
    BASE_URL = "https://www.haimashu.com"

    @classmethod
    def search(cls, keyword):
        url = f"{cls.BASE_URL}/search/{urllib.parse.quote(keyword)}"
        html = fetch_html(url)
        if not html: return None
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if "/book/" in href and keyword in title:
                m = re.search(r"/book/(\d+)/", href)
                if m: return {"engine": "haimashu", "bid": m.group(1), "title": title}
        return None

    @classmethod
    def get_chapters(cls, bid):
        first_cat = f"{cls.BASE_URL}/book/{bid}/catalog/"
        html = fetch_html(first_cat)
        soup = BeautifulSoup(html, "html.parser")
        max_p = 1
        for a in soup.find_all("a"):
            m = re.search(rf"/book/{bid}/catalog/(\d+)\.html", a.get("href", ""))
            if m and int(m.group(1)) > max_p: max_p = int(m.group(1))
        
        items = []
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
                        items.append((t_val or a.get_text().strip(), f_url))
        
        def num_sort(it):
            m = re.search(r"\d+", it[0])
            return int(m.group()) if m else 99999
        items.sort(key=num_sort)
        return items

    @classmethod
    def download_chapter(cls, item):
        title, url = item
        html = fetch_html(url)
        if not html: return url, title, ""
        m = re.search(r"\.html\(d\([\"\'](.*?)[\"\'],\s*[\"\'](.*?)[\"\']\)\)", html)
        if m:
            c_text, k_text = m.groups()
            raw_html = decrypt_haimashu_aes(c_text, k_text)
            soup = BeautifulSoup(raw_html, "html.parser")
            lines = [clean_zero_width(p.get_text().strip()) for p in soup.find_all(["p", "div"]) if p.get_text().strip()]
            return url, title, "\n\n".join(lines)
        soup = BeautifulSoup(html, "html.parser")
        c = soup.select_one("div.RBGsectionThree-content")
        return url, title, clean_zero_width(c.get_text("\n", strip=True)) if c else ""

class B8xskAdapter:
    BASE_URL = "https://8xsk.com"
    COOKIE = "age18_ok=1; jieqiVisitId=article_articleviews%3D6401"

    @classmethod
    def search(cls, keyword):
        url = f"{cls.BASE_URL}/search/?searchkey={urllib.parse.quote(keyword)}"
        html = fetch_html(url, headers={**HEADERS, "Cookie": cls.COOKIE})
        if not html: return None
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if "/book/" in href and keyword in title:
                m = re.search(r"/book/(\d+)\.html", href)
                if m: return {"engine": "8xsk", "bid": m.group(1), "title": title}
        return None

    @classmethod
    def get_chapters(cls, bid):
        # Scan index pages
        pages = [f"{cls.BASE_URL}/book/{bid}_1.html", f"{cls.BASE_URL}/book/{bid}_2.html"]
        items = []
        seen = set()
        for p_url in pages:
            html = fetch_html(p_url, headers={**HEADERS, "Cookie": cls.COOKIE})
            if not html: continue
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a"):
                href = a.get("href", "")
                title = re.sub(r"\s*\(\d+-\d+\)\s*", "", a.get_text().strip())
                if f"/read/{bid}/" in href and href.endswith(".html") and title:
                    f_url = href if href.startswith("http") else cls.BASE_URL + href
                    if f_url not in seen:
                        seen.add(f_url)
                        items.append((title, f_url))
        return items

    @classmethod
    def download_chapter(cls, item):
        title, url = item
        html = fetch_html(url, headers={**HEADERS, "Cookie": cls.COOKIE})
        if not html: return url, title, ""
        m = re.search(r'atob\([\"\']([A-Za-z0-9+/=]+)[\"\']\)', html)
        if m:
            plain = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
            soup = BeautifulSoup(plain, "html.parser")
            lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]
            clean = [l for l in lines if not any(k in l for k in ["若无法读取正文", "本站发布页", "8xsk"])]
            return url, title, "\n\n".join(clean)
        return url, title, ""

class AaddkkAdapter:
    DOMAINS = ["https://www.aaddkk.com", "https://www.aakkcc.com"]

    @classmethod
    def search(cls, keyword):
        for base in cls.DOMAINS:
            url = f"{base}/search/?searchkey={urllib.parse.quote(keyword)}"
            html = fetch_html(url)
            if not html: continue
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a"):
                href = a.get("href", "")
                title = a.get_text().strip()
                if "/book/" in href and keyword in title:
                    m = re.search(r"/book/(\d+)/", href)
                    if m: return {"engine": "aaddkk", "base": base, "bid": m.group(1), "title": title}
        return None

    @classmethod
    def get_chapters(cls, info):
        base, bid = info["base"], info["bid"]
        html = fetch_html(f"{base}/book/{bid}/")
        soup = BeautifulSoup(html, "html.parser")
        chapters = []
        seen = set()
        for a in soup.find_all("a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if not href or f"/book/{bid}/" not in href or not href.endswith(".html"):
                continue
            if title in ["开始阅读", "上一章", "下一章", ""]: continue
            f_url = href if href.startswith("http") else base + href
            if f_url not in seen:
                seen.add(f_url)
                chapters.append((title, f_url))
        return chapters

    @classmethod
    def download_chapter(cls, item):
        title, url = item
        html = fetch_html(url)
        if not html: return url, title, ""
        soup = BeautifulSoup(html, "html.parser")
        c = soup.find("div", id="content")
        if not c: return url, title, ""
        for tag in c.find_all(["script", "style", "a"]): tag.decompose()
        lines = [l.strip() for l in c.get_text("\n").split("\n") if l.strip()]
        clean = [l for l in lines if not any(k in l for k in ["请记住本书", "最新章节", "天才一秒"])]
        return url, title, "\n\n".join(clean)

class B111bzAdapter:
    PC_BASE = "http://www.111bz.cc"
    MOBILE_BASE = "http://m.111bz.cc"

    @classmethod
    def search(cls, keyword):
        try:
            url = f"{cls.PC_BASE}/modules/article/search.php?searchkey={urllib.parse.quote(keyword.encode('gbk'))}"
            html = fetch_html(url, encoding="gbk")
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a"):
                href = a.get("href", "")
                title = a.get_text().strip()
                if "/9_" in href and keyword in title:
                    m = re.search(r"/(9_\d+)/", href)
                    if m: return {"engine": "111bz", "bid": m.group(1), "title": title}
        except Exception: pass
        return None

    @classmethod
    def get_chapters(cls, bid):
        html = fetch_html(f"{cls.PC_BASE}/{bid}/", encoding="gbk")
        soup = BeautifulSoup(html, "html.parser")
        chapters = []
        seen = set()
        for a in soup.select("div#list a, dl dd a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if not href or not href.endswith(".html") or not title: continue
            m_url = href.replace("www.111bz.cc", "m.111bz.cc") if href.startswith("http") else f"{cls.MOBILE_BASE}{href}"
            if m_url not in seen:
                seen.add(m_url)
                chapters.append((title, m_url))
        return chapters

    @classmethod
    def download_chapter(cls, item):
        orig_title, start_url = item
        curr = start_url
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
        return start_url, orig_title, "\n\n".join(pages)

class CzbooksAdapter:
    BASE_URL = "https://czbooks.net"

    @classmethod
    def search(cls, keyword):
        url = f"{cls.BASE_URL}/s/{urllib.parse.quote(keyword)}"
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("ul.novel-item-list a, div.novel-item a"):
            title = a.get_text().strip()
            href = a.get("href", "")
            if keyword in title and "/n/" in href:
                slug = href.split("/n/")[1].split("/")[0]
                return {"engine": "czbooks", "slug": slug, "title": title}
        return None

    @classmethod
    def get_chapters(cls, slug):
        html = fetch_html(f"{cls.BASE_URL}/n/{slug}")
        soup = BeautifulSoup(html, "html.parser")
        chapters = []
        seen = set()
        for a in soup.select("ul.chapter-list a, li a"):
            href = a.get("href", "")
            title = a.get_text().strip()
            if not href or f"/n/{slug}/" not in href or not title.startswith("第"):
                continue
            f_url = "https:" + href if href.startswith("//") else href
            if f_url not in seen:
                seen.add(f_url)
                chapters.append((title, f_url))
        return chapters

    @classmethod
    def download_chapter(cls, item):
        title, url = item
        html = fetch_html(url)
        if not html: return url, title, ""
        soup = BeautifulSoup(html, "html.parser")
        c = soup.select_one("div.content")
        if not c: return url, title, ""
        for tag in c.find_all(["script", "style", "a"]): tag.decompose()
        lines = [l.strip() for l in c.get_text("\n").split("\n") if l.strip()]
        return url, title, "\n\n".join(lines)

# ==================== Level 2 & 3: Anti-Verification Search Fallbacks ==================== #

class SearchFallbackEngine:
    @staticmethod
    def search_duckduckgo_lite(keyword):
        """
        Level 2 Fallback: Pure HTTP, lightweight, zero JS execution, 100% immune to anti-bot captchas.
        """
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": f"{keyword} 小说 目录"}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        results = []
        try:
            html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            for td in soup.select("td a.result-link"):
                href = td.get("href", "")
                title = td.get_text().strip()
                if href.startswith("http") and not any(k in href for k in ["duckduckgo", "baidu.com"]):
                    results.append({"title": title, "url": href})
        except Exception:
            pass
        return results

    @staticmethod
    def search_chrome_google(keyword):
        """
        Level 3 Fallback: Uses existing active Chrome browser session with Google.
        Google does not trigger smartcaptcha / puzzle verification under human profile.
        """
        try:
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(keyword + ' 小说 目录')}"
            subprocess.run(["opencli", "browser", "default", "open", search_url],
                           capture_output=True, text=True, timeout=10)
            
            eval_js = """(function() {
              var res = [];
              var items = document.querySelectorAll('div.g, div[data-hveid]');
              for (var i = 0; i < items.length; i++) {
                var a = items[i].querySelector('a');
                var h3 = items[i].querySelector('h3');
                if (a && h3) {
                  var href = a.href || '';
                  var title = h3.textContent.trim();
                  if (href.startsWith('http') && !href.includes('google.com')) {
                    res.push({ title: title, url: href });
                  }
                }
              }
              return res.slice(0, 10);
            })()"""
            p = subprocess.run(["opencli", "browser", "default", "eval", eval_js],
                               capture_output=True, text=True, timeout=10)
            return json.loads(p.stdout)
        except Exception:
            return []

# ==================== Universal Adaptive Novel Parser ==================== #

class UniversalNovelParser:
    """
    Auto-detects chapter lists and text containers on arbitrary third-party novel sites.
    """
    NAV_BLACKLIST = {
        "换肤", "阅读记录", "首页", "书架", "书库", "排行榜", "完本", "玄幻", "武侠",
        "都市", "历史", "军事", "网游", "科幻", "恐怖", "全本", "下一页", "上一页",
        "返回书页", "加入书架", "推荐本书", "书友留言", "登录", "注册", "客户端", "APP",
        "目录", "简介", "投票", "打赏", "章节错误", "点此举报"
    }

    @classmethod
    def probe_and_parse(cls, target_url, keyword):
        html = fetch_html(target_url)
        if not html: return None
        soup = BeautifulSoup(html, "html.parser")

        base_host = urllib.parse.urlparse(target_url).scheme + "://" + urllib.parse.urlparse(target_url).netloc
        base_path = urllib.parse.urlparse(target_url).path.rstrip("/")
        if "." in os.path.basename(base_path):
            base_path = os.path.dirname(base_path)

        # 优先在主流目录容器中寻找
        candidate_containers = []
        for tag_name in ["div", "dl", "ul"]:
            for el in soup.find_all(tag_name):
                el_id = el.get("id", "") or ""
                el_cls = " ".join(el.get("class", [])) if el.get("class") else ""
                if any(k in (el_id + " " + el_cls).lower() for k in ["list", "dir", "chapter", "catalog", "volume"]):
                    candidate_containers.append(el)

        # 如果没有找到带名字的容器，就考虑整个页面
        if not candidate_containers:
            candidate_containers = [soup]

        best_chapters = []
        for container in candidate_containers:
            chapters = []
            seen = set()
            for a in container.find_all("a"):
                href = a.get("href", "")
                title = a.get_text().strip()
                if not href or not title: continue
                if href.startswith("javascript:") or href.startswith("#"): continue
                if title in cls.NAV_BLACKLIST: continue

                # 必须符合章节命名特征或者处于目录容器内
                has_chap_num = bool(re.search(r"第\s*[0-9一二三四五六七八九十百千万]+\s*[章回卷节篇]", title))
                has_chap_mark = any(k in title for k in ["章", "回", "卷", "节", "序", "楔子", "尾声", "外传", "后记", "感言", "番外"])
                
                # 只有当包含章节特征词，或者包含连续序号且排除导航词时才收录
                if not (has_chap_num or has_chap_mark):
                    # 如果都不带，但链接数量很大且标题长度适中
                    if len(title) > 30 or any(k in title for k in ["小说", "网", "最新", "在线阅读"]):
                        continue

                # 补全 URL
                if href.startswith("http"): full_url = href
                elif href.startswith("/"): full_url = base_host + href
                else: full_url = base_host + base_path + "/" + href

                if full_url not in seen and full_url != target_url:
                    seen.add(full_url)
                    chapters.append((title, full_url))

            if len(chapters) > len(best_chapters):
                best_chapters = chapters

        # 如果章节数量较少（< 50），尝试寻找“查看全部章节/完整目录”链接进行二次跟进
        if len(best_chapters) < 50:
            for a in soup.find_all("a"):
                t = a.get_text().strip()
                h = a.get("href", "")
                if not h or h.startswith("javascript:") or h.startswith("#"): continue
                if any(k in t for k in ["查看全部", "全部章节", "完整目录", "完整列表", "所有章节", "查看目录", "全部目录"]):
                    next_target = urllib.parse.urljoin(target_url, h)
                    if next_target != target_url:
                        # 递归跟进真实完整目录
                        sub_res = cls.probe_and_parse(next_target, keyword)
                        if sub_res and len(sub_res["chapters"]) > len(best_chapters):
                            return sub_res

        if len(best_chapters) >= 5:
            # 过滤掉首尾可能混入的非章节噪音
            cleaned_chapters = []
            for t, u in best_chapters:
                if t in cls.NAV_BLACKLIST: continue
                cleaned_chapters.append((t, u))

            return {
                "engine": "universal",
                "title": soup.title.string.strip() if soup.title else keyword,
                "chapters": cleaned_chapters,
                "downloader": cls.download_chapter
            }
        return None

    @classmethod
    def download_chapter(cls, item):
        title, url = item
        html = fetch_html(url)
        if not html: return url, title, ""
        soup = BeautifulSoup(html, "html.parser")
        
        # 常见正文容器选择器
        c = (soup.find("div", id="txtContent") or
             soup.find("div", class_="con") or
             soup.find("div", id=re.compile(r"txtContent|content|article|text|chaptercontent|nr1|htmlContent", re.I)) or
             soup.find("div", class_=re.compile(r"content|read-content|novelcontent|text|entry", re.I)))
        if not c:
            # 选文本量最大的 div 标签
            divs = soup.find_all("div")
            if divs:
                c = max(divs, key=lambda d: len(d.get_text()))

        if c:
            for tag in c.find_all(["script", "style", "a", "button", "iframe"]):
                tag.decompose()
            lines = [l.strip() for l in c.get_text("\n").split("\n") if l.strip()]
            clean = [l for l in lines if not any(k in l for k in ["请记住", "最新章节", "无弹窗", "投推荐票", "上一章", "下一章", "目录", "书签"])]
            return url, title, "\n\n".join(clean)
        return url, title, ""

# ==================== Main Orchestrator ==================== #

def download_novel(name, output_dir):
    print(f"\n" + "=" * 55)
    print(f"[*] 启动全网自动嗅探与下载调度器：《{name}》")
    print(f"=" * 55)

    target_info = None
    chapters = []
    downloader_func = None

    # Step 1: 内置直连聚合书库（0 验证码、高成功率、专业逆向解密）
    print(f"[阶段 1/3] 检索内置专用源站池...")
    built_in_candidates = [
        ("海马读书网 (AES-CBC 注入源)", HaimashuAdapter, lambda info: HaimashuAdapter.get_chapters(info["bid"])),
        ("第一版主网 (长文子页连贯拼接源)", B111bzAdapter, lambda info: B111bzAdapter.get_chapters(info["bid"])),
        ("八叉书库 (Base64 混淆源)", B8xskAdapter, lambda info: B8xskAdapter.get_chapters(info["bid"])),
        ("辣文/笔趣阁镜像库", AaddkkAdapter, lambda info: AaddkkAdapter.get_chapters(info)),
        ("小说狂人 (实体精校繁简源)", CzbooksAdapter, lambda info: CzbooksAdapter.get_chapters(info["slug"])),
    ]

    for label, adapter, chap_fetcher in built_in_candidates:
        print(f"  -> 探测 {label}...")
        try:
            info = adapter.search(name)
            if info:
                ch = chap_fetcher(info)
                if ch and len(ch) > 0:
                    print(f"     [✓] 命中有效源站！发现 {len(ch)} 章节。")
                    target_info = info
                    chapters = ch
                    downloader_func = adapter.download_chapter
                    break
                else:
                    print(f"     [-] 页面已下架或目录为空，跳过此源。")
        except Exception as e:
            print(f"     [-] 探测失败: {e}")

    # Step 2: 免验证搜索引擎回退机制 (Zero-Captcha Engine Fallback)
    if not target_info:
        print(f"[阶段 2/3] 内置专用源池未命中，启动免验证搜索引擎回退...")
        print(f"  -> [Level 2] 调用纯 HTTP 免验证引擎 (DuckDuckGo Lite)...")
        
        PAYWALL_DOMAINS = [
            "qidian.com", "qq.com", "iqiyi.com", "hongxiu.com", "readnovel.com",
            "faloo.com", "17k.com", "zongheng.com", "tieba.baidu.com", "zhihu.com",
            "douban.com", "wikipedia.org", "baike.baidu.com", "bqquge.org"
        ]

        raw_queries = [
            f"{name} 笔趣阁 txt 目录",
            f"{name} 笔趣阁 完整目录",
            f"{name} 目录 笔趣阁"
        ]
        raw_results = []
        for q in raw_queries:
            raw_results.extend(SearchFallbackEngine.search_duckduckgo_lite(q))

        # 过滤掉官方付费截断站、百科与死链重定向站
        search_results = []
        seen_urls = set()
        for r in raw_results:
            u = r["url"]
            if u not in seen_urls and not any(p in u.lower() for p in PAYWALL_DOMAINS):
                seen_urls.add(u)
                search_results.append(r)
        
        # Step 3: 若 Level 2 未命中，平滑回退至 Level 3 (Chrome Google 会话)
        if not search_results:
            print(f"  -> [Level 3] 切换至受信任 Chrome Google 引擎 (规避 Yandex 字符拦截)...")
            g_results = SearchFallbackEngine.search_chrome_google(f"{name} 笔趣阁 完整目录")
            for r in g_results:
                u = r["url"]
                if u not in seen_urls and not any(p in u.lower() for p in PAYWALL_DOMAINS):
                    seen_urls.add(u)
                    search_results.append(r)

        if search_results:
            print(f"  -> 搜索引擎成功发现 {len(search_results)} 个外部候选网页，启动自适应解析与全本择优...")
            best_parsed = None
            max_chaps = 0

            for res in search_results:
                candidate_url = res["url"]
                candidate_title = res["title"]
                print(f"     * 尝试探测候选源: {candidate_title} ({candidate_url})")
                
                # Check built-in adapters first if url matches
                parsed = None
                if "haimashu.com" in candidate_url:
                    m = re.search(r"/book/(\d+)/", candidate_url)
                    if m:
                        ch = HaimashuAdapter.get_chapters(m.group(1))
                        if ch: parsed = {"engine": "haimashu", "title": candidate_title, "chapters": ch, "downloader": HaimashuAdapter.download_chapter}
                elif "111bz.cc" in candidate_url:
                    m = re.search(r"/(9_\d+)/", candidate_url)
                    if m:
                        ch = B111bzAdapter.get_chapters(m.group(1))
                        if ch: parsed = {"engine": "111bz", "title": candidate_title, "chapters": ch, "downloader": B111bzAdapter.download_chapter}
                elif "8xsk.com" in candidate_url:
                    m = re.search(r"/book/(\d+)", candidate_url)
                    if m:
                        ch = B8xskAdapter.get_chapters(m.group(1))
                        if ch: parsed = {"engine": "8xsk", "title": candidate_title, "chapters": ch, "downloader": B8xskAdapter.download_chapter}
                elif "czbooks.net" in candidate_url:
                    m = re.search(r"/n/([a-z0-9]+)", candidate_url)
                    if m:
                        ch = CzbooksAdapter.get_chapters(m.group(1))
                        if ch: parsed = {"engine": "czbooks", "title": candidate_title, "chapters": ch, "downloader": CzbooksAdapter.download_chapter}
                
                if not parsed:
                    parsed = UniversalNovelParser.probe_and_parse(candidate_url, name)

                if parsed and len(parsed["chapters"]) > 0:
                    cnt = len(parsed["chapters"])
                    # 正文有效性抽样检测（排除假站、重定向劫持与付费截断）
                    sample_idx = [0]
                    if cnt > 10: sample_idx.append(10)
                    sample_lens = []
                    for s_i in sample_idx:
                        _, _, s_txt = parsed["downloader"](parsed["chapters"][s_i])
                        sample_lens.append(len(s_txt.strip()))
                    avg_len = sum(sample_lens) / len(sample_lens) if sample_lens else 0
                    print(f"       => 目录章节: {cnt}，正文抽样均长: {avg_len:.0f} 字")

                    if avg_len < 400:
                        print(f"       [-] 正文存在截断/劫持/防盗异常 (均长<{avg_len:.0f})，弃用此源。")
                        continue

                    # 优先选择章节数量最多且正文真实饱满的源
                    if cnt > max_chaps:
                        max_chaps = cnt
                        best_parsed = parsed
                        if cnt >= 1500:
                            print(f"       => 已锁定完本超大容量全本 ({cnt} 章)，停止探测。")
                            break

            if best_parsed:
                target_info = best_parsed
                chapters = best_parsed["chapters"]
                downloader_func = best_parsed["downloader"]

    if not target_info or not chapters:
        print(f"[-] 全网回退检索完毕，未能定位到《{name}》的可用在线目录。")
        return False

    engine = target_info.get("engine", "universal")
    print(f"\n[+] 最终锁定目标源！采用引擎: [{engine.upper()}]，书名: 《{target_info.get('title', name)}》")

    total = len(chapters)
    print(f"[+] 目录解析成功：共锁定 {total} 篇章节。启动并发下载与清洗...")

    # 根据章节总数动态调整并发线程数
    workers = 30 if total >= 1500 else (20 if total >= 500 else 10)
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_item = {executor.submit(downloader_func, item): item for item in chapters}
        completed = 0
        for future in as_completed(future_to_item):
            url, title, text = future.result()
            results[url] = (title, text)
            completed += 1
            if completed % 50 == 0 or completed == total:
                print(f"    -> 抓取进度: {completed}/{total} 章节 ({(completed/total)*100:.1f}%)")

    # 自动并发重试补漏（针对空章节）
    empty_items = [item for item in chapters if not results.get(item[1], ("", ""))[1]]
    if empty_items:
        print(f"[*] 发现 {len(empty_items)} 章存在丢包，启动快速并发重试修复...")
        with ThreadPoolExecutor(max_workers=5) as retry_exec:
            retry_futures = {retry_exec.submit(downloader_func, item): item for item in empty_items}
            for rf in as_completed(retry_futures):
                url, title, text = rf.result()
                if text:
                    results[url] = (title, text)

    # 导出文件
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"{name}.txt")
    print(f"[*] 正在组装全集并写入: {out_file}")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"《{name}》\n全本纯净精校版\n\n" + "=" * 40 + "\n\n")
        for title, url in chapters:
            t, text = results.get(url, (title, ""))
            f.write(f"\n\n### {t}\n\n")
            f.write(text)
            f.write("\n")

    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"[✓] 《{name}》全本下载完成！保存路径: {out_file} (大小: {size_mb:.2f} MB，章节: {total})\n")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Novel Downloader Skill CLI")
    parser.add_argument("novel_name", help="Name of the novel to search and download")
    parser.add_argument("--output-dir", default="/Users/huangjinjin/Documents/workspace/books/downloads", help="Directory to save the novel txt")
    args = parser.parse_args()

    download_novel(args.novel_name, args.output_dir)
