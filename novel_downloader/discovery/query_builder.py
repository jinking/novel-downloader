"""
Query Builder: 动态多维搜索词生成器
"""
from typing import List, Optional

class QueryBuilder:
    @staticmethod
    def build_queries(name: str, author: Optional[str] = None, deep: bool = False) -> List[str]:
        queries = []
        clean_name = name.strip().replace("《", "").replace("》", "").replace('"', '').replace("'", "")
        
        # 1. 基础高召回查询 (不带硬引号，确保搜索引擎自然分词)
        queries.append(f"{clean_name} 小说 目录")
        queries.append(f"{clean_name} 笔趣阁 目录")
        queries.append(f"{clean_name} 完整目录 章节")
        
        # 2. 作者联合查询 (若提供作者，置于高优先级)
        if author:
            clean_author = author.strip().replace('"', '').replace("'", "")
            queries.insert(0, f"{clean_name} {clean_author} 目录")
            queries.append(f"{clean_name} {clean_author} 全本")

        # 3. 深度兜底词路
        if deep:
            queries.append(f"{clean_name} 全集 在线阅读")
            queries.append(f"{clean_name} 完结版 章节列表")
            queries.append(f"{clean_name} txt 小说 目录")
            if author:
                queries.append(f"{clean_name} {clean_author} 笔趣阁")

        # 去重保持顺序
        seen = set()
        final_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                final_queries.append(q)
        return final_queries
