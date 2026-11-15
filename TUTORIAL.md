# HALOFLUX for Hermes — 小白安装教程

## 1. 这是什么

HALOFLUX for Hermes 是一个 Hermes Agent dashboard 插件：它把 HALOFLUX 的
光环可视化接上你自己 Hermes 的实时数据——令牌总量、生成速率、缓存命中
率、工具调用、会话、当前任务，一起驱动中央光环、环带上的进程卡片和底部
8 个数据面板跳动。还带一个会随音乐节奏跳动的 BGM 频谱小窗。

数据全部来自 Hermes 自己的会话数据库（只读），不上传、不联网、不经过
任何第三方服务。

<!-- 截图占位：发布前在此处插入一张实际运行截图（建议用演示数据，
     不要用你自己的真实会话标题） -->

血统与许可：原作 HALOFLUX © Ryder191；二次改编 HALOFLUX · AI LINK by
yeshuiwushen；本作是其 Hermes dashboard 插件移植（完整署名链见仓库
NOTICE）。许可证 PolyForm Noncommercial License 1.0.0，**仅限非商业
使用**。

## 2. 装之前要有的东西

- 一个能正常登录的 **Hermes dashboard**（本插件在 Hermes Agent
  **v0.23.0** 上实测通过，其它版本未逐一验证）；
- 能碰到 Hermes 所在机器的文件系统（本机、SSH、远程桌面都行），因为
  安装就是把几个文件放进插件目录。

不需要 Node、不需要编译、不需要额外账号、不需要改任何配置。

## 3. 安装（三条路任选其一）

先把本仓库下载或克隆到任意目录，下面的命令都在**仓库根目录**里执行。

### 路线 A：一键脚本（Linux / macOS）

```sh
./scripts/install.sh
```

### 路线 B：一键脚本（Windows）

在 PowerShell 里执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

### 路线 C：手动复制

把仓库里的 `dashboard/` 整个目录，复制到 Hermes 的插件目录里，让最终
结构长这样：

```
~/.hermes/plugins/haloflux/dashboard/manifest.json
~/.hermes/plugins/haloflux/dashboard/plugin_api.py
~/.hermes/plugins/haloflux/dashboard/dist/...
```

如果你给 Hermes 设置了 `HERMES_HOME` 环境变量，把上面的 `~/.hermes`
换成那个路径即可。

**三条路做的事完全一样**：一键脚本只负责复制文件；目标位置已有旧版时，
会先把旧版备份到同目录旁的 `haloflux.bak-<时间戳>`。脚本不联网、不改
配置、不会自动重启任何服务。

## 4. 启用

1. 重启 hermes-dashboard。用 systemd 管理的安装，命令是：

   ```sh
   systemctl restart hermes-dashboard
   ```

   其它安装方式（手动拉起、容器、桌面端）就重启你自己的 dashboard
   进程，效果一样——插件是被 dashboard 自动发现的，不用改配置。

2. 在浏览器里**先登录 dashboard**（插件接口走 dashboard 的登录鉴权，
   没登录会被挡回去，这是故意的）。

3. 打开：

   ```
   https://你的地址/haloflux
   ```

   把「你的地址」换成你平时打开 dashboard 的地址和端口。

> **入口在哪：** 网页版 dashboard 左侧边栏「插件」一栏里就有
> **HALOFLUX**，点它就能进（和 KANBAN、ACHIEVEMENTS 并列）。个别前端
> （如手机 App 内嵌页）不画插件入口时，直接打开 `/haloflux` 也一样。

## 5. 验证清单（逐项打勾）

- [ ] `/haloflux` 页面能打开，不再跳回登录页；
- [ ] 页面上的数字是活的：令牌总量、会话数和你实际用 Hermes 的量对得
      上，发一条消息后工具调用 / 消息数会变；
- [ ] 在**未登录**的浏览器（或无痕窗口）里访问
      `https://你的地址/api/plugins/haloflux/stats`，返回 **401**——
      这是成功标志，说明接口在登录鉴权后面，没有裸奔；
- [ ] 底部「数据链路」面板显示服务版本 **v1.3.0**；
- [ ] （Linux）中央光环环带上的卡片显示的是你机器上的真实进程名、
      CPU 和内存；
- [ ] 在页面上点一下（给浏览器播放许可），BGM 响起，左下角频谱小窗的
      7 根柱子随节奏跳动。

全部打勾，安装完成。

## 6. 换 BGM（两条路）

插件自带一首曲子（上游素材）。想换成你自己的歌，任选一条路：

### 路 1：页面里选本地文件（最简单，按浏览器生效）

点页面右上角的「**本地音乐**」按钮，选一个你设备上的音频文件，当场
就换。文件只存在你这个浏览器的本地存储里，不上传服务器；换浏览器或
换设备要重新选一次。想换回去，点旁边的「**默认**」即可恢复自带曲。

### 路 2：替换服务器上的文件（所有设备统一生效）

把你的音频文件改名覆盖这个位置（替换前先备份原文件）：

```
~/.hermes/plugins/haloflux/dashboard/dist/haloflux/audio/sw421k.mp3
```

（用了 `HERMES_HOME` 的话换前缀。）覆盖完刷新页面即可，不用重启、
不用改代码——音乐是经插件自己的路由供出来的。文件请用 MP3 等浏览器
能直接播的格式。

## 7. 常见问题

| 现象 | 原因与处理 |
|---|---|
| 打开 `/haloflux` 跳回登录页 | 还没登录 dashboard。先登录，再开 `/haloflux`。 |
| 接口返回 401，或页面提示登录过期 | 正常现象：插件接口在登录鉴权后面，401 说明鉴权在工作。登录过期就重新登录 dashboard。 |
| 页面能开，但数字不动 / 显示离线 | dashboard 刚重启时等几秒再刷新；还不行，确认 Hermes 的会话库路径对不对——自定义过路径的，用 `HERMES_DB` 环境变量指向 `state.db`，改完要重启 dashboard 才生效。 |
| 环带卡片是空的、没有进程名 | 先看你是不是非 Linux 系统：进程采样目前只实现了 Linux，Windows / macOS 上这里会诚实地空着（见 DESKTOP.md 的平台表），AI 数据部分不受影响。Linux 上则刷新等几秒，采样需要两次读数做差分。 |
| GPU 显示「不可用」 | 你的机器没有可用显卡（或没有探针），这是诚实显示，不影响其它数据。 |
| BGM 没声音 | 先在页面上点一下：浏览器禁止没打过招呼的自动播放。若之前文件加载失败过，BGM 会被自动禁用防反复请求，刷新页面再点一次即可。 |
| 代理调度面板只有一行 / 是空的 | 它是按「模型」分组的：你只用了一个模型就只有一组，只用过一个会话也可能接近空态，属正常。 |
| 频谱小窗不动 | BGM 还没开始播时它是平躺待机的；点一下页面让 BGM 响起来就会跳。 |
| 侧边栏找不到 HALOFLUX 入口 | 网页版在左侧「插件」一栏；个别前端（如手机 App 内嵌页）不画入口，直接打开 `/haloflux`。 |

## 8. 卸载与回滚

- **停用 / 卸载**：删掉 `~/.hermes/plugins/haloflux` 目录，再重启
  hermes-dashboard，页面和接口就都没了。插件从不写 Hermes 的数据库
  （只读），卸载不会留下数据残留。
- **回滚到上一版**：用一键脚本装过的话，旧版备份在
  `~/.hermes/plugins/` 里，名叫 `haloflux.bak-<时间戳>`。删掉现行
  `haloflux`，把备份目录改名回 `haloflux`，重启 dashboard 即可。

---

有问题先看仓库 README 的设计说明与自测记录；再不行，带上你的 Hermes
版本和上面验证清单卡住的那一项去提 Issue。
