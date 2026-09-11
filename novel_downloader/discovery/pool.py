"""
Candidate Pool: 候选 URL 池、归一化去重与初筛
"""
import re
import urllib.parse
from typing import List, Dict, Optional, Set
from novel_downloader.models import SearchResult, Candidate

PAYWALL_OR_NOISE_DOMAINS = {
    "qidian.com", "qq.com", "iqiyi.com", "hongxiu.com", "readnovel.com",
    "faloo.com", "17k.com", "zongheng.com", "tieba.baidu.com", "zhihu.com",
    "douban.com", "wikipedia.org", "baike.baidu.com", "bqquge.org"
}

def normalize_url(raw_url: str) -> str:
    """URL 归一化处理"""
    if not raw_url:
        return ""
    try:
        parsed = urllib.parse.urlparse(raw_url)
        # 统一 https
        scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme
        netloc = parsed.netloc.lower()
        # 去除默认端口
        if netloc.endswith(":80"): netloc = netloc[:-3]
        elif netloc.endswith(":443"): netloc = netloc[:-4]
        
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
            
        # 过滤 utm_*, spm 等无意义追踪参数
        query_params = urllib.parse.parse_qsl(parsed.query)
        filtered_params = [(k, v) for k, v in query_params if not k.startswith("utm_") and k not in ("spm", "from")]
        new_query = urllib.parse.urlencode(filtered_params)
        
        return urllib.parse.urlunparse((scheme, netloc, path, "", new_query, ""))
    except Exception:
        return raw_url.strip()

class CandidatePool:
    def __init__(self, novel_name: str, author: Optional[str] = None):
        self.novel_name = novel_name
        self.author = author
        self._candidates: Dict[str, Candidate] = {}

    def add_search_results(self, results: List[SearchResult]):
        for r in results:
            clean_url = normalize_url(r.url)
            if not clean_url or not clean_url.startswith("http"):
                continue
                
            domain = urllib.parse.urlparse(clean_url).netloc.lower()
            if any(p in domain for p in PAYWALL_OR_NOISE_DOMAINS):
                continue
                
            if clean_url not in self._candidates:
                self._candidates[clean_url] = Candidate(
                    url=clean_url,
                    domain=domain,
                    discovered_by=[r.provider],
                    matched_queries=[r.query],
                    search_titles=[r.title],
                    snippets=[r.snippet] if r.snippet else []
                )
            else:
                c = self._candidates[clean_url]
                if r.provider not in c.discovered_by:
                    c.discovered_by.append(r.provider)
                if r.query not in c.matched_queries:
                    c.matched_queries.append(r.query)
                if r.title not in c.search_titles:
                    c.search_titles.append(r.title)
                if r.snippet and r.snippet not in c.snippets:
                    c.snippets.append(r.snippet)

    def add_manual_url(self, raw_url: str):
        clean_url = normalize_url(raw_url)
        if clean_url:
            domain = urllib.parse.urlparse(clean_url).netloc.lower()
            self._candidates[clean_url] = Candidate(
                url=clean_url,
                domain=domain,
                discovered_by=["manual"],
                matched_queries=["--url"],
                search_titles=[self.novel_name],
                discovery_score=100.0
            )

    def rank_candidates(self) -> List[Candidate]:
        """计算初始 Discovery 评分并排序"""
        for c in self._candidates.values():
            score = 50.0  # 基础分
            
            # 多引擎命中加成
            if len(c.discovered_by) >= 2:
                score += 20.0
                
            # 标题特征加成
            combined_title = " ".join(c.search_titles)
            if self.novel_name in combined_title:
                score += 30.0
            if self.author and self.author in combined_title:
                score += 20.0
            if any(k in combined_title for k in ["目录", "章节", "全集", "全本"]):
                score += 10.0
                
            c.discovery_score = score
            
        return sorted(self._candidates.values(), key=lambda x: x.discovery_score, reverse=True)

    def count(self) -> int:
        return len(self._candidates)
