# HALOFLUX for Hermes — 桌面端部署

本插件不只能跑在服务器上：只要你的桌面电脑（Windows / macOS / Linux）本机
运行着 Hermes Agent 的 dashboard，就可以用下面的脚本一键装上，效果与
服务器端一致。

署名链（详见仓库 NOTICE）：原作 HALOFLUX © Ryder191；二次改编
HALOFLUX · AI LINK by yeshuiwushen；本作是其 Hermes dashboard 插件移植。
许可证：PolyForm Noncommercial License 1.0.0，仅限非商业使用。

## 现在就能用

下载或克隆本仓库后，在仓库根目录执行一条命令即可。脚本只做一件事：
把 `dashboard/` 复制到 Hermes 的插件目录
（`~/.hermes/plugins/haloflux/`，可用环境变量 `HERMES_HOME` 覆盖）。
已有旧版时会自动备份为同目录旁的 `haloflux.bak-<时间戳>`。
脚本不联网、不提权、不改任何配置、不会自动重启服务。

Linux / macOS：

```sh
sh scripts/install.sh
```

Windows（PowerShell）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

装完后：

1. 重启 `hermes-dashboard`（插件会被自动发现，无需改配置）；
2. 在 dashboard 里打开 `/haloflux`；
3. 未登录时先登录 dashboard（插件接口走 dashboard 的登录鉴权）。

## 桌面端数据完整度

| 数据 | 来源 | Windows | macOS | Linux |
|---|---|---|---|---|
| AI 数据：令牌、会话、工具调用、缓存命中率、底部面板 | Hermes 自己的 `state.db`（只读） | 完整 | 完整 | 完整 |
| 进程列表（环带卡片）、每核 CPU、网络速率 | 操作系统采样 | 显示为空 / `—` | 显示为空 / `—` | 已实现 |
| GPU 利用率 | 需专用探针 | 无探针时恒空 | 无探针时恒空 | 无探针时恒空 |

说明：系统采样目前只有 Linux 实现。Windows / macOS 上对应位置会诚实地
显示为空或 `—`，不会报错，也不会用假数据填充；AI 数据部分在所有平台
都是完整的，这才是这个看板的主体。

## 路线图

- **桌面原生采样器**：后端已经有一层平台分发（platform dispatch），
  Linux 采样器是第一个实现；`darwin` / `windows` 的进程列表、每核 CPU、
  网络速率采样器是预留接口，欢迎 PR 按同一接口补齐。
- **一键包形态**：当前发布形态就是 release zip + 本目录的安装脚本，
  解压后一条命令完成部署；后续如有更集成的分发方式会在此更新。
