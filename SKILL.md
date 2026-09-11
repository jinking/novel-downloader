---
name: novel-downloader
description: 全自动全网智能嗅探、逆向解密、多维质量验收、产物完整度核验与批量下载中文小说为纯净精校 TXT 全集。具备解耦架构、纠正伪兜底深度检索、5点正文抽样质量核验、直连 URL 模式、多源故障转移与 PostDownload 产物核验机制。当用户提供小说书名、要求下载某本小说、提供小说在线目录地址或需要突破小说防爬机制时使用。
---

# 小说全网智能嗅探与质量核验下载器 V2.1 (Novel Downloader V2.1)

该技能提供了一套高鲁棒性、多维质量验收、产物完整度核验、自适应反爬解密、章节连贯拼接与纯净全本 TXT 导出的全自动化工作流。

---

## 核心架构机制 (V2.1)

1. **发现层多引擎并发与隔离**：
   - 统筹 Built-in 专用源、Google、Yandex 与 DuckDuckGo Lite。
   - 单个搜索引擎超时或验证码异常完全隔离，并记入诊断记录，不影响任务整体执行。
2. **彻底纠正伪兜底 (Deep Discovery)**：
   - 深度拓展检索由“候选池中是否存在真实达标可用源（`has_qualified_source()`）”驱动，绝不因搜索引擎有返回无价值链接而草率退出。
3. **5 点正文抽样多维质量核验 (SourceValidator)**：
   - 首章、25%、50%、75% 及最后一章多点抽检。
   - 严格检验章节标题正规率（排斥推荐书单伪目录）。
   - 抽样正文均长 `< 400` 字或包含截断/防盗推广词自动判定不合格。
4. **源站故障转移 (Failover)**：
   - 若优选源站突发 WAF 频控封锁，自动平滑切换至备选顺位达标源。
5. **产物完整度核验 (PostDownloadValidator)**：
   - 校验最终产物的全书缺章率、有效章节平均字数与异常短小章节比例。
   - 来源质量合格 + 抓取完整 + 产物合格，才可判定为最终 `SUCCESS`。
   - 默认禁止未达标源进入正式下载；若显式指定 `--allow-low-quality`，下载完成仍严正标记为 `LOW_QUALITY`，状态绝不漂移为 `SUCCESS`。

---

## 常用调用命令

当用户给出书名或小说下载需求时，直接执行本技能的核心工具：

```bash
# 1. 基础用法 (书名搜索)
python3 /Users/huangjinjin/Documents/workspace/novel-downloader/scripts/download.py "全职高手" --output-dir "/Users/huangjinjin/Documents/workspace/books/downloads"

# 2. 作者联合高精度匹配 (强烈推荐，彻底避免同名书误判)
python3 /Users/huangjinjin/Documents/workspace/novel-downloader/scripts/download.py "诛仙" --author "萧鼎" --output-dir "/Users/huangjinjin/Documents/workspace/books/downloads"

# 3. 直连 URL 模式 (跳过搜索，直接解析指定目录)
python3 /Users/huangjinjin/Documents/workspace/novel-downloader/scripts/download.py "诛仙" --url "https://www.wyshu.com/wl/zhuxian" --output-dir "/Users/huangjinjin/Documents/workspace/books/downloads"

# 4. JSON 诊断报告输出 (便于 Agent 解析状态)
python3 /Users/huangjinjin/Documents/workspace/novel-downloader/scripts/download.py "诛仙" --author "萧鼎" --json
```

---

## ⚠️ 重要说明：网络环境与 AI 模型选型建议

1. **科学上网环境推荐**：
   - 许多高质量小说镜像站与轻量免验证检索节点部署在海外 CDN 节点（Cloudflare 等），国内直连容易遇到 DNS 污染或连接重置。
   - 运行下载时，**建议确保系统/全局代理处于开启状态**，以保证多级源站顺利连通。

2. **推荐使用海外最新前沿大模型（Claude 5 / Gemini 3.8 / ChatGPT 6 等）**：
   - **国内大模型痛点**：国内 AI 模型受限于极度严格的商业版权合规与内容安全审核策略。当识别到小说书名或防爬抓取时，极易直接触发拒答策略（Refusal / Policy Error），拒绝调用终端工具或中断下载执行。
   - **海外模型优势**：如 Claude 5、Gemini 3.8 Pro / Flash、ChatGPT 6 / GPT-6 等最新一代前沿旗舰大模型具备顶尖的工程代码执行力与客观的工具调度能力，能专注完成用户的技术分析与端到端自动化抓取任务，不发生版权误拒。
