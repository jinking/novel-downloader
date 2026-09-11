"""
Concurrent Downloader with Retry Phase for Novel Downloader V2
"""
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Tuple, Dict
from novel_downloader.models import Chapter, ChapterContent

class ConcurrentDownloader:
    @classmethod
    def download_all(
        cls,
        chapters: List[Chapter],
        downloader_func: Callable[[Chapter], ChapterContent],
        max_workers: int = 12,
        verbose: bool = True
    ) -> Tuple[List[ChapterContent], int]:
        total = len(chapters)
        if total == 0:
            return [], 0

        # 平稳限制并发在 8-15 之间，避免单 IP 被小型小说站直接拉黑
        workers = min(max_workers, 15)
        if verbose:
            print(f"[*] 开始高并发抓取共 {total} 章 (并发线程数: {workers})...")

        results: Dict[int, ChapterContent] = {}
        failed_indices: List[int] = []

        start_time = time.time()
        completed_count = 0

        def fetch_wrapper(ch: Chapter):
            time.sleep(random.uniform(0.02, 0.08))
            return downloader_func(ch)

        # 第 1 轮主并发抓取
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {
                executor.submit(fetch_wrapper, ch): ch.index
                for ch in chapters
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                completed_count += 1
                try:
                    content = future.result()
                    if content and content.is_valid and len(content.text) >= 40:
                        results[idx] = content
                    else:
                        failed_indices.append(idx)
                except Exception:
                    failed_indices.append(idx)

                if verbose and (completed_count % 25 == 0 or completed_count == total):
                    elapsed = time.time() - start_time
                    speed = completed_count / (elapsed + 1e-5)
                    percent = (completed_count / total) * 100
                    print(f"    进度: {completed_count}/{total} ({percent:.1f}%) | 速度: {speed:.1f} 章/秒", end="\r", flush=True)

        if verbose:
            print()

        # 第 2 轮补漏重试（如果存在失败章节）
        if failed_indices and (len(failed_indices) / float(total)) <= 0.35:
            if verbose:
                print(f"[*] 启动轻量补漏机制，重试 {len(failed_indices)} 处异常章节...")
            time.sleep(1.0)
            still_failed = []
            retry_workers = min(4, workers)
            with ThreadPoolExecutor(max_workers=retry_workers) as executor:
                future_to_idx = {
                    executor.submit(fetch_wrapper, chapters[idx]): idx
                    for idx in failed_indices
                }
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        content = future.result()
                        if content and content.is_valid and len(content.text) >= 40:
                            results[idx] = content
                        else:
                            still_failed.append(idx)
                    except Exception:
                        still_failed.append(idx)
            failed_indices = still_failed

        # 整理保序结果并对最终缺失章节填充占位符
        final_list: List[ChapterContent] = []
        for ch in chapters:
            if ch.index in results:
                final_list.append(results[ch.index])
            else:
                final_list.append(ChapterContent(
                    url=ch.url,
                    title=ch.title,
                    text=f"【本章正文抓取失败，原章节地址: {ch.url}】",
                    length=0,
                    is_valid=False
                ))

        if verbose:
            elapsed = round(time.time() - start_time, 2)
            print(f"[✓] 抓取完毕！耗时 {elapsed}s，成功: {total - len(failed_indices)} 章，失败: {len(failed_indices)} 章")

        return final_list, len(failed_indices)
