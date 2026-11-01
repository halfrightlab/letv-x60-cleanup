# 乐视 X60 可撤销精简工具

> 开机广告、后台上报、购物推送……这台老电视背了太多它不想背的东西。帮它卸卸货。

乐视 X60 的屏幕其实还很能打，就是开机先放广告、后台偷偷跑一堆服务、桌面挤满推荐，用起来像在逛商场。这个工具帮它**减负**：

- 🚫 停掉广告、广告屏保、日志上报、购物这几个已经认出来的「累赘」
- 🏠 装上干净的 **SimpleTV** 桌面，开机直接进，四列两行，一眼看完
- ⚡ 三项系统动画调到 `0.5`，切换起来更利落
- ↩️ **每一步都能撤销**：改之前先备份原值，一条 `restore` 就能回到原样

它不刷机、不升级 Android、不替换系统底层，只是把不想要的东西「关掉」而不是「删掉」。

[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](LICENSE)
[![Release](https://img.shields.io/github/v/release/halfrightlab/letv-x60-cleanup?style=flat-square)](https://github.com/halfrightlab/letv-x60-cleanup/releases)
[![Device](https://img.shields.io/badge/LeTV-X60%20%C2%B7%20EUI%206.0.070S-e60012?style=flat-square)](#先看你的电视能不能用)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](x60_tool.py)

[脱敏验证摘要](./validation.json) · [验证边界](./ROADMAP.md) · [第三方 SimpleTV 许可证](./SIMPLETV-LICENSE.txt)

## 先看你的电视能不能用

这个工具是「量体裁衣」做的，只认一种固件。对不上就会自己停下，不会硬来：

| 项目 | 要求 |
|---|---|
| 机型 / 硬件 | `LeTVX60` / `X603100` |
| 系统 | Android `4.1.2`（API 16，armeabi-v7a） |
| EUI | `6.0.070S_0703` |
| 固件 | 包含 `V1101RCN02C060070B07031S` |

除了这些，工具还会核对系统框架、原生开机播放器、厂商权限入口和目标 APK 的 SHA-256。所以**固件名字一样，也可能因为你后来更新过某个应用而被拦下**。比如购物应用目前只接受原案例的 `4.2.2`，旧出厂版 `3.2.0` 带数据提供器，没纳入停用范围。

被拦下了也别去改 `profile.json` 或者刷别的电视的文件来「骗过」检测。检测就是来保护你的电视的。

## 它到底改了什么

| 动作 | 细节 |
|---|---|
| 停用 4 个整包 | 广告管理、广告屏保、日志上报、购物。只停用，不卸载 |
| 天气 | 只停更新服务和自启 / 定时接收器，天气应用和两个提供器保留 |
| 动画 | 三项系统动画设为 `0.5` |
| 开机宣传视频 | 先完整备份，再原地改名隔离 |
| SimpleTV 桌面 | 安装作者原版 SimpleTV `1.5.9`，配置四列两行快捷方式；已有布局先备份。快捷方式对应的应用不存在就留空，不会顺手帮你装酷喵之类的 |
| 开机组件 | 新增 `X60 SimpleTV Boot 1.1`，见下文 |

**开机组件**是本项目新写的一个小程序，只申请了 `RECEIVE_BOOT_COMPLETED` 权限：不联网、不共享 UID、没有常驻服务。它接收这版固件 EUI 桌面的启动通知，用一次两秒的定时交接打开 SimpleTV；按本次开机 ID 去重，正常的 Android 开机广播作为第二条入口。

实际效果：每次开机自动进 SimpleTV。底层 Android 还是要先启动，所以中间可能闪一下原界面。物理主页键、返回键和待机唤醒都没改，在 SimpleTV 里按返回键会回到原桌面。

## 准备工作

1. **只在你自己的电视上用**，由电视主人本人操作。
2. 电脑装好 Python `3.9` 或更新版本，再下载 [Google 官方 Platform-Tools](https://developer.android.com/tools/releases/platform-tools)。ADB 解压就能用，不用全局安装，也不用 `sudo`。
3. 电脑和电视连在同一个家庭局域网，记下电视的 IP。
4. 打开电视的调试入口。这版固件上验证过的入口是「信号源 → 1 → 4 → 7」。别的固件上不灵就停下，别乱猜口令。
5. 电视弹出连接授权时，本人批准这一次就好，**不要勾「始终允许」**。电脑如果弹本地网络权限提示，自己看清楚再决定，工具不会替你改系统权限。
6. 让电视停在原桌面或 SimpleTV，别在播放东西。工具只连你给的那一个 IP，不扫描网络。

## 下载

1. 到 [Releases](https://github.com/halfrightlab/letv-x60-cleanup/releases) 下载 [完整工具 ZIP](https://github.com/halfrightlab/letv-x60-cleanup/releases/download/v2.0.0/letv-x60-tool-v2.zip) 和 [SHA-256 校验文件](https://github.com/halfrightlab/letv-x60-cleanup/releases/download/v2.0.0/letv-x60-tool-v2.zip.sha256)。
2. 在两个文件所在目录运行 `shasum -a 256 -c letv-x60-tool-v2.zip.sha256`，显示 `OK` 再解压。ZIP 的 SHA-256 是 `afc30cd942a0f5dad5f8048e056b2579eef86f56ab55d9f0bdb3b8fee1ec6a50`。
3. 认准完整工具 ZIP，它里面带着两个必需的 APK。GitHub 自动生成的 `Source code (zip)` 和 `Code → Download ZIP` 只是源码快照，**缺 APK，跑不起来**。

## 四条命令

在解压出来的 `letv-x60-tool-v2` 目录里打开终端，把 `TV_IP` 和 ADB 路径换成你自己的：

```sh
# 1. 体检：只读核对兼容性，不改任何配置
python3 x60_tool.py inspect --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"

# 2. 动手：先备份原值，再应用固定范围的优化
python3 x60_tool.py apply   --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"

# 3. 复查：检查上次应用或恢复后的状态
python3 x60_tool.py check   --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"

# 4. 后悔药：撤销本工具的改动，回到第一次 apply 之前
python3 x60_tool.py restore --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"
```

Windows 把 `python3` 换成 `py -3`，ADB 路径指向 `adb.exe`，其余一样。

**`inspect` 没通过，就不要往下跑 `apply`。**

几个值得知道的细节：

- `inspect` 会从电视上下载少量框架和目标 APK 到私人检查目录做哈希比对，读一些设备信息，不提权、不改配置。
- 所有模式都用本机独立的 ADB 端口 `5038`，被占用就停。电视调试端口默认 `5555`，只有电视明确显示别的端口时才用 `--port`。
- 每条命令带时间戳。logcat 只在命令执行期间显示少量新产生的相关错误，不保存、不长期采集。每次运行的命令和返回值存进 `runs/`。

## 备份目录：比遥控器还重要

`--state` 指定的目录是这台电视的「病历本」：设备识别信息、原应用备份、布局、原广告素材都在里面。

- **每台电视一个目录**，好好保存，不要拿另一台电视的目录来用。
- 里面有设备识别信息，**不要公开转发**。
- 第一次 `apply` 会生成 `original.json`，以后不会被当前状态覆盖。所以同一个目录可以「应用 → 撤销 → 再应用」随便来回。
- 电视 IP 变了可以换 `--ip`，但备份仍要和原设备对得上。

## 撤销会撤到哪

`restore` 恢复的是**这台电视第一次 `apply` 之前**的样子：

- 恢复目标状态、动画原值（包括那一行原来存不存在）、SimpleTV 布局和开机素材。
- 只移除本工具新装的两个应用，你之前自己装的都留着。
- 原来就被别的办法禁用的广告包，撤销后还是禁用，它不会「好心」帮你打开。
- 布局恢复会替换这次涉及的两个偏好文件，所以 apply 之后你手动改的布局也会一起撤掉。
- 工具不写厂商权限数据库。

## 装完怎么验收

`APPLIED` 的意思是：工具已经读回包和组件、动画、布局、素材状态，以及原有应用是否保留。**它没有替你看过开机过程。**

所以请亲自做一次完整重启：

- [ ] 自动进入 SimpleTV
- [ ] 开机过程中没有商业广告
- [ ] 遥控器、设置、信号源都正常
- [ ] 待机唤醒也单独试一次（短按电源可能只是待机，不能代替完整重启）

重启后按前面的入口重新打开 ADB，再跑一次 `check`。

## 出问题了怎么办

- 遇到 `STOP`、超时或者中断：**整个私人目录原样保留**，看最新一次 `runs/` 里的 `error.json` 和 `commands.json`。
- 退出码是 `0` 不代表每个 Binder 操作都成功了，工具会另外读回确认。结果说不清时先查实际状态，别闷头重复 `apply`。
- 别删备份、别手改 `original.json` 来让报错消失。那不是修好了，是把病历撕了。
- 电视返回 `Connection refused`：重新打开调试。Android 4.1.2 没有 Android 11 那种无线调试配对功能。

## 关于提权（给好奇的人）

普通的 `adb root` 拿不到这套方案需要的权限。清理和原值恢复沿用在原机上验证过的临时 UID `0` 方法：先检查厂商脚本 / 二进制、busybox 是否缺失、PPP 是否空闲，用私有临时目录，做完就清理。

它会调用厂商的 `pppmanager disconnect` 入口，所以**正在用 PPP / PPPoE 拨号上网的电视不要用**，环境不对工具也会自己停。它不调整权限策略，不加常驻服务，不改网络属性。开机组件本身不需要 root。

`apply`、`check`、`restore` 核对素材和布局时可能临时取得 UID `0`；`check` 不改持久配置。

## 验证到哪一步了（如实说明）

- ✅ 原案例电视完成了「应用 → 撤销 → 再应用」，开机组件 `1.1` 通过完整重启实机验收：自动进入 SimpleTV，没有商业广告，组件读回了和新开机 ID 一致的真实启动回调。方向键和设置入口可用，返回键保留原系统行为。
- ⚠️ 这轮循环用的是一台已经优化过的电视，首次安装、移除新增应用、素材移动这三个分支没有覆盖到；素材隔离 / 恢复 / 再隔离、旧包和组件恢复在此前的原机测试里分别验证过。
- ❌ 没有第二台电视，也没有恢复出厂后的整套测试。
- ❌ 没有数据能证明开机或菜单变快了，不会把停用了几个包当成提速幅度来吹。也不保证所有应用内广告都消失。

## 仓库里有什么

```text
x60_tool.py           单文件命令工具
profile.json          已识别的固件、系统文件和 APK 哈希
boot-app/             开机组件完整 Java 源码及清单
SIMPLETV-LICENSE.txt  SimpleTV 原作者的 Apache 2.0 许可证
validation.json       脱敏验证摘要
ROADMAP.md            已完成和尚未验证的事项
```

源码都直接展开在仓库里，可以随便看、比较、修改。Releases 里的完整工具 ZIP 另外带 `assets/`，里面是原版 SimpleTV 和本项目自建的开机组件 APK。

## 来源与边界

- **Simple TV Launcher `1.5.9`** 是 [原作者 GitHub 发行版](https://github.com/alescdb/LauncherTV/releases/tag/v1.5.9) 的未修改 APK，SHA-256 为 `633dda416c05046d887e8112a8e43f0735d92fd0b737f3bfecc255e4f24f9615`。版权归 Alexandre Del Bigio，许可证随包保留。布局格式核对了同一标签的 `Setup.java`、`ApplicationFragment.java` 和 `ApplicationView.java`。
- **开机组件**是本项目新写的源码，独立签名，只会打开 `org.cosinus.launchertv/.Launcher`，不接受任意包名或命令。EUI 入口依据本固件 `services.jar` 里的 `startHomeActivityLocked` 和广播筛选代码；标准广播定义见 [Android 开机完成广播](https://developer.android.com/reference/android/content/Intent#ACTION_BOOT_COMPLETED)。两秒交接用系统单次定时器，接收器不对外导出；诊断和测试入口要求调用方具备 `DUMP` 权限。
- 本工具**不提供**固件、别的电视的备份、原机广告素材、ADB 密钥、登录凭据或任何盗版资源。

## 贡献者

| | 谁 | 干了什么 |
|---|---|---|
| 🧑‍🔬 | [半对实验室 halfrightlab](https://github.com/halfrightlab) | 出主意、贡献自家电视、真机验收 |
| 🤖 | [Claude](https://github.com/claude)（Anthropic） | 编程助手 |
| 🤖 | [Codex / ChatGPT](https://github.com/codex)（OpenAI） | 编程助手 |
| 🤖 | WorkBuddy | 编程助手 |

家里也有一台 X60、愿意帮忙验证第二台？欢迎提 issue。

## 许可协议

本项目代码采用 [Apache License 2.0](LICENSE)：可以自由使用、修改、商用，再分发时请保留 [NOTICE](NOTICE) 里的署名。SimpleTV 遵循其原作者的 [Apache 2.0 许可证](SIMPLETV-LICENSE.txt)。
