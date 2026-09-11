"""
Text Exporter for Novel Downloader V2
Exports chapters to clean, well-formatted TXT files.
"""
import os
import time
from typing import List, Optional
from novel_downloader.models import ChapterContent

class TxtExporter:
    @classmethod
    def export(
        cls,
        novel_name: str,
        chapters: List[ChapterContent],
        output_dir: str = "./",
        author: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)
        # 清理非法文件名字符
        safe_name = "".join(c for c in novel_name if c not in r'\/:*?"<>|').strip()
        filename = f"{safe_name}.txt"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            # 写入元信息头
            f.write("=" * 50 + "\n")
            f.write(f"书名：《{novel_name}》\n")
            if author:
                f.write(f"作者：{author}\n")
            if source_url:
                f.write(f"来源：{source_url}\n")
            f.write(f"导出时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"章节总计：{len(chapters)} 章\n")
            f.write("=" * 50 + "\n\n")

            # 逐章写入
            for ch in chapters:
                f.write(f"{ch.title}\n\n")
                if ch.text:
                    f.write(ch.text)
                else:
                    f.write("【本章抓取失败】")
                f.write("\n\n" + "-" * 30 + "\n\n")

        return os.path.abspath(file_path)
