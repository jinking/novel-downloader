"""
Network, Decryption & Text Cleaning Utilities for Novel Downloader V2
"""
import gzip
import time
import base64
import hashlib
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict

DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
}

def clean_zero_width(text: str) -> str:
    """剔除 Unicode 零宽字符与特殊排版水印"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    zero_width = [
        "\u200b", "\u200c", "\u200d", "\u200e", "\u200f",
        "\ufeff", "\u00ad", "\u202a", "\u202b", "\u202c",
        "\u202d", "\u202e", "\u2060", "\u180e"
    ]
    for ch in zero_width:
        text = text.replace(ch, "")
    return text

def fetch_html(url: str, headers: Optional[Dict[str, str]] = None, retries: int = 2, delay: float = 0.3, encoding: Optional[str] = None) -> str:
    """
    通用 HTML 抓取工具：
    - 超时 7s，快速熔断
    - 自动补充 Referer 防盗链
    - 自动拦截 302 劫持（如重定向至 google/baidu 首页）
    - 自动探测 GBK / GB2312 编码
    """
    if url.startswith("//"):
        url = "https:" + url

    parsed = urllib.parse.urlparse(url)
    base_origin = f"{parsed.scheme}://{parsed.netloc}/"

    req_headers = dict(HEADERS)
    if headers:
        req_headers.update(headers)
    if "Referer" not in req_headers:
        req_headers["Referer"] = base_origin

    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=7) as resp:
                final_url = resp.geturl()
                if "google.com" in final_url or "baidu.com" in final_url:
                    return ""
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip" or (len(raw) >= 2 and raw[:2] == b"\x1f\x8b"):
                    raw = gzip.decompress(raw)
                
                # 自动检测编码
                enc = encoding
                if not enc:
                    header_content = raw[:1024].lower()
                    if b"charset=gbk" in header_content or b"charset=\"gbk\"" in header_content or b"charset=gb2312" in header_content:
                        enc = "gbk"
                    else:
                        enc = "utf-8"
                return raw.decode(enc, errors="ignore")
        except urllib.error.HTTPError as he:
            if he.code in (404, 410):
                return ""
            time.sleep(delay)
        except Exception:
            time.sleep(delay)
    return ""

def decrypt_aes_cbc(cipher_b64: str, key_str: str) -> str:
    """海马书库等站点 AES-128-CBC 动态脚本解密"""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    
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
