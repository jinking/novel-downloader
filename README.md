# Novel Downloader (小说全网智能嗅探精校下载引擎 V2)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-V2%20Decoupled-brightgreen.svg)]()

全自动全网小说嗅探、逆向解密、多维质量验收、智能源站故障转移与全本纯净精校 TXT 生成引擎。

无论是知名网文大作（如《全职高手》1728章、《诛仙》250章全集），还是各类被强反爬、动态混淆加密、防盗截断保护的小说（如风月经典、武侠传奇、短篇完结篇），仅需输入书名或直连 URL，即可实现一键检索、质量核验、并发抓取、自动丢包补漏并拼接为规范精校全集。同时无缝兼容作为 **AI Agent 智能体专属技能（Skill）** 直接调用。

---

## 🌟 V2 架构演进与核心特性

```
用户输入: 书名 / --author [作者] / --url [直连目录]
  │
  ├──► [直连模式] 若指定 --url: 直接跳过搜索，直达解析与质量校验层
  │
  └──► [全网自适应多源发现层 (Discovery)]
         ├── 动态多维词路生成 (QueryBuilder: 基础词 + 作者联合词 + 完本拓展词)
         ├── 内置专用源池直查 (BuiltinProvider: 海马 AES-CBC / 八叉 Base64 / 小说狂人等)
         ├── 免验证纯 HTTP 引擎 (DuckDuckGo Lite: 100% 免疫 CAPTCHA)
         └── 本地 Chrome 受信任引擎 (Google Provider 兜底)
         └──► 候选 URL 池 (CandidatePool: 规范化去重、去追踪参数、多引擎置信加权)
  │
  ├──► [解析与路由分发层 (Router)]
  │      ├── 专用站点适配器 (海马 AES 解密、八叉 Base64 还原、移动端无缝子分页递归等)
  │      └── 通用自适应解析器 (UniversalParser V2: 容器自动定位、目录页自动跃迁、正文字符密度提取)
  │
  ├──► [多维质量验收器 (SourceValidator)] 彻底废弃单一“章节数最多”的原始策略
  │      ├── 身份吻合度评分 (30%): 书名与作者元信息交叉校验
  │      ├── 目录健康度评分 (20%): 章节量级、章节重复率、正规章节命名格式率 (防推荐书单)
  │      ├── 5 点正文抽样评分 (30%): 首章 / 25% / 50% / 75% / 尾章，均长与截断/防盗词检测
  │      ├── 完本与完整度评分 (15%): 终章/大结局特征识别
  │      └── 发现层可信度评分 (5%)
  │
  ├──► [综合排序与故障转移 (SourceRanker & Failover)]
  │      ├── 锁定达标优质源 (is_qualified == True 且综合评分优先)
  │      └── 源站故障转移机制: 若首选源遭遇瞬时 WAF 限流封锁 (403/503)，自动平滑切换至备选源
  │
  └──► [平稳高并发下载与导出层 (Downloader & Export)]
         ├── 自适应平稳并发流水线 (防单 IP 高频封锁，内置随机 Jitter)
         ├── 丢包快速并发补漏重试 (自动修复个别网络抖动章节)
         └── 精校纯净全本 TXT 输出 (含元信息头与章节标准化分卷)
```

### 1. 彻底纠正“伪兜底” Bug
- **旧版缺陷**：只要兜底搜索引擎返回了网页列表就判定“搜索成功”，但若这些页面全部无法解析或为假站，流程直接终止退出。
- **V2 纠正**：将搜索收敛条件从“引擎是否有返回”彻底重构为“候选池中是否存在达标可用源（`has_qualified_source()`）”。常规搜索未命中达标全本时，自动下潜启动深度兜底词路，直到找到真正合格可读的全集。

### 2. 5 点正文抽样质量验收器（反假站、反截断）
不盲信单一章节数，结合**首章、25%、50%、75% 和最后一章**进行多点正文抽查：
- 严格检验章节标题命名规范（排斥非小说的推荐书单聚合流）。
- 抽样章节平均有效正文字数 `< 400` 字或包含付费/截断提示，自动判定为残次源并剔除。

### 3. 多源故障转移（Failover）与平稳防风控并发
- 抓取并发数动态控制在稳健区间，彻底避免触发目标小型小说站的 Nginx / Cloudflare 403 频控封锁。
- 若某个源站突发异常，自动按质量排名无缝切换至下一顺位合格源。

---

## ⚠️ 注意事项与前置要求

> [!IMPORTANT]
> 1. **网络环境（科学上网 / 代理推荐）**：
>    部分高质量小说镜像站与搜索引擎部署在海外节点（Cloudflare CDN），境内直连网络可能会遭遇 DNS 污染或连接重置。**强烈建议在科学上网（开启全局/系统代理）环境下运行**。
>
> 2. **AI 智能体模型选型建议**：
>    如果你将本项目接入 AI Agent（如 Claude Code、Antigravity、Cursor 等）：
>    - **推荐使用海外最新前沿大模型**（如 Claude 5、Gemini 3.8 Pro / Flash、ChatGPT 6 / GPT-6 等），指令遵从度极高，具备强大的代码工程执行力与自动化下载调度能力。
>    - **慎用国内大模型**：国内模型普遍具备非常严格的商业版权合规与内容审查机制，在识别到小说书名或防爬抓取时，极易直接触发拒答策略（Content Policy Invalidation），拒绝调用工具或阻断下载流程。

---

## 🚀 安装与使用

### 环境要求
- Python 3.9+
- 推荐开启系统代理环境

### 1. 安装依赖
```bash
git clone https://github.com/jinking/novel-downloader.git
cd novel-downloader
pip install -r requirements.txt
```

或者本地以可编辑模式安装 CLI：
```bash
pip install -e .
```

---

### 2. 运行下载命令

#### 基础用法（全网自动发现与优选）
```bash
python3 scripts/download.py "诛仙"
```

#### 作者联合高精度匹配（强烈推荐）
通过 `--author` / `-a` 提供小说原作者，可彻底排除同名作品并提升源站匹配得分：
```bash
python3 scripts/download.py "诛仙" --author "萧鼎"
```

#### 手动直连目录 URL 模式（跳过搜索）
若您已有目标小说目录或简介页链接，可直接通过 `--url` / `-u` 直连下载：
```bash
python3 scripts/download.py "诛仙" --url "https://www.wyshu.com/wl/zhuxian"
```

#### 自定义输出目录与并发控制
```bash
python3 scripts/download.py "全职高手" --author "蝴蝶蓝" --output-dir "./my_novels" --concurrency 15
```

#### JSON 诊断报告输出（便于 Agent 或脚本集成）
```bash
python3 scripts/download.py "诛仙" --author "萧鼎" --json
```

---

## 📊 实测案例与任务报告

以经典长篇仙侠小说《诛仙》（作者：萧鼎）为例：

```
[*] 启动全网多源搜寻: 《诛仙》 (作者: 萧鼎)
[阶段 1] 发起基础全网搜索...
    [-] 排除低质/残缺源: book.sina.cn (得分: 61.0, 章节: 50, 原因: 抽样章节正文抓取失败)
    [-] 排除低质/残缺源: m.bigee.cc (得分: 58.0, 章节: 13, 原因: 综合评分不足60分)
    [✓] 发现达标可用源! [universal] www.xuges.com | 章节: 568 | 质量分: 87.0
    [-] 排除低质/残缺源: www.tianyabooks.com (得分: 67.0, 章节: 262, 原因: 正文包含截断推广)
    [✓] 发现达标可用源! [universal] m.guishuji.com | 章节: 30 | 质量分: 91.0
    [✓] 发现达标可用源! [universal] www.wyshu.com | 章节: 250 | 质量分: 97.0

[★] 选定最佳优质源: www.wyshu.com | 章节: 250 | 质量分: 97.0
[*] 开始高并发抓取共 250 章 (并发线程数: 15)...
    进度: 250/250 (100.0%) | 速度: 7.4 章/秒
[*] 启动轻量补漏机制，重试 50 处异常章节...
[✓] 抓取完毕！耗时 52.09s，成功: 250 章，失败: 0 章

=== Novel Downloader V2 任务报告 ===
书名: 《诛仙》 (作者: 萧鼎)
最终状态: SUCCESS
调用发现引擎: duckduckgo, google
候选源统计: 发现 19 个 -> 解析 6 个 -> 达标 3 个
中标源站: https://www.wyshu.com/wl/zhuxian
章节总数: 250 (失败/丢失: 0)
导出文件: ./downloads/诛仙.txt
```

导出生成 **4.2 MB** 完整纯净全集，从草庙村序章到大结局陆雪琪相视一笑，全篇零乱码、无防盗广告注入。

---

## 🤖 接入 AI Agent / Antigravity / Claude Code

本项目已原生封装为智能体 Agent Skill 规格：

1. 将本项目目录关联至您的智能体配置目录：
   ```bash
   ln -s /path/to/novel-downloader ~/.gemini/config/skills/novel-downloader
   ```
2. 在任意 Agent 对话中输入自然语言指令：
   > “帮我下载《诛仙》，作者是萧鼎”
   > “帮我把这个网址的小说下载下来：https://www.wyshu.com/wl/zhuxian”
3. Agent 将自动调用底层模块完成全网探测、反爬逆向、质量校验与文件交付。

---

## 📂 项目结构

```
novel-downloader/
├── README.md                     # 项目完整说明与实测报告
├── LICENSE                       # MIT 开源协议
├── requirements.txt              # 核心依赖 (beautifulsoup4, cryptography)
├── pyproject.toml                # 包构建与 CLI 命令注册
├── SKILL.md                      # Agent Skill 规范契约文件
├── scripts/
│   └── download.py               # 向后兼容与一键执行入口 CLI
├── novel_downloader/             # V2 模块化解耦核心包
│   ├── __init__.py               # 包版本与核心类导出
│   ├── models.py                 # 数据契约与数据模型定义
│   ├── utils.py                  # 网络抓取、AES-CBC解密与零宽字符清洗
│   ├── orchestrator.py           # 总调度器 (包含状态收敛与故障转移)
│   ├── cli.py                    # 完整参数命令行入口
│   ├── discovery/                # 发现层
│   │   ├── query_builder.py      # 动态多维搜索词构建器
│   │   ├── pool.py               # 候选 URL 池与归一化
│   │   ├── engine.py             # 发现驱动引擎
│   │   └── providers/            # 搜索引擎适配器 (Builtin, DuckDuckGo, Google)
│   ├── parsers/                  # 解析层
│   │   ├── router.py             # 解析路由器
│   │   ├── universal.py          # 通用自适应解析器 V2
│   │   └── adapters/             # 专有站深度逆向适配器
│   ├── validation/               # 质量验收层
│   │   └── validator.py          # 5 点抽样多维质量验收器
│   ├── ranking/                  # 排序决策层
│   │   └── source_ranker.py      # 综合质量评分加权排斥与优选
│   ├── downloader/               # 并发下载层
│   │   └── concurrent.py         # 平稳多线程抓取与丢包补漏
│   └── export/                   # 产物导出层
│       └── txt_exporter.py       # 精校纯净 TXT 装配导出
└── downloads/                    # 默认下载产物目录
```

---

## ⚖️ 开源协议与免责声明

- 本项目基于 **[MIT License](LICENSE)** 开源。
- 本项目代码仅供网络数据抓取、信息检索技术学习与逆向工程安全研究之用。所爬取的小说内容版权均归原作者及版权方所有，请在下载后 24 小时内删除，严禁用于商业牟利或侵权传播。
