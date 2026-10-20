# 乐视 X60 可撤销精简工具

用于原案例的 X60／X603100、EUI 6.0.070S_0703、Android 4.1.2 固件：停用已识别广告和后台组件，配置 SimpleTV 简洁桌面及开机进入，保留原值和撤销入口。它不会升级 Android 或替换底层系统。

## 下载与使用

1. 到 [Releases](https://github.com/halfrightlab/letv-x60-cleanup/releases) 下载 [完整工具 ZIP](https://github.com/halfrightlab/letv-x60-cleanup/releases/download/v2.0.0/letv-x60-tool-v2.zip) 和 [SHA-256 校验文件](https://github.com/halfrightlab/letv-x60-cleanup/releases/download/v2.0.0/letv-x60-tool-v2.zip.sha256)。在二者所在目录运行 `shasum -a 256 -c letv-x60-tool-v2.zip.sha256`，显示 `OK` 后解压。
2. 在解压得到的 `letv-x60-tool-v2` 目录中执行下文命令。完整工具 ZIP 包含两份必需 APK；GitHub 自动生成的 `Source code (zip)` 和 `Code → Download ZIP` 是源码快照，不是完整运行包。
3. 先运行 `inspect`，只有严格兼容检查通过后再运行 `apply`；每台电视保存自己的备份目录。恢复使用同一目录运行 `restore`。

ZIP SHA-256：`afc30cd942a0f5dad5f8048e056b2579eef86f56ab55d9f0bdb3b8fee1ec6a50`。

[脱敏验证摘要](./validation.json) · [第三方 SimpleTV 许可证](./SIMPLETV-LICENSE.txt) · [验证边界](./ROADMAP.md)

当前状态：原案例电视已完成应用／撤销／再应用，开机组件 `1.1` 已通过完整重启与本人实机验收，自动进入 SimpleTV，未出现商业广告。工具用于下列严格匹配的固件，尚未在第二台电视验收。

## 工具范围

- 停用广告管理、广告屏保、日志上报、购物四个已识别整包，原有应用不卸载。
- 天气只停更新服务和自启／定时接收器，保留天气应用及两个提供器。
- 三项动画设为 `0.5`。
- 对已核实的默认开机宣传视频完整备份，再原位改名隔离。
- 安装作者原版 SimpleTV `1.5.9`，配置四列两行快捷方式；已有布局先备份。快捷方式对应的原应用不存在时留空，不代装酷喵等应用。
- 新增 `X60 SimpleTV Boot 1.1` 开机组件，只有 `RECEIVE_BOOT_COMPLETED` 权限，无联网权限、共享 UID 或常驻服务。接收本固件的 EUI 桌面启动通知，通过一次两秒定时交接打开 SimpleTV；按本次开机 ID 去重，正常 Android 开机广播作为另一条入口。
- `restore` 恢复这台电视应用前保存的目标状态、动画原值及行存在性、SimpleTV 布局和开机素材；只移除本工具本次新装的两个应用，保留应用前已有的应用。工具不写厂商权限数据库。

开机组件每次开机成功打开 SimpleTV 一次，底层 Android 仍须启动，期间可能短暂显示原界面。物理主页键、返回键和待机唤醒路径未修改；本机从 SimpleTV 按返回键会进入原桌面。它不替换底层系统。

## 支持条件

已研究设备为 `LeTVX60`、硬件 `X603100`、Android `4.1.2 / API 16 / armeabi-v7a`、EUI `6.0.070S_0703`、固件含 `V1101RCN02C060070B07031S`。

工具还会核对系统框架、原生开机播放器、厂商权限入口和实际目标 APK 的 SHA-256。因此，同固件名称相同仍可能因后装应用更新不同而停止。购物应用目前只接受原案例的 `4.2.2`；旧出厂版 `3.2.0` 含数据提供器，未纳入整包停用。不要为通过检测而改 `profile.json` 或刷入其他电视的文件。

普通 `adb root` 不会直接获得本方案需要的权限。清理和原值恢复沿用已在原机验证的临时 UID `0` 方法，先检查厂商脚本／二进制、busybox 缺失及 PPP 空闲状态，使用私有临时目录，完成后清理。它会调用厂商 `pppmanager disconnect` 入口；环境不符即停止，不用于正在进行 PPP／PPPoE 拨号的电视。不调整权限策略，不新增常驻服务或更改网络属性；开机组件本身不需要 root。

## 目录

```text
x60_tool.py          单文件命令工具
profile.json         已识别固件、系统文件和 APK 哈希
boot-app/            本次开机组件完整 Java 源码及清单
SIMPLETV-LICENSE.txt  SimpleTV 原作者 Apache 2.0 许可证
```

上述源码直接展开在仓库中，可以浏览、比较和修改。Releases 的完整工具 ZIP 另含 `assets/`，提供原版 SimpleTV 和本次自建开机组件 APK；使用时下载完整工具 ZIP。

所有运行记录与备份放在你自己指定的 `--state` 目录，不在分享包内。每台电视单独一个目录，务必保存；它含设备识别资料、原应用备份、布局和原广告素材，不要公开转发。

## 使用前

1. 由电视所有者在自己的设备上授权操作。准备 Python `3.9` 或更新版本，以及 [Google 官方 Platform-Tools](https://developer.android.com/tools/releases/platform-tools) 。ADB 可直接解压使用，无须全局安装或 `sudo`。
2. 电脑与电视处于互通的家庭局域网，查看电视自己的 IP。在本机该版固件上，已验证的调试入口是「信号源 → 1 → 4 → 7」。其他固件无效就停止，不猜口令。
3. 如电视出现连接授权，由本人批准本次连接，不勾选“始终允许”。电脑如有本地网络权限提示，自行核对并明确决定；工具不会更改系统权限。
4. 回到原桌面或 SimpleTV，停止播放和其他操作。只连接你提供的单一 IP，不扫描网络。

## 命令

在解压目录打开终端，将 `TV_IP` 和 ADB 路径换成你自己的值。以下以 macOS／Linux 为例：

```sh
# 只读核对兼容性，不改电视配置
python3 x60_tool.py inspect --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"

# 保存本机原值和备份，然后应用固定范围优化
python3 x60_tool.py apply --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"

# 检查上次成功应用或恢复后的状态
python3 x60_tool.py check --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"

# 撤销本工具本次变更，恢复到首次 apply 之前
python3 x60_tool.py restore --ip TV_IP --adb "/path/to/platform-tools/adb" --state "./my-x60-backup"
```

Windows 使用 `py -3` 替换 `python3`，ADB 路径指向 `adb.exe`，参数用法相同。

`inspect` 会下载指定电视上少量框架和目标 APK 到私人检查目录作哈希比较，读取相关设备信息，不执行提权或配置修改。`apply`、`check`、`restore` 的素材和布局核对可能临时取得 UID `0`；`check` 不改持久配置。所有模式使用本机独立 ADB 端口 `5038`，被占用即停止。电视调试端口默认 `5555`，只有电视明确给出其他端口时才使用 `--port`。

首次 `apply` 创建 `original.json`，之后不会拿当前优化状态覆盖它。同一个私人目录可以执行“应用 → 撤销 → 再应用”。如电视 IP 变化可以更新 `--ip`，备份仍须匹配原设备标识；不要用另一台电视的目录。

每条命令会显示时间戳。logcat 仅在命令执行期间显示新产生的少量相关错误，不保存、不长期采集。每次运行的命令与返回值保存在 `runs/`。

## 验收与失败处理

`APPLIED` 表示工具已读回包／组件、动画、布局、素材状态及原有包保留情况，不代表本人看过启动过程。正常重启后须由本人确认自动进入 SimpleTV、观察有无广告、检查遥控／设置／信号源。短按电源可能只是待机，不能代替完整启动验收；待机唤醒也应单独检查。重启后按上述入口重新开启 ADB，再执行 `check`。

`RESTORED` 恢复的是首次 `apply` 前的配置。例如原来已被其他方法禁用的广告包仍会保持禁用；它不会擅自恢复到另一台电视或另一份历史记录的值。撤销布局会替换本次涉及的两个偏好文件，因此应用后的手动布局修改也会被撤销。原本没有的新应用在撤销时会被移除，其本地配置随之清除。

完整开机仍须本人观察；工具的配置检查或手动打开不能代替它。本版本接收 EUI 自身的启动事件，不通过修改厂商权限数据库维持自启。

本轮实机循环使用的是已经优化过的原案例电视：三步均读回通过，冻结的首次备份未被覆盖。该循环开始时广告素材已隔离、两个新增应用已经存在，因此没有覆盖首次安装、移除新增应用和素材移动三个分支；素材隔离／恢复／再次隔离、旧包和组件的恢复另有此前原机测试。本轮完整重启由本人确认自动进入 SimpleTV 且无商业广告，组件也读回了与新开机 ID 一致的真实启动回调。方向键及设置入口可用，返回键保留上述原系统行为。没有第二台电视或恢复出厂后整套测试，也没有可比数据证明整体开机、菜单提速。

遇到 `STOP`、超时或中断，保留整个私人目录，查看最新 `runs/` 下的 `error.json` 和 `commands.json`。不把退出码 `0` 当作所有 Binder 操作成功；工具会另行读回。结果不明时先检查实际状态，不盲目重复应用。不要删除备份或手改 `original.json` 来消除报错。电视返回 `Connection refused` 时，先重新开启调试；Android 4.1.2 没有 Android 11 的无线调试配对功能。

## 来源与边界

Simple TV Launcher `1.5.9` 为 [原作者 GitHub 发行版](https://github.com/alescdb/LauncherTV/releases/tag/v1.5.9) 的未修改 APK，SHA-256 为 `633dda416c05046d887e8112a8e43f0735d92fd0b737f3bfecc255e4f24f9615`。版权归 Alexandre Del Bigio，许可证随包保留。布局格式核对了同一标签的 `Setup.java`、`ApplicationFragment.java` 和 `ApplicationView.java`。

开机组件为本任务新增源码，使用独立签名，仅固定打开 `org.cosinus.launchertv/.Launcher`，不接受任意包名或命令。EUI 入口由本固件 `services.jar` 的 `startHomeActivityLocked` 和广播筛选代码核对；正常广播定义见 [Android 开机完成广播](https://developer.android.com/reference/android/content/Intent#ACTION_BOOT_COMPLETED) 。两秒交接使用系统单次定时器，接收器不对外导出；诊断与测试入口要求调用方具备 `DUMP` 权限。

本工具不提供固件、第三方电视的备份、原机广告素材、ADB 密钥、登录凭据或盗版来源。不保证所有应用内广告消失，不将停用包数量当作提速幅度，也没有在第二台电视做过硬件验收。
