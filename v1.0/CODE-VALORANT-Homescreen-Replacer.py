import os
import sys
import json
import shutil
import string
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import psutil

# ============================================================
# tkinterdnd2
# ============================================================

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False

    # 如果没有安装 tkinterdnd2，仍然允许程序启动
    # 只是拖拽功能不可用
    TkinterDnD = None


# ============================================================
# 基础配置
# ============================================================

APP_NAME = "VALORANT 主页面背景视频替换器"

CONFIG_DIR = os.path.join(
    os.environ.get(
        "APPDATA",
        os.path.expanduser("~")
    ),
    "VALORANT_Homescreen"
)

CONFIG_FILE = os.path.join(
    CONFIG_DIR,
    "config.json"
)

MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB

# ============================================================
# VALORANT 进程名称
# ============================================================

GAME_PROCESS_NAMES = {
    "VALORANT-Win64-Shipping.exe",
    "VALORANT.exe",
}


# ============================================================
# 游戏路径
# ============================================================

RIOT_RELATIVE_PATH = os.path.join(
    "Riot Games",
    "VALORANT",
    "live",
    "ShooterGame",
    "Content",
    "Movies",
    "Menu"
)

TENCENT_RELATIVE_PATH = os.path.join(
    "Tencent Games",
    "VALORANT",
    "live",
    "ShooterGame",
    "Content",
    "Movies",
    "Menu"
)


# ============================================================
# 默认配置
# ============================================================

DEFAULT_CONFIG = {
    "video_path": "",
    "riot_menu_path": "",
    "tencent_menu_path": "",
    "last_server": "riot"
}


# ============================================================
# 配置文件
# ============================================================

def ensure_config_dir():
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass


def load_config():
    ensure_config_dir()

    if not os.path.isfile(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()

    try:
        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        config = DEFAULT_CONFIG.copy()

        if isinstance(data, dict):
            config.update(data)

        return config

    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    ensure_config_dir()

    temp_file = CONFIG_FILE + ".tmp"

    try:
        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                config,
                f,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            temp_file,
            CONFIG_FILE
        )

        return True

    except Exception:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass

        return False


# ============================================================
# 工具函数
# ============================================================

def normalize_path(path):
    if not path:
        return ""

    path = os.path.expandvars(path)
    path = os.path.expanduser(path)

    try:
        path = os.path.abspath(path)
    except Exception:
        pass

    return os.path.normpath(path)


def is_mp4(path):
    if not path:
        return False

    return path.lower().endswith(".mp4")


def format_size(size):
    try:
        size = float(size)
    except Exception:
        return "未知"

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]

    index = 0

    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1

    return f"{size:.2f} {units[index]}"


def get_drives():
    drives = []

    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"

        if os.path.exists(drive):
            drives.append(drive)

    return drives


# ============================================================
# 搜索 VALORANT 路径
# ============================================================

def search_valorant_paths():
    """
    搜索所有磁盘：

        X:\Riot Games\VALORANT\live\...
        X:\Tencent Games\VALORANT\live\...

    返回：

        {
            "riot": "...",
            "tencent": "..."
        }
    """

    results = {
        "riot": "",
        "tencent": ""
    }

    for drive in get_drives():

        riot_path = os.path.join(
            drive,
            RIOT_RELATIVE_PATH
        )

        if (
            not results["riot"]
            and os.path.isdir(riot_path)
        ):
            results["riot"] = normalize_path(
                riot_path
            )

        tencent_path = os.path.join(
            drive,
            TENCENT_RELATIVE_PATH
        )

        if (
            not results["tencent"]
            and os.path.isdir(tencent_path)
        ):
            results["tencent"] = normalize_path(
                tencent_path
            )

        if (
            results["riot"]
            and results["tencent"]
        ):
            break

    return results


# ============================================================
# 搜索 Homescreen
# ============================================================

def find_homescreen_files(menu_path):
    """
    找到 Menu 文件夹中：

        xxx_Homescreen.mp4
        xxx_homescreen.mp4

    等包含 Homescreen.mp4 的文件。

    返回按修改时间倒序排列。
    """

    menu_path = normalize_path(menu_path)

    if not menu_path:
        return []

    if not os.path.isdir(menu_path):
        return []

    result = []

    try:
        for filename in os.listdir(menu_path):

            full_path = os.path.join(
                menu_path,
                filename
            )

            if not os.path.isfile(full_path):
                continue

            lower_name = filename.lower()

            if (
                lower_name.endswith(".mp4")
                and "homescreen.mp4" in lower_name
            ):
                try:
                    mtime = os.path.getmtime(
                        full_path
                    )
                except Exception:
                    mtime = 0

                result.append(
                    (
                        full_path,
                        mtime
                    )
                )

    except Exception:
        return []

    result.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return [
        item[0]
        for item in result
    ]


# ============================================================
# 获取当前 Homescreen
# ============================================================

def get_current_homescreen(menu_path):
    files = find_homescreen_files(menu_path)

    if not files:
        return ""

    # 默认使用最新修改的 Homescreen
    return files[0]


# ============================================================
# 进程检测
# ============================================================

def get_running_game_processes():
    """
    获取当前所有 VALORANT 相关进程。
    """

    result = []

    try:
        for proc in psutil.process_iter(
            ["pid", "name", "exe"]
        ):
            try:
                name = proc.info.get("name") or ""
                exe = proc.info.get("exe") or ""

                name_lower = name.lower()
                exe_name = os.path.basename(
                    exe
                ).lower()

                if (
                    "valorant" in name_lower
                    or "valorant" in exe_name
                ):
                    result.append(
                        {
                            "pid": proc.info.get("pid"),
                            "name": name,
                            "exe": exe
                        }
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
            ):
                continue

    except Exception:
        pass

    return result


def is_process_running(process_names=None):
    """
    检测 VALORANT 游戏进程。

    支持：

        VALORANT-Win64-Shipping.exe
        VALORANT.exe
    """

    if process_names is None:
        process_names = GAME_PROCESS_NAMES

    targets = {
        name.lower()
        for name in process_names
    }

    try:
        for proc in psutil.process_iter(
            ["name", "exe"]
        ):
            try:
                name = proc.info.get("name") or ""

                if name.lower() in targets:
                    return True

                exe = proc.info.get("exe") or ""

                if exe:
                    exe_name = os.path.basename(
                        exe
                    ).lower()

                    if exe_name in targets:
                        return True

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
            ):
                continue

    except Exception:
        return False

    return False


# ============================================================
# 主程序
# ============================================================

class ValorantHomescreenApp:

    def __init__(self, root):

        self.root = root

        self.root.title(APP_NAME)

        self.root.geometry(
            "900x760"
        )

        self.root.minsize(
            820,
            680
        )

        self.config = load_config()

        self.operation_running = False

        self.stop_event = threading.Event()

        self.scan_thread = None

        self.replace_thread = None

        # ----------------------------------------------------
        # Variables
        # ----------------------------------------------------

        self.server_var = tk.StringVar(
            value=self.config.get(
                "last_server",
                "riot"
            )
        )

        self.game_path_var = tk.StringVar()

        self.video_path_var = tk.StringVar(
            value=self.config.get(
                "video_path",
                ""
            )
        )

        self.target_var = tk.StringVar(
            value=""
        )

        self.status_var = tk.StringVar(
            value="正在初始化..."
        )

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.build_ui()

        # ----------------------------------------------------
        # Drag & Drop
        # ----------------------------------------------------

        self.setup_drag_drop()

        # ----------------------------------------------------
        # 关闭事件
        # ----------------------------------------------------

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        # ----------------------------------------------------
        # 加载保存的路径
        # ----------------------------------------------------

        self.load_saved_paths()

        # ----------------------------------------------------
        # 启动自动搜索
        # ----------------------------------------------------

        self.root.after(
            500,
            self.start_auto_scan
        )


    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        # ----------------------------------------------------
        # 主容器
        # ----------------------------------------------------

        main = ttk.Frame(
            self.root,
            padding=15
        )

        main.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # 标题
        # ----------------------------------------------------

        title = ttk.Label(
            main,
            text="VALORANT 主页面背景视频替换器",
            font=(
                "Microsoft YaHei UI",
                18,
                "bold"
            )
        )

        title.pack(
            anchor="w"
        )

        subtitle = ttk.Label(
            main,
            text=(
                "等待游戏启动后自动替换主页面背景视频"
            ),
            foreground="#666666"
        )

        subtitle.pack(
            anchor="w",
            pady=(3, 15)
        )

        # ----------------------------------------------------
        # 服务器区域
        # ----------------------------------------------------

        server_frame = ttk.LabelFrame(
            main,
            text="游戏版本"
        )

        server_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Radiobutton(
            server_frame,
            text="国际服 (Riot Game)",
            value="riot",
            variable=self.server_var,
            command=self.server_changed
        ).pack(
            side="left",
            padx=15,
            pady=10
        )

        ttk.Radiobutton(
            server_frame,
            text="中国服 (Tencent Game)",
            value="tencent",
            variable=self.server_var,
            command=self.server_changed
        ).pack(
            side="left",
            padx=15,
            pady=10
        )

        # ----------------------------------------------------
        # 游戏 Menu 路径
        # ----------------------------------------------------

        path_frame = ttk.LabelFrame(
            main,
            text="VALORANT 主页面背景视频文件夹"
        )

        path_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        path_entry_frame = ttk.Frame(
            path_frame
        )

        path_entry_frame.pack(
            fill="x",
            padx=10,
            pady=10
        )

        self.game_path_entry = ttk.Entry(
            path_entry_frame,
            textvariable=self.game_path_var
        )

        self.game_path_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            path_entry_frame,
            text="选择文件夹",
            command=self.select_game_folder
        ).pack(
            side="left",
            padx=(8, 0)
        )

        ttk.Button(
            path_entry_frame,
            text="重新搜索",
            command=self.start_auto_scan
        ).pack(
            side="left",
            padx=(8, 0)
        )

        # ----------------------------------------------------
        # Homescreen
        # ----------------------------------------------------

        target_frame = ttk.LabelFrame(
            main,
            text="当前主页面背景"
        )

        target_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            target_frame,
            textvariable=self.target_var,
            wraplength=820
        ).pack(
            fill="x",
            padx=10,
            pady=10
        )

        # ----------------------------------------------------
        # 新视频
        # ----------------------------------------------------

        video_frame = ttk.LabelFrame(
            main,
            text="新的 MP4 视频"
        )

        video_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        video_entry_frame = ttk.Frame(
            video_frame
        )

        video_entry_frame.pack(
            fill="x",
            padx=10,
            pady=(10, 5)
        )

        self.video_entry = ttk.Entry(
            video_entry_frame,
            textvariable=self.video_path_var
        )

        self.video_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        ttk.Button(
            video_entry_frame,
            text="选择 MP4",
            command=self.select_video
        ).pack(
            side="left",
            padx=(8, 0)
        )

        # ----------------------------------------------------
        # 拖拽提示
        # ----------------------------------------------------

        self.drop_label = tk.Label(
            video_frame,
            text=(
                "将 MP4 文件直接拖到这里"
                if DRAG_DROP_AVAILABLE
                else
                "拖拽功能未启用，请安装 tkinterdnd2"
            ),
            height=2,
            relief="groove",
            bd=1,
            fg="#555555"
        )

        self.drop_label.pack(
            fill="x",
            padx=10,
            pady=(5, 10)
        )

        # ----------------------------------------------------
        # 操作按钮
        # ----------------------------------------------------

        button_frame = ttk.Frame(
            main
        )

        button_frame.pack(
            fill="x",
            pady=(5, 10)
        )

        self.replace_button = ttk.Button(
            button_frame,
            text="替换主页面背景",
            command=self.replace_video
        )

        self.replace_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5)
        )

        self.restore_button = ttk.Button(
            button_frame,
            text="恢复原始主页面背景",
            command=self.restore_original
        )

        self.restore_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5
        )

        self.status_button = ttk.Button(
            button_frame,
            text="刷新状态",
            command=self.check_status
        )

        self.status_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(5, 0)
        )

        # ----------------------------------------------------
        # 状态
        # ----------------------------------------------------

        status_frame = ttk.LabelFrame(
            main,
            text="状态"
        )

        status_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            status_frame,
            textvariable=self.status_var
        ).pack(
            anchor="w",
            padx=10,
            pady=8
        )

        # ----------------------------------------------------
        # 日志
        # ----------------------------------------------------

        log_frame = ttk.LabelFrame(
            main,
            text="运行日志"
        )

        log_frame.pack(
            fill="both",
            expand=True
        )

        log_inner = ttk.Frame(
            log_frame
        )

        log_inner.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8
        )

        self.log_text = tk.Text(
            log_inner,
            height=12,
            wrap="word",
            state="disabled",
            font=(
                "Consolas",
                9
            )
        )

        scrollbar = ttk.Scrollbar(
            log_inner,
            orient="vertical",
            command=self.log_text.yview
        )

        self.log_text.configure(
            yscrollcommand=scrollbar.set
        )

        self.log_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )


    # ========================================================
    # Drag & Drop
    # ========================================================

    def setup_drag_drop(self):

        if not DRAG_DROP_AVAILABLE:
            return

        try:
            # 整个窗口都接受拖拽
            self.root.drop_target_register(
                DND_FILES
            )

            self.root.dnd_bind(
                "<<Drop>>",
                self.on_drop
            )

            # 单独的拖拽区域
            self.drop_label.drop_target_register(
                DND_FILES
            )

            self.drop_label.dnd_bind(
                "<<Drop>>",
                self.on_drop
            )

        except Exception as e:
            self.log(
                f"拖拽功能初始化失败：{e}"
            )


    def on_drop(self, event):

        try:
            files = self.root.tk.splitlist(
                event.data
            )

        except Exception:
            files = []

        if not files:
            return

        mp4_file = ""

        for file_path in files:

            file_path = normalize_path(
                file_path
            )

            if is_mp4(file_path):
                mp4_file = file_path
                break

        if not mp4_file:

            self.log(
                "拖拽的文件不是 MP4。"
            )

            messagebox.showwarning(
                "文件格式错误",
                "请拖入 MP4 视频文件。"
            )

            return

        self.set_video_path(
            mp4_file
        )

        self.log(
            f"已通过拖拽选择视频：{mp4_file}"
        )


    # ========================================================
    # 日志
    # ========================================================

    def log(self, message):

        def write_log():

            try:
                self.log_text.configure(
                    state="normal"
                )

                current_time = time.strftime(
                    "%H:%M:%S"
                )

                self.log_text.insert(
                    "end",
                    f"[{current_time}] {message}\n"
                )

                self.log_text.see(
                    "end"
                )

                self.log_text.configure(
                    state="disabled"
                )

            except Exception:
                pass

        try:
            self.root.after(
                0,
                write_log
            )

        except Exception:
            pass


    # ========================================================
    # 状态
    # ========================================================

    def set_status(self, text):

        try:
            self.root.after(
                0,
                lambda: self.status_var.set(text)
            )

        except Exception:
            pass


    # ========================================================
    # 加载保存路径
    # ========================================================

    def load_saved_paths(self):

        server = self.server_var.get()

        if server == "riot":
            path = self.config.get(
                "riot_menu_path",
                ""
            )

        else:
            path = self.config.get(
                "tencent_menu_path",
                ""
            )

        if path and os.path.isdir(path):

            self.game_path_var.set(
                path
            )

            self.update_target()

        video_path = self.config.get(
            "video_path",
            ""
        )

        if video_path:
            self.video_path_var.set(
                video_path
            )


    # ========================================================
    # 服务器切换
    # ========================================================

    def server_changed(self):

        server = self.server_var.get()

        if server == "riot":

            path = self.config.get(
                "riot_menu_path",
                ""
            )

        else:

            path = self.config.get(
                "tencent_menu_path",
                ""
            )

        self.game_path_var.set(
            path
        )

        self.config["last_server"] = server

        save_config(
            self.config
        )

        self.update_target()


    # ========================================================
    # 手动选择游戏文件夹
    # ========================================================

    def select_game_folder(self):

        path = filedialog.askdirectory(
            title="选择 VALORANT 主页面背景视频文件夹"
        )

        if not path:
            return

        path = normalize_path(
            path
        )

        self.game_path_var.set(
            path
        )

        self.save_current_paths()

        self.update_target()

        self.log(
            f"已设置文件夹路径：{path}"
        )


    # ========================================================
    # 选择视频
    # ========================================================

    def select_video(self):

        path = filedialog.askopenfilename(
            title="选择 MP4 视频",
            filetypes=[
                (
                    "MP4 视频",
                    "*.mp4"
                ),
                (
                    "所有文件",
                    "*.*"
                )
            ]
        )

        if not path:
            return

        self.set_video_path(
            path
        )


    def set_video_path(self, path):

        path = normalize_path(
            path
        )

        if not os.path.isfile(path):
            messagebox.showerror(
                "文件不存在",
                "选择的视频文件不存在。"
            )
            return

        if not is_mp4(path):

            messagebox.showwarning(
                "格式错误",
                "请选择 MP4 文件。"
            )

            return

        try:
            size = os.path.getsize(
                path
            )

        except Exception:

            messagebox.showerror(
                "读取失败",
                "无法读取视频文件。"
            )

            return

        if size <= 0:

            messagebox.showerror(
                "文件错误",
                "视频文件大小为 0。"
            )

            return

        if size > MAX_FILE_SIZE:

            messagebox.showerror(
                "文件过大",
                (
                    "视频文件超过程序允许的最大大小："
                    f"{format_size(MAX_FILE_SIZE)}"
                )
            )

            return

        self.video_path_var.set(
            path
        )

        self.config["video_path"] = path

        save_config(
            self.config
        )

        self.log(
            f"已选择视频：{path}"
        )

        self.log(
            f"视频大小：{format_size(size)}"
        )


    # ========================================================
    # 保存当前路径
    # ========================================================

    def save_current_paths(self):

        server = self.server_var.get()

        path = normalize_path(
            self.game_path_var.get()
        )

        self.game_path_var.set(
            path
        )

        if server == "riot":
            self.config[
                "riot_menu_path"
            ] = path

        else:
            self.config[
                "tencent_menu_path"
            ] = path

        self.config[
            "last_server"
        ] = server

        self.config[
            "video_path"
        ] = normalize_path(
            self.video_path_var.get()
        )

        save_config(
            self.config
        )


    # ========================================================
    # 自动搜索
    # ========================================================

    def start_auto_scan(self):

        if self.operation_running:
            return

        self.set_status(
            "正在搜索 VALORANT 安装目录..."
        )

        self.log("")
        self.log(
            "开始搜索 VALORANT 主页面背景视频文件夹..."
        )

        self.replace_button.configure(
            state="disabled"
        )

        self.restore_button.configure(
            state="disabled"
        )

        self.scan_thread = threading.Thread(
            target=self.auto_scan_worker,
            daemon=True
        )

        self.scan_thread.start()


    def auto_scan_worker(self):

        try:

            results = search_valorant_paths()

            self.root.after(
                0,
                lambda: self.set_game_path_from_scan(
                    results
                )
            )

        except Exception as e:

            self.root.after(
                0,
                lambda: self.scan_not_found(
                    str(e)
                )
            )


    def set_game_path_from_scan(
        self,
        results
    ):

        riot_path = results.get(
            "riot",
            ""
        )

        tencent_path = results.get(
            "tencent",
            ""
        )

        # 保存找到的路径
        if riot_path:

            self.config[
                "riot_menu_path"
            ] = riot_path

            self.log(
                f"找到国际服路径：{riot_path}"
            )

        if tencent_path:

            self.config[
                "tencent_menu_path"
            ] = tencent_path

            self.log(
                f"找到中国服路径：{tencent_path}"
            )

        save_config(
            self.config
        )

        # 根据当前选择设置
        server = self.server_var.get()

        if server == "riot":
            path = riot_path or self.config.get(
                "riot_menu_path",
                ""
            )

        else:
            path = tencent_path or self.config.get(
                "tencent_menu_path",
                ""
            )

        if path:

            self.game_path_var.set(
                path
            )

            self.log(
                "自动搜索完成。"
            )

        else:

            self.log(
                "未找到当前选择的 VALORANT 主页面背景视频文件夹。"
            )

        self.update_target()

        self.replace_button.configure(
            state="normal"
        )

        self.restore_button.configure(
            state="normal"
        )

        self.set_status(
            "准备就绪"
        )

        if not riot_path and not tencent_path:

            messagebox.showwarning(
                "未找到 VALORANT",
                (
                    "程序没有自动找到 VALORANT 主页面背景视频文件夹。\n\n"
                    "请点击「选择文件夹」，"
                    "手动选择：\n\n"
                    "Riot Games\\VALORANT\\live\\"
                    "ShooterGame\\Content\\Movies\\Menu\n\n"
                    "或：\n\n"
                    "Tencent Games\\VALORANT\\live\\"
                    "ShooterGame\\Content\\Movies\\Menu"
                )
            )


    def scan_not_found(self, error):

        self.log(
            f"搜索失败：{error}"
        )

        self.replace_button.configure(
            state="normal"
        )

        self.restore_button.configure(
            state="normal"
        )

        self.set_status(
            "搜索失败"
        )

        messagebox.showerror(
            "搜索失败",
            f"自动搜索失败：\n{error}"
        )


    # ========================================================
    # 更新 Homescreen
    # ========================================================

    def update_target(self):

        path = normalize_path(
            self.game_path_var.get()
        )

        if not path:

            self.target_var.set(
                "未设置文件夹路径"
            )

            return

        if not os.path.isdir(path):

            self.target_var.set(
                "文件夹路径不存在"
            )

            return

        files = find_homescreen_files(
            path
        )

        if not files:

            self.target_var.set(
                "未找到 Homescreen.mp4"
            )

            self.log(
                "当前主页面背景视频文件夹没有找到 Homescreen.mp4，请检查游戏完整性。"
            )

            return

        target = files[0]

        try:
            size = os.path.getsize(
                target
            )

            text = (
                f"{target}\n"
                f"大小：{format_size(size)}"
            )

        except Exception:

            text = target

        self.target_var.set(
            text
        )


    def get_target_file(self):

        path = normalize_path(
            self.game_path_var.get()
        )

        if not path:
            return ""

        return get_current_homescreen(
            path
        )


    # ========================================================
    # 替换
    # ========================================================

    def replace_video(self):

        if self.operation_running:
            return

        menu_path = normalize_path(
            self.game_path_var.get()
        )

        video_path = normalize_path(
            self.video_path_var.get()
        )

        # ----------------------------------------------------
        # 检查 Menu
        # ----------------------------------------------------

        if not menu_path:

            messagebox.showerror(
                "路径错误",
                "请先设置 VALORANT 主页面背景视频文件夹。"
            )

            return

        if not os.path.isdir(menu_path):

            messagebox.showerror(
                "路径错误",
                (
                    "文件夹路径不存在：\n\n"
                    f"{menu_path}"
                )
            )

            return

        # ----------------------------------------------------
        # 检查视频
        # ----------------------------------------------------

        if not video_path:

            messagebox.showerror(
                "视频未选择",
                "请先选择一个 MP4 视频。"
            )

            return

        if not os.path.isfile(video_path):

            messagebox.showerror(
                "视频不存在",
                (
                    "视频文件不存在：\n\n"
                    f"{video_path}"
                )
            )

            return

        if not is_mp4(video_path):

            messagebox.showerror(
                "格式错误",
                "只能使用 MP4 视频。"
            )

            return

        # ----------------------------------------------------
        # 找 Homescreen
        # ----------------------------------------------------

        target = self.get_target_file()

        if not target:

            messagebox.showerror(
                "未找到原有主页面背景视频",
                (
                    "当前文件夹中没有找到 "
                    "Homescreen.mp4 文件。"
                    "请检查游戏完整性"
                )
            )

            self.update_target()

            return

        # ----------------------------------------------------
        # 保存配置
        # ----------------------------------------------------

        self.save_current_paths()

        # ----------------------------------------------------
        # 开始任务
        # ----------------------------------------------------

        self.operation_running = True

        self.stop_event.clear()

        self.replace_button.configure(
            state="disabled"
        )

        self.restore_button.configure(
            state="disabled"
        )

        self.status_button.configure(
            state="disabled"
        )

        self.set_status(
            "等待 VALORANT 启动..."
        )

        self.log("")
        self.log(
            "========================================"
        )
        self.log(
            "替换任务已准备"
        )
        self.log(
            "========================================"
        )

        self.log(
            f"目标文件：{target}"
        )

        self.log(
            f"新视频：{video_path}"
        )

        self.log(
            f"新视频大小："
            f"{format_size(os.path.getsize(video_path))}"
        )

        self.log(
            "等待游戏程序启动..."
        )

        self.log(
            "检测目标："
            + " / ".join(
                sorted(GAME_PROCESS_NAMES)
            )
        )

        self.replace_thread = threading.Thread(
            target=self.wait_for_game_process,
            daemon=True
        )

        self.replace_thread.start()


    # ========================================================
    # 等待游戏进程
    # ========================================================

    def wait_for_game_process(self):

        diagnostic_done = False

        while not self.stop_event.is_set():

            # -----------------------------------------------
            # 检测
            # -----------------------------------------------

            if is_process_running():

                self.log("")
                self.log(
                    "✓ 检测到 VALORANT 游戏进程！"
                )

                processes = get_running_game_processes()

                for process in processes:

                    name = process.get(
                        "name",
                        ""
                    )

                    pid = process.get(
                        "pid",
                        ""
                    )

                    if name:
                        self.log(
                            f"进程：{name} "
                            f"(PID {pid})"
                        )

                self.set_status(
                    "已检测到游戏，准备替换..."
                )

                # 给游戏一点初始化时间
                time.sleep(1)

                if self.stop_event.is_set():
                    return

                # 真正执行替换
                self.perform_replacement()

                return

            # -----------------------------------------------
            # 第一次检测失败时，输出诊断信息
            # -----------------------------------------------

            if not diagnostic_done:

                processes = get_running_game_processes()

                if processes:

                    self.log(
                        "检测到以下 VALORANT 相关进程："
                    )

                    for process in processes:

                        name = process.get(
                            "name",
                            ""
                        )

                        pid = process.get(
                            "pid",
                            ""
                        )

                        self.log(
                            f"  {name} "
                            f"(PID {pid})"
                        )

                else:

                    self.log(
                        "当前没有检测到 VALORANT 相关进程。"
                    )

                diagnostic_done = True

            time.sleep(1)


    # ========================================================
    # 实际替换
    # ========================================================

    def perform_replacement(self):

        try:

            self.log("")
            self.log(
                "开始执行主页面背景替换..."
            )

            self.set_status(
                "替换主页面背景..."
            )

            # ------------------------------------------------
            # 重新获取目标
            # ------------------------------------------------

            menu_path = normalize_path(
                self.game_path_var.get()
            )

            video_path = normalize_path(
                self.video_path_var.get()
            )

            target = get_current_homescreen(
                menu_path
            )

            if not target:

                raise RuntimeError(
                    "游戏启动后未找到 Homescreen.mp4。"
                )

            self.log(
                f"最终目标文件：{target}"
            )

            # ------------------------------------------------
            # 检查源文件
            # ------------------------------------------------

            if not os.path.isfile(video_path):

                raise FileNotFoundError(
                    f"视频文件不存在：{video_path}"
                )

            source_size = os.path.getsize(
                video_path
            )

            if source_size <= 0:

                raise RuntimeError(
                    "视频文件大小为 0。"
                )

            # ------------------------------------------------
            # 原始文件备份
            # ------------------------------------------------

            backup_path = target + ".bak"

            if not os.path.exists(
                backup_path
            ):

                self.log(
                    "正在备份原始主页面背景..."
                )

                shutil.copy2(
                    target,
                    backup_path
                )

                self.log(
                    f"原始文件已备份：{backup_path}"
                )

            else:

                self.log(
                    "检测到已有原始备份，不覆盖原备份。"
                )

            # ------------------------------------------------
            # 临时文件
            # ------------------------------------------------

            temp_path = target + ".new"

            # 如果之前残留
            if os.path.exists(temp_path):

                try:
                    os.remove(temp_path)
                except Exception:
                    pass

            self.log(
                "正在复制新视频..."
            )

            # ------------------------------------------------
            # 复制
            # ------------------------------------------------

            shutil.copyfile(
                video_path,
                temp_path
            )

            # ------------------------------------------------
            # 验证临时文件
            # ------------------------------------------------

            if not os.path.isfile(temp_path):

                raise RuntimeError(
                    "临时文件创建失败。"
                )

            temp_size = os.path.getsize(
                temp_path
            )

            if temp_size != source_size:

                raise RuntimeError(
                    (
                        "文件复制验证失败。\n"
                        f"源文件：{source_size}\n"
                        f"临时文件：{temp_size}"
                    )
                )

            self.log(
                "视频复制完成，大小验证通过。"
            )

            # ------------------------------------------------
            # 替换
            # ------------------------------------------------

            self.log(
                "正在替换主页面背景..."
            )

            os.remove(
                target
            )

            os.replace(
                temp_path,
                target
            )

            # ------------------------------------------------
            # 最终验证
            # ------------------------------------------------

            if not os.path.isfile(target):

                raise RuntimeError(
                    "替换完成后未找到目标文件。"
                )

            final_size = os.path.getsize(
                target
            )

            if final_size != source_size:

                raise RuntimeError(
                    (
                        "最终文件大小验证失败。\n"
                        f"源文件：{source_size}\n"
                        f"目标文件：{final_size}"
                    )
                )

            # ------------------------------------------------
            # 成功
            # ------------------------------------------------

            self.log("")
            self.log(
                "========================================"
            )

            self.log(
                "✓ 主页面背景替换成功！"
            )

            self.log(
                f"目标文件：{target}"
            )

            self.log(
                f"文件大小：{format_size(final_size)}"
            )

            self.log(
                f"原始备份：{backup_path}"
            )

            self.log(
                "========================================"
            )

            self.set_status(
                "替换成功"
            )

            # ------------------------------------------------
            # 5 秒退出
            # ------------------------------------------------

            self.log(
                "5秒后自动退出程序..."
            )

            self.root.after(
                5000,
                self.exit_program
            )

        except Exception as e:

            # 如果临时文件存在，清理
            try:

                if (
                    "temp_path" in locals()
                    and os.path.exists(temp_path)
                ):
                    os.remove(
                        temp_path
                    )

            except Exception:
                pass

            self.log("")
            self.log(
                "✗ 主页面背景替换失败"
            )

            self.log(
                f"错误：{e}"
            )

            self.set_status(
                "替换失败"
            )

            self.root.after(
                0,
                lambda error=str(e):
                self.show_replace_error(
                    error
                )
            )


    def show_replace_error(self, error):

        self.operation_running = False

        self.replace_button.configure(
            state="normal"
        )

        self.restore_button.configure(
            state="normal"
        )

        self.status_button.configure(
            state="normal"
        )

        messagebox.showerror(
            "替换失败",
            (
                "主页面背景替换失败。\n\n"
                f"{error}"
            )
        )


    # ========================================================
    # 恢复原始 Homescreen
    # ========================================================

    def restore_original(self):

        if self.operation_running:

            messagebox.showwarning(
                "操作进行中",
                "当前正在执行其他操作，请稍候。"
            )

            return

        menu_path = normalize_path(
            self.game_path_var.get()
        )

        if not menu_path:

            messagebox.showerror(
                "路径错误",
                "请先设置文件夹路径。"
            )

            return

        target = get_current_homescreen(
            menu_path
        )

        if not target:

            messagebox.showerror(
                "未找到主页面背景",
                "没有找到当前 Homescreen.mp4。"
            )

            return

        backup_path = target + ".bak"

        if not os.path.isfile(
            backup_path
        ):

            messagebox.showinfo(
                "没有备份",
                (
                    "没有找到原始主页面背景备份：\n\n"
                    f"{backup_path}"
                )
            )

            return

        answer = messagebox.askyesno(
            "确认恢复",
            (
                "确定要恢复原始主页面背景吗？\n\n"
                f"目标：\n{target}"
            )
        )

        if not answer:
            return

        try:

            self.log("")
            self.log(
                "开始恢复原始主页面背景..."
            )

            temp_path = target + ".restore"

            if os.path.exists(
                temp_path
            ):

                try:
                    os.remove(
                        temp_path
                    )

                except Exception:
                    pass

            shutil.copyfile(
                backup_path,
                temp_path
            )

            backup_size = os.path.getsize(
                backup_path
            )

            temp_size = os.path.getsize(
                temp_path
            )

            if backup_size != temp_size:

                raise RuntimeError(
                    "恢复文件复制验证失败。"
                )

            os.remove(
                target
            )

            os.replace(
                temp_path,
                target
            )

            self.log(
                "✓ 原始主页面背景恢复成功。"
            )

            self.set_status(
                "原始主页面背景已恢复"
            )

            messagebox.showinfo(
                "恢复成功",
                "原始主页面背景已恢复。"
            )

            self.update_target()

        except Exception as e:

            try:

                if os.path.exists(
                    target + ".restore"
                ):
                    os.remove(
                        target + ".restore"
                    )

            except Exception:
                pass

            self.log(
                f"恢复失败：{e}"
            )

            messagebox.showerror(
                "恢复失败",
                f"恢复原始主页面背景失败：\n\n{e}"
            )


    # ========================================================
    # 刷新状态
    # ========================================================

    def check_status(self):

        menu_path = normalize_path(
            self.game_path_var.get()
        )

        if not menu_path:

            self.set_status(
                "未设置文件夹路径"
            )

            return

        if not os.path.isdir(
            menu_path
        ):

            self.set_status(
                "文件夹路径不存在"
            )

            return

        target = get_current_homescreen(
            menu_path
        )

        if not target:

            self.target_var.set(
                "未找到 Homescreen.mp4"
            )

            self.set_status(
                "未找到主页面背景"
            )

            return

        self.update_target()

        backup = target + ".bak"

        if os.path.isfile(
            backup
        ):

            self.set_status(
                "主页面背景已找到，存在原始备份"
            )

        else:

            self.set_status(
                "主页面背景已找到，没有原始备份"
            )


    # ========================================================
    # 退出
    # ========================================================

    def exit_program(self):

        try:
            self.stop_event.set()
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass


    def on_close(self):

        if self.operation_running:

            answer = messagebox.askyesno(
                "确认退出",
                (
                    "当前正在等待游戏启动或执行替换。\n\n"
                    "确定要退出程序吗？"
                )
            )

            if not answer:
                return

        self.stop_event.set()

        self.root.destroy()


# ============================================================
# 主入口
# ============================================================

def main():

    if DRAG_DROP_AVAILABLE:

        root = TkinterDnD.Tk()

    else:

        root = tk.Tk()

    try:

        # Windows 下使用 DPI 感知
        if sys.platform == "win32":

            try:
                import ctypes

                ctypes.windll.shcore.SetProcessDpiAwareness(
                    1
                )

            except Exception:
                pass

    except Exception:
        pass

    app = ValorantHomescreenApp(
        root
    )

    root.mainloop()


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()