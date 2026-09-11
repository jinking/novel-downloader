---
name: novel-downloader
description: 全自动全网嗅探、逆向解密并批量下载中文小说（尤其是成人向、都市风月、经典武侠及各类被反爬防盗保护的小说）为纯净精校 TXT 全集。具备“站内聚合优先 -> 免验证搜索引擎兜底”的多级容灾架构，彻底避免弹窗与二次人机验证。当用户提供小说书名、要求下载某本小说、或需要破解小说网站防爬机制时使用。
---

# 小说全网嗅探与逆向解密下载器 (Novel Downloader)

该技能提供了一套经过实战检验的高鲁棒性小说全网检索、反爬逆向解密、章节连贯拼接与纯净全本 TXT 导出工作流。

---

## 核心架构：多级弹性检索与防二次验证机制

为了彻底避免像 Yandex 那样频繁弹出俄文拼图/图序二次验证码（`SmartCaptcha`），本技能采用了**“多级隔离与免验证平滑降级”**机制：

```
 用户输入书名
      │
      ▼
【Level 1：内置专用小说库池】（0 验证码，秒级直连，专业逆向）
  ├─ 海马读书网（AES-128-CBC 动态脚本注入解密，零宽字符清洗）
  ├─ 第一版主网（PC/WAP 目录映射，移动端长文子页自动连贯拼接）
  ├─ 八叉书库（自动绕过 18+ 年龄拦截，atob Base64 隐蔽解码）
  ├─ 笔趣阁/辣文库（连续章节 ID 提取，广告特征文本过滤）
  └─ 小说狂人（实体精校繁简库，多线程丢包自动修补）
      │
      ├─► [命中] ──► 并发下载正文 ──► 自动补漏 ──► 导出 TXT 全本
      │
      ▼ [全部未命中]
【Level 2：免验证轻量搜索引擎回退】（DuckDuckGo Lite API）
  ├─ 纯无头 HTTP 请求，0 JavaScript 执行，100% 免疫机器人风控
  └─ 提取排名前列的高质量小说目录页
      │
      ├─► [命中] ──► 自动匹配专用源或通用自适应解析器 ──► 导出全本
      │
      ▼ [未命中]
【Level 3：受信任本地 Chrome Google 引擎】（Google Search via OpenCLI）
  ├─ 借助本地已登录信任的 Chrome 用户环境检索 Google
  ├─ 享受正常用户权重，彻底告别 Yandex 的字符点选与二次拦截
  └─ 提取候选源并由 Universal Parser 智能解析
```

---

## 快速调用命令

当用户给出书名（例如：“帮我下载《xxx》”或“把《xxx》下下来”），直接执行技能内置的核心工具：

```bash
python3 /Users/huangjinjin/.gemini/config/skills/novel-downloader/scripts/download.py "<书名>" --output-dir "/Users/huangjinjin/Documents/workspace/books/downloads"
```

### 示例

```bash
# 下载指定小说（全自动走 Level 1 -> Level 2 -> Level 3 梯队调度）
python3 /Users/huangjinjin/.gemini/config/skills/novel-downloader/scripts/download.py "沧澜曲"

# 自定义保存目录
python3 /Users/huangjinjin/.gemini/config/skills/novel-downloader/scripts/download.py "陈皮皮的斗争" --output-dir "/path/to/save"
```

---

## 通用自适应解析器 (Universal Parser)

当通过搜索引擎回退探测到第三方全新小说站时，技能会自动启动通用解析器：
1. **智能目录探测**：动态匹配 `dl dd a`, `div.listmain a`, `ul.chapter-list a` 等 10+ 种主流章节结构。
2. **正文容器提取**：优先定位 `div#txtContent`, `div#content`, `div.con`, `div#article`, `div#nr1`，并对复杂 DOM 自动选取文本密度最大容器。
3. **正文质量抽样**：锁定前抽样章节字数，防盗截断或 302 重定向假站自动弃用。
4. **广告与噪音清洗**：自动剔除包含“本章完”、“加入书签”、“最新章节无弹窗”等防盗干扰行。
5. **空章自动二次修复**：下载完成后自动检测丢包章节，启动快速并发重试，确保 0 空章。

---

## ⚠️ 重要说明：网络环境与 AI 模型选型建议

1. **必须配合科学上网环境**：
   - 大部分高质量小说镜像站与轻量免验证检索节点部署在海外 CDN 节点（Cloudflare 等），国内直连容易遇到 DNS 污染或连接重置。
   - 运行下载时，**务必确保系统/全局代理处于开启状态**（支持常见 7890/10808 等代理端口），以保证多级源站顺利连通。

2. **推荐使用海外前沿大模型（Claude 4.5/4.0 / Gemini 3.0 / GPT-5 等）**：
   - **国内大模型痛点**：国内 AI 模型受限于极度严格的商业版权合规与内容安全审核策略。当用户要求抓取某本商业小说或书名包含特定风月/敏感词汇时，国内模型极易判定为“涉及版权风险”或“不合规请求”，直接触发拒答策略（Refusal / Policy Error），拒绝调用终端工具或中断下载执行。
   - **海外模型优势**：如 Claude 4.5 / 4.0 Sonnet & Opus、Gemini 3.0 Pro / Ultra、GPT-5 / o3 等前沿旗舰大模型具备顶尖的工程代码执行力与客观的工具调度能力，能专注完成用户的技术分析与端到端自动化抓取任务，不发生版权误拒。
