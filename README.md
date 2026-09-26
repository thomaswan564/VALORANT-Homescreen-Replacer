# VALORANT Homescreen Replacer

> 🚀 **懒人直达：** [点击这里直接跳转到使用方法](https://github.com/thomaswan564/VALORANT-Homescreen-Replacer#-%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95)

一个用于替换《VALORANT》主菜单 / 首页背景视频（Homescreen）的 Windows 小工具。

本项目使用 Python + Tkinter 开发，支持 [Riot Games-VALORANT](https://playvalorant.com/) 国际服和 [Tencent Games-无畏契约](https://val.qq.com/main.html) 国服，可以自动搜索 VALORANT 安装目录，并通过选择或拖放 MP4 视频快速替换游戏主菜单视频。

> **仅用于个人学习、研究和自定义游戏体验。**
>
> 请勿将本项目用于商业用途或任何违反游戏服务条款的行为。
> 
> **VALORANT在启动时会校验文件完整性，所以在更改后第二次启动时，启动器会自动更新游戏，更新不影响此工具的作用（此条不适用于[WeGame-无畏契约](https://www.wegame.com.cn/)启动的中国服）**

---

## ✨ 功能

* 🎬 替换 VALORANT 主菜单 Homescreen 视频
* 🌍 支持 [Riot Games-VALORANT](https://playvalorant.com/) 国际服
* 🇨🇳 支持 [Tencent Games-无畏契约](https://val.qq.com/main.html) 中国服
* 🔍 自动搜索 VALORANT 安装目录
* 📁 支持手动选择 `Menu` 文件夹
* 🎥 自动识别当前 `*_Homescreen.mp4`
* 🖱️ 支持拖放 MP4 视频
* 💾 自动记住上次选择的视频路径
* 💾 自动记住 Riot / Tencent 的游戏目录
* 🔐 替换前自动备份原始视频
* ♻️ 支持恢复原始 Homescreen
* ⏳ 等待 VALORANT 启动后再执行替换
* 📝 内置运行日志
* 🖥️ 支持打包为独立 `.exe`
* 🚫 不需要修改游戏文件夹以外的程序配置

---

## 📸 使用界面

程序启动后，可以选择服务器类型：

* [Riot Games-VALORANT](https://playvalorant.com/)
* [Tencent Games-无畏契约](https://val.qq.com/main.html)

然后程序会自动寻找 VALORANT 的 `Menu` 文件夹。

如果没有自动找到，也可以手动选择：

```text
VALORANT
└── live
    └── ShooterGame
        └── Content
            └── Movies
                └── Menu
```

---

## 📂 VALORANT 视频位置

### [Riot Games-VALORANT](https://playvalorant.com/)

通常位于：

```text
Riot Games\VALORANT\live\ShooterGame\Content\Movies\Menu
```

### [Tencent Games-无畏契约](https://val.qq.com/main.html)

通常位于：

```text
Tencent Games\VALORANT\live\ShooterGame\Content\Movies\Menu
```

程序会自动在 `Menu` 文件夹中寻找包含：

```text
Homescreen.mp4
```

的文件。

例如：

```text
xxxx_Homescreen.mp4
```

---

## 🚀 使用方法

### 1. 选择视频

选择一个 `.mp4` 视频文件。

也可以直接将 MP4 文件拖入程序。

---

### 2. 选择服务器

根据自己的 VALORANT 客户端选择：

```text
Riot Games
```

或者：

```text
Tencent Games
```

---

### 3. 选择 Menu 文件夹

程序会自动搜索。

如果没有找到，可以点击手动选择目录。

目录应该类似：

```text
...\VALORANT\live\ShooterGame\Content\Movies\Menu
```

---

### 4. 执行替换

程序会等待 VALORANT 相关进程启动，然后自动替换 Homescreen 视频。

原始视频会首先被备份。

备份文件格式：

```text
原文件名.mp4.bak
```

例如：

```text
Homescreen.mp4
Homescreen.mp4.bak
```

---

### 5. 恢复原视频

如果想恢复 VALORANT 原本的 Homescreen，可以使用恢复功能。

程序会使用之前创建的：

```text
*.mp4.bak
```

进行恢复。

---

# 💾 配置文件

程序会自动保存用户上一次使用的路径。

配置文件**不会保存在 EXE 所在目录**，而是保存在 Windows 用户的 AppData 中：

```text
%APPDATA%\VALORANT_Homescreen\config.json
```

可以按：

```text
Win + R
```

输入：

```text
%APPDATA%\VALORANT_Homescreen
```

即可打开配置目录。

配置文件大致如下：

```json
{
    "video_path": "D:\\Videos\\my_video.mp4",
    "riot_menu_path": "C:\\Riot Games\\VALORANT\\live\\ShooterGame\\Content\\Movies\\Menu",
    "tencent_menu_path": "",
    "last_server": "riot"
}
```

这样即使移动或重新打包：

```text
VALORANT_Homescreen.exe
```

之前保存的路径也不会丢失。

---

# 🛠️ 从源码运行

## 环境要求

推荐：

```text
Windows 10 / Windows 11
Python 3.10+
```

安装依赖：

```powershell
py -m pip install psutil tkinterdnd2
```

运行：

```powershell
py main.py
```

---

# 📦 打包 EXE

安装 PyInstaller：

```powershell
py -m pip install pyinstaller
```

然后执行：

```powershell
py -m PyInstaller --onefile --windowed --name VALORANT_Homescreen --collect-all tkinterdnd2 main.py
```

生成的程序位于：

```text
dist\VALORANT_Homescreen.exe
```

---

## 🎨 使用自定义图标

如果仓库中有：

```text
icon.ico
```

可以执行：

```powershell
py -m PyInstaller --onefile --windowed --name VALORANT_Homescreen --icon=icon.ico --collect-all tkinterdnd2 main.py
```

最终：

```text
dist\
└── VALORANT_Homescreen.exe
```

---

# 📁 项目结构

推荐的项目结构：

```text
VALORANT-Homescreen-Replacer/
│
├── main.py
├── icon.ico
├── README.md
├── LICENSE
│
└── dist/
    └── VALORANT_Homescreen.exe
```

如果不希望将编译后的 EXE 放进 GitHub 仓库，也可以只上传源码和 Release：

```text
VALORANT-Homescreen-Replacer/
│
├── main.py
├── icon.ico
├── README.md
└── LICENSE
```

然后将：

```text
VALORANT_Homescreen.exe
```

上传到 GitHub Releases。

---

# ⚠️ 注意事项

### 1. 建议备份游戏文件

虽然程序会自动创建：

```text
*.mp4.bak
```

但仍然建议在修改之前备份相关游戏文件。

---

### 2. 游戏更新可能导致文件变化

VALORANT 更新后，Homescreen 文件名称、位置或格式可能发生变化。

如果更新后程序无法正常替换，请重新选择 `Menu` 文件夹，并检查当前 Homescreen 文件。

---

### 3. 视频格式

目前主要针对：

```text
.mp4
```

视频文件。

建议使用与原 Homescreen 视频相近的编码格式、分辨率和帧率，以减少兼容性问题。

---

### 4. 游戏更新后可能需要重新替换

VALORANT 更新可能会重新下载或覆盖原始 Homescreen 文件。

这种情况下重新运行本程序即可。

---

# 🔒 隐私

本程序不会主动上传：

* 视频文件
* VALORANT 游戏数据
* 用户名
* 游戏账号信息
* 个人文件

程序保存的路径信息仅存储在本地：

```text
%APPDATA%\VALORANT_Homescreen\config.json
```

---

# 📜 License

本项目仅供个人学习、研究及自定义游戏体验使用。

VALORANT、[Riot Games](https://www.riotgames.com/) 及 [Tencent](https://game.qq.com/) 等相关名称、商标和游戏内容归其各自所有者所有。

[Riot Games-VALORANT](https://playvalorant.com/):
> RIOT GAMES、《特戰英豪》及其相關標誌皆為 Riot Games, Inc.專屬之商標、服務商標及註冊商標。
> © 2020-2026 Riot Games, Inc. 版權所有。
> 通過下載，安裝和／或將Riot帳戶連接到特戰英豪遊戲軟體，即表示您同意台灣大哥大股份有限公司的「使用者合約」和「隱私權政策」。

[Tencent Games-无畏契约](https://val.qq.com/main.html)
> COPYRIGHT © 1998 - 2026 TENCENT.ALL RIGHTS RESERVED.
> 腾讯公司 版权所有
> 营业执照|粤网文[2023]2882-203号|（署）网出证（粤）字第054号
> 网络游戏行业防沉迷自律公约：本公司积极履行《网络游戏行业防沉迷自律公约》
> 审批文号：国新出审[2022]1665号
> 出版物号：ISBN 978-7-498-09857-3
> 防沉迷提醒：根据国家新闻出版署《关于防止未成年人沉迷网络游戏的通知》、《关于进一步严格管理切实防止未成年人沉迷网络游戏的通知》， 所有网络游戏用户均需使用有效身份信息完成账号实名注册后方可进入游戏，认证为未成年的玩家将受到防沉迷功能限制。

本项目与 [Riot Games](https://www.riotgames.com/)、[Tencent](https://game.qq.com/) 或 VALORANT 官方没有任何隶属、授权或合作关系。

---

# 👨‍💻 Author

**Thomas Wan**

Personal Website:

https://thomaswan.uk

---

Personal interest project, mainly developed for learning.

个人与兴趣项目，主要用于学习。

⭐ 如果这个项目对你有帮助，欢迎 Star。

Issues and Pull Requests are welcome.

欢迎提交 Issue 或 Pull Request，共同改进项目。
