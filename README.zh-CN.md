# HALOFLUX for Hermes

> 把 HALOFLUX 的光环遥测视觉接到你自己的 Hermes Agent 数据上 —— 一个 dashboard 插件页。

[![许可证：PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)](LICENSE)
[![版本](https://img.shields.io/badge/version-1.3.0-green)](dashboard/manifest.json)
[![已测版本](https://img.shields.io/badge/tested%20on-Hermes%20Agent%20v0.23.0-orange)](#兼容性)

[English](README.md) · **简体中文**

![HALOFLUX for Hermes — 演示数据](docs/images/hero%20(1).png)

*截图为虚构演示数据 — 你装好后显示的是你自己的 Hermes 数字。*

HALOFLUX for Hermes 是 Hermes Agent 网页仪表盘的一个插件页。它把 HALOFLUX 的
光环画面 —— 中央光环、环带实时数据卡、底部 8 个数据面板、右上角 HUD —— 全部
用 Hermes 自己的数据驱动：会话 / 令牌 / 工具遥测读自本机 `state.db`，再加上
本机系统采样。页面上没有假数据，每个数字都来自 dashboard 所在的那台机器。

本项目是三级衍生作品（见[署名与许可证](#署名与许可证)），**仅限非商业用途**。

## 功能

- **环带实时卡片**：本机真实进程 —— 进程名、CPU、内存、网络速率。
- **8 个数据面板**，全部真数据驱动（见[面板一览](#面板一览)）。
- **HUD + 顶部 KPI**：当前会话、模型、令牌总量、吞吐、缓存命中率、工具调用、
  消息数、会话数。
- **BGM + 频谱小窗**：自带一首曲子，左下角 7 段频谱随音乐跳动，两种方式换成
  你自己的音乐（见 [BGM 与频谱](#bgm-与频谱)）。
- **后端零依赖**：只用 Python 标准库，无构建步骤；前端是普通 HTML/JS，由
  dashboard 自己提供。
- **隐私口径明确**：只读数据库、只查元数据列、不读消息正文、全部接口在
  dashboard 登录之后（见[数据与隐私](#数据与隐私)）。

## 兼容性

- **已在 Hermes Agent v0.23.0 上测试**，不宣称兼容其他版本。
- 需要：一个你能登录的 Hermes dashboard，以及往运行它的机器上放文件并重启
  dashboard 的权限。

## 快速安装

### 一键脚本（推荐）

在本仓库的检出目录里运行：

```bash
# Linux / macOS
./scripts/install.sh

# Windows（PowerShell）
.\scripts\install.ps1
```

脚本会把 `dashboard/` 复制到 `~/.hermes/plugins/haloflux/dashboard/`，已有
旧版会先备份。它不改任何配置，也不自动重启服务。

### 手动安装

把本仓库的 `dashboard/` 目录复制到：

```
~/.hermes/plugins/haloflux/dashboard/
```

### 装完之后

1. 重启 Hermes dashboard；
2. 在浏览器里登录 dashboard；
3. 点 dashboard 左侧边栏「插件」一栏里的 **HALOFLUX**，或直接打开
   `/haloflux`（如 `http://<你的 dashboard 地址>/haloflux`）——个别前端
   （如手机 App 内嵌页）不画插件入口，用地址直开一样。

环境变量：

- `HERMES_HOME`：换 Hermes 家目录（默认 `~/.hermes`）；
- `HERMES_DB`：指定 `state.db` 的路径。改完任一变量都要重启 dashboard。

## 工作原理

```
Hermes state.db（只读） ─┐
                         ├─► plugin_api.py ─► /api/plugins/haloflux/stats（JSON 快照）
本机采样（Linux /proc） ─┘        ▲                    │
                                  │                    ▼
                          dashboard 进程        ai-link 前端（本页面）
```

后端（`dashboard/plugin_api.py`）把 `state.db` 的遥测聚合与 CPU / 每核 CPU /
内存 / 网络 / 进程采样合成一份小 JSON 快照，缓存数秒，经 dashboard 进程内的
同源接口提供；前端每秒轮询一次，驱动光环、环带卡片、面板与 HUD。没有独立
服务，不多开端口。

## 数据与隐私

- **只读**：后端以只读方式打开 `state.db`，从不写入。
- **只查元数据**：只查会话 / 消息的元数据列 —— 计数、令牌总量、工具名、
  时间戳，**从不读取消息正文**。
- **登录之后**：全部插件接口（含 stats JSON 与 BGM 供音）都在 dashboard
  自身登录鉴权之后。未登录访问 stats 返回 **401，这是预期行为**，不是故障。
- **无遥测、无外连**：插件不向任何地方上报；页面不发任何外部请求 —— 字体
  走系统字体栈，全部资源（含 BGM）由 dashboard 本地提供。
- **进程采样只取进程名 / CPU / 内存**，从不读取进程命令行参数。

## BGM 与频谱

插件自带一首上游原曲（随原作许可证），舞台左下角有一个 7 段频谱小窗，随
正在播放的音乐跳动。换成你自己的音乐有两种方式：

1. **页面里换（按浏览器）**：点页面右上角的「本地音乐」，选你设备上的音频
   文件。文件存进浏览器本地（IndexedDB），刷新不丢；点「默认」随时切回
   自带曲。本地文件若损坏播不了，会自动退回自带曲，不会把播放器搞死。
2. **服务器上换（对所有访客生效）**：把已安装插件里的
   `dashboard/dist/haloflux/audio/sw421k.mp3` 换成你自己的 MP3（保持同名）。
   不用重启 —— 供音走插件的 `/api/plugins/haloflux/bgm` 路由（同一道登录
   鉴权），每次请求现读文件。

> 请只用你有权利使用的音乐。页面本地换曲的方式文件只留在你自己的设备上，
> 对有版权的曲目通常是更合适的选择。

## 面板一览

| # | 面板 | 内容 |
|---|------|------|
| 1 | AI 事件流 | 最近的工具调用（真实工具名），最新在前 |
| 2 | 令牌吞吐 | 滚动窗口算出的实时 tok/s 曲线 + 缓存命中率 |
| 3 | 运行状态 | 模型、当前会话及其消息 / 工具数、运行时长、最近事件 |
| 4 | CPU / GPU 负载 | 本机 CPU（总量 + 每核）与 GPU（如有） |
| 5 | 数据链路 | 插件链路状态、轮询间隔、会话文件数、插件版本 |
| 6 | 工具 / 消息 | 工具调用与消息总量及实时增量 |
| 7 | 代理调度 | 按模型分组的会话聚合：每组的会话数、活跃数、令牌、工具数 |
| 8 | 系统负载索引 | CPU / GPU / 内存 / 网络的活跃热力行 |

环带卡片显示本机占用最高的进程（名、CPU、内存、网络速率）。**没有显卡的
机器上 GPU 字段显示"不可用"，这是预期行为**，不是 bug。

## 平台支持

AI 数据（令牌、会话、工具、各面板）在所有平台上一致。系统采样（进程列表、
每核 CPU、网络速率）目前仅实现了 **Linux**；Windows / macOS 上对应位置会
诚实地显示空白 / `—`，不用假数字填充。桌面端细目与路线图见
[DESKTOP.md](DESKTOP.md)。

## 设计注记

几个踩出来的细节，记下来免得后来人重踩：

- **`state.db` 的 schema 各版本不一致**：可能缺列。后端对用到的每一列都做
  守卫，缺列就降级为 `null` / 空列表，绝不因为缺一列就 500。
- **"当前会话"不能只看 `started_at` / `ended_at`**：旧会话会残留"未结束"
  标记，实现里用的是组合判定（未结束标记 + 最近消息活动 + 开始时间），
  不是单列说了算。
- **速率是累计值的差分**：tok/s 用累计令牌总量在一个短滚动窗口上做差分 ——
  和顶部 KPI 是同一批计数器，曲线和总量永远对得上。
- **WAL 模式下只读打开要注意**：后端依赖实时数据库文件（包括 `-wal` 附属
  文件）可读；Hermes 还在运行时把 `HERMES_DB` 指向一个单独拷出来的 `.db`
  文件，读到的可能是旧数据。

## 自测记录

用 [`tools/make_demo_db.py`](tools/make_demo_db.py) 生成的虚构演示库验证
（输入 12,345,678 / 输出 234,567 / 缓存读 34,567,890 令牌、1,234 条消息、
567 次工具调用、23 个会话，全部虚构）：

| 场景 | 结果 |
|------|------|
| 演示库基线 | 全部聚合字段与生成数据逐项对账一致 |
| 缺列的库 | 优雅降级，不出 500 |
| 空库 / 无库 | 返回离线快照，页面显示离线态 |
| 写锁库 | 回退到上一份好的缓存快照 |
| 8 线程并发请求 | 无错误，快照一致 |
| 真实部署 | v1.3.0 已在真实 Hermes Agent v0.23.0 上部署验收（环带卡片、全部面板、频谱、本地音乐 BGM） |

## 与上游 ai-link 的区别

- **载体**：上游是 Wallpaper Engine 壁纸 + 独立 Node 服务；本作是 Hermes
  dashboard 插件，没有独立进程，不多开端口。
- **鉴权**：上游用自带令牌 + JSONP 降级；本作已移除 JSONP 与独立服务直连
  口径，完全走 dashboard 登录。
- **数据源**：上游读 DeepSeek Harness / Ekko Studio 的库；本作读 Hermes
  Agent 自己的 `state.db`，并加了 Linux 本机采样。

## 署名与许可证

署名链（全文见 [NOTICE](NOTICE)）：

1. **HALOFLUX**，作者 **Ryder191** —— https://github.com/Ryder191/haloflux
2. **HALOFLUX · AI LINK**，作者 **yeshuiwushen** —— https://github.com/yeshuiwushen/haloflux-ai-link
3. **HALOFLUX for Hermes** —— 本仓库，将上者移植为 dashboard 插件。

许可证为 **PolyForm Noncommercial License 1.0.0**，上游许可证全文原样收录
于 [LICENSE](LICENSE)。**仅限非商业用途**，不提供商业授权。原作（包括其
源代码与视听设计）的版权归 Ryder191 所有。
