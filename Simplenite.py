import glob
import shutil
import sys
import json
import threading
import winreg
import urllib.request
import configparser
from PyQt5 import QtWidgets
from PyQt5 import QtGui
import pygame, math
from PIL import Image, ImageFilter
import win32gui,win32process,psutil,win32api,win32ui,win32security
from PyQt5.QtWidgets import QApplication, QListWidgetItem, QMainWindow, QMessageBox, QScroller, QSystemTrayIcon, QMenu , QVBoxLayout, QDialog, QGridLayout, QWidget, QPushButton, QLabel, QDesktopWidget, QHBoxLayout, QFileDialog, QSlider, QLineEdit, QProgressBar, QScrollArea, QFrame, QTabWidget, QStackedWidget, QTextEdit, QListWidget
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QPixmap, QIcon, QColor, QLinearGradient, QKeySequence
from PyQt5.QtCore import QDateTime, QSize, Qt, QThread, pyqtSignal, QTimer, QPoint, QProcess, QPropertyAnimation, QRect, QObject, QEasingCurve, QParallelAnimationGroup, QTranslator
import subprocess, time, os,win32con, ctypes, re, win32com.client, ctypes, time, pyautogui
from ctypes import wintypes

APP_VERSION = "0.95.9"

#& C:/Users/86150/AppData/Local/Programs/Python/Python38/python.exe -m PyInstaller --add-data "fav.ico;." --add-data '1.png;.' --add-data 'pssuspend64.exe;.' -w Simplenite.py -i '.\fav.ico' --uac-admin --noconfirm
# 定义 Windows API 函数
SetWindowPos = ctypes.windll.user32.SetWindowPos
SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
FindWindow = ctypes.windll.user32.FindWindowW
# 定义常量
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
# 定义 SetWindowPos 函数的参数类型和返回类型
SetWindowPos.restype = wintypes.BOOL
SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
SetForegroundWindow.restype = wintypes.BOOL
SetForegroundWindow.argtypes = [wintypes.HWND]


pyautogui.FAILSAFE = False    # 禁用角落快速退出
pyautogui.PAUSE = 0           # 禁用自动暂停，确保动作即时响应
#确认你的sunshine安装目录
def get_app_install_path():
    app_name = "sunshine"
    try:
        # 打开注册表键，定位到安装路径信息
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                      r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        # 遍历注册表中的子项，查找对应应用名称
        for i in range(winreg.QueryInfoKey(registry_key)[0]):
            subkey_name = winreg.EnumKey(registry_key, i)
            subkey = winreg.OpenKey(registry_key, subkey_name)
            try:
                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                if app_name.lower() in display_name.lower():
                    install_location, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
                    if os.path.exists(install_location):
                        return os.path.dirname(install_location)
            except FileNotFoundError:
                continue
    except Exception as e:
        print(f"Error: {e}")
    print(QObject.tr("未检测到安装目录！"))
    # 开发环境：返回当前 py 文件所在目录
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))
APP_INSTALL_PATH=get_app_install_path()
if ctypes.windll.shell32.IsUserAnAdmin()==0:
    ADMIN = False
elif ctypes.windll.shell32.IsUserAnAdmin()==1:
    ADMIN = True
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    program_directory = os.path.dirname(sys.executable)
    getattrs = True
else:
    # 如果是脚本运行
    program_directory = os.path.dirname(os.path.abspath(__file__))
    getattrs = False
# 将工作目录更改为上一级目录
os.chdir(program_directory)
# 读取设置文件
settings_path = "set.json"
settings = {
    "favorites": [],
    "last_played": [],
    "more_favorites": [],
    "more_last_used": [],
    "extra_paths": [],
    "scale_factor": 1.0,
    "show_battery": False,
    "use_peer_level_launch": False,
    "debug_output_window": False,
    "ignored_apps": ["Desktop", "Steam Big Picture", "Xbox Game"]
}
try:
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    if "ignored_apps" not in settings:
        settings["ignored_apps"] = ["Desktop", "Steam Big Picture", "Xbox Game"]
except Exception as e:
    print(f"Error loading settings: {e}")

# ========== config.ini 多语言配置（与 SunshineAppManager 共用） ==========
config_ini = configparser.ConfigParser()
if getattr(sys, 'frozen', False):
    config_ini_path = os.path.join(os.path.dirname(sys.executable), 'config.ini')
else:
    config_ini_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')

language = "zh_CN"  # 默认语言

def load_language_from_config():
    """从 config.ini 加载语言设置"""
    global language
    if os.path.exists(config_ini_path):
        try:
            with open(config_ini_path, 'r', encoding='utf-8') as f:
                config_ini.read_file(f)
            language = config_ini.get('Settings', 'language', fallback='zh_CN')
        except Exception:
            language = "zh_CN"
    return language

def save_language_to_config(lang_code):
    """保存语言设置到 config.ini"""
    global language
    language = lang_code
    try:
        if os.path.exists(config_ini_path):
            with open(config_ini_path, 'r', encoding='utf-8') as f:
                config_ini.read_file(f)
        if not config_ini.has_section('Settings'):
            config_ini.add_section('Settings')
        config_ini.set('Settings', 'language', lang_code)
        with open(config_ini_path, 'w', encoding='utf-8') as f:
            config_ini.write(f)
    except Exception as e:
        print(f"保存语言配置失败: {e}")

load_language_from_config()
# ========== config.ini 结束 ==========

def get_target_path(lnk_file):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_file)
    return shortcut.TargetPath

def load_apps():
    """加载有效的应用程序列表"""
    global valid_apps, games
    # 读取 JSON 数据
    json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"
    if not os.path.exists(json_path):
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"env": "", "apps": []}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"无法创建 apps.json: {e}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        # 如果普通 utf-8 读取失败，尝试用带 BOM 的 utf-8-sig 读取并回写为纯 utf-8
        try:
            with open(json_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e2:
                print(f"保存为 utf-8 失败: {e2}")
        except Exception as e2:
            print(f"读取 apps.json 失败: {e} / {e2}")
            # 使用 Win32 API弹窗提示
            try:
                msg = QApplication.translate("Simplenite", "读取 apps.json 失败：\n%1\n%2\n。").replace('%1', str(e)).replace('%2', str(e2))
                ctypes.windll.user32.MessageBoxW(0, msg, QApplication.translate("Simplenite", "读取错误"), 0x10)  # 0x10 = MB_ICONERROR
            except Exception:
                pass
            data = {"apps": []}

    ###下面俩行代码用于SunshineAppManager的伪排序清除，若感到困惑可删除###
    for idx, entry in enumerate(data.get("apps", [])):
        entry["name"] = re.sub(r'^\d{2} ', '', entry.get("name", ""))
    ignored_apps = [str(item).strip() for item in settings.get("ignored_apps", ["Desktop", "Steam Big Picture", "Xbox Game"])]
    # 仅保留 name 不在 ignored_apps 且 image-path 存在且非空的条目
    games = [
        app for app in data.get("apps", [])
        if app.get("name") not in ignored_apps
        and str(app.get("image-path", "")).strip() != ""
    ]
    print(f"+++++检测到 {len(games)} 个游戏")

    # 存储解析后的有效软件条目
    valid_apps = []
    for app in data.get("apps", []):
        cmda = app.get("cmd")
        if cmda is None:
            continue  # 跳过无 cmd 的条目
        cmd = cmda.strip('"')
        # 新增2：如果app["name"]已存在于settings["custom_valid_apps"]的"name"，则跳过
        if "custom_valid_apps" in settings and any(app["name"] == item["name"] for item in settings["custom_valid_apps"]):
            continue
        if cmd:
            # 如果cmd是快捷方式路径（.lnk）
            if cmd.lower().endswith('.lnk'):
                try:
                    target_path = get_target_path(cmd)
                    valid_apps.append({"name": app["name"], "path": target_path})#os.path.splitext(file_name)[0]；file_name = os.path.basename(full_path)
                except Exception as e:
                    print(f"无法解析快捷方式 {cmd}：{e}")
            # 如果cmd是.exe文件路径
            elif cmd.lower().endswith('.exe'):
                valid_apps.append({"name": app["name"], "path": cmd})
        if "last_played" in settings:
            if app["name"] not in settings["last_played"]:
                settings["last_played"].insert(0, app["name"])
        else:
            settings["last_played"] = [app["name"]]
    # 加载自定义 valid_apps
    if "custom_valid_apps" in settings:
        for item in settings["custom_valid_apps"]:
            if "name" in item and "path" in item:
                valid_apps.append({"name": item["name"], "path": item["path"]})
    #print(f"已加载 {valid_apps} 个有效应用程序")
load_apps()

more_apps = []
def load_morefloder_shortcuts():
    """解析 ./morefloder 文件夹下的快捷方式并添加到 more_apps"""
    more_apps.clear()  # 清空 more_apps 列表
    morefloder_path = os.path.join(program_directory, "morefloder")
    if not os.path.exists(morefloder_path):
        print(f"目录 {morefloder_path} 不存在")
        return

    # 遍历文件夹下的所有 .lnk 文件
    shortcut_files = glob.glob(os.path.join(morefloder_path, "*.lnk"))
    for shortcut_file in shortcut_files:
        try:
            target_path = get_target_path(shortcut_file)
            app_name = os.path.splitext(os.path.basename(shortcut_file))[0]
            more_apps.append({"name": app_name, "path": target_path})
        except Exception as e:
            print(f"无法解析快捷方式 {shortcut_file}：{e}")
load_morefloder_shortcuts()
#print(more_apps)
#print(valid_apps)

def get_desktop_listview():
    # 先找WorkerW窗口
    def callback(hwnd, result):
        if win32gui.GetClassName(hwnd) == "WorkerW":
            defview = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
            if defview:
                result.append(defview)
    result = []
    win32gui.EnumWindows(callback, result)
    if result:
        return win32gui.FindWindowEx(result[0], 0, "SysListView32", None)
    # 兼容老方式
    progman = win32gui.FindWindow("Progman", None)
    defview = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
    if defview:
        return win32gui.FindWindowEx(defview, 0, "SysListView32", None)
    return None

def hide_desktop_icons():
    listview = get_desktop_listview()
    if listview:
        win32gui.ShowWindow(listview, win32con.SW_HIDE)

def show_desktop_icons():
    listview = get_desktop_listview()
    if listview:
        win32gui.ShowWindow(listview, win32con.SW_SHOW)
def toggle_taskbar():
    # 获取任务栏窗口句柄
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    # 获取当前任务栏状态
    is_visible = win32gui.IsWindowVisible(taskbar)
    # 切换显示状态
    ctypes.windll.user32.ShowWindow(taskbar, 0 if is_visible else 5)  # 0=隐藏, 5=显示

def hide_taskbar():
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    ctypes.windll.user32.ShowWindow(taskbar, 0)  # 隐藏

def show_taskbar():
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    ctypes.windll.user32.ShowWindow(taskbar, 5)  # 显示

# 获取系统的屏幕边界
def get_screen_rect():
    user32 = ctypes.windll.user32
    return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

# 获取当前的工作区域（最大化时的边界）
def get_work_area():
    # 获取整个屏幕区域
    user32 = ctypes.windll.user32
    screen_rect = (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    # 获取任务栏窗口句柄
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    if not taskbar:
        return screen_rect
    # 获取任务栏位置和大小
    rect = win32gui.GetWindowRect(taskbar)
    # 判断任务栏在屏幕的哪一边
    left, top, right, bottom = rect
    sw, sh = screen_rect[2], screen_rect[3]
    # 默认工作区为全屏
    work_left, work_top, work_right, work_bottom = 0, 0, sw, sh
    # 判断任务栏位置
    if left <= 0 and right >= sw:  # 顶部或底部
        if top == 0:
            work_top = bottom  # 任务栏在顶部
        else:
            work_bottom = top  # 任务栏在底部
    elif top <= 0 and bottom >= sh:  # 左侧或右侧
        if left == 0:
            work_left = right  # 任务栏在左侧
        else:
            work_right = left  # 任务栏在右侧
    return (work_left, work_top, work_right, work_bottom)

# 设置工作区域
def set_work_area(left, top, right, bottom):
    SPI_SETWORKAREA = 0x002F
    rect = ctypes.wintypes.RECT(left, top, right, bottom)
    res = ctypes.windll.user32.SystemParametersInfoW(SPI_SETWORKAREA, 0, ctypes.byref(rect), 1)
    return res != 0


def _enable_peer_level_launch():
    settings["use_peer_level_launch"] = True
    try:
        with open("set.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _fallback_to_peer_level_launch(path, show_warning=True):
    if show_warning:
        QMessageBox.warning(None, QApplication.translate("Simplenite", "权限提示"),
            QApplication.translate("Simplenite", "CreateProcessAsUser 失败（权限不足）。已启用同级权限启动模式规避此问题，可前往应用设置-开发者选项查看该选项详情"))
    _enable_peer_level_launch()
    try:
        print(f"以同级权限启动: {path}")
        os.startfile(path)
    except Exception as retry_e:
        print(f"同级权限启动失败: {retry_e}")


def get_explorer_token():
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'].lower() == 'explorer.exe':
            explorer_pid = p.info['pid']
            break

    hProcess = win32api.OpenProcess(
        win32con.PROCESS_QUERY_INFORMATION,
        False,
        explorer_pid
    )

    token = win32security.OpenProcessToken(
        hProcess,
        win32con.TOKEN_DUPLICATE | win32con.TOKEN_ASSIGN_PRIMARY | win32con.TOKEN_QUERY
    )

    return win32security.DuplicateTokenEx(
        token,
        win32security.SecurityImpersonation,
        win32con.TOKEN_ALL_ACCESS,
        win32security.TokenPrimary
    )
EXPLORERTOKEN = get_explorer_token()
def run_as_user(path):
    # 去除引号
    path = path.strip('"')
    if settings.get("use_peer_level_launch", False):
        try:
            print(f"以同级权限启动: {path}")
            os.startfile(path)
            return
        except Exception as e:
            print(f"同级权限启动失败 {e}")
            return
    cmd = f'cmd.exe /c start "" "{path}"'
    print(f"以当前用户权限启动: {cmd}")
    try:
        win32process.CreateProcessAsUser(
            EXPLORERTOKEN,
            None,
            cmd,
            None,
            None,
            False,
            win32con.DETACHED_PROCESS | win32con.CREATE_NEW_PROCESS_GROUP,
            None,
            None,
            win32process.STARTUPINFO()
        )
    except Exception as e:
        error_code = getattr(e, 'winerror', None)
        if error_code == 1314:  # ERROR_PRIVILEGE_NOT_HELD
            _fallback_to_peer_level_launch(path, show_warning=True)
        else:
            print(f"CreateProcessAsUser 错误 (错误码{error_code}): {e}")

class _DebugStream(QObject):
    message_signal = pyqtSignal(str)

    def __init__(self, original_stream):
        super().__init__()
        self.original_stream = original_stream

    def write(self, message):
        if not isinstance(message, str):
            message = str(message)
        if self.original_stream:
            self.original_stream.write(message)
        if message:
            self.message_signal.emit(message)

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()


class DebugOutputWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("调试输出"))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(560, 320)
        self._dragging = False
        self._drag_offset = QPoint(0, 0)

        self.title_bar = QWidget(self)
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(18, 18, 18, 120);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QLabel {
                color: #dddddd;
                font-size: 12px;
            }
            QPushButton {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 30);
                border: none;
                border-radius: 6px;
                min-width: 22px;
                min-height: 20px;
                max-width: 22px;
                max-height: 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 55);
            }
        """)

        self.title_label = QLabel(self.tr("调试输出"))
        self.minimize_button = QPushButton("—")
        self.minimize_button.clicked.connect(self.showMinimized)
        self.title_bar.mousePressEvent = self._title_bar_mouse_press
        self.title_bar.mouseMoveEvent = self._title_bar_mouse_move
        self.title_bar.mouseReleaseEvent = self._title_bar_mouse_release

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 4, 8, 4)
        title_layout.setSpacing(6)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.minimize_button)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 120);
                color: #ccffcc;
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 10px;
                font-size: 13px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        layout.addWidget(self.text_edit)

    def append_message(self, message):
        if not message:
            return
        self.text_edit.moveCursor(QtGui.QTextCursor.End)
        self.text_edit.insertPlainText(message)
        # 限制日志行数，避免窗口本身持有太多内存
        doc = self.text_edit.document()
        while doc.blockCount() > 400:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
            doc = self.text_edit.document()
        self.text_edit.moveCursor(QtGui.QTextCursor.End)

    def position_top_left(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geometry = screen.availableGeometry()
        margin = 50
        self.move(
            geometry.left() + margin,
            geometry.top() + margin
        )

    def closeEvent(self, event):
        # 禁止关闭，统一最小化到任务栏
        self.showMinimized()
        event.ignore()

    def _title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            event.ignore()

    def _title_bar_mouse_move(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self._drag_offset)
            event.accept()
        else:
            event.ignore()

    def _title_bar_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
        else:
            event.ignore()


_stdout_stream = None
_stderr_stream = None
_debug_output_window_ref = None


def _attach_debug_output_window(window):
    global _debug_output_window_ref
    _debug_output_window_ref = window


def _install_debug_output_redirect():
    global _stdout_stream, _stderr_stream
    if _stdout_stream is not None and _stderr_stream is not None:
        return
    _stdout_stream = _DebugStream(sys.stdout)
    _stderr_stream = _DebugStream(sys.stderr)

    def _forward(message):
        if _debug_output_window_ref is not None:
            _debug_output_window_ref.append_message(message)

    _stdout_stream.message_signal.connect(_forward)
    _stderr_stream.message_signal.connect(_forward)
    sys.stdout = _stdout_stream
    sys.stderr = _stderr_stream


class TaskbarWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnBottomHint |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.7)
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                border: 1px solid #222;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 22px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #aaa, stop:1 #888);
                border: 1px solid #222;
                font-size: 26px;
                min-width: 120px;
                min-height: 60px;
            }
            QPushButton:hover {
                background: #bbb;
            }
            QSlider::groove:horizontal {
                height: 10px;
                border: 1px solid #666;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #999, stop:1 #666
                );
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #000;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)
        def get_desktop_parent():
            progman = win32gui.FindWindow("Progman", None)
            defview = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
            if defview:
                return defview
            # 查找WorkerW
            result = []
            def callback(hwnd, result):
                if win32gui.GetClassName(hwnd) == "WorkerW":
                    child = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
                    if child:
                        result.append(child)
            win32gui.EnumWindows(callback, result)
            if result:
                return result[0]
            return win32gui.GetDesktopWindow()
        desktop_parent = get_desktop_parent()
        self.winId()  # 确保窗口已创建
        ctypes.windll.user32.SetParent(int(self.winId()), desktop_parent)
        # taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
        # rect = win32gui.GetWindowRect(taskbar)
        # taskbar_height = rect[3] - rect[1]
        # taskbar_width = rect[2] - rect[0]
        # self.resize(taskbar_width, taskbar_height)
        # self.move(rect[0], rect[1])
        screen = QApplication.primaryScreen().geometry()
        # 让主窗口全屏
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.setWindowOpacity(0.9)

        # 主部件和布局
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 创建一个居中容器用于放置按钮
        btn_container = QWidget(self.centralWidget())
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        # 回到桌面按钮
        btn_desktop = QPushButton(self.tr("🖥️回到桌面"), self)
        btn_desktop.setStyleSheet("font-size: 15px;")
        btn_desktop.clicked.connect(self.on_back_to_desktop)
        btn_layout.addWidget(btn_desktop)

        # Win+Tab按钮
        btn_wintab = QPushButton(self.tr("🗒️任务视图"), self)
        btn_wintab.setStyleSheet("font-size: 15px;")
        btn_wintab.clicked.connect(self.on_win_tab)
        btn_layout.addWidget(btn_wintab)

        # 打开资源管理器按钮
        btn_explorer = QPushButton(self.tr("📦️打开前端"), self)
        btn_explorer.setStyleSheet("font-size: 15px;")
        btn_explorer.clicked.connect(self.on_open_dgmix)
        btn_layout.addWidget(btn_explorer)

        # 将按钮容器添加到主布局并居中
        layout.addWidget(btn_container, alignment=Qt.AlignCenter)

        # 全屏隐藏按钮（中空，四个区域覆盖，按钮区域不覆盖）
        self.btn_hide_top = QPushButton("", self)
        self.btn_hide_top.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_top.clicked.connect(self.on_hide_all)
        self.btn_hide_top.setVisible(True)

        self.btn_hide_bottom = QPushButton("", self)
        self.btn_hide_bottom.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_bottom.clicked.connect(self.on_hide_all)
        self.btn_hide_bottom.setVisible(True)

        self.btn_hide_left = QPushButton("", self)
        self.btn_hide_left.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_left.clicked.connect(self.on_hide_all)
        self.btn_hide_left.setVisible(True)

        self.btn_hide_right = QPushButton("", self)
        self.btn_hide_right.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_right.clicked.connect(self.on_hide_all)
        self.btn_hide_right.setVisible(True)

        # 跟随窗口和btn_container大小变化调整隐藏按钮大小和位置
        self.resizeEvent = self._resizeEvent

        # 重写show方法，在显示窗口时执行相关代码
        old_show = self.show
        def new_show():
            # 获取屏幕工作区，保存供恢复
            self._original_work_area = get_work_area()
            screen_rect = get_screen_rect()
            set_work_area(*screen_rect)
            old_show()
        self.show = new_show

    def _resizeEvent(self, event):
        # 获取btn_container的几何信息
        btn_container = self.centralWidget().findChild(QWidget)
        if btn_container:
            # 重新计算中间空白区域的位置和大小
            screen = QApplication.primaryScreen().geometry()
            width = int(screen.width() * 0.33)
            height = int(screen.height() * 0.1)
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            btn_container.setGeometry(x, y, width, height)
            btn_container.setFixedSize(width, height)
            c_geo = btn_container.geometry()
            # 顶部按钮
            self.btn_hide_top.setGeometry(
                0, 0, self.width(), c_geo.top()
            )
            # 底部按钮
            self.btn_hide_bottom.setGeometry(
                0, c_geo.bottom() + 1, self.width(), self.height() - c_geo.bottom() - 1
            )
            # 左侧按钮
            self.btn_hide_left.setGeometry(
                0, c_geo.top(), c_geo.left(), c_geo.height()
            )
            # 右侧按钮
            self.btn_hide_right.setGeometry(
                c_geo.right() + 1, c_geo.top(), self.width() - c_geo.right() - 1, c_geo.height()
            )
        if hasattr(super(), 'resizeEvent'):
            super().resizeEvent(event)
    def on_back_to_desktop(self):
        show_desktop_icons()
        show_taskbar()
        set_work_area(*getattr(self, "_original_work_area", get_work_area()))
        self.close()
    def on_win_tab(self):
        # 模拟 Win+Tab
        pyautogui.hotkey('win', 'tab')
    def on_hide_all(self):
        # 模拟 Win+D
        pyautogui.hotkey('win', 'd')
    def on_open_dgmix(self):
        global GSHWND
        ctypes.windll.user32.ShowWindow(GSHWND, 9) # 9=SW_RESTORE            
        ctypes.windll.user32.SetForegroundWindow(GSHWND)

# 游戏运行状态监听线程
class MonitorRunningAppsThread(QThread):
    play_reload_signal = pyqtSignal()  # 用于通知主线程重载
    play_app_name_signal = pyqtSignal(list)  # 用于传递 play_app_name 到主线程
    background_windows_changed = pyqtSignal()  # 当前可见窗口数量变化

    def __init__(self, play_lock, play_app_name):
        super().__init__()
        self.play_lock = play_lock
        self.play_app_name = play_app_name
        self.running = True
        self._last_visible_count = None

    def check_running_apps(self):
        """检查当前运行的应用"""
        global valid_apps
        # 获取当前运行的所有进程
        current_running_apps = set()
        exe_to_names = {}
        for app in valid_apps:
            exe_to_names.setdefault(app['path'].lower(), []).append(app['name'])

        for process in psutil.process_iter(['pid', 'exe']):
            try:
                exe_path = process.info['exe']
                if exe_path:
                    exe_path_lower = exe_path.lower()
                    if exe_path_lower in exe_to_names:
                        # 只保留last_played靠前的游戏名
                        for game_name in settings.get("last_played", []):
                            if game_name in exe_to_names[exe_path_lower]:
                                current_running_apps.add(game_name)
                                break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # 如果当前运行的应用和 play_app_name 中的内容不同，更新 play_app_name
        with self.play_lock:  # 加锁，确保修改时线程安全
            if current_running_apps != set(self.play_app_name):
                self.play_app_name = list(current_running_apps)
                self.play_reload_signal.emit()  # 发出信号通知主线程
                self.play_app_name_signal.emit(self.play_app_name)  # 将 play_app_name 发送到主线程
            else:
                play_reload = False

        # 额外：检查前台可见窗口数量是否变化，变化时通知主线程更新后台窗口列表
        try:
            visible_count = 0
            def _cb(hwnd, lparam):
                nonlocal visible_count
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                        # 过滤工具窗口和无标题窗口
                        if (ex_style & win32con.WS_EX_TOOLWINDOW) and not (ex_style & win32con.WS_EX_APPWINDOW):
                            return True
                        if win32gui.GetWindow(hwnd, win32con.GW_OWNER) and not (ex_style & win32con.WS_EX_APPWINDOW):
                            return True
                        title = win32gui.GetWindowText(hwnd)
                        if title and title.strip():
                            visible_count += 1
                except Exception:
                    pass
                return True
            win32gui.EnumWindows(_cb, None)
            if self._last_visible_count is None:
                self._last_visible_count = visible_count
            elif visible_count != self._last_visible_count:
                self._last_visible_count = visible_count
                try:
                    self.background_windows_changed.emit()
                except Exception:
                    pass
        except Exception:
            pass

    def run(self):
        """后台线程的运行方法"""
        while self.running:
            self.check_running_apps()  # 检查运行的应用
            time.sleep(1)  # 每秒检查一次进程

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束
class ScreenshotScannerThread(QThread):
    """后台线程用于扫描截图目录"""
    screenshots_scanned = pyqtSignal(list)  # 信号，用于通知主线程扫描完成

    def __init__(self):
        super().__init__()
        self.running = True

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束

    def run(self):
        """扫描截图目录，加载文件路径和元数据"""
        all_screenshots = []
        base_dir = "screenshot"
        if self.running and os.path.isdir(base_dir):
            for game in os.listdir(base_dir):
                if not self.running:  # 检查是否需要停止
                    break
                game_dir = os.path.join(base_dir, game)
                if os.path.isdir(game_dir):
                    for fname in os.listdir(game_dir):
                        if not self.running:  # 检查是否需要停止
                            break
                        if fname.lower().endswith(".png"):
                            path = os.path.join(game_dir, fname)
                            ts = os.path.getmtime(path)
                            all_screenshots.append((path, game, ts))
        
        if self.running:  # 只有在没有停止的情况下才发送信号
            all_screenshots.sort(key=lambda x: x[2], reverse=True)
            self.screenshots_scanned.emit(all_screenshots)

class ScreenshotLoaderThread(QThread):
    """后台线程用于加载和缩放图片"""
    screenshot_loaded = pyqtSignal(list)  # 信号，用于通知主线程全部加载完成
    screenshot_single_loaded = pyqtSignal(int, tuple)  # 信号，用于通知主线程单张图片加载完成 (索引, (thumb, path, game, ts))

    def __init__(self, screenshots, icon_size, image_indices=None):
        super().__init__()
        self.screenshots = screenshots
        self.icon_size = icon_size
        self.running = True
        # 如果没有指定索引，默认加载所有图片
        self.image_indices = image_indices if image_indices is not None else list(range(len(screenshots)))

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束

    def run(self):
        """批量加载图片并定期释放UI线程"""
        loaded_screenshots = []
        for idx in self.image_indices:
            if not self.running:  # 检查是否需要停止
                break
            try:
                if 0 <= idx < len(self.screenshots):
                    path, game, ts = self.screenshots[idx]
                    pixmap = QtGui.QPixmap(path)
                    thumb = pixmap.scaled(
                        int(self.icon_size), int(self.icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    loaded_screenshots.append((thumb, path, game, ts))
                    
                    # 发送单张图片加载完成信号，让UI线程立即更新
                    self.screenshot_single_loaded.emit(idx, (thumb, path, game, ts))
                    
                    # 短暂休眠，给UI线程处理事件的机会
                    self.msleep(1)
                    
            except Exception as e:
                print(f"加载图片失败: {path}, 错误: {e}")
        
        if self.running:  # 只有在没有停止的情况下才发送信号
            self.screenshot_loaded.emit(loaded_screenshots)

class ScreenshotWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_dialog = None  # 新增：记录当前弹窗
        self.filter_game_name = None  # 当前筛选的游戏名
        self.setWindowTitle(self.tr("截图浏览"))
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #1e1e1e;")
        # 从父类获取缩放因子，如果父类没有则从设置中读取
        self.scale_factor = getattr(parent, 'scale_factor', settings.get("scale_factor", 1.0))
        
        # 获取屏幕信息
        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        
        # 计算高度：从屏幕顶端到GameSelector的divider之上
        # 获取父窗口（GameSelector）的高度
        parent_height = getattr(parent, 'height', lambda: screen.height)()
        if callable(parent_height):
            parent_height = parent_height()

        # 设置ScreenshotWindow的高度为父窗口高度减去底部区域高度
        window_height = parent_height - int(70 * self.scale_factor)
        
        # 调整大小
        self.resize(screen_width, window_height)
        # 将窗口定位在屏幕左上角
        self.move(0, 0)
        
        self.icon_size = 256 * self.scale_factor
        # ScreenshotWindow.__init__ 内左侧面板部分
        # 统一按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * self.scale_factor)}px;
                border: none;
                font-size: {int(30 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """

        BTN_HEIGHT = int(90 * self.scale_factor)  # 统一按钮高度

        def on_backup_save_clicked():
            open_maobackup("--quick-dgaction")
        def on_backup_restore_clicked(): 
            open_maobackup("--quick-dgrestore")
        def on_view_backup_list_clicked(): 
            open_maobackup("-backuplist")
        def open_maobackup(sysargv):
            exe_path = os.path.join(program_directory, "maobackup.exe")
            game_name = self.game_name_label.text()
            self.parent().startopenmaobackup(sysargv, game_name, exe_path)
            self.safe_close()  # 关闭当前窗口
        def on_mapping_clicked():
            game_name = self.game_name_label.text()
            # 读取 set.json 的 on_mapping_clicked 列表
            if "on_mapping_clicked" not in settings:
                settings["on_mapping_clicked"] = []
            if game_name in settings["on_mapping_clicked"]:
                settings["on_mapping_clicked"].remove(game_name)
                self.btn_mapping.setText(self.tr("游玩时开启映射(×)"))
            else:
                settings["on_mapping_clicked"].append(game_name)
                self.btn_mapping.setText(self.tr("游玩时开启映射(✔)"))
            # 保存到 set.json
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        def on_freeze_clicked():
            game_name = self.game_name_label.text()
            #options = ["跟随全局", "不冻结", "内置核心冻结", "调用雪藏冻结"]
            options = ["跟随全局"]
            if "freeze_mode" not in settings:
                settings["freeze_mode"] = {}
            current_mode = settings["freeze_mode"].get(game_name, "跟随全局")
        
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(self.tr("选择冻结方式"))
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: rgba(46, 46, 46, 0.98);
                    border-radius: 12px;
                    border: 2px solid #444444;
                }
            """)
            layout = QtWidgets.QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)
        
            info_label = QLabel(self.tr("请选择该游戏的冻结方式"))
            info_label.setStyleSheet("color: #aaa; font-size: 18px;")
            layout.addWidget(info_label)
        
            dialog.buttons = []
            dialog.current_index = 0
        
            def update_highlight():
                for i, btn in enumerate(dialog.buttons):
                    if i == dialog.current_index:
                        btn.setStyleSheet("background-color: #93ffff; color: #222; font-size: 18px; border-radius: 8px;")
                    else:
                        btn.setStyleSheet("background-color: #444444; color: white; font-size: 18px; border-radius: 8px;")
            dialog.update_highlight = update_highlight
        
            def select_option(idx):
                mode = options[idx]
                settings["freeze_mode"][game_name] = mode
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                self.btn_freeze.setText(self.tr("冻结方式(%1)").replace('%1', mode))
                dialog.accept()
        
            for idx, opt in enumerate(options):
                btn = QPushButton(opt)
                btn.clicked.connect(lambda checked=False, idx=idx: select_option(idx))
                layout.addWidget(btn)
                dialog.buttons.append(btn)
        
            dialog.setLayout(layout)
            dialog.update_highlight()
        
            def keyPressEvent(event):
                if event.key() in (Qt.Key_Up, Qt.Key_W):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Down, Qt.Key_S):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    dialog.buttons[dialog.current_index].click()
            dialog.keyPressEvent = keyPressEvent
        
            def handle_gamepad_input(action):
                if action in ('UP',):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('DOWN',):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('A',):
                    dialog.buttons[dialog.current_index].click()
                elif action in ('B',):
                    dialog.close()
            dialog.handle_gamepad_input = handle_gamepad_input
            self.active_dialog = dialog  # 记录当前弹窗
            dialog.exec_()
            self.active_dialog = None    # 关闭后清空
            
        def on_custom_proc_clicked():
            """自定义进程：调用GameSelector的后台窗口选择器"""
            game_name = self.game_name_label.text()
            parent_window = self.parent()
            if parent_window and hasattr(parent_window, '_show_process_selector_for_game'):
                parent_window._show_process_selector_for_game(game_name)
            self.safe_close()
        def on_tools_clicked():
            game_name = self.game_name_label.text()
            if "custom_tools" not in settings:
                settings["custom_tools"] = []
            found = next((item for item in settings["custom_tools"] if item["name"] == game_name), None)
            tools = found["tools"] if found else []
            tool_names = [app["name"] for app in more_apps]
            tool_paths = {app["name"]: app["path"] for app in more_apps}
        
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(self.tr("选择要关联的工具"))
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: rgba(46, 46, 46, 0.98);
                    border-radius: 12px;
                    border: 2px solid #444444;
                }
            """)
            layout = QtWidgets.QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)
        
            info_label = QLabel(self.tr("点击工具添加到游戏连携启动"))
            info_label.setStyleSheet("color: #aaa; font-size: 18px;")
            layout.addWidget(info_label)
        
            dialog.buttons = []
            dialog.current_index = 0
        
            def update_btn_text(btn, tool_name):
                if any(t["name"] == tool_name for t in tools):
                    btn.setText(f"✔ {tool_name}")
                else:
                    btn.setText(tool_name)
        
            def update_highlight():
                for i, btn in enumerate(dialog.buttons):
                    if i == dialog.current_index:
                        btn.setStyleSheet("background-color: #93ffff; color: #222; font-size: 18px; border-radius: 8px;")
                    else:
                        btn.setStyleSheet("background-color: #444444; color: white; font-size: 18px; border-radius: 8px;")
            dialog.update_highlight = update_highlight
        
            def on_click(tool):
                if any(t["name"] == tool for t in tools):
                    tools[:] = [t for t in tools if t["name"] != tool]
                else:
                    tool_entry = {"name": tool, "path": tool_paths[tool]}
                    if found:
                        found["tools"].append(tool_entry)
                    else:
                        settings["custom_tools"].append({"name": game_name, "tools": [tool_entry]})
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                count = len(found["tools"]) if found else 1
                self.btn_tools.setText(self.tr("附加工具启动(%1)").replace('%1', str(count)))
                for idx, btn in enumerate(dialog.buttons):
                    update_btn_text(btn, tool_names[idx])
                dialog.update_highlight()
        
            for tool_name in tool_names:
                btn = QPushButton()
                update_btn_text(btn, tool_name)
                btn.clicked.connect(lambda checked=False, tool=tool_name: on_click(tool))
                layout.addWidget(btn)
                dialog.buttons.append(btn)
        
            dialog.setLayout(layout)
            dialog.update_highlight()
        
            def keyPressEvent(event):
                if event.key() in (Qt.Key_Up, Qt.Key_W):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Down, Qt.Key_S):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    dialog.buttons[dialog.current_index].click()
            dialog.keyPressEvent = keyPressEvent
        
            def handle_gamepad_input(action):
                if action in ('UP',):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('DOWN',):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('A',):
                    dialog.buttons[dialog.current_index].click()
                elif action in ('B',):
                    dialog.close()
            dialog.handle_gamepad_input = handle_gamepad_input
            self.active_dialog = dialog  # 记录当前弹窗
            dialog.exec_()
            self.active_dialog = None    # 关闭后清空
            
        def on_cover_clicked():
            self.qsaa_thread = SunshineAppManagerThread(args=["--choosecover", str(self.game_name_label.text())])
            if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                self.qsaa_thread.finished_signal.connect(self.parent().deep_reload_games)
            self.qsaa_thread.start()
        def on_rename_clicked():
            # 自定义重命名对话框，支持“使用存档游戏名称”按钮
            old_name = self.game_name_label.text()
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(self.tr("重命名游戏"))
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            vbox = QtWidgets.QVBoxLayout(dialog)
            prompt = QLabel('<span style="color:white;">' + self.tr("请输入新的游戏名称：") + '</span>')
            prompt.setTextFormat(Qt.RichText)
            # 放大一倍的字体大小并设为白色
            large_font_px = int(40 * self.scale_factor)
            prompt.setStyleSheet(f"color: white; font-size: {large_font_px}px;")
            vbox.addWidget(prompt)
            edit = QLineEdit(old_name)
            edit.setStyleSheet(f"color: white; font-size: {large_font_px}px; background-color: #333333; border: 1px solid #555555; padding: 8px;")
            edit.setFixedHeight(int(BTN_HEIGHT))
            vbox.addWidget(edit)
            hbox = QtWidgets.QHBoxLayout()
            use_btn = QPushButton(self.tr("使用存档游戏名称"))
            ok_btn = QPushButton(self.tr("确定"))
            cancel_btn = QPushButton(self.tr("取消"))
            btn_h = int(BTN_HEIGHT)
            btn_style_big = f"background-color: #444444; color: white; font-size: {large_font_px}px; padding: {int(12 * self.scale_factor)}px; border: none; border-radius: 8px;"
            use_btn.setStyleSheet(btn_style_big)
            ok_btn.setStyleSheet(btn_style_big)
            cancel_btn.setStyleSheet(btn_style_big)
            use_btn.setFixedHeight(btn_h)
            ok_btn.setFixedHeight(btn_h)
            cancel_btn.setFixedHeight(btn_h)
            hbox.addWidget(use_btn)
            hbox.addStretch(1)
            hbox.addWidget(ok_btn)
            hbox.addWidget(cancel_btn)
            vbox.addLayout(hbox)

            def use_save_name():
                config_path = os.path.join(program_directory, "webdav_config.json")
                if not os.path.exists(config_path):
                    QMessageBox.warning(dialog, self.tr("提示"), self.tr("未找到 webdav_config.json"))
                    return
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    names = [g.get("name") for g in cfg.get("games", []) if isinstance(g, dict) and g.get("name")]
                except Exception as e:
                    QMessageBox.warning(dialog, self.tr("提示"), self.tr("读取配置失败：%1").replace('%1', str(e)))
                    return
                if not names:
                    QMessageBox.warning(dialog, self.tr("提示"), self.tr("配置文件中未找到游戏名称"))
                    return
                # 使用自定义列表对话框以支持键盘/触屏操作
                select_dlg = QtWidgets.QDialog(dialog)
                select_dlg.setWindowTitle(self.tr("选择存档游戏名称"))
                select_dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
                # 统一外观样式，圆角半透明背景
                select_dlg.setStyleSheet("""
                    QDialog { background-color: rgba(46,46,46,0.98); border-radius: 12px; border: 2px solid #444444; }
                """)
                select_layout = QtWidgets.QVBoxLayout(select_dlg)
                select_layout.setContentsMargins(16, 12, 16, 12)
                select_layout.setSpacing(12)

                list_widget = QtWidgets.QListWidget(select_dlg)
                list_widget.setFrameShape(QtWidgets.QFrame.NoFrame)
                list_widget.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
                list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
                list_widget.setSpacing(int(8 * self.scale_factor))
                list_widget.setStyleSheet(f"""
                    QListWidget {{ color: white; background-color: #2b2b2b; border-radius: 8px; padding: 8px; }}
                    QListWidget::item {{ padding: 12px; }}
                    QListWidget::item:selected {{ background-color: #93ffff; color: #222; border-radius: 6px; }}
                    QScrollBar:vertical {{ background: transparent; width: 14px; margin: 0px 0px 0px 0px; }}
                    QScrollBar::handle:vertical {{ background: #555; border-radius: 7px; min-height: 20px; }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                """)
                # 填充列表项并调整每项高度以便可读
                item_h = int( (large_font_px * 1.6) )
                for name in names:
                    it = QtWidgets.QListWidgetItem(name)
                    it.setSizeHint(QSize(0, item_h))
                    list_widget.addItem(it)
                list_widget.setCurrentRow(0)
                select_layout.addWidget(list_widget)

                # 按钮区域：居中显示
                btn_h_small = int(BTN_HEIGHT * 1.2)
                btn_ok2 = QPushButton(self.tr("确定"), select_dlg)
                btn_cancel2 = QPushButton(self.tr("取消"), select_dlg)
                btn_ok2.setFixedHeight(btn_h_small)
                btn_cancel2.setFixedHeight(btn_h_small)
                btn_ok2.setStyleSheet(f"background-color: #444444; color: white; font-size: {int(24 * self.scale_factor)}px; border: none; border-radius: 8px;")
                btn_cancel2.setStyleSheet(f"background-color: #444444; color: white; font-size: {int(24 * self.scale_factor)}px; border: none; border-radius: 8px;")
                h2 = QtWidgets.QHBoxLayout()
                h2.setSpacing(int(12 * self.scale_factor))
                btn_ok2.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                btn_cancel2.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                h2.addWidget(btn_ok2, 1)
                h2.addWidget(btn_cancel2, 1)
                select_layout.addLayout(h2)

                # 支持触屏拖动滚动（若可用）
                try:
                    QScroller.grabGesture(list_widget.viewport(), QScroller.LeftMouseButtonGesture)
                except Exception:
                    pass

                # 回车选择、双击选择
                def on_accept():
                    cur = list_widget.currentItem()
                    if cur:
                        edit.setText(cur.text())
                    select_dlg.accept()
                def on_reject():
                    select_dlg.reject()
                btn_ok2.clicked.connect(on_accept)
                btn_cancel2.clicked.connect(on_reject)
                list_widget.itemDoubleClicked.connect(lambda it: (edit.setText(it.text()), select_dlg.accept()))

                # 键盘事件：Enter 接受, Esc 取消
                def list_key_event(event):
                    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                        on_accept()
                    elif event.key() == Qt.Key_Escape:
                        on_reject()
                    else:
                        return QtWidgets.QListWidget.keyPressEvent(list_widget, event)
                list_widget.keyPressEvent = list_key_event

                # 限制对话框大小，以避免列表项过度拉伸
                dlg_w = min(int(self.width() * 0.6), int(900 * self.scale_factor))
                dlg_h = min(int(self.height() * 0.6), int(600 * self.scale_factor))
                select_dlg.setFixedSize(dlg_w, dlg_h)

                # 标记为当前活动弹窗，便于手柄事件转发
                self.active_dialog = select_dlg
                try:
                    if select_dlg.exec_() == QDialog.Accepted:
                        pass
                finally:
                    self.active_dialog = None

            use_btn.clicked.connect(use_save_name)
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            if dialog.exec_() == QDialog.Accepted:
                new_name = edit.text().strip()
                if new_name and new_name != old_name:
                    # 直接修改 apps.json
                    json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        changed = False
                        for app in data.get("apps", []):
                            if app.get("name") == old_name:
                                app["name"] = new_name
                                changed = True
                        if changed:
                            with open(json_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=4, ensure_ascii=False)
                        else:
                            QMessageBox.warning(self, self.tr("提示"), self.tr("未找到要重命名的游戏"))
                    except Exception as e:
                        QMessageBox.warning(self, self.tr("提示"), self.tr("重命名失败：%1").replace('%1', str(e)))
                        return

                    # 替换 set.json 中所有 old_name
                    try:
                        set_path = "set.json"
                        if os.path.exists(set_path):
                            with open(set_path, "r", encoding="utf-8") as f:
                                set_data = json.load(f)
                            def replace_name(obj):
                                if isinstance(obj, list):
                                    return [replace_name(x) for x in obj]
                                elif isinstance(obj, dict):
                                    return {k: replace_name(v) for k, v in obj.items()}
                                elif isinstance(obj, str):
                                    return new_name if obj == old_name else obj
                                else:
                                    return obj
                            set_data = replace_name(set_data)
                            with open(set_path, "w", encoding="utf-8") as f:
                                json.dump(set_data, f, indent=4, ensure_ascii=False)
                    except Exception as e:
                        QMessageBox.warning(self, self.tr("提示"), self.tr("set.json替换失败：%1").replace('%1', str(e)))
                    # 刷新游戏列表
                    if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                        self.parent().deep_reload_games()
                    # 关闭窗口
                    self.close()
        def on_open_folder_clicked():
            # 打开当前游戏的文件夹
            game_name = self.game_name_label.text()
            # 在 valid_apps 里查找对应游戏的路径
            game_path = None
            for app in valid_apps:
                if app["name"] == game_name:
                    game_path = app["path"]
                    break
            if game_path and os.path.exists(game_path):
                folder = os.path.dirname(game_path)
                if os.path.exists(folder):
                    subprocess.Popen(f'explorer "{folder}"')
                else:
                    QMessageBox.warning(self, self.tr("提示"), self.tr("未找到游戏文件夹。"))
            else:
                QMessageBox.warning(self, self.tr("提示"), self.tr("未找到游戏路径。"))
        def on_remove_clicked():
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog(self.tr("确认从游戏列表移除该游戏吗？\n（不会删除游戏数据）"), scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            self.confirm_dialog = ConfirmDialog(self.tr("确认从游戏列表移除该游戏吗？\n（二次确认）"), scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            self.qsaa_thread = SunshineAppManagerThread(args=["--delete", str(self.game_name_label.text())])
            if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                self.qsaa_thread.finished_signal.connect(self.parent().deep_reload_games)
                self.qsaa_thread.finished_signal.connect(self.safe_close)
            self.qsaa_thread.start()


        # 主水平布局
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(int(10 * self.scale_factor), int(10 * self.scale_factor), int(10 * self.scale_factor), int(10 * self.scale_factor))
        self.main_layout.setSpacing(int(10 * self.scale_factor))

        # 左侧信息面板
        self.left_panel = QWidget(self)
        left_panel_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_panel_layout.setAlignment(Qt.AlignTop)

        # 游戏名标签
        self.game_name_label = QLabel(self.tr("游戏名称"), self.left_panel)
        self.game_name_label.setStyleSheet(f"color: white; font-size: {int(40 * self.scale_factor)}px; font-weight: bold;")
        self.game_name_label.setMaximumWidth(self.width() // 2 - int(150 * self.scale_factor))
        self.play_time_label = QLabel(self.left_panel)
        self.play_time_label.setStyleSheet(f"color: white; font-size: {int(30 * self.scale_factor)}px; font-weight: normal;")
        left_panel_layout.addWidget(self.game_name_label)
        left_panel_layout.setSpacing(int(10 * self.scale_factor))
        left_panel_layout.addWidget(self.play_time_label)
        left_panel_layout.setSpacing(int(19 * self.scale_factor))

        # 开头单独按钮
        btn_toolx = QPushButton(self.tr("同步游戏存档"), self.left_panel)
        btn_toolx.setFixedHeight(BTN_HEIGHT)
        btn_toolx.setStyleSheet(btn_style)
        btn_toolx.clicked.connect(on_backup_save_clicked)
        left_panel_layout.addWidget(btn_toolx)

        # 第一排：恢复/查看存档列表
        row1 = QHBoxLayout()
        btn_backup = QPushButton(self.tr("恢复游戏存档"), self.left_panel)
        btn_backup.setFixedHeight(BTN_HEIGHT)
        btn_backup.setStyleSheet(btn_style)
        btn_backup.clicked.connect(on_backup_restore_clicked)
        row1.addWidget(btn_backup)

        btn_restore = QPushButton(self.tr("查看存档列表"), self.left_panel)
        btn_restore.setFixedHeight(BTN_HEIGHT)
        btn_restore.setStyleSheet(btn_style)
        btn_restore.clicked.connect(on_view_backup_list_clicked)
        row1.addWidget(btn_restore)
        left_panel_layout.addLayout(row1)

        self.info_label2 = QLabel(self.tr("---------------------------------------------游戏特性相关---------------------------------------------"), self)
        self.info_label2.setStyleSheet(f"color: #aaa; font-size: {int(16 * self.scale_factor)}px; padding: 0px;")
        self.info_label2.setAlignment(Qt.AlignCenter)
        left_panel_layout.addWidget(self.info_label2)
        # 第二排：映射/冻结
        row2 = QHBoxLayout()
        self.btn_mapping = QPushButton(self.tr("游玩时开启映射(×)"), self.left_panel)
        self.btn_mapping.setFixedHeight(BTN_HEIGHT)
        self.btn_mapping.setStyleSheet(btn_style)
        # 新增：根据 set.json 设置初始状态
        if "on_mapping_clicked" in settings and self.game_name_label.text() in settings["on_mapping_clicked"]:
            self.btn_mapping.setText(self.tr("游玩时开启映射(✔)"))
        self.btn_mapping.clicked.connect(on_mapping_clicked)
        row2.addWidget(self.btn_mapping)

        self.btn_freeze = QPushButton(self.tr("冻结方式(跟随全局)"), self.left_panel)
        if "freeze_mode" in settings and self.game_name_label.text() in settings["freeze_mode"]:
            self.btn_freeze.setText(self.tr("冻结方式(%1)").replace('%1', settings['freeze_mode'][self.game_name_label.text()]))
        self.btn_freeze.setFixedHeight(BTN_HEIGHT)
        self.btn_freeze.setStyleSheet(btn_style)
        self.btn_freeze.clicked.connect(on_freeze_clicked)
        row2.addWidget(self.btn_freeze)
        left_panel_layout.addLayout(row2)

        # 第三排：配置自定义进程 + 附加工具启动
        row3 = QHBoxLayout()
        self.btn_custom_proc = QPushButton(self.tr("配置自定义进程(×)"), self.left_panel)
        if "custom_valid_apps" in settings and any(item["name"] == self.game_name_label.text() for item in settings["custom_valid_apps"]):
            self.btn_custom_proc.setText(self.tr("配置自定义进程(✔)"))
        self.btn_custom_proc.setFixedHeight(BTN_HEIGHT)
        self.btn_custom_proc.setStyleSheet(btn_style)
        self.btn_custom_proc.clicked.connect(on_custom_proc_clicked)
        row3.addWidget(self.btn_custom_proc)

        self.btn_tools = QPushButton(self.tr("附加工具启动(0)"), self.left_panel)
        if "custom_tools" in settings:
            for item in settings["custom_tools"]:
                if item["name"] == self.game_name_label.text():
                    self.btn_tools.setText(self.tr("附加工具启动(%1)").replace('%1', str(len(item['tools']))))
        self.btn_tools.setFixedHeight(BTN_HEIGHT)
        self.btn_tools.setStyleSheet(btn_style)
        self.btn_tools.clicked.connect(on_tools_clicked)
        row3.addWidget(self.btn_tools)
        left_panel_layout.addLayout(row3)
        self.info_label1 = QLabel(self.tr("---------------------------------------------游戏数据相关---------------------------------------------"), self)
        self.info_label1.setStyleSheet(f"color: #aaa; font-size: {int(16 * self.scale_factor)}px; padding: 0px;")
        self.info_label1.setAlignment(Qt.AlignCenter)
        left_panel_layout.addWidget(self.info_label1)

        # 第四排：自定义封面/重命名
        row4 = QHBoxLayout()
        btn_cover = QPushButton(self.tr("自定义封面"), self.left_panel)
        btn_cover.setFixedHeight(BTN_HEIGHT)
        btn_cover.setStyleSheet(btn_style)
        btn_cover.clicked.connect(on_cover_clicked)
        row4.addWidget(btn_cover)

        btn_rename = QPushButton(self.tr("重命名游戏名称"), self.left_panel)
        btn_rename.setFixedHeight(BTN_HEIGHT)
        btn_rename.setStyleSheet(btn_style)
        btn_rename.clicked.connect(on_rename_clicked)
        row4.addWidget(btn_rename)
        left_panel_layout.addLayout(row4)

        # 第五排：打开文件夹/移除游戏
        row5 = QHBoxLayout()
        btn_open_folder = QPushButton(self.tr("打开游戏文件夹"), self.left_panel)
        btn_open_folder.setFixedHeight(BTN_HEIGHT)
        btn_open_folder.setStyleSheet(btn_style)
        btn_open_folder.clicked.connect(on_open_folder_clicked)
        row5.addWidget(btn_open_folder)

        btn_remove = QPushButton(self.tr("移除游戏"), self.left_panel)
        btn_remove.setFixedHeight(BTN_HEIGHT)
        btn_remove.setStyleSheet(btn_style)
        btn_remove.clicked.connect(on_remove_clicked)
        row5.addWidget(btn_remove)
        left_panel_layout.addLayout(row5)
        # 截图列表控件
        self.listWidget = QtWidgets.QListWidget(self)
        self.listWidget.setViewMode(QtWidgets.QListView.IconMode)
        self.listWidget.setIconSize(QSize(int(self.icon_size), int(self.icon_size)))
        self.listWidget.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.listWidget.setMovement(QtWidgets.QListView.Static)
        self.listWidget.setSpacing(int(10 * self.scale_factor))
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.listWidget.itemClicked.connect(self.on_item_clicked)
        self.listWidget.setFocus()
        # 添加鼠标左键拖动滚动手势
        QScroller.grabGesture(self.listWidget.viewport(), QScroller.LeftMouseButtonGesture)

        # 右侧布局（包含listWidget）
        right_panel = QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(int(10 * self.scale_factor))
        # 不在此处设置对齐，改为保存布局供后续动态调整
        right_layout.addWidget(self.listWidget)
        self.right_panel = right_panel
        self.right_layout = right_layout
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet(f"color: #aaa; font-size: {int(18 * self.scale_factor)}px; padding: {int(8 * self.scale_factor)}px;")
        self.info_label.setAlignment(Qt.AlignLeft)
        right_layout.addWidget(self.info_label)
        # 初始使列表靠右以匹配带左侧面板的布局
        self.right_layout.setAlignment(self.listWidget, Qt.AlignRight)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(right_panel)

        # 用 QWidget 包裹 main_layout
        main_widget = QWidget(self)
        main_widget.setLayout(self.main_layout)
        main_widget.setFixedWidth(int(1800 * self.scale_factor))

        # 外层垂直布局
        layout = QtWidgets.QVBoxLayout(self)
        # 关闭按钮放在最上面
        self.closeButton = QPushButton(self.tr("关闭"), self)
        self.closeButton.setFixedHeight(int(50 * self.scale_factor))
        self.closeButton.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                font-size: 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.closeButton.clicked.connect(self.close)
        layout.addWidget(self.closeButton)

        # 使用水平包装布局在左右两侧添加弹性间距，使主内容固定为1800且居中
        h_wrapper = QtWidgets.QHBoxLayout()
        h_wrapper.addStretch(1)
        h_wrapper.addWidget(main_widget)
        h_wrapper.addStretch(1)
        layout.addLayout(h_wrapper)

        self.setLayout(layout)
        self.all_screenshots = []
        self.current_screenshots = []
        # 事件过滤：拦截按键处理快捷操作
        self.listWidget.installEventFilter(self)
        self.batch_mode = False

        # 添加手柄输入相关属性
        self.current_index = 0
        self.current_button_index = 0  # 当前焦点按钮索引
        self.in_left_panel = False     # 是否在左侧按钮区域
        self.left_panel_buttons = [] # 用于存储左侧按钮
        self.disable_left_panel_switch = False
        self.last_input_time = 0
        self.input_delay = 200
        self.ignore_input_until = 0
        self.buttons = []  # 用于存储列表项
        self.init_left_panel_buttons() # 初始化左侧按钮
        self.load_all_images = False  # 新增：是否加载全部图片的标志
        #self.update_highlight()  # 初始化高亮状态

    def on_item_clicked(self, item):
        if QApplication.mouseButtons() == Qt.RightButton:  # 检测是否为右键点击
            img_path = item.data(Qt.UserRole)  # 获取图片路径
            if os.path.exists(img_path):
                subprocess.Popen(f'explorer /select,"{img_path}"')  # 使用文件管理器打开图片位置
        self.start_fullscreen_preview()
    def showEvent(self, event):
        """窗口显示时触发重新加载截图"""
        super().showEvent(event)
        #self.reload_screenshots()
        self.raise_()

    def reload_screenshots(self):
        """重新加载截图目录并启动后台线程"""
        # 清除原图片并显示加载提示
        self.listWidget.clear()
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        label = QLabel(self.tr("正在扫描截图目录..."))
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: #aaa; font-size: 28px;")
        label.setMinimumHeight(220)
        label.setMinimumWidth(self.listWidget.viewport().width() - 40)
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, label)
        item.setSizeHint(label.sizeHint())
        # 判断是否筛选了具体游戏
        if self.filter_game_name and self.filter_game_name != "全部游戏":
            filtered = [item for item in self.all_screenshots if item[1] == self.filter_game_name]
            if not getattr(self, "load_all_images", False):
                self.current_screenshots = filtered[:6]
                self.has_load_more_button = len(filtered) > 6
            else:
                self.current_screenshots = filtered
                self.has_load_more_button = False
            # 显示左侧面板并恢复合理最大宽度
            self.left_panel.setVisible(True)
            self.left_panel.setMaximumWidth(int(950 * self.scale_factor))
            self.listWidget.setFixedWidth(int(950 * self.scale_factor))
            self.icon_size = int(256 * self.scale_factor * 1.75)
            if hasattr(self, 'right_layout'):
                self.right_layout.setAlignment(self.listWidget, Qt.AlignRight)
        else:
            self.current_screenshots = list(self.all_screenshots)
            # 隐藏左侧面板并将其最大宽度设为0，避免残留占位
            self.left_panel.setVisible(False)
            self.left_panel.setMaximumWidth(0)
            self.listWidget.setFixedWidth(int(1630 * self.scale_factor))
            self.icon_size = 256 * self.scale_factor
            if hasattr(self, 'right_layout'):
                self.right_layout.setAlignment(self.listWidget, Qt.AlignHCenter)
            self.has_load_more_button = False

        self.listWidget.setIconSize(QSize(int(self.icon_size), int(self.icon_size)))
        # 设置网格大小以确保正确排列（包含间距），宽高遵循16:9
        grid_width = int(self.icon_size) + int(10 * self.scale_factor)
        grid_height = int(grid_width * 9 / 16)
        self.listWidget.setGridSize(QSize(grid_width, grid_height))
        
        # 启动后台线程扫描截图目录
        self.scanner_thread = ScreenshotScannerThread()
        self.scanner_thread.screenshots_scanned.connect(self.on_screenshots_scanned)
        self.scanner_thread.start()

        # 启动后台线程加载所有图片
        self.loader_thread = ScreenshotLoaderThread(self.current_screenshots, self.icon_size)
        self.loader_thread.screenshot_loaded.connect(self.on_screenshots_loaded)
        self.loader_thread.finished.connect(self.update_highlight)
        self.loader_thread.start()
    
    def on_screenshots_scanned(self, all_screenshots):
        """处理扫描完成的截图列表"""
        self.all_screenshots = all_screenshots
        
        # 根据筛选条件过滤截图
        if self.filter_game_name and self.filter_game_name != "全部游戏":
            filtered = [item for item in self.all_screenshots if item[1] == self.filter_game_name]
            self.current_screenshots = filtered
        else:
            self.current_screenshots = list(self.all_screenshots)
        
        # 取消"加载全部图片"按钮逻辑
        self.has_load_more_button = False
        
        # 立即创建所有图片占位符
        self.listWidget.clear()
        
        # 没有截图时显示提示文字
        if not self.current_screenshots:
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            label = QLabel(self.tr("还没有截图\n在游戏中按下L3+R3记录美好时刻～"))
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setStyleSheet("color: #aaa; font-size: 28px;")
            label.setMinimumHeight(int(220 * self.scale_factor))
            label.setMinimumWidth(self.listWidget.viewport().width() - int(40 * self.scale_factor))
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, label)
            item.setSizeHint(label.sizeHint())
            return
        
        # 创建所有图片占位符
        self.image_items = []
        for _ in range(len(self.current_screenshots)):
            item = QListWidgetItem()
            # 设置图片项大小为图标大小
            item.setSizeHint(QSize(int(self.icon_size), int(self.icon_size * 9 / 16)))
            self.listWidget.addItem(item)
            self.image_items.append(item)
        
        # 计算初始加载数量
        initial_count = 30 if getattr(self, 'disable_left_panel_switch', False) else 6
        # 确保初始数量不超过截图总数
        initial_count = min(initial_count, len(self.current_screenshots))
        
        # 记录已加载的图片数量
        self.loaded_image_count = initial_count
        
        # 启动后台线程加载初始图片
        initial_indices = list(range(initial_count))
        self.loader_thread = ScreenshotLoaderThread(self.current_screenshots, self.icon_size, initial_indices)
        self.loader_thread.screenshot_loaded.connect(self.on_screenshots_loaded)
        self.loader_thread.screenshot_single_loaded.connect(self.on_screenshot_single_loaded)
        self.loader_thread.finished.connect(self.update_highlight)
        self.loader_thread.start()
        
        # 添加滚动事件监听器，实现懒加载
        self.listWidget.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.listWidget.horizontalScrollBar().valueChanged.connect(self.on_scroll)
        # 为listWidget的viewport添加事件过滤器，捕获鼠标滚轮事件
        self.listWidget.viewport().installEventFilter(self)

    def update_highlight(self):
        """更新高亮状态"""
        self.buttons = [self.listWidget.item(i) for i in range(self.listWidget.count())]
        info_text = ""
        if self.buttons:
            self.current_index = max(0, min(self.current_index, len(self.buttons) - 1))
            if not self.in_left_panel:
                self.listWidget.setCurrentItem(self.buttons[self.current_index])
                self.listWidget.scrollToItem(self.buttons[self.current_index])
                for i, item in enumerate(self.buttons):
                    if i == self.current_index:
                        item.setBackground(QColor("#93ffff"))
                        # 显示信息
                        img_path = item.data(Qt.UserRole)
                        # 查找截图元数据并获取索引
                        allidx = len(self.current_screenshots)
                        for idx, (path, game, ts) in enumerate(self.current_screenshots):
                            if path == img_path:
                                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                                info_text = f"{game} / {timestamp}  （{idx + 1}/{allidx}）"
                                print(info_text)
                                break
                    else:
                        item.setBackground(QColor("transparent"))
            else:
                for item in self.buttons:
                    item.setBackground(QColor("transparent"))
                info_text = ""
        self.info_label.setText(info_text)
        
    def eventFilter(self, source, event):
        """事件过滤器，捕获listWidget的鼠标滚轮事件"""
        if source == self.listWidget.viewport() and event.type() == event.Wheel:
            # 触发懒加载
            self.on_scroll()
        return super().eventFilter(source, event)
        
    def on_scroll(self):
        """处理滚动事件，实现懒加载"""
        # 如果所有图片已经加载完成，或者正在加载中，就直接返回
        if hasattr(self, 'all_images_loaded') and self.all_images_loaded:
            return
        
        if hasattr(self, 'is_loading_images') and self.is_loading_images:
            return
        
        # 检查必要属性是否存在
        if not hasattr(self, 'loaded_image_count') or not hasattr(self, 'current_screenshots'):
            return
        
        # 标记正在加载图片
        self.is_loading_images = True
        
        # 计算需要加载的剩余图片索引
        remaining_indices = list(range(self.loaded_image_count, len(self.current_screenshots)))
        
        # 启动后台线程加载剩余图片
        self.loader_thread = ScreenshotLoaderThread(self.current_screenshots, self.icon_size, remaining_indices)
        self.loader_thread.screenshot_loaded.connect(self.on_remaining_screenshots_loaded)
        self.loader_thread.screenshot_single_loaded.connect(self.on_screenshot_single_loaded)
        self.loader_thread.finished.connect(self.update_highlight)
        self.loader_thread.start()
        
    def on_remaining_screenshots_loaded(self, loaded_screenshots):
        """处理剩余图片加载完成事件"""
        # 标记所有图片已加载完成
        self.all_images_loaded = True
        # 清除正在加载标记
        self.is_loading_images = False
        
    def wheelEvent(self, event):
        """处理鼠标滚轮事件，实现懒加载"""
        # 先调用父类方法处理滚轮事件
        super().wheelEvent(event)
        # 触发懒加载
        self.on_scroll()
        
    def load_screenshots(self):
        """扫描截图目录，加载文件路径和元数据"""
        self.all_screenshots = []
        base_dir = "screenshot"
        if not os.path.isdir(base_dir):
            return
        for game in os.listdir(base_dir):
            game_dir = os.path.join(base_dir, game)
            if not os.path.isdir(game_dir):
                continue
            for fname in os.listdir(game_dir):
                if fname.lower().endswith(".png"):
                    path = os.path.join(game_dir, fname)
                    ts = os.path.getmtime(path)
                    self.all_screenshots.append((path, game, ts))
        self.all_screenshots.sort(key=lambda x: x[2], reverse=True)
        self.current_screenshots = list(self.all_screenshots)

    def on_screenshots_loaded(self, loaded_screenshots):
        """处理所有图片加载完成的事件"""
        # 图片已通过 on_screenshot_single_loaded 逐个加载完成并更新UI
        # 这里只需处理加载完成后的收尾工作
        
        # 移除"加载全部图片"按钮相关逻辑
        self.load_more_item_index = None
        
        # 加载完成后恢复索引并高亮
        if hasattr(self, "restore_index_after_load"):
            self.current_index = min(self.restore_index_after_load, self.listWidget.count() - 1)
            del self.restore_index_after_load
    
    def on_screenshot_single_loaded(self, index, screenshot_data):
        """处理单张图片加载完成信号，立即更新UI"""
        if index < len(self.image_items):
            thumb, path, game, ts = screenshot_data
            item = self.image_items[index]
            icon = QtGui.QIcon(thumb)
            item.setIcon(icon)
            item.setText("")
            item.setData(Qt.UserRole, path)
    
    def get_row_count(self):
        """获取每行的缩略图数量"""
        if self.filter_game_name and self.filter_game_name != "全部游戏":
            return 2
        else:
            return 6
    def move_selection(self, offset):
        """移动选择的截图或左侧按钮"""
        if self.in_left_panel:
            # 左侧按钮区域上下移动
            self.current_button_index = (self.current_button_index + (1 if offset > 0 else -1)) % len(self.left_panel_buttons)
            self.update_left_panel_button_styles()
        else:
            total_buttons = len(self.buttons)
            new_index = self.current_index + offset
            row_count = self.get_row_count()
            # 上下键逻辑，循环跳转
            if offset == -row_count:  # 上移一行
                if new_index < 0:
                    column = self.current_index % row_count
                    new_index = (total_buttons - 1) - (total_buttons - 1) % row_count + column
                    if new_index >= total_buttons:
                        new_index -= row_count
            elif offset == row_count:  # 下移一行
                if new_index >= total_buttons:
                    column = self.current_index % row_count
                    new_index = column
            # 左右键逻辑，循环跳转
            if offset == -1 and new_index < 0:
                new_index = total_buttons - 1
            elif offset == 1 and new_index >= total_buttons:
                new_index = 0
            self.current_index = new_index
            self.update_highlight()

    def handle_gamepad_input(self, action):
        """处理手柄输入，支持左侧按钮和截图框切换"""
        current_time = pygame.time.get_ticks()
        if current_time < self.ignore_input_until:
            return
        if current_time - self.last_input_time < self.input_delay:
            return
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog and self.confirm_dialog.isVisible():
            self.confirm_dialog.handle_gamepad_input(action)
            return
        # 新增：如果有弹窗，转发给弹窗（这个应该是不必要的，不过放着无妨）
        if hasattr(self, "active_dialog") and self.active_dialog is not None:
            if hasattr(self.active_dialog, "handle_gamepad_input"):
                self.active_dialog.handle_gamepad_input(action)
            return
        # 全屏预览等原有逻辑...
        if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
            if getattr(self, "has_load_more_button", False):
                allidx = len(self.current_screenshots) + 1  
            else:
                allidx = len(self.current_screenshots)
            if action == 'LEFT':
                self.preview_index = (self.preview_index - 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == 'RIGHT':
                self.preview_index = (self.preview_index + 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == 'LB':  # 添加LB键切换到上一张
                self.preview_index = (self.preview_index - 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == 'RB':  # 添加RB键切换到下一张
                self.preview_index = (self.preview_index + 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == "X":
                current_item = self.listWidget.currentItem()
                if current_item:
                    img_path = current_item.data(Qt.UserRole)
                    if img_path and os.path.exists(img_path):
                        subprocess.Popen(f'explorer /select,"{img_path}"')
                return
            elif action == 'Y':
                self.delete_selected_items()
            elif action in ('A', 'B'):
                self.is_fullscreen_preview.close()  # 修复调用
                self.is_fullscreen_preview = None  # 清除引用
                return

        # 新增：左侧按钮区域手柄操作
        if self.in_left_panel:
            if action in ('UP',):
                if self.current_button_index == 0:
                    return  # 如果在第一行的第一个按钮，不能上移
                if self.current_button_index == 1:
                    self.current_button_index = (self.current_button_index - 1) % len(self.left_panel_buttons)
                else:
                    self.current_button_index = (self.current_button_index - 2) % len(self.left_panel_buttons)
                self.update_left_panel_button_styles()
            elif action in ('DOWN',):
                if self.current_button_index == 0:
                    self.current_button_index = (self.current_button_index + 1) % len(self.left_panel_buttons)
                # 如果在倒数第二个或最后一个按钮，不能下移
                elif self.current_button_index >= len(self.left_panel_buttons) - 2:
                    return
                else:
                    self.current_button_index = (self.current_button_index + 2) % len(self.left_panel_buttons)
                self.update_left_panel_button_styles()
            elif action in ('A',):
                self.left_panel_buttons[self.current_button_index].click()
                self.ignore_input_until = pygame.time.get_ticks() + 350  
            elif action in ('LEFT',):
                if self.current_button_index == 0:
                    return
                if self.current_button_index % 2 == 0:
                    self.current_button_index = (self.current_button_index - 1) % len(self.left_panel_buttons)
                    self.update_left_panel_button_styles()
                #else:
                #    # 切换到截图框区域
                #    self.in_left_panel = False
                #    self.update_left_panel_button_styles()
                #    self.update_highlight()
            elif action in ('RIGHT',):
                if (self.current_button_index+1) % 2 == 0:
                    self.current_button_index = (self.current_button_index + 1) % len(self.left_panel_buttons)
                    self.update_left_panel_button_styles()
                else:
                    # 切换到截图框区域
                    self.in_left_panel = False
                    self.update_left_panel_button_styles()
                    self.update_highlight()
            elif action in ('B',):
                self.safe_close()
            self.last_input_time = current_time
            return

        # 截图框区域手柄操作
        if not self.in_left_panel:
            if action == 'A':
                self.start_fullscreen_preview()
            elif action == 'X':
                self.start_filter_mode()
            elif action == 'Y':
                self.delete_selected_items()
            elif action == 'B':
                self.safe_close()
            elif action == 'UP':
                self.move_selection(-self.get_row_count())
            elif action == 'DOWN':
                self.move_selection(self.get_row_count())
            elif action == 'LEFT':
                if self.current_index % 2 == 0 and self.disable_left_panel_switch == False:
                    self.in_left_panel = True
                    self.update_left_panel_button_styles()
                    self.update_highlight()
                else:
                    self.current_index = max(0, self.current_index - 1)
                    self.update_highlight()
            elif action == 'RIGHT':
                if self.current_index % 2 != 0 and self.disable_left_panel_switch == False:
                    return
                else:
                    self.current_index = min(len(self.buttons) - 1, self.current_index + 1)
                    self.update_highlight()
            elif action == 'START':
                self.safe_close()
            self.last_input_time = current_time

    def handle_info_bar_link(self, link):
        if getattr(self, "has_load_more_button", False):
            allidx = len(self.current_screenshots) + 1  
        else:
            allidx = len(self.current_screenshots)
        if link == "prev":
            self.preview_index = (self.preview_index - 1) % allidx
            self.is_fullscreen_preview.load_preview(self.preview_index)
        elif link == "next":
            self.preview_index = (self.preview_index + 1) % allidx
            self.is_fullscreen_preview.load_preview(self.preview_index)
        elif link == "action1":
            self.delete_selected_items()
            #if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
            #    self.is_fullscreen_preview.close()  # 修复调用
            #    self.is_fullscreen_preview = None  # 清除引用
            #self.start_fullscreen_preview()  # 重新打开预览窗口
        elif link == "action2":
            current_item = self.listWidget.currentItem()
            if current_item:
                img_path = current_item.data(Qt.UserRole)
                if img_path and os.path.exists(img_path):
                    subprocess.Popen(f'explorer /select,"{img_path}"')
        elif link == "action3":
            if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
                self.is_fullscreen_preview.close()  # 修复调用
                self.is_fullscreen_preview = None  # 清除引用    

    def init_left_panel_buttons(self):
        # 初始化左侧面板按钮
        self.left_panel_buttons = []  # 存储按钮引用
        for i, btn in enumerate(self.left_panel.findChildren(QPushButton)):
            self.left_panel_buttons.append(btn)
        self.update_left_panel_button_styles()

    def update_left_panel_button_styles(self):
        # 更新左侧面板按钮样式
        for i, button in enumerate(self.left_panel_buttons):
            if i == self.current_button_index and self.in_left_panel:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        text-align: center;
                        padding: {int(10 * self.scale_factor)}px;
                        border: {int(2 * self.scale_factor)}px solid #93ffff;
                        font-size: {int(30 * self.scale_factor)}px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        text-align: center;
                        padding: {int(10 * self.scale_factor)}px;
                        border: none;
                        font-size: {int(30 * self.scale_factor)}px;
                    }}
                    QPushButton:hover {{
                        background-color: #555555;
                    }}
                """)

    def start_fullscreen_preview(self):
        """显示当前选中图片的全屏预览对话框"""
        global FSPREVIEWHWND
        current_item = self.listWidget.currentItem()
        if not current_item:
            return
        path = current_item.data(Qt.UserRole)
        try:
            index = [item[0] for item in self.current_screenshots].index(path)
        except ValueError:
            index = 0
        self.preview_index = index
    
        self.is_fullscreen_preview = QtWidgets.QDialog(self, flags=Qt.Dialog)
        self.is_fullscreen_preview.setAttribute(Qt.WA_DeleteOnClose)
        self.is_fullscreen_preview.setWindowFlag(Qt.FramelessWindowHint)
        # 初始窗口透明度为0，随后播放淡入动画
        try:
            self.is_fullscreen_preview.setWindowOpacity(0.0)
        except Exception:
            pass
        self.is_fullscreen_preview.showFullScreen()
        FSPREVIEWHWND = int(self.is_fullscreen_preview.winId())
        # 窗口淡入动画（保存引用以防被垃圾回收）
        try:
            fade_in_win = QPropertyAnimation(self.is_fullscreen_preview, b"windowOpacity")
            fade_in_win.setDuration(100)
            fade_in_win.setStartValue(0.0)
            fade_in_win.setEndValue(1.0)
            self._fsp_window_fade_in = fade_in_win
            fade_in_win.start()
        except Exception:
            pass
        
        # 创建主布局
        main_layout = QtWidgets.QVBoxLayout(self.is_fullscreen_preview)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        #self.is_fullscreen_preview.setAttribute(Qt.WA_TranslucentBackground)
        #self.is_fullscreen_preview.setStyleSheet("""
        #    QDialog {
        #    background-color: rgba(0, 0, 0, 0.6); /* 设置半透明背景 */
        #    }
        #""")
        
        # 添加信息栏到顶部
        info_bar = QtWidgets.QLabel(self.is_fullscreen_preview)
        info_bar.setStyleSheet(f"""
            QLabel {{ 
                background-color: rgba(0, 0, 0, 0.8); /* 半透明黑色背景 */
                color: white;
                font-size: {int(18 * self.scale_factor)}px;
                padding: {int(12 * self.scale_factor)}px {int(20 * self.scale_factor)}px;
                border-bottom: {int(1 * self.scale_factor)}px solid rgba(255, 255, 255, 0.1);
            }} 
        """)
        info_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_bar.setFixedHeight(int(50 * self.scale_factor))  # 调整高度
        info_bar.setTextFormat(Qt.RichText)
        info_bar.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_bar.setOpenExternalLinks(False)  # 不自动打开外部链接
        info_bar.linkActivated.connect(self.handle_info_bar_link)
        def close_fullscreen_preview(event):
            """关闭全屏预览窗口（使用淡出动画）"""
            if not (hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview):
                return
            dlg = self.is_fullscreen_preview
            try:
                # 创建淡出动画并在完成后真正关闭对话框
                fade_out_win = QPropertyAnimation(dlg, b"windowOpacity")
                fade_out_win.setDuration(100)
                fade_out_win.setStartValue(dlg.windowOpacity() if hasattr(dlg, 'windowOpacity') else 1.0)
                fade_out_win.setEndValue(0.0)
                def _on_fade_finished():
                    try:
                        dlg.close()
                        dlg.deleteLater()
                    except Exception:
                        pass
                    # 清除引用
                    if hasattr(self, 'is_fullscreen_preview'):
                        self.is_fullscreen_preview = None
                fade_out_win.finished.connect(_on_fade_finished)
                self._fsp_window_fade_out = fade_out_win
                fade_out_win.start()
            except Exception:
                try:
                    self.is_fullscreen_preview.close()
                except Exception:
                    pass
                self.is_fullscreen_preview = None
        #info_bar.mousePressEvent = close_fullscreen_preview
        # 绑定实例的 close 方法，使外部直接调用 close() 时也能使用淡出动画
        def _close_no_event():
            close_fullscreen_preview(None)
        try:
            self.is_fullscreen_preview.close = _close_no_event
        except Exception:
            pass
        main_layout.addWidget(info_bar)
        
        # 创建图片标签
        label = QtWidgets.QLabel(self.is_fullscreen_preview)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: black;")
        label.mousePressEvent = close_fullscreen_preview
        # 为 label 添加不透明度效果，QLabel 本身没有 "opacity" 属性
        effect = QtWidgets.QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(effect)
        effect.setOpacity(1.0)
        # 添加鼠标滚轮支持
        def wheelEvent(event):
            delta = event.angleDelta().y()
            if delta > 0:  # 向上滚动，切换到上一张
                self.preview_index = (self.preview_index - 1) % len(self.current_screenshots)
            else:  # 向下滚动，切换到下一张
                self.preview_index = (self.preview_index + 1) % len(self.current_screenshots)
            self.is_fullscreen_preview.load_preview(self.preview_index)
        label.wheelEvent = wheelEvent
        # 添加图片标签和切换按钮
        # 创建水平布局来容纳左右按钮和图片
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        
        # 左侧切换按钮
        left_btn = QtWidgets.QPushButton("←")
        left_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: rgba(0, 0, 0, 0.3);
                color: white;
                font-size: {int(36 * self.scale_factor)}px;
                border: none;
                width: {int(50 * self.scale_factor)}px;
                height: {int(1000 * self.scale_factor)}px;
                opacity: 0.5;
            }} 
            QPushButton:hover {{ 
                opacity: 0.9;
            }} 
        """)
        left_btn.clicked.connect(lambda: (
            setattr(self, 'preview_index', (self.preview_index - 1) % len(self.current_screenshots)),
            self.is_fullscreen_preview.load_preview(self.preview_index)
        ))
        h_layout.addWidget(left_btn, alignment=Qt.AlignVCenter)
        
        # 将图片标签添加到布局中心
        h_layout.addWidget(label, 1)
        
        # 右侧切换按钮
        right_btn = QtWidgets.QPushButton("→")
        right_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: rgba(0, 0, 0, 0.3);
                color: white;
                font-size: {int(36 * self.scale_factor)}px;
                border: none;
                width: {int(50 * self.scale_factor)}px;
                height: {int(1000 * self.scale_factor)}px;
                opacity: 0.5;
            }} 
            QPushButton:hover {{ 
                opacity: 0.9;
            }} 
        """)
        right_btn.clicked.connect(lambda: (
            setattr(self, 'preview_index', (self.preview_index + 1) % len(self.current_screenshots)),
            self.is_fullscreen_preview.load_preview(self.preview_index)
        ))
        h_layout.addWidget(right_btn, alignment=Qt.AlignVCenter)
        
        # 将水平布局添加到主布局
        main_layout.addLayout(h_layout, 1)
    
        # 在嵌套函数外部预翻译，确保 lupdate 能正确识别
        tr_left = self.tr('左切换')
        tr_right = self.tr('右切换')
        tr_delete = self.tr('删除图片')
        tr_open_loc = self.tr('打开图片位置')
        tr_back = self.tr('返回')
        
        def load_preview(idx):
            # --- 新增：如果只加载了6张且有更多，且向右到第6张，自动加载全部 ---
            if (
                getattr(self, "has_load_more_button", False)
                and idx == 6
                and not getattr(self, "load_all_images", False)
            ):
                # 记录当前图片路径
                current_path = self.current_screenshots[idx - 1][0]
                self.load_all_images = True
                self.reload_screenshots()
                # 重新定位到第6张（原第7张）
                self.preview_index = 6
                QTimer.singleShot(200, lambda: self.is_fullscreen_preview.load_preview(self.preview_index))
                return
    
            path = self.current_screenshots[idx][0]
            pix = QtGui.QPixmap(path)
            screen = QtWidgets.QApplication.primaryScreen().size()
            # 计算90%的尺寸
            scaled_width = int(screen.width() * 0.95)
            scaled_height = int(screen.height() * 0.95)
            scaled = pix.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # 添加淡入淡出动画（针对 QGraphicsOpacityEffect）
            def animate_image():
                # 淡出当前图片 — 动画目标为 effect
                fade_out = QPropertyAnimation(effect, b"opacity")
                fade_out.setDuration(50)
                fade_out.setStartValue(1.0)
                fade_out.setEndValue(0.0)

                def on_fade_out_finished():
                    # 设置新图片并淡入
                    label.setPixmap(scaled)
                    fade_in = QPropertyAnimation(effect, b"opacity")
                    fade_in.setDuration(50)
                    fade_in.setStartValue(0.0)
                    fade_in.setEndValue(1.0)
                    # 保存引用以防被垃圾回收
                    self._preview_fade_in = fade_in
                    fade_in.start()

                # 保存引用以防被垃圾回收
                self._preview_fade_out = fade_out
                fade_out.finished.connect(on_fade_out_finished)
                fade_out.start()
            
            animate_image()
            if getattr(self, "has_load_more_button", False):
                allidx = ".."
            else:
                allidx = len(self.current_screenshots)
            # 更新信息栏内容
            game_name = self.current_screenshots[idx][1]
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.current_screenshots[idx][2]))
            info_bar.setText(
                f"{game_name} / {timestamp}  （{idx + 1}/{allidx}）    "
                f"<a href='prev' style='color: white;'>← {tr_left}</a>    "
                f"<a href='next' style='color: white;'>→ {tr_right}</a>     "
                f"<a href='action1' style='color: white;'>Y/{tr_delete}</a>    "
                f"<a href='action2' style='color: white;'>X/{tr_open_loc}</a>    "
                f"<a href='action3' style='color: white;'>A,B/{tr_back}</a>"
            )
    
        # 将 load_preview 方法绑定到 is_fullscreen_preview 对象
        self.is_fullscreen_preview.load_preview = load_preview
        self.is_fullscreen_preview.load_preview(self.preview_index)
    
        def preview_key(event):
            key = event.key()
            if key == Qt.Key_Left:
                self.preview_index = (self.preview_index - 1) % len(self.current_screenshots)
                self.is_fullscreen_preview.load_preview(self.preview_index)
            elif key == Qt.Key_Right:
                self.preview_index = (self.preview_index + 1) % len(self.current_screenshots)
                self.is_fullscreen_preview.load_preview(self.preview_index)
            elif key in (Qt.Key_Escape, Qt.Key_A, Qt.Key_B):
                self.is_fullscreen_preview.close()
    
        self.is_fullscreen_preview.keyPressEvent = preview_key
        self.is_fullscreen_preview.raise_()

    def start_filter_mode(self, game_name=None):
        """弹出对话框选择游戏名进行筛选，支持直接传入游戏名（即使没有截图也能筛选）"""
        games = ["全部游戏"] + sorted({g for (_, g, _) in self.all_screenshots})
        if game_name is not None:
            # 只要不是全部游戏，都允许筛选（即使没有截图）
            if game_name == "全部游戏":
                self.filter_game_name = None
            else:
                self.filter_game_name = game_name
            game = game_name
            ok = True
        else:
            game, ok = QtWidgets.QInputDialog.getItem(self, self.tr("筛选游戏"), self.tr("选择游戏："), games, 0, False)
            self.filter_game_name = game if ok and game != "全部游戏" else None
        if ok and game:
            self.game_name_label.setText(game)
            # 新增：同步按钮状态
            if "freeze_mode" in settings and game in settings["freeze_mode"]:
                self.btn_freeze.setText(self.tr("冻结方式(%1)").replace('%1', settings['freeze_mode'][game]))
            else:
                self.btn_freeze.setText(self.tr("冻结方式(跟随全局)"))
            if "custom_tools" in settings:
                for item in settings["custom_tools"]:
                    if item["name"] == game:
                        self.btn_tools.setText(self.tr("附加工具启动(%1)").replace('%1', str(len(item['tools']))))
                        break
                else:
                    self.btn_tools.setText(self.tr("附加工具启动(0)"))
            else:
                self.btn_tools.setText(self.tr("附加工具启动(0)"))
            if "custom_valid_apps" in settings and game in [item["name"] for item in settings["custom_valid_apps"]]:
                self.btn_custom_proc.setText(self.tr("配置自定义进程(✔)"))
            else:
                self.btn_custom_proc.setText(self.tr("配置自定义进程(×)"))
            if "on_mapping_clicked" in settings and game in settings["on_mapping_clicked"]:
                self.btn_mapping.setText(self.tr("游玩时开启映射(✔)"))
            else:
                self.btn_mapping.setText(self.tr("游玩时开启映射(×)"))
            # 新增：显示游玩时间
            play_time = settings.get("play_time", {}).get(game, 0)
            if play_time < 60:
                play_time_str = self.tr("游玩时间：%1 分钟").replace('%1', str(play_time))
            else:
                hours = play_time // 60
                minutes = play_time % 60
                play_time_str = self.tr("游玩时间：%1 小时 %2 分钟").replace('%1', str(hours)).replace('%2', str(minutes))
            self.play_time_label.setText(play_time_str)
            self.reload_screenshots()

    def clear_filter(self):
        self.filter_game_name = None
        self.game_name_label.setText(self.tr("全部游戏"))
        self.reload_screenshots()


    #def toggle_batch_mode(self):
    #    """切换批量多选模式"""
    #    if not self.batch_mode:
    #        # 进入多选模式
    #        self.batch_mode = True
    #        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
    #    else:
    #        # 退出多选模式
    #        self.batch_mode = False
    #        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    #        self.listWidget.clearSelection()
    def delete_selected_items(self):
        """删除选中的截图文件"""
        if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
            # 使用 self.preview_index 获取当前放大显示的图片路径
            path = self.current_screenshots[self.preview_index][0]  # 获取当前预览图片的路径
            self.confirm_dialog = ConfirmDialog(self.tr("确认删除选中的截图？\n%1").replace('%1', path), scale_factor=self.scale_factor)
            if self.confirm_dialog.exec_():
                if os.path.exists(path):
                    os.remove(path)
                # 从列表中移除
                self.all_screenshots = [s for s in self.all_screenshots if s[0] != path]
                self.current_screenshots = [s for s in self.current_screenshots if s[0] != path]
                self.reload_screenshots()
                # 修正：如果没有截图了，关闭全屏预览
                if not self.current_screenshots:
                    if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
                        self.is_fullscreen_preview.close()
                        self.is_fullscreen_preview = None
                else:
                    # 修正：删除后索引可能越界，重置为0
                    self.preview_index = min(self.preview_index, len(self.current_screenshots) - 1)
                    self.is_fullscreen_preview.load_preview(self.preview_index)
        else:
            items = self.listWidget.selectedItems()
            if not items:
                return
            # 弹出确认对话框
            for item in items:
                path = item.data(Qt.UserRole)  # 修复：从选中项获取路径
                self.confirm_dialog = ConfirmDialog(self.tr("确认删除选中的截图？\n%1").replace('%1', path), scale_factor=self.scale_factor)
                if self.confirm_dialog.exec_():
                    if os.path.exists(path):
                        os.remove(path)
                    row = self.listWidget.row(item)
                    self.listWidget.takeItem(row)
                    # 同时从数据列表移除
                    self.all_screenshots = [s for s in self.all_screenshots if s[0] != path]
                    self.current_screenshots = [s for s in self.current_screenshots if s[0] != path]
                    self.reload_screenshots()

    def safe_close(self):
        """安全关闭窗口，确保停止所有后台线程"""
        # 检查并停止 ScreenshotLoaderThread
        if hasattr(self, 'loader_thread') and self.loader_thread:
            if self.loader_thread.isRunning():
                self.loader_thread.stop()
        # 关闭窗口
        self.close()

    def closeEvent(self, event):
        """窗口关闭事件，确保停止所有后台线程并重置状态"""
        # 检查并停止 ScreenshotLoaderThread
        if hasattr(self, 'loader_thread') and self.loader_thread:
            if self.loader_thread.isRunning():
                self.loader_thread.stop()
        
        # 重置懒加载状态变量
        if hasattr(self, 'all_images_loaded'):
            del self.all_images_loaded
        if hasattr(self, 'is_loading_images'):
            del self.is_loading_images
        if hasattr(self, 'loaded_image_count'):
            del self.loaded_image_count
        
        # 调用父类的 closeEvent
        super().closeEvent(event)
class Overlay(QWidget):
    """全屏灰色覆盖层类"""
    def __init__(self, parent=None):
        super().__init__()
        # 记录关联的对话框，但不作为 Qt 的 parent 以避免行为异常
        self.associated_dialog = parent
        self.setAttribute(Qt.WA_DeleteOnClose)
        # 作为独立的顶级窗口，不设置parent
        # 可使用 Qt.WindowTransparentForInput 让事件穿过覆盖层
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        # 使用纯色背景，确保可以看到
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.2);")  # 半透明灰色
        self.setGeometry(QApplication.primaryScreen().geometry())  # 覆盖全屏
        self.setWindowOpacity(0.0)  # 初始透明度为0
        self._fade_anim = None
        self._is_fading = False
    
    def fade_in(self, duration=180):
        """淡入效果"""
        if self._is_fading:
            return
        self._is_fading = True
        # 确保覆盖层显示
        self.show()
        # 确保覆盖层在对话框之下
        self.lower()
        if self._fade_anim:
            self._fade_anim.stop()
            self._fade_anim.deleteLater()
            
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(0.2)  # 半透明
        anim.finished.connect(lambda: setattr(self, '_is_fading', False))
        self._fade_anim = anim
        anim.start()
    
    def fade_out(self, duration=180):
        """淡出效果"""
        if self._is_fading:
            return
        self._is_fading = True
        if self._fade_anim:
            self._fade_anim.stop()
            self._fade_anim.deleteLater()
            
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(self.windowOpacity())  # 使用当前透明度
        anim.setEndValue(0.0)
        def on_finished():
            self._is_fading = False
            if self._fade_anim:
                self._fade_anim.deleteLater()
                self._fade_anim = None
            self.close() # 使用 close() 触发 WA_DeleteOnClose
        anim.finished.connect(on_finished)
        self._fade_anim = anim
        anim.start()

def get_dialog_qss(scale_factor):
    """根据缩放因子生成对话框样式表"""
    return f"""
            QDialog {{
                background-color: #2E2E2E;
                border: {int(5 * scale_factor)}px solid #2E7D9B;
                border-radius: {int(8 * scale_factor)}px;
            }}
            QLabel {{
                font-size: {int(36 * scale_factor)}px;
                color: #FFFFFF;
                margin-bottom: {int(40 * scale_factor)}px;
                text-align: center;
            }}
            QPushButton {{
                background-color: #2E7D9B;
                color: white;
                border: none;
                padding: {int(20 * scale_factor)}px 0;
                font-size: {int(32 * scale_factor)}px;
                margin: 0;
                width: 100%;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #388e3c;
            }}
            QVBoxLayout {{
                margin: {int(40 * scale_factor)}px;
                spacing: 0;
            }}
            QHBoxLayout {{
                justify-content: center;
                spacing: 0;
            }}
        """
class ConfirmDialog(QDialog):
    def __init__(self, variable1, scale_factor=1.0, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.variable1 = variable1
        self.scale_factor = scale_factor
        self.setWindowTitle(self.tr("游戏确认"))
        # 添加 Qt.WindowStaysOnTopHint 确保对话框在 Overlay 之上
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setFixedSize(int(800 * self.scale_factor), int(400 * self.scale_factor))  # 更新后的固定尺寸
        self.setStyleSheet(get_dialog_qss(self.scale_factor))
        # 初始透明度为 0，使用动画淡入
        try:
            self.setWindowOpacity(0.0)
        except Exception:
            pass
        self._fade_anim = None
        self._is_fading = False
        
        # 创建覆盖层 - 不传 parent 给 super().__init__ 以免行为异常，但保留引用
        self.overlay = Overlay(self)
        
        self.init_ui()
        self.buttons = [self.cancel_button, self.confirm_button]
        if hasattr(self, 'shutdown_button'):
            self.buttons.append(self.shutdown_button)
        self.current_index = 1  # 默认选中第一个（取消）
        self.last_input_time = 0  # 最后一次处理输入的时间
        self.input_delay = 300  # 去抖延迟时间，单位：毫秒
        self.ignore_input_until = 0  # 忽略输入的时间戳
        self.update_highlight()  # 初始化时更新高亮状态

    def init_ui(self):
        layout = QVBoxLayout()

        # 显示提示文本
        self.label = QLabel(self.variable1)
        self.label.setAlignment(Qt.AlignCenter)  # 设置文本居中
        if "※" in self.variable1:
            self.label.setStyleSheet(f"font-size: {24 * self.scale_factor}px; color: #FFFFFF; margin-bottom: 40px; text-align: center;")
        layout.addWidget(self.label)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        # 取消按钮
        self.cancel_button = QPushButton(self.tr("取消"))
        self.cancel_button.clicked.connect(self.cancel_action)
        button_layout.addWidget(self.cancel_button)

        # 确认按钮
        self.confirm_button = QPushButton(self.tr("确认"))
        self.confirm_button.clicked.connect(self.confirm_action)
        button_layout.addWidget(self.confirm_button)

        # 特殊处理：关机确认时在右侧添加大按钮
        if self.variable1 == "要进入睡眠吗":
            self.shutdown_button = QPushButton(self.tr("立即关机"))
            self.shutdown_button.clicked.connect(self.shutdown_confirm_action)
            button_layout.addWidget(self.shutdown_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def shutdown_confirm_action(self):
        """立即关机的二次确认"""
        self.cancel_action()
        QTimer.singleShot(100, selector.shutdownnow)
    def confirm_action(self): 
        print("用户点击了确认按钮") 
        # 使用淡出动画后再 accept
        try:
            self.fade_out_and_accept()
        except Exception:
            self.accept()

    def cancel_action(self):
        print("用户点击了取消按钮")
        # 使用淡出动画后再 reject
        try:
            self.fade_out_and_reject()
        except Exception:
            self.reject()
    
    def showEvent(self, event):
        """窗口显示时的事件处理"""
        super().showEvent(event)
        try:
            self.fade_in()
        except Exception:
            pass
        self.ignore_input_until = pygame.time.get_ticks() + 350  # 打开窗口后1秒内忽略输入

    def closeEvent(self, event):
        """确保对话框关闭时，关联的覆盖层也被销毁"""
        try:
            # 停止并删除对话框动画
            if self._fade_anim:
                self._fade_anim.stop()
                self._fade_anim.deleteLater()
                self._fade_anim = None
            
            # 显式关闭覆盖层以释放全屏窗口内存 (20MB+)
            if hasattr(self, 'overlay') and self.overlay:
                # 如果覆盖层还在淡入淡出，强制其关闭
                try:
                    self.overlay.close()
                    self.overlay = None
                except Exception:
                    pass
        except Exception:
            pass
        super().closeEvent(event)

    def fade_in(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            
            # 先淡入覆盖层
            self.overlay.fade_in(duration)
            
            # 显示对话框并确保在覆盖层之上
            self.show()
            self.raise_()
            
            if self._fade_anim:
                self._fade_anim.stop()
                self._fade_anim.deleteLater()
            
            # 再淡入对话框
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: setattr(self, '_is_fading', False))
            self._fade_anim = anim
            anim.start()
        except Exception:
            pass

    def fade_out_and_accept(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            
            if self._fade_anim:
                self._fade_anim.stop()
                self._fade_anim.deleteLater()
            
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(self.windowOpacity())
            anim.setEndValue(0.0)
            def on_finished():
                try:
                    # 先淡出对话框，再淡出覆盖层
                    self.overlay.fade_out(duration)
                    self._is_fading = False
                    super(ConfirmDialog, self).accept()
                except Exception:
                    pass
            anim.finished.connect(on_finished)
            self._fade_anim = anim
            anim.start()
        except Exception:
            self.overlay.fade_out(duration)
            super(ConfirmDialog, self).accept()

    def fade_out_and_reject(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            
            if self._fade_anim:
                self._fade_anim.stop()
                self._fade_anim.deleteLater()
            
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(self.windowOpacity())
            anim.setEndValue(0.0)
            def on_finished():
                try:
                    # 先淡出对话框，再淡出覆盖层
                    self.overlay.fade_out(duration)
                    self._is_fading = False
                    super(ConfirmDialog, self).reject()
                except Exception:
                    pass
            anim.finished.connect(on_finished)
            self._fade_anim = anim
            anim.start()
        except Exception:
            try:
                self.overlay.fade_out(duration)
            except Exception:
                pass
            super(ConfirmDialog, self).reject()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        current_time = pygame.time.get_ticks()  # 获取当前时间（毫秒）
        # 如果在忽略输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
            return
        
        if event.key() in (Qt.Key_Left, Qt.Key_Up):
            self.current_index = max(0, self.current_index - 1)
            self.update_highlight()
        elif event.key() in (Qt.Key_Right, Qt.Key_Down):
            self.current_index = min(len(self.buttons) - 1, self.current_index + 1)
            self.update_highlight()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.buttons[self.current_index].click()
        # 更新最后一次按键时间
        self.last_input_time = current_time

    def handle_gamepad_input(self, action):
        """处理手柄输入"""
        current_time = pygame.time.get_ticks()  # 获取当前时间（毫秒）
        # 如果在忽略输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
            return
        if action in ('LEFT', 'UP'):
            self.current_index = max(0, self.current_index - 1)
            self.update_highlight()
        elif action in ('RIGHT', 'DOWN'):
            self.current_index = min(len(self.buttons) - 1, self.current_index + 1)
            self.update_highlight()
        elif action == 'A':
            self.buttons[self.current_index].click()
        elif action == 'B':
            self.cancel_action()
        # 更新最后一次按键时间
        self.last_input_time = current_time

    def update_highlight(self):
        """更新按钮高亮状态"""
        for index, button in enumerate(self.buttons):
            is_shutdown = hasattr(self, 'shutdown_button') and button == self.shutdown_button
            if index == self.current_index:
                if is_shutdown:
                    bg_color = "#f44336"  # 红色
                    border = "2px solid #ffffff"
                else:
                    bg_color = "#245A71"  # 深绿色
                    border = "1px solid #93ffff"
                
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_color};
                        color: white;
                        border: {border};
                        padding: 20px 0;
                        font-size: 32px;
                        margin: 0;
                        width: 100%;
                        font-weight: bold;
                    }}
                """)
            else:
                if is_shutdown:
                    bg_color = "#cd4040"  # 红色
                else:
                    bg_color = "#2E7D9B"  # 绿色
                
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_color};
                        color: white;
                        border: none;
                        padding: 20px 0;
                        font-size: 32px;
                        margin: 0;
                        width: 100%;
                    }}
                """)
class LoadingDialog(QDialog):
    """通用加载窗口，显示一条提示信息并保持在最上层。"""
    def __init__(self, message="加载中...", scale_factor=1.0, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.message = message
        self.scale_factor = scale_factor
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        #self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(int(800 * self.scale_factor), int(400 * self.scale_factor))  # 更新后的固定尺寸
        # 初始透明度为 0，使用动画淡入
        try:
            self.setWindowOpacity(0.0)
        except Exception:
            pass
        self._fade_anim = None
        self._is_fading = False
        
        # 创建覆盖层 - 不传 parent 给 super().__init__ 以免行为异常，但保留引用
        self.overlay = Overlay(self)
        
        self.init_ui()

    def init_ui(self):
        # 使样式与 ConfirmDialog 对齐
        self.setStyleSheet(get_dialog_qss(self.scale_factor))
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.label = QLabel(self.tr(self.message))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 24px; color: #FFFFFF;")
        layout.addWidget(self.label)
        # 添加无限加载进度条作为加载动画（不依赖外部资源）
        try:
            from PyQt5.QtWidgets import QProgressBar
            self.progress = QProgressBar()
            self.progress.setTextVisible(False)
            self.progress.setFixedHeight(int(10 * self.scale_factor))
            self.progress.setRange(0, 0)  # 不确定进度的忙碌指示器
            # 样式与对话框风格对齐
            self.progress.setStyleSheet("QProgressBar { background-color: rgba(255,255,255,0.06); border-radius: 5px; } QProgressBar::chunk { background-color: #2E7D9B; }")
            layout.addWidget(self.progress)
        except Exception:
            self.progress = None
        self.setLayout(layout)

    def showEvent(self, event):
        try:
            # 在显示时启用等待光标并淡入
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            except Exception:
                pass
            self.fade_in()
        except Exception:
            pass
        super().showEvent(event)

    def fade_in(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            
            # 先淡入覆盖层
            self.overlay.fade_in(duration)
            
            # 显示对话框并确保在覆盖层之上
            self.show()
            self.raise_()
            
            if self._fade_anim:
                self._fade_anim.stop()
                self._fade_anim.deleteLater()
            
            # 再淡入对话框
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: setattr(self, '_is_fading', False))
            self._fade_anim = anim
            anim.start()
        except Exception:
            pass

    def fade_out_and_close(self, duration=180):
        try:
            # 如果已有动画，则先停止它，确保可以强制开始淡出
            try:
                if self._fade_anim is not None:
                    self._fade_anim.stop()
                    self._fade_anim.deleteLater()
            except Exception:
                pass
            self._is_fading = True
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            try:
                start_val = float(self.windowOpacity())
            except Exception:
                start_val = 1.0
            anim.setStartValue(start_val)
            anim.setEndValue(0.0)
            def on_finished():
                try:
                    # 先淡出对话框，再淡出覆盖层
                    self.overlay.fade_out(duration)
                    self._is_fading = False
                    try:
                        QApplication.restoreOverrideCursor()
                    except Exception:
                        pass
                    super(LoadingDialog, self).close()
                except Exception:
                    pass
            anim.finished.connect(on_finished)
            self._fade_anim = anim
            anim.start()
        except Exception:
            try:
                # 淡出覆盖层
                self.overlay.fade_out(duration)
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            super(LoadingDialog, self).close()

    def close(self):
        # 强制使用淡出动画再真正关闭（停止任何正在进行的淡入）
        try:
            self.fade_out_and_close()
        except Exception:
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            super(LoadingDialog, self).close()

    def closeEvent(self, event):
        """确保对话框关闭时，清理动画并销毁关联的覆盖层"""
        try:
            # 停止并删除对话框动画
            if self._fade_anim:
                self._fade_anim.stop()
                self._fade_anim.deleteLater()
                self._fade_anim = None
            
            # 确保光标恢复
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            
            # 显式关闭覆盖层以释放全屏窗口内存 (20MB+)
            if hasattr(self, 'overlay') and self.overlay:
                try:
                    self.overlay.close()
                    self.overlay = None
                except Exception:
                    pass
        except Exception:
            pass
        super().closeEvent(event)

    def setMessage(self, msg):
        self.message = msg
        self.label.setText(msg)


class LaunchOverlay(QWidget):
    """启动游戏的悬浮窗"""
    class _ProcessCheckThread(QThread):
        """在后台检查指定可执行文件是否运行并返回内存使用情况，避免阻塞主线程。"""
        status_signal = pyqtSignal(bool, float)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.game_path = None
            self._running = True

        def run(self):
            while getattr(self, '_running', True):
                game_running = False
                memory_mb = 0.0
                try:
                    gp = self.game_path
                    if gp:
                        for process in psutil.process_iter(['pid', 'exe', 'memory_info']):
                            try:
                                exe = process.info.get('exe') or ''
                                if exe and exe.lower() == gp.lower():
                                    game_running = True
                                    memory_info = process.info.get('memory_info')
                                    if memory_info:
                                        memory_mb = memory_info.rss / (1024 * 1024)
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                continue
                except Exception:
                    pass

                try:
                    self.status_signal.emit(game_running, memory_mb)
                except Exception:
                    pass

                # sleep in short increments so stop() can be responsive
                for _ in range(5):
                    if not getattr(self, '_running', False):
                        break
                    QThread.msleep(100)

        def stop(self):
            self._running = False

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("launchOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)        
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.bg = QWidget(self)
        self.bg.setGeometry(0, 0, self.parent.width(), self.parent.height())
        self.bg.setAttribute(Qt.WA_StyledBackground, True)
        self.bg.setStyleSheet("background-color: rgba(46,46,46,230);")
        self.bg.show()
        self.bg.raise_()
        
        # 设置悬浮窗大小为父窗口大小
        self.setFixedSize(self.parent.size())
        
        # 使用绝对定位，不使用布局
        #self.setLayout(None) （会卡住）
        
        # 创建图片标签（用于封面动画）
        self.overlay_image = QLabel(self)
        self.overlay_image.setAlignment(Qt.AlignCenter)
        self.overlay_image.setScaledContents(False)
        self.overlay_image.hide()
        
        # 创建背景图片标签（用于放大后的背景）
        self.overlay_bg_image = QLabel(self)
        self.overlay_bg_image.setAlignment(Qt.AlignCenter)
        self.overlay_bg_image.setScaledContents(True)
        self.overlay_bg_image.hide()
        
        # 创建文本标签（启动文字）- 添加文字阴影效果
        self.overlay_text = QLabel(self)
        self.overlay_text.setAlignment(Qt.AlignCenter)
        # 改进文字样式：更大字体、文字阴影、更好的字体
        self.overlay_text.setStyleSheet(f"""
            font-size: {int(42 * self.parent.scale_factor)}px; 
            color: #EEEEEE; 
            background: transparent;
        """)
        # 添加文字阴影效果
        text_shadow = QtWidgets.QGraphicsDropShadowEffect(self.overlay_text)
        text_shadow.setBlurRadius(15)
        text_shadow.setXOffset(2)
        text_shadow.setYOffset(2)
        text_shadow.setColor(QColor(0, 0, 0, 180))
        self.overlay_text.setGraphicsEffect(text_shadow)
        self.overlay_text.hide()
        
        # 创建加载条 - 改进视觉效果
        self.overlay_progress = QProgressBar(self)
        self.overlay_progress.setTextVisible(False)
        progress_height = int(8 * self.parent.scale_factor)
        self.overlay_progress.setFixedHeight(progress_height)
        self.overlay_progress.setRange(0, 0)  # 不确定进度的忙碌指示器
        # 改进加载条样式：渐变、发光效果
        self.overlay_progress.setStyleSheet("""
            QProgressBar { 
                background-color: rgba(30, 30, 30, 0.8); 
                border: 2px solid rgba(100, 100, 100, 0.3);
                border-radius: 4px; 
            } 
            QProgressBar::chunk { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2E7D9B,
                    stop:0.5 #2E7D9B,
                    stop:1 #2E7D9B);
                border-radius: 2px;
            }
        """)
        # 添加发光效果
        progress_glow = QtWidgets.QGraphicsDropShadowEffect(self.overlay_progress)
        progress_glow.setBlurRadius(10)
        progress_glow.setXOffset(0)
        progress_glow.setYOffset(0)
        progress_glow.setColor(QColor(76, 175, 80, 100))
        self.overlay_progress.setGraphicsEffect(progress_glow)
        self.overlay_progress.hide()
        
        # 创建状态标签（右下角显示进程状态）- 添加背景和阴影
        self.overlay_status = QLabel(self)
        self.overlay_status.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        # 改进状态标签样式：半透明背景、圆角、阴影
        self.overlay_status.setStyleSheet(f"""
            font-size: {int(18 * self.parent.scale_factor)}px; 
            font-weight: 500;
            color: #E0E0E0; 
            background-color: rgba(20, 20, 20, 0.7);
            border-radius: {int(8 * self.parent.scale_factor)}px;
            padding: {int(12 * self.parent.scale_factor)}px {int(16 * self.parent.scale_factor)}px;
        """)
        # 添加状态标签阴影
        status_shadow = QtWidgets.QGraphicsDropShadowEffect(self.overlay_status)
        status_shadow.setBlurRadius(8)
        status_shadow.setXOffset(0)
        status_shadow.setYOffset(2)
        status_shadow.setColor(QColor(0, 0, 0, 150))
        self.overlay_status.setGraphicsEffect(status_shadow)
        self.overlay_status.hide()
        
        # 动画相关变量
        self.launch_animations = []
        self.status_timer = None
        self.focus_check_timer = None
        self._phase_timer = QTimer(self)
        self._phase_timer.setSingleShot(True)
        self._on_top_timer = QTimer(self)
        self._on_top_timer.setSingleShot(True)
        self._process_check_thread = None
        self.current_game_name = None
        self.current_game_path = None
        
        # 初始时隐藏
        self.hide()
    
    def hideEvent(self, event):
        """窗口隐藏时自动停止动画并释放资源，并销毁自身以节省内存"""
        self._stop_launch_animations()
        if hasattr(self.parent, 'launch_overlay') and self.parent.launch_overlay == self:
            self.parent.launch_overlay = None
        self.deleteLater()
        super().hideEvent(event)

    def mousePressEvent(self, event):
        """点击悬浮窗时隐藏"""
        self.hide()
    
    def show_launch_window(self, game_name, image_path):
        """显示启动游戏的悬浮窗"""
        # 停止之前的动画和定时器
        self._stop_launch_animations()
        
        # 保存游戏信息
        self.current_game_name = game_name
        # 查找游戏路径
        self.current_game_path = None
        for app in valid_apps:
            if app["name"] == game_name:
                self.current_game_path = app["path"]
                break
        
        # 重置所有组件状态
        self.setWindowOpacity(0.0)
        self.overlay_image.hide()
        self.overlay_bg_image.hide()
        self.overlay_text.hide()
        self.overlay_progress.hide()
        self.overlay_status.hide()
        
        # 获取父窗口大小
        parent_size = self.parent.size()
        parent_width = parent_size.width()
        parent_height = parent_size.height()
        
        # 更新悬浮窗大小
        self.setFixedSize(parent_width, parent_height)
        
        # 获取当前按钮位置（光标位置，参考4328行）
        start_pos = None
        if hasattr(self.parent, 'buttons') and self.parent.buttons and hasattr(self.parent, 'current_index'):
            try:
                current_button = self.parent.buttons[self.parent.current_index]
                # 获取按钮在父窗口中的位置
                button_pos = current_button.mapTo(self.parent, QPoint(0, 0))
                button_size = current_button.size()
                start_pos = QPoint(
                    button_pos.x() + button_size.width() // 2,
                    button_pos.y() + button_size.height() // 2
                )
            except Exception:
                pass
        
        # 如果没有找到按钮位置，使用屏幕中心
        if start_pos is None:
            start_pos = QPoint(parent_width // 2, parent_height // 2)
        
        # 目标位置（屏幕中心）
        target_x = parent_width // 2
        target_y = parent_height // 2
        
        # 根据图片比例计算封面尺寸
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 读取原始宽高，按比例缩放，目标宽度 400*scale_factor
                cover_width = int(400 * self.parent.scale_factor)
                cover_height = int(pixmap.height() * cover_width / pixmap.width())
            else:
                cover_width = int(400 * self.parent.scale_factor)
                cover_height = int(533 * self.parent.scale_factor)
        else:
            cover_width = int(400 * self.parent.scale_factor)
            cover_height = int(533 * self.parent.scale_factor)
        
        # 加载并设置封面图片
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                cover_width,
                cover_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.overlay_image.setPixmap(scaled_pixmap)
            # 设置初始位置和大小
            self.overlay_image.setGeometry(
                start_pos.x() - cover_width // 2,
                start_pos.y() - cover_height // 2,
                cover_width,
                cover_height
            )
            self.overlay_image.show()
        else:
            self.overlay_image.hide()
        
        # 设置文本
        self.overlay_text.setText(self.tr("正在启动 %1").replace('%1', game_name))
        text_width = int(1600 * self.parent.scale_factor)
        text_height = int(50 * self.parent.scale_factor)
        # 初始位置在屏幕下方中央
        self.overlay_text.setGeometry(
            (parent_width - text_width) // 2,
            parent_height - text_height - int(100 * self.parent.scale_factor),
            text_width,
            text_height
        )
        self.overlay_text.hide()
        
        # 设置加载条位置（底部）
        progress_width = int(800 * self.parent.scale_factor)
        progress_height = int(10 * self.parent.scale_factor)
        self.overlay_progress.setGeometry(
            (parent_width - progress_width) // 2,
            parent_height - progress_height - int(50 * self.parent.scale_factor),
            progress_width,
            progress_height
        )
        
        # 设置状态标签位置（右下角）
        status_width = int(400 * self.parent.scale_factor)
        status_height = int(60 * self.parent.scale_factor)
        self.overlay_status.setGeometry(
            parent_width - status_width - int(20 * self.parent.scale_factor),
            parent_height - status_height - int(20 * self.parent.scale_factor),
            status_width,
            status_height
        )
        
        # 将悬浮窗置于最上层并显示
        self.raise_()
        self.show()
        
        # 第一阶段：淡入悬浮窗
        self.overlay_text.setAlignment(Qt.AlignCenter)
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        self.launch_animations.append(fade_in)
        # 开始焦点监听
        self._start_focus_monitoring()
        
        def on_fade_in_finished():
            if not self.isVisible():
                return
            # 第二阶段：封面从光标位置移动到中央，同时添加缩放和变暗效果
            if self.overlay_image.isVisible():
                # 位置动画
                move_anim = QPropertyAnimation(self.overlay_image, b"pos")
                move_anim.setDuration(700)
                move_anim.setStartValue(QPoint(
                    start_pos.x() - cover_width // 2,
                    start_pos.y() - cover_height // 2
                ))
                move_anim.setEndValue(QPoint(
                    target_x - cover_width // 2,
                    target_y - cover_height // 2
                ))
                try:
                    from PyQt5.QtCore import QEasingCurve
                    move_anim.setEasingCurve(QEasingCurve.OutCubic)
                except Exception:
                    pass
                self.launch_animations.append(move_anim)
                
                # 缩放动画：从稍小到正常大小，增加层次感
                scale_anim = QPropertyAnimation(self.overlay_image, b"geometry")
                scale_anim.setDuration(700)
                start_rect = QRect(
                    start_pos.x() - cover_width // 2,
                    start_pos.y() - cover_height // 2,
                    int(cover_width * 0.8),  # 起始时稍小
                    int(cover_height * 0.8)
                )
                end_rect = QRect(
                    target_x - cover_width // 2,
                    target_y - cover_height // 2,
                    cover_width,
                    cover_height
                )
                scale_anim.setStartValue(start_rect)
                scale_anim.setEndValue(end_rect)
                try:
                    from PyQt5.QtCore import QEasingCurve
                    scale_anim.setEasingCurve(QEasingCurve.OutCubic)
                except Exception:
                    pass
                self.launch_animations.append(scale_anim)
                
                # 变暗效果：从完全不透明到半透明
                if not hasattr(self.overlay_image, 'opacity_effect'):
                    opacity_effect = QtWidgets.QGraphicsOpacityEffect(self.overlay_image)
                    self.overlay_image.setGraphicsEffect(opacity_effect)
                    self.overlay_image.opacity_effect = opacity_effect
                else:
                    opacity_effect = self.overlay_image.opacity_effect
                    opacity_effect.setOpacity(1.0)  # 重置为完全不透明
                
                dim_anim = QPropertyAnimation(opacity_effect, b"opacity")
                dim_anim.setDuration(700)
                dim_anim.setStartValue(1.0)
                dim_anim.setEndValue(0.6)  # 变暗到60%透明度，保持更好的可见性
                try:
                    from PyQt5.QtCore import QEasingCurve
                    dim_anim.setEasingCurve(QEasingCurve.OutCubic)
                except Exception:
                    pass
                self.launch_animations.append(dim_anim)
                
                # 同时启动所有动画
                move_anim.start()
                scale_anim.start()
                dim_anim.start()
                
                def on_move_finished():
                    if not self.isVisible():
                        return
                    # 第三阶段：文字淡入，同时从下方滑入
                    self.overlay_text.show()
                    
                    # 文字淡入效果
                    text_effect = QtWidgets.QGraphicsOpacityEffect(self.overlay_text)
                    self.overlay_text.setGraphicsEffect(text_effect)
                    text_fade_in = QPropertyAnimation(text_effect, b"opacity")
                    text_fade_in.setDuration(500)
                    text_fade_in.setStartValue(0.0)
                    text_fade_in.setEndValue(1.0)
                    try:
                        from PyQt5.QtCore import QEasingCurve
                        text_fade_in.setEasingCurve(QEasingCurve.OutCubic)
                    except Exception:
                        pass
                    self.launch_animations.append(text_fade_in)
                    
                    # 文字位置动画：从下方滑入
                    text_start_y = parent_height
                    text_end_y = parent_height - text_height - int(100 * self.parent.scale_factor)
                    text_pos_anim = QPropertyAnimation(self.overlay_text, b"pos")
                    text_pos_anim.setDuration(500)
                    text_pos_anim.setStartValue(QPoint(
                        (parent_width - text_width) // 2,
                        text_start_y
                    ))
                    text_pos_anim.setEndValue(QPoint(
                        (parent_width - text_width) // 2,
                        text_end_y
                    ))
                    try:
                        from PyQt5.QtCore import QEasingCurve
                        text_pos_anim.setEasingCurve(QEasingCurve.OutCubic)
                    except Exception:
                        pass
                    self.launch_animations.append(text_pos_anim)
                    
                    def on_text_fade_in_finished():
                        if not self.isVisible():
                            return
                        # 停留1秒后进入第四阶段
                        self._phase_timer.timeout.disconnect() if self._phase_timer.receivers(self._phase_timer.timeout) > 0 else None
                        self._phase_timer.timeout.connect(start_phase4)
                        self._phase_timer.start(800)
                    
                    text_fade_in.finished.connect(on_text_fade_in_finished)
                    text_fade_in.start()
                    text_pos_anim.start()
                
                # 使用scale_anim的完成信号，因为它是最后一个动画
                scale_anim.finished.connect(on_move_finished)
            else:
                # 如果没有图片，直接显示文字
                self.overlay_text.show()
                text_effect = QtWidgets.QGraphicsOpacityEffect(self.overlay_text)
                self.overlay_text.setGraphicsEffect(text_effect)
                text_fade_in = QPropertyAnimation(text_effect, b"opacity")
                text_fade_in.setDuration(400)
                text_fade_in.setStartValue(0.0)
                text_fade_in.setEndValue(1.0)
                self.launch_animations.append(text_fade_in)
                
                def on_text_fade_in_finished():
                    if not self.isVisible():
                        return
                    self._phase_timer.timeout.disconnect() if self._phase_timer.receivers(self._phase_timer.timeout) > 0 else None
                    self._phase_timer.timeout.connect(start_phase4)
                    self._phase_timer.start(1000)
                
                text_fade_in.finished.connect(on_text_fade_in_finished)
                text_fade_in.start()
        
        fade_in.finished.connect(on_fade_in_finished)
        fade_in.start()
        
        def start_phase4():
            """第四阶段：图片变暗放大做背景，文字移动到左上角，显示加载条和状态"""
            if not self.isVisible():
                return
            # 隐藏原封面图片（淡出效果）
            if self.overlay_image.isVisible():
                if hasattr(self.overlay_image, 'opacity_effect'):
                    fade_out = QPropertyAnimation(self.overlay_image.opacity_effect, b"opacity")
                    fade_out.setDuration(400)
                    fade_out.setStartValue(self.overlay_image.opacity_effect.opacity())
                    fade_out.setEndValue(0.0)
                    fade_out.finished.connect(lambda: self.overlay_image.hide())
                    fade_out.start()
                    self.launch_animations.append(fade_out)
                else:
                    self.overlay_image.hide()
            
            # 创建背景图片（变暗放大）- 添加渐变遮罩和模糊效果
            if image_path and os.path.exists(image_path):
                # 使用 PIL 进行模糊处理，因为 QGraphicsEffect 在同一个 Widget 上只能有一个，会被后面的淡入效果覆盖
                try:
                    pil_img = Image.open(image_path).convert("RGBA")
                    # 稍微放大一点以支持模糊边缘
                    scale_factor = 1.1
                    target_w = int(parent_width * scale_factor)
                    target_h = int(target_w * pil_img.height / pil_img.width)
                    pil_img = pil_img.resize((target_w, target_h), Image.LANCZOS)
                    # 添加高斯模糊
                    pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=25))
                    
                    # 转换为 QPixmap
                    data = pil_img.tobytes("raw", "RGBA")
                    qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_RGBA8888)
                    bg_scaled = QPixmap.fromImage(qimg)
                    
                    # 显式清理不再需要的 PIL 对象和数据，减少内存占用
                    del data
                    del qimg
                    pil_img.close()
                    del pil_img
                except Exception as e:
                    print(f"PIL Blur error: {e}")
                    bg_pixmap = QPixmap(image_path)
                    bg_scaled = bg_pixmap.scaled(
                        int(parent_width * 1.1),
                        int(parent_width * bg_pixmap.height() / bg_pixmap.width() * 1.1),
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation
                    )
                
                # 创建渐变遮罩效果（从顶部到底部逐渐变暗）
                dark_pixmap = QPixmap(bg_scaled.size())
                dark_pixmap.fill(Qt.transparent)
                painter = QPainter(dark_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # 先绘制原图
                painter.drawPixmap(0, 0, bg_scaled)
                
                # 添加整体变暗效果（半透明黑色遮罩）
                painter.fillRect(dark_pixmap.rect(), QColor(0, 0, 0, 150))
                
                # 添加渐变遮罩效果（从上往下进一步加深）
                linear_gradient = QLinearGradient(0, 0, 0, dark_pixmap.height())
                linear_gradient.setColorAt(0, QColor(0, 0, 0, 0))
                linear_gradient.setColorAt(1, QColor(0, 0, 0, 100))
                painter.fillRect(dark_pixmap.rect(), linear_gradient)
                painter.end()
                
                self.overlay_bg_image.setPixmap(dark_pixmap)
                # 居中显示
                bg_x = int((parent_width - dark_pixmap.width()) / 2)
                bg_y = int((parent_height - dark_pixmap.height()) / 2)
                self.overlay_bg_image.setGeometry(bg_x, bg_y, dark_pixmap.width(), dark_pixmap.height())
                
                # 淡入显示背景
                if not hasattr(self.overlay_bg_image, 'opacity_effect'):
                    bg_opacity = QtWidgets.QGraphicsOpacityEffect(self.overlay_bg_image)
                    self.overlay_bg_image.setGraphicsEffect(bg_opacity)
                    self.overlay_bg_image.opacity_effect = bg_opacity
                else:
                    bg_opacity = self.overlay_bg_image.opacity_effect
                
                bg_opacity.setOpacity(0.0)
                self.overlay_bg_image.show()
                
                bg_fade_in = QPropertyAnimation(bg_opacity, b"opacity")
                bg_fade_in.setDuration(600)
                bg_fade_in.setStartValue(0.0)
                bg_fade_in.setEndValue(1.0)
                try:
                    from PyQt5.QtCore import QEasingCurve
                    bg_fade_in.setEasingCurve(QEasingCurve.InOutCubic)
                except Exception:
                    pass
                bg_fade_in.start()
                self.launch_animations.append(bg_fade_in)
            
            # 文字移动到左上角
            text_effect = self.overlay_text.graphicsEffect()
            if text_effect:
                self.overlay_text.setGraphicsEffect(None)
            
            # 文字移动到左上角，同时缩小字体
            text_move = QPropertyAnimation(self.overlay_text, b"pos")
            text_move.setDuration(200)
            text_move.setStartValue(self.overlay_text.pos())
            text_move.setEndValue(QPoint(
                int(20 * self.parent.scale_factor),
                int(20 * self.parent.scale_factor)
            ))
            try:
                from PyQt5.QtCore import QEasingCurve
                text_move.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass
            self.launch_animations.append(text_move)
            # 去掉“正在启动”前缀，仅保留游戏名称
            current_text = self.overlay_text.text()
            if current_text.startswith(self.tr("正在启动 ")):
                current_text = current_text[5:]  # 去掉前5个字符
                self.overlay_text.setText(current_text)
                # 动画结束后设置为左对齐
                self.overlay_text.setAlignment(Qt.AlignLeft)

            font_size = int(14 * self.parent.scale_factor)
            self.overlay_text.setFont(QFont(self.overlay_text.font().family(), font_size))
            
            def on_text_move_finished():
                if not self.isVisible():
                    return
                # 显示加载条和状态（带淡入动画）
                # 将加载条放在状态标签底部（相对定位并做边界检测）
                status_geom = self.overlay_status.geometry()
                prog_w = max(int(300 * self.parent.scale_factor), status_geom.width())
                prog_h = max(int(8 * self.parent.scale_factor), self.overlay_progress.height() if self.overlay_progress else int(8 * self.parent.scale_factor))
                prog_x = status_geom.x() + max(0, (status_geom.width() - prog_w) // 2)
                prog_y = status_geom.y() + status_geom.height() + int(8 * self.parent.scale_factor)

                # 如果超出屏幕底部则向上调整到边界内
                if prog_y + prog_h > parent_height - int(10 * self.parent.scale_factor):
                    prog_y = parent_height - prog_h - int(10 * self.parent.scale_factor)

                # 应用几何并淡入显示加载条
                self.overlay_progress.setGeometry(prog_x, prog_y, prog_w, prog_h)
                if not hasattr(self.overlay_progress, 'opacity_effect'):
                    progress_opacity = QtWidgets.QGraphicsOpacityEffect(self.overlay_progress)
                    self.overlay_progress.setGraphicsEffect(progress_opacity)
                    self.overlay_progress.opacity_effect = progress_opacity
                else:
                    progress_opacity = self.overlay_progress.opacity_effect
                
                progress_opacity.setOpacity(0.0)
                self.overlay_progress.show()

                progress_fade = QPropertyAnimation(progress_opacity, b"opacity")
                progress_fade.setDuration(400)
                progress_fade.setStartValue(0.0)
                progress_fade.setEndValue(1.0)
                progress_fade.start()
                self.launch_animations.append(progress_fade)

                # 状态标签淡入（保持原位）
                if not hasattr(self.overlay_status, 'opacity_effect'):
                    status_opacity = QtWidgets.QGraphicsOpacityEffect(self.overlay_status)
                    self.overlay_status.setGraphicsEffect(status_opacity)
                    self.overlay_status.opacity_effect = status_opacity
                else:
                    status_opacity = self.overlay_status.opacity_effect
                
                status_opacity.setOpacity(0.0)
                self.overlay_status.show()

                status_fade = QPropertyAnimation(status_opacity, b"opacity")
                status_fade.setDuration(400)
                status_fade.setStartValue(0.0)
                status_fade.setEndValue(1.0)
                status_fade.start()
                self.launch_animations.append(status_fade)
                
                # 开始更新状态
                self._start_status_update()
            
            text_move.finished.connect(on_text_move_finished)
            text_move.start()
        
        # 保持窗口在最上层
        self.selection_count = 0
        def keep_on_top():
            if not self.isVisible():
                return
            self.raise_()
            self.selection_count += 1
            if self.selection_count < 200:  # 持续约30秒
                self._on_top_timer.timeout.disconnect() if self._on_top_timer.receivers(self._on_top_timer.timeout) > 0 else None
                self._on_top_timer.timeout.connect(keep_on_top)
                self._on_top_timer.start(150)
        
        # 初始调用
        keep_on_top()
    
    def _stop_launch_animations(self):
        """停止所有启动动画并回收资源"""
        # 停止并删除所有动画
        for anim in self.launch_animations:
            try:
                anim.stop()
                anim.deleteLater()
            except Exception:
                pass
        self.launch_animations.clear()
        
        # 释放图片资源
        try:
            self.overlay_image.setPixmap(QPixmap())
            self.overlay_bg_image.setPixmap(QPixmap())
            
            # 清除所有缓存的特效，因为特效内部可能引用了大型 pixmap
            for widget in [self.overlay_image, self.overlay_bg_image, self.overlay_progress, self.overlay_status, self.overlay_text]:
                if hasattr(widget, 'opacity_effect'):
                    widget.setGraphicsEffect(None)
                    delattr(widget, 'opacity_effect')
                else:
                    widget.setGraphicsEffect(None)
        except Exception:
            pass

        if self.status_timer:
            self.status_timer.stop()
            self.status_timer = None
        
        if self.focus_check_timer:
            self.focus_check_timer.stop()
            self.focus_check_timer = None
        
        if hasattr(self, '_phase_timer'):
            self._phase_timer.stop()
        if hasattr(self, '_on_top_timer'):
            self._on_top_timer.stop()

        # 停止并删除后台进程检查线程
        if getattr(self, '_process_check_thread', None):
            try:
                # 先断开所有信号连接
                try:
                    self._process_check_thread.status_signal.disconnect()
                except Exception:
                    pass
                self._process_check_thread.stop()
                self._process_check_thread.wait(500)
                # 显式从父对象中移除
                self._process_check_thread.setParent(None)
                self._process_check_thread.deleteLater()
            except Exception:
                pass
            self._process_check_thread = None
        
        # 显式调用垃圾回收 (可选，但对于处理大型图像数据有帮助)
        import gc
        gc.collect()
    
    def _start_status_update(self):
        """开始更新游戏进程状态"""
        if not self.current_game_path:
            return

        # 如果已有后台检查线程，先停止它
        if getattr(self, '_process_check_thread', None):
            try:
                self._process_check_thread.stop()
                self._process_check_thread.wait(500)
            except Exception:
                pass
            self._process_check_thread = None

        # 启动后台线程进行进程检查，避免在主线程中使用 psutil 导致卡顿
        self._process_check_thread = self._ProcessCheckThread(self)
        self._process_check_thread.game_path = self.current_game_path

        def on_status(game_running, memory_mb):
            if not self.isVisible():
                return
            try:
                status_text = self.tr("运行中 | 已载入: %1 MB").replace('%1', f"{memory_mb:.0f}") if game_running else self.tr("正在启动")
                self.overlay_status.setText(status_text)
            except Exception:
                self.overlay_status.setText(self.tr("状态未知"))

        self._process_check_thread.status_signal.connect(on_status)
        self._process_check_thread.start()
    
    def _start_focus_monitoring(self):
        """开始监听焦点变化"""
        def check_focus():
            if not self.isVisible():
                if self.focus_check_timer:
                    self.focus_check_timer.stop()
                return
            
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    # 检查是否是游戏窗口（不是GSHWND）
                    if hwnd != GSHWND:
                        # 焦点从GSHWND切换到窗口，关闭悬浮窗
                        if not settings.get("skip_minimize_on_game_open", False):
                            self.parent.hide_window()
                        self.hide()
                        self._stop_launch_animations()
                        return
            except Exception:
                pass
        
        # 每0.2秒检查一次焦点
        self.focus_check_timer = QTimer(self)
        self.focus_check_timer.timeout.connect(check_focus)
        self.focus_check_timer.start(200)


class SunshineAppManagerThread(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, args=None, parent=None):
        super().__init__(parent)
        self.args = args if args else []

    def run(self):
        # 支持传入启动参数
        # 检查 SunshineAppManager.exe 是否存在
        if not os.path.exists("SunshineAppManager.exe"):
            print("SunshineAppManager.exe 未找到，无法执行。")
            # 弹窗告知用户
            QMessageBox.warning(None, QApplication.translate("Simplenite", "提示"), QApplication.translate("Simplenite", "未找到 SunshineAppManager.exe，无法执行相关操作。"))
            self.finished_signal.emit()
            return
        # 构建命令行参数，正确拼接每个参数
        cmdline = "SunshineAppManager.exe " + " ".join(f"\"{str(arg)}\"" for arg in self.args)

        try:
            # 检查是否使用同级权限启动
            if settings.get("use_peer_level_launch", False):
                try:
                    print(f"以同级权限启动: {cmdline}")
                    proc = subprocess.Popen(["SunshineAppManager.exe"])
                    proc.wait()  # 等待进程完成
                    print("SunshineAppManager.exe 已结束")
                    self.finished_signal.emit()
                    return
                except Exception as e:
                    print(f"同级权限启动失败 {e}，尝试使用当前用户权限启动")
            
            try:
                proc_info = win32process.CreateProcessAsUser(
                    EXPLORERTOKEN,
                    None,
                    cmdline,
                    None,
                    None,
                    False,
                    win32con.CREATE_NEW_PROCESS_GROUP,
                    None,
                    None,
                    win32process.STARTUPINFO()
                )

                process_handle = proc_info[0]

                while True:
                    exit_code = win32process.GetExitCodeProcess(process_handle)
                    if exit_code != win32con.STILL_ACTIVE:
                        break
                    time.sleep(0.1)

                print("SunshineAppManager.exe 已结束")
            except Exception as e:
                error_code = getattr(e, 'winerror', None)
                if error_code == 1314:  # ERROR_PRIVILEGE_NOT_HELD
                    _enable_peer_level_launch()
                    QMessageBox.warning(None, QApplication.translate("Simplenite", "权限提示（可能需要重新进入软件）"), QApplication.translate("Simplenite", "CreateProcessAsUser 失败（权限不足）。已启用同级权限启动模式规避此问题，可前往应用设置-开发者选项查看该选项详情"))
                    try:
                        print(f"以同级权限启动: {cmdline}")
                        proc = subprocess.Popen(["SunshineAppManager.exe"])
                        proc.wait()  # 等待进程完成
                        print("SunshineAppManager.exe 已结束")
                    except Exception as retry_e:
                        print(f"同级权限启动失败: {retry_e}")
                else:
                    print(f"CreateProcessAsUser 错误 (错误码{error_code}): {e}")

        except Exception as e:
            print(f"SunshineAppManagerThread error: {e}")
        self.finished_signal.emit()

class GameSelector(QWidget):
    def __init__(self):
        global play_reload, GSHWND
        super().__init__()
        _install_debug_output_redirect()
        self.back_start_pressed_time = None  # 初始化按键按下时间
        self.back_start_action = set()
        self.is_mouse_simulation_running = False
        self.ignore_input_until = 0  # 初始化防抖时间戳

        # 初始化翻译器
        self.translator = QTranslator()
        self._apply_language(language)

        # 初始化QShortcut，用于在应用程序有焦点时捕获快捷键
        self.shortcut = None
        self.update_shortcut()

        self.current_section = 0  # 0=游戏选择区域，1=控制按钮区域
        GSHWND = int(self.winId())
        self.setWindowIcon(QIcon('./_internal/fav.ico'))
        self.setWindowOpacity(0.0)  # 透明度为0
        self.more_section = 0  # 0=主页面，1=更多页面
        self.setWindowTitle(self.tr("Simplenite"))
        QApplication.setFont(QFont("Microsoft YaHei"))  # 设置字体为微软雅黑
        # 获取屏幕的分辨率
        screen = QDesktopWidget().screenGeometry()
        # 设置窗口大小为屏幕分辨率
        self.resize(1, 1)  # 初始设置为1x1，后续会调整为全屏
        self.setWindowFlags(Qt.FramelessWindowHint)  # 全屏无边框
        self.setStyleSheet("background-color: transparent;")
        self.background_label = QLabel(self)
        self.background_label.setScaledContents(True)
        self.background_label.setGeometry(self.rect())
        self.background_label.setStyleSheet("background-color: transparent;")
        self.background_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.background_label.lower()

        self.background_overlay = QWidget(self)
        self.background_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.background_overlay.setGeometry(self.rect())
        self.background_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.background_overlay.lower()  # 确保背景覆盖层在背景标签下方

        self.killexplorer = settings.get("killexplorer", False)
        self.freeze = settings.get("freeze", False)
        self.debug_output_window = DebugOutputWindow()
        _attach_debug_output_window(self.debug_output_window)
        self.apply_debug_output_setting()
        self.freezeapp = None
        self.winTaskbar = TaskbarWindow()
        if self.killexplorer == True and STARTUP == False:
            self.wintaskbarshow()
        self.showFullScreen()
        # 确保窗口捕获焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.activateWindow()
        self.raise_()
        if STARTUP:
            hwnd = int(self.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0=SW_HIDE
        self.resize(screen.width(), screen.height()) # 设置窗口大小为屏幕分辨率
        # 调整窗口大小后立即更新背景覆盖层的几何信息
        if hasattr(self, 'background_overlay'):
            self.background_overlay.setGeometry(self.rect())
        
        # 初始化缩放因子
        self.scale_factor = 1.0  # 初始缩放因子，将由 resizeEvent / 初始化逻辑更新
        self.scale_factor2 = self.scale_factor * 2  # 用于按钮和图像的缩放因数
        
        # 缩放参数（事件驱动模式）
        self.base_height = 1080
        self.min_scale = 0.45
        self.max_scale = 2.5
        self.precision = 2
        self.threshold = 0.01

        # 立即根据屏幕高度计算并应用初始缩放，避免启动时因 widget 几何尚未准备好导致尺寸异常
        try:
            raw = float(screen.height()) / float(self.base_height)
            initial_scale = round(raw, self.precision)
            initial_scale = max(self.min_scale, min(initial_scale, self.max_scale))
            # 使用事件驱动更新一次初始缩放
            try:
                self.on_scale_factor_updated(initial_scale)
            except Exception:
                self.scale_factor = initial_scale
                self.scale_factor2 = self.scale_factor * 2
        except Exception:
            pass
        # 游戏索引和布局
        self.player = {}
        self.current_index = 0  # 从第一个按钮开始
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(int(20 * self.scale_factor))  # 设置按钮之间的间距
        # 需要选择进程的游戏列表（内存变量，不写入硬盘）
        self.need_select_process = []

        # 从设置中读取 row_count，如果不存在则使用默认值
        self.row_count = settings.get("row_count", 6)  # 每行显示的按钮数量

        # 从设置中读取主页游戏数量，如果不存在则使用默认值
        self.buttonsindexset = settings.get("buttonsindexset", 12)

        # 创建顶部布局
        self.top_layout = QHBoxLayout()
        self.top_layout.setContentsMargins(int(20 * self.scale_factor), 0, int(20 * self.scale_factor), 0)  # 添加左右边距

        # 创建左侧布局（用于"更多"按钮）
        self.left_layout = QHBoxLayout()
        self.left_layout.setAlignment(Qt.AlignLeft)

        # 创建中间布局（用于游戏标题）
        self.center_layout = QHBoxLayout()
        self.center_layout.setAlignment(Qt.AlignCenter)

        # 创建右侧布局（用于收藏和退出按钮）
        self.right_layout = QHBoxLayout()
        self.right_layout.setAlignment(Qt.AlignRight)

        # 创建计时器用于控制按钮显示时间
        self.button_timer = QTimer(self)
        self.button_timer.setSingleShot(True)
        self.button_timer.timeout.connect(self.hide_all_buttons)

        # 按钮原始文本
        self.button_texts = {
            'more': self.tr('工具'),
            'favorite': self.tr('收藏'),
            'quit': self.tr('最小化'),
            'screenshot': self.tr('游戏详情')
        }
        # 创建更多按钮
        self.more_button = QPushButton("*")
        self.more_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.more_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: none;
                color: #888888;
                font-size: {int(16 * self.scale_factor)}px;
            }}
        """)
        self.more_button.clicked.connect(self.on_button_clicked)
        self.more_button.clicked.connect(self.show_more_window)

        # 添加收藏按钮
        self.favorite_button = QPushButton("*")
        self.favorite_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.favorite_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: none;
                color: #888888;
                font-size: {int(16 * self.scale_factor)}px;
            }}
        """)
        self.favorite_button.clicked.connect(self.on_button_clicked)
        self.favorite_button.clicked.connect(self.on_favorite_button_clicked)

        # 创建退出按钮
        self.quit_button = QPushButton("*")
        self.quit_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.quit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: none;
                color: #888888;
                font-size: {int(16 * self.scale_factor)}px;
            }}
        """)
        self.quit_button.clicked.connect(self.on_button_clicked)
        self.quit_button.clicked.connect(self.exitbutton)

        # 新增：截图按钮
        self.screenshot_button = QPushButton("*")
        self.screenshot_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.screenshot_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: none;
                color: #888888;
                font-size: {int(16 * self.scale_factor)}px;
            }}
        """)
        self.screenshot_button.clicked.connect(self.on_button_clicked)
        self.screenshot_button.clicked.connect(self.open_selected_game_screenshot)

        # 创建游戏标题标签
        sorted_games = self.sort_games()
        if sorted_games:  # 检查是否有游戏
            self.game_name_label = QLabel(sorted_games[self.current_index]["name"])
        else:
            self.game_name_label = QLabel(self.tr("没有找到游戏"))  # 显示提示信息
        
        self.game_name_label.setAlignment(Qt.AlignCenter)
        self.game_name_label.setStyleSheet(f"""
            QLabel {{
                color: #1e1e1e;
                font-size: {int(20 * self.scale_factor)}px;
                font-weight: bold;
                padding: 0 {int(20 * self.scale_factor)}px;
            }}
        """)
        # 创建时间显示标签
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {int(25 * self.scale_factor)}px;
                padding-top: {int(10 * self.scale_factor)}px;
                padding-bottom: {int(10 * self.scale_factor)}px;
                padding-right: {int(20 * self.scale_factor)}px;
            }}
        """)
        self.update_time()  # 初始化时间显示
        self.right_layout.addWidget(self.time_label)  # 添加到右侧布局，在 quit_button 之前
        # 添加收藏按钮到左侧布局
        self.right_layout.addWidget(self.favorite_button)
        # 将按钮和标签添加到对应的布局
        self.left_layout.addWidget(self.more_button)
        self.center_layout.addWidget(self.game_name_label)
        self.right_layout.addWidget(self.quit_button)

        # 设置定时器每秒更新一次时间
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
        # 将三个布局添加到顶部布局
        self.top_layout.addLayout(self.left_layout, 1)  # stretch=1
        self.top_layout.addLayout(self.center_layout, 2)  # stretch=2，让中间部分占据更多空间
        self.top_layout.addLayout(self.right_layout, 1)  # stretch=1

        # 创建悬浮窗
        self.floating_window = None
        # 添加游戏按钮
        self.buttons = []
        if sorted_games:  # 只在有游戏时添加按钮
            for index, game in enumerate(sorted_games[:self.buttonsindexset]):
                button = self.create_game_button(game, index)
                #self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)    #由self.buttonsindexset和sorted_games的长度决定是否要添加更多按钮（暂时不做
                self.grid_layout.addWidget(button, 0, index)
                self.buttons.append(button)
            
            # 添加"更多"按钮
            if len(sorted_games) > self.buttonsindexset:
                more_button = QPushButton("🟦🟦\n🟦🟦")
                more_button.setFont(QFont("Microsoft YaHei", 40))
                more_button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                more_button.clicked.connect(self.switch_to_all_software)  # 绑定"更多"按钮的功能
                self.grid_layout.addWidget(more_button, 0, len(sorted_games[:self.buttonsindexset]))  # 添加到最后一列
                self.buttons.append(more_button)

        else:
            # 添加一个提示按钮
            no_games_button = QPushButton(self.tr("∑(°口°๑) ‌‌库中无游戏(っ°Д°;)っ\n点击此处开启库管理工具进行添加"))
            no_games_button.setFixedSize(int(700 * self.scale_factor), int(200 * self.scale_factor))
            no_games_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2e2e2e; 
                    border-radius: {int(10 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #444444;
                    color: white;
                    font-size: {int(30 * self.scale_factor)}px;
                }}
            """)
            no_games_button.clicked.connect(self.addgamebutton)  # 绑定"更多"按钮的功能
            self.grid_layout.addWidget(no_games_button, 0, 0)
            self.buttons.append(no_games_button)

        # 获取排序后的游戏列表
        sorted_games = self.sort_games()
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        main_layout.setSpacing(0)  # 设置间距为0
        main_layout.addLayout(self.top_layout)  # 添加顶部布局
        main_layout.setAlignment(Qt.AlignTop)

        # 创建一个新的布局容器用于放置游戏按钮网格
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(int(320 * self.scale_factor *2.4))  # 设置高度为90% 
        self.scroll_area.setFixedWidth(int(self.width()))  # 设置宽度为100%
        self.scroll_area.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        # 启用触摸滑动手势
        QScroller.grabGesture(self.scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self.update_additional_game_name_label_position)
        # 垂直的self.scroll_area.verticalScrollBar().valueChanged.connect(self.update_additional_game_name_label_position)

        # 隐藏滚动条和边框
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                width: 0px;
                height: 0px;
            }
        """)

        # 创建一个 QWidget 作为滚动区域的容器
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        # 将滚动区域添加到主布局
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)
        self.load_background_image()

        # 启动游戏运行状态监听线程
        self.play_reload = False
        self.play_lock = threading.Lock()
        self.play_app_name = []
        self.monitor_thread = MonitorRunningAppsThread(self.play_lock, self.play_app_name)
        self.monitor_thread.play_app_name_signal.connect(self.update_play_app_name)  # 连接信号到槽
        self.monitor_thread.play_reload_signal.connect(self.handle_reload_signal)  # 连接信号到槽
        # 当前台可见窗口数量发生变化时，刷新后台窗口列表以即时更新按钮
        try:
            self.monitor_thread.background_windows_changed.connect(self.update_background_buttons)
        except Exception:
            pass
        self.monitor_thread.start() 
        
        # 初始化启动游戏的悬浮窗（延迟创建，关闭后销毁）
        self.launch_overlay = None
        
        # 启动手柄输入监听线程
        self.controller_thread = GameControllerThread(self)
        self.controller_thread.gamepad_signal.connect(self.handle_gamepad_input)
        self.controller_thread.start()

        # 按键去抖的间隔时间（单位：毫秒）
        self.last_input_time = 0  # 最后一次处理输入的时间
        self.input_delay = 200  # 去抖延迟时间，单位：毫秒

        # 添加悬浮窗开关防抖
        self.last_window_toggle_time = 0
        self.window_toggle_delay = 300  # 设置300毫秒的防抖延迟

        # 将按钮添加到左侧布局
        self.left_layout.addWidget(self.screenshot_button)

        # 初始化时隐藏悬浮窗
        self.control_buttons = []
        # 初始化后台任务相关变量
        self.background_windows = []  # 存储后台窗口信息
        self.background_app_index = 0  # 后台应用的当前显示起始索引
        self.show_background_apps = False  # 是否显示全部后台应用
        self.texta_layout = None  # 保存对 texta_layout 的引用
        self.extra_buttons_container = None  # 额外按钮容器
        # 初始化 control_layout
        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(int(50 * self.scale_factor))  # 设置按钮之间的间距
        # 创建一个 QWidget 作为容器
        control_widget = QWidget()
        control_widget.setLayout(self.control_layout)
        
        # 设置最大宽度为屏幕宽度的 75%
        max_width = int(screen.width()*0.75)
        control_widget.setMaximumWidth(max_width)
        # 创建一个水平布局用于居中显示
        centered_layout = QHBoxLayout()
        centered_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        centered_layout.setSpacing(0)  # 设置间距为0
        centered_layout.addStretch()  # 左侧弹性空间
        centered_layout.addWidget(control_widget)  # 添加控制按钮容器
        centered_layout.addStretch()  # 右侧弹性空间
        # 将居中布局添加到主布局
        main_layout.addLayout(centered_layout)
        main_layout.setSpacing(0)  # 设置主布局的间距为0
        # 创建7个圆形按钮
        self.control_button_modes = {}  # 存储每个按钮的当前模式
        for i in range(7):
            btn = QPushButton()
            btn.setFixedSize(int(125 * self.scale_factor), int(125 * self.scale_factor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(87, 87, 87, 0.45);
                    border-radius: 62%;
                    font-size: {int(40 * self.scale_factor)}px; 
                    border: {int(5 * self.scale_factor)}px solid rgba(40, 40, 40, 0.9);
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.12);
                }}
                QPushButton:checked {{
                    background-color: rgba(69, 160, 73, 0.85);
                    border: {int(6 * self.scale_factor)}px solid rgba(255, 255, 0, 0.9);
                }}
            """)
            # 记录模式并统一连接到点击处理器，处理器会实现"第一次点击只聚焦，第二次执行"逻辑
            if i == 0 or i == 1 or i == 2 or i == 3:
                # 前3个按钮为后台任务切换按钮
                self.control_button_modes[i] = 'background'
            elif i == 4:
                self.control_button_modes[i] = 'image'
                btn.setText("🗺️")
            elif i == 5:
                self.control_button_modes[i] = 'settings'
                btn.setText("⚙️")
            elif i == 6:
                self.control_button_modes[i] = 'sleep'
                btn.setText("💤")
            # 统一使用本类处理器，以支持首次点击只聚焦的行为
            btn.clicked.connect(lambda checked=False, idx=i: self.handle_control_button_click(idx))
            self.control_buttons.append(btn)
            self.control_layout.addWidget(btn)
        
        # 将控制区域添加到主布局
        main_layout.addLayout(self.control_layout)
        # 创建分割线和文字布局
        divider_layout = QHBoxLayout()
        divider_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        divider_layout.setSpacing(0)  # 设置间距为0
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setFixedHeight(int(4 * self.scale_factor))  # 设置分割线高度
        divider.setStyleSheet("""
            background-color: #444444;  /* 设置背景颜色 */
            border: none;              /* 移除边框 */
        """)
        divider_layout.addWidget(divider)
        
        # 包装分割线布局到 QWidget
        divider_widget = QWidget()
        divider_widget.setLayout(divider_layout)
        
        # 创建文字布局
        texta_layout = QHBoxLayout()
        texta_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        texta_layout.setSpacing(0)  # 设置控件之间的间距为0
        
        # 左侧文字
        self.left_label = QLabel(self.tr("🎮️未连接手柄"))
        self.left_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei"; 
                color: white;
                font-size: {int(25 * self.scale_factor)}px;
                padding-bottom: {int(10 * self.scale_factor)}px;
                padding-left: {int(50 * self.scale_factor)}px;
            }}
        """)
        texta_layout.addWidget(self.left_label, alignment=Qt.AlignLeft)
        # 保存对 texta_layout 的引用，用于添加额外的后台应用按钮
        self.texta_layout = texta_layout
        self.extra_buttons_container = None
        # 连接手柄连接信号到槽函数
        self.controller_thread.controller_connected_signal.connect(self.update_controller_status)
        # 连接手柄断开信号到槽函数
        self.controller_thread.controller_disconnected_signal.connect(self.on_controller_disconnected)
        # 连接手柄错误信号到槽函数
        self.controller_thread.controller_error_signal.connect(self.on_controller_error)
        for controller_data in self.controller_thread.controllers.values():
            controller_name = controller_data['controller'].get_name()
            self.update_controller_status(controller_name)
        # 右侧文字
        self.right_label = QLabel(
            self.tr(
                "A / 进入游戏        Y / 关闭游戏        X / 鼠标模拟        ≡ / 游戏菜单            📦️Simplenite v%1"
            ).replace("%1", APP_VERSION)
        )
        self.right_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei"; 
                color: white;
                font-size: {int(25 * self.scale_factor)}px;
                padding-bottom: {int(10 * self.scale_factor)}px;
                padding-right: {int(50 * self.scale_factor)}px;
            }}
        """)
        texta_layout.addWidget(self.right_label, alignment=Qt.AlignRight)
        
        # 包装文字布局到 QWidget
        texta_widget = QWidget()
        texta_widget.setLayout(texta_layout)
        
        # 创建一个垂直布局，将分割线和文字布局组合
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(divider_widget)
        bottom_layout.addWidget(texta_widget)
        
        # 包装到一个 QWidget 中
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_layout)
        
        # 将底部布局添加到主布局，并设置对齐方式为底部
        main_layout.addWidget(bottom_widget, alignment=Qt.AlignBottom)
        # 初始化完成后立即高亮第一个项目
        self.update_highlight()
        #if STARTUP:
        #    # 设置窗口标志，使其不在任务栏显示
        #    self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        #    # 重新显示窗口以应用新的窗口标志
        #    self.show()
        #    # 立即隐藏窗口
        #    self.hide()
        #    # 延迟一小段时间以确保窗口完全初始化
        #    QTimer.singleShot(100, self.hide)
        # 在 GameSelector 的 __init__ 方法中添加以下代码
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("./_internal/fav.ico"))  # 设置托盘图标为 fav.ico
        self.tray_icon.setToolTip("Simplenite")
        def build_tray_menu():
            # 重用已有的 QMenu 实例以避免重复创建导致的资源和状态问题
            if hasattr(self, '_tray_menu') and isinstance(self._tray_menu, QMenu):
                tray_menu = self._tray_menu
                try:
                    tray_menu.clear()
                except Exception:
                    # 如果清理失败则重建菜单
                    tray_menu = QMenu(self)
                    self._tray_menu = tray_menu
            else:
                tray_menu = QMenu(self)
                self._tray_menu = tray_menu
            sorted_games = self.sort_games()
            # 缓存已解析图标，避免重复解析
            if not hasattr(self, "_icon_cache"):
                self._icon_cache = {}

            # 辅助：从文件或可执行中提取图标，优先用 icoextract 提取 exe/dll 图标，否则尝试作为图片加载
            def _icon_from_file(fp, size=24):
                try:
                    key = os.path.abspath(fp) if fp else ""
                except Exception:
                    key = str(fp)
                # 缓存命中直接返回
                if key and key in self._icon_cache:
                    return self._icon_cache[key]
                icon = QIcon()
                try:
                    from icoextract import IconExtractor
                    extractor = IconExtractor(fp)
                    bio = extractor.get_icon(num=0)
                    data = bio.getvalue()
                    pix = QPixmap()
                    if pix.loadFromData(data):
                        pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        icon = QIcon(pix)
                except Exception:
                    # 忽略 icoextract 失败，继续尝试作为图片加载
                    pass
                if icon.isNull():
                    try:
                        pix = QPixmap(fp)
                        if not pix.isNull():
                            pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            icon = QIcon(pix)
                    except Exception:
                        pass
                # 保存到缓存（即使是空图标也缓存，避免重复尝试）
                try:
                    if key:
                        self._icon_cache[key] = icon
                except Exception:
                    pass
                return icon

            # 辅助：解析可能含参数或是快捷方式的启动路径，返回可用的 exe 路径或目录
            def _resolve_exec_path(raw_path):
                if not raw_path:
                    return raw_path
                p = raw_path.strip()
                candidate = None
                if p.startswith('"'):
                    m = re.match(r'^\"([^\"]+)\"', p)
                    if m:
                        candidate = m.group(1)
                if not candidate:
                    exts = ['.exe', '.lnk', '.bat', '.cmd', '.com', '.ps1']
                    lower = p.lower()
                    for ext in exts:
                        idx = lower.find(ext)
                        if idx != -1:
                            candidate = p[:idx + len(ext)]
                            break
                if not candidate:
                    candidate = p.split(' ')[0]
                candidate = candidate.strip('"')
                if os.path.exists(candidate):
                    return candidate
                if candidate.lower().endswith('.lnk'):
                    try:
                        from win32com.client import Dispatch
                        shell = Dispatch('WScript.Shell')
                        shortcut = shell.CreateShortCut(candidate)
                        target = shortcut.Targetpath
                        if target and os.path.exists(target):
                            return target
                    except Exception:
                        pass
                if os.path.isdir(candidate):
                    try:
                        for fname in os.listdir(candidate):
                            if fname.lower().endswith('.exe'):
                                cand = os.path.join(candidate, fname)
                                if os.path.exists(cand):
                                    return cand
                    except Exception:
                        pass
                return candidate

            if sorted_games:
                tray_menu.addSeparator()
                for idx, game in enumerate(reversed(sorted_games[:self.buttonsindexset])):
                    icon = QIcon()
                    exec_path_raw = game.get("path", "")
                    if not exec_path_raw:
                        try:
                            for v in valid_apps:
                                if v.get("name") == game.get("name") and v.get("path"):
                                    exec_path_raw = v.get("path")
                                    break
                        except Exception:
                            pass

                    exec_path = _resolve_exec_path(exec_path_raw)
                    exists_flag = os.path.exists(exec_path) if exec_path else False
                    if exec_path and exists_flag:
                        icon = _icon_from_file(exec_path, 24)
                    if icon.isNull():
                        image_path = game.get("image-path", "")
                        if image_path and not os.path.isabs(image_path):
                            image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
                        icon = _icon_from_file(image_path, 24)

                    text = game["name"][:24] + "..." if len(game["name"]) > 24 else game["name"]
                    game_action = tray_menu.addAction(icon, text)
                    # 使用默认参数捕获索引，避免闭包问题
                    game_index = len(sorted_games[:self.buttonsindexset]) - 1 - idx
                    game_action.triggered.connect(lambda checked=False, i=game_index: (self.tray_icon.contextMenu().hide(), self.launch_game(i)))
            tray_menu.addSeparator()
            # 新增“工具”子菜单
            tools_menu = QMenu(self.tr("工具"), self)
            tools_menu.setStyleSheet("""
                QMenu, QMenu::item {
                    color: white;
                    background-color: #232323;
                }
                QMenu::item:selected,
                QMenu QMenu::item:selected {
                    color: black;
                    background-color: #93ffff;
                }
            """)
            for app in more_apps:
                icon = QIcon()
                path = app.get("path", "")
                if path and os.path.exists(path):
                    icon = _icon_from_file(path, 24)
                if icon.isNull():
                    image_path = app.get("image-path", "")
                    if image_path and not os.path.isabs(image_path):
                        image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
                    icon = _icon_from_file(image_path, 24)

                text = app.get("name", "")
                tool_action = tools_menu.addAction(icon, text)
                def launch_tool(checked=False, path=app.get("path", "")):
                    self.hide_window()
                    if isinstance(path, str) and path.strip():
                        run_as_user(path)
                tool_action.triggered.connect(launch_tool)
            tray_menu.addMenu(tools_menu)
            tray_menu.addSeparator()
            restart_action = tray_menu.addAction(self.tr("重启程序"))
            restart_action.triggered.connect(self.restart_program)
            restore_action = tray_menu.addAction(self.tr("导入新游戏"))
            restore_action.triggered.connect(self.addandrefresh_games)
            exit_action = tray_menu.addAction(self.tr("退出"))
            exit_action.triggered.connect(self.exitdef)
            tray_menu.setStyleSheet("""
                QMenu, QMenu::item {
                    color: white;
                    background-color: #232323;
                }
                QMenu::item:selected,
                QMenu QMenu::item:selected {
                    color: black;
                    background-color: #93ffff;
                }
            """)
            return tray_menu

        # 初始菜单（构建并设置菜单）
        self._tray_menu = build_tray_menu()
        self.tray_icon.setContextMenu(self._tray_menu)

        def tray_icon_activated(reason):
            if reason == QSystemTrayIcon.Context:  # 右键
                self._tray_menu = build_tray_menu()
                self.tray_icon.setContextMenu(self._tray_menu)
            elif reason == QSystemTrayIcon.Trigger:  # 左键
                if self.is_mouse_simulation_running:
                    self.is_mouse_simulation_running = False
                    return
                self.show_window()
                if self.killexplorer == True:
                    self.wintaskbarshow()

        self.tray_icon.activated.connect(tray_icon_activated)
        self.tray_icon.show()  # 显示托盘图标
        # 新增：每分钟记录游玩时间
        self.play_time_timer = QTimer(self)
        self.play_time_timer.timeout.connect(self.update_play_time)
        self.play_time_timer.start(60 * 1000)  # 60秒
        # ==============================
        # 控制按钮标签和缩略图初始化
        # ==============================
        self._current_control_button_label = None
        self._current_control_button_thumbnail = None
        self._label_fade_anims = []
        
        # ==============================
        # 键盘覆盖层（整合键盘逻辑至 GameSelector）
        # ==============================
        self.keyboard_overlay = None
        self.keyboard_overlay_mapping = None
        self.keyboard_overlay_thread = None
        # 键盘覆盖层内部状态（按需初始化）
        self._kb_rb_last_pressed = False
        self._kb_left_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_right_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_last_outer_time = {'left': 0, 'right': 0}
        self._kb_last_zone = {'left': 'dead', 'right': 'dead'}
        self._kb_inner_ignore_until = {'left': 0, 'right': 0}
        self._kb_last_x_pressed = [False, False]
        self._kb_last_a_pressed = [False, False]
        self._kb_last_b_pressed = [False, False]
        self._kb_last_y_pressed = [False, False]
        # 每个摇杆的最后一次发送按键时间（用于去抖，避免 time.sleep 导致阻塞和重复）
        self._kb_last_key_time = [0.0, 0.0]
        # 记录上次 hat / dpad 状态，和按键是否仍为按下（用于 keyDown/keyUp）
        self._kb_last_hat = [(0, 0), (0, 0)]
        self._kb_last_dpad = [
            {'up': False, 'down': False, 'left': False, 'right': False},
            {'up': False, 'down': False, 'left': False, 'right': False}
        ]
        self._kb_last_fkey_move_time = 0
        self._kb_ignore_start_until = 0
        
        # 初始化后台窗口信息并更新按钮
        self.update_background_buttons()
        
        # 启动时的淡入动画（如果不是静默启动）
        if not STARTUP:
            self._startup_anim = QPropertyAnimation(self, b"windowOpacity", self)
            self._startup_anim.setStartValue(0.0) # 透明度为0
            self._startup_anim.setEndValue(1.0)
            self._startup_anim.setDuration(400) # 启动动画
            try:
                from PyQt5.QtCore import QEasingCurve
                self._startup_anim.setEasingCurve(QEasingCurve.OutCubic)
            except Exception:
                pass
            self._startup_anim.start()
            
        # ==============================
    
    def shutdownnow(self):
        self.confirm_dialog = ConfirmDialog(self.tr("确定立即关机吗？"), self.scale_factor)
        if self.confirm_dialog.exec_():
            if ADMIN:
                os.system("shutdown /s /t 0")
            else:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "shutdown", "/s /t 0", None, 1)

    def update_shortcut(self):
        """更新快捷键设置：支持应用内 QShortcut 回退，同时使用 Windows RegisterHotKey 注册全局热键。

        行为：
        - 取消并删除原有的 QShortcut（如果存在）
        - 注销已注册的全局热键
        - 从 set.json 读取 home_page_hotkey（如 "Ctrl+Alt+H"）并尝试注册为全局热键
        - 在注册成功时通过原生事件过滤器接收 WM_HOTKEY 并触发 `show_window()`
        """
        # 取消旧的 QShortcut（只在应用内生效的快捷键）
        try:
            if self.shortcut:
                try:
                    self.shortcut.setEnabled(False)
                except Exception:
                    pass
                self.shortcut = None
        except Exception:
            pass

        # 注销先前通过 RegisterHotKey 注册的全局热键（如果有）
        try:
            self.unregister_all_hotkeys()
        except Exception:
            pass

        # 从设置中获取快捷键字符串
        try:
            with open('set.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
            hotkey = settings.get("home_page_hotkey", None)
        except Exception:
            hotkey = None

        # 如果未配置全局热键，则保留原有行为（可选创建应用内 QShortcut）
        if not hotkey:
            return

        # 确保已安装原生事件过滤器以接收 WM_HOTKEY
        try:
            self._ensure_hotkey_filter_installed()
        except Exception as e:
            print(f"安装原生事件过滤器失败: {e}")

        # 注册全局热键
        try:
            ok, hid = self.register_global_hotkey(hotkey)
            if ok:
                print(f"全局热键注册成功: {hotkey} (id={hid})")
            else:
                print(f"全局热键注册失败: {hotkey}")
        except Exception as e:
            print(f"注册全局热键异常: {e}")

    def _ensure_hotkey_filter_installed(self):
        """安装一个 QAbstractNativeEventFilter，用于捕获 WM_HOTKEY 并调用 _on_hotkey_triggered。"""
        try:
            if getattr(self, '_hotkey_filter_installed', False):
                return
            from PyQt5.QtCore import QAbstractNativeEventFilter, QCoreApplication
            import ctypes
            # 常量
            WM_HOTKEY = 0x0312

            class _HotkeyFilter(QAbstractNativeEventFilter):
                def __init__(self, parent):
                    super().__init__()
                    self._parent = parent

                def nativeEventFilter(self, eventType, message):
                    # 仅处理 Windows 消息
                    if eventType != 'windows_generic_MSG':
                        return False, 0
                    try:
                        # message 是一个指向 MSG 结构体的指针
                        msg = ctypes.wintypes.MSG.from_address(int(message))
                        if msg.message == WM_HOTKEY:
                            hid = int(msg.wParam)
                            try:
                                self._parent._on_hotkey_triggered(hid)
                            except Exception:
                                pass
                            return True, 0
                    except Exception:
                        pass
                    return False, 0

            self._hotkey_filter = _HotkeyFilter(self)
            from PyQt5.QtCore import QCoreApplication
            QCoreApplication.instance().installNativeEventFilter(self._hotkey_filter)
            self._hotkey_filter_installed = True
        except Exception:
            # 失败则继续不阻塞主流程
            self._hotkey_filter_installed = False

    def register_global_hotkey(self, hotkey_str):
        """解析 hotkey_str（例如 'Ctrl+Alt+H'）并调用 RegisterHotKey。返回 (success, id)。"""
        try:
            import ctypes
            import re
            from ctypes import wintypes

            MOD_ALT = 0x0001
            MOD_CONTROL = 0x0002
            MOD_SHIFT = 0x0004
            MOD_WIN = 0x0008

            def _parse(s):
                s = (s or '').replace('＋', '+')
                parts = [p.strip() for p in s.split('+') if p.strip()]
                mods = 0
                key = None
                for p in parts:
                    low = p.lower()
                    if low in ('ctrl', 'control'):
                        mods |= MOD_CONTROL
                    elif low in ('alt',):
                        mods |= MOD_ALT
                    elif low in ('shift',):
                        mods |= MOD_SHIFT
                    elif low in ('win', 'windows'):
                        mods |= MOD_WIN
                    else:
                        key = p
                if not key:
                    return mods, None
                k = key.upper()
                # F1-F24
                m = re.match(r'^F(\d{1,2})$', k)
                if m:
                    n = int(m.group(1))
                    if 1 <= n <= 24:
                        return mods, 0x70 + n - 1
                # 单字符字母/数字
                if len(k) == 1:
                    return mods, ord(k)
                # 常用特殊键
                special = {
                    'SPACE': 0x20, 'ENTER': 0x0D, 'TAB': 0x09, 'ESC': 0x1B,
                    'BACKSPACE': 0x08, 'INSERT':0x2D, 'DELETE':0x2E, 'HOME':0x24,
                    'END':0x23, 'PGUP':0x21, 'PGDN':0x22, 'LEFT':0x25, 'UP':0x26,
                    'RIGHT':0x27, 'DOWN':0x28
                }
                return mods, special.get(k.upper(), None)

            mods, vk = _parse(hotkey_str)
            if vk is None:
                return False, None

            if not hasattr(self, '_next_hotkey_id'):
                self._next_hotkey_id = 1
            hid = self._next_hotkey_id
            self._next_hotkey_id += 1

            # 使用 NULL HWND（线程级注册），消息会投递到线程消息队列，nativeEventFilter 可捕获
            if ctypes.windll.user32.RegisterHotKey(None, hid, mods, vk):
                if not hasattr(self, '_registered_hotkeys'):
                    self._registered_hotkeys = {}
                self._registered_hotkeys[hid] = (mods, vk, hotkey_str)
                return True, hid
            else:
                return False, None
        except Exception as e:
            print(f"register_global_hotkey 异常: {e}")
            return False, None

    def unregister_all_hotkeys(self):
        """注销本进程中已注册的所有全局热键并清理注册表。"""
        try:
            import ctypes
            if hasattr(self, '_registered_hotkeys') and self._registered_hotkeys:
                for hid in list(self._registered_hotkeys.keys()):
                    try:
                        ctypes.windll.user32.UnregisterHotKey(None, int(hid))
                    except Exception:
                        pass
                self._registered_hotkeys = {}
        except Exception:
            pass

    def _on_hotkey_triggered(self, hotkey_id):
        """全局热键触发回调（由 native event filter 调用）。"""
        try:
            self.guide_run()
        except Exception:
            pass

    def closeEvent(self, event):
        # 程序退出或窗口关闭时注销热键并移除事件过滤器
        try:
            try:
                self.unregister_all_hotkeys()
            except Exception:
                pass
            if getattr(self, '_hotkey_filter_installed', False):
                try:
                    from PyQt5.QtCore import QCoreApplication
                    QCoreApplication.instance().removeNativeEventFilter(self._hotkey_filter)
                except Exception:
                    pass
                self._hotkey_filter_installed = False
        except Exception:
            pass
        try:
            super().closeEvent(event)
        except Exception:
            event.accept()
    def wintaskbarshow(self):
        hide_desktop_icons()
        hide_taskbar()
        self.winTaskbar.show()
    def update_additional_game_name_label_position(self):
        """在滚动时同步更新additional_game_name_label的位置"""
        if (
            hasattr(self, 'additional_game_name_label')
            and isinstance(self.additional_game_name_label, QLabel)
            and self.current_section == 0
            and self.more_section == 0
            and self.buttons
            and 0 <= self.current_index < len(self.buttons)
        ):
            current_button = self.buttons[self.current_index]
            button_width = current_button.width()
            button_pos = current_button.mapToGlobal(QPoint(0, 0))
            self.additional_game_name_label.move(
                button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2,
                button_pos.y() - self.game_name_label.height() - 20
            )

    def resizeEvent(self, event):
        """在窗口尺寸变化时更新依赖宽度的控件布局和位置。"""
        try:
            # 根据高度变化计算新的缩放因子（事件驱动覆盖原来的轮询逻辑）
            try:
                # 优先使用 frameGeometry 以包含窗口装饰
                current_h = int(self.frameGeometry().height())
            except Exception:
                current_h = int(self.height())
            try:
                raw = float(current_h) / float(getattr(self, 'base_height', 1080))
                new_scale = round(raw, getattr(self, 'precision', 2))
                new_scale = max(getattr(self, 'min_scale', 0.45), min(new_scale, getattr(self, 'max_scale', 2.5)))
                if abs(new_scale - getattr(self, 'scale_factor', 0)) >= getattr(self, 'threshold', 0.01):
                    # 使用现有的更新函数统一处理样式与布局更新
                    try:
                        self.on_scale_factor_updated(new_scale)
                    except Exception:
                        self.scale_factor = new_scale
                        self.scale_factor2 = self.scale_factor * 2
            except Exception:
                pass

            w = int(self.width())
            if hasattr(self, 'background_label'):
                try:
                    self.background_label.setGeometry(self.rect())
                except Exception:
                    pass
            if hasattr(self, 'background_overlay'):
                try:
                    self.background_overlay.setGeometry(self.rect())
                except Exception:
                    pass
            if hasattr(self, 'scroll_area'):
                try:
                    self.scroll_area.setFixedWidth(w)
                except Exception:
                    pass

            # 调整控制区的最大宽度（control_layout 的容器）
            try:
                if hasattr(self, 'control_layout'):
                    control_widget = self.control_layout.parentWidget()
                    if control_widget:
                        control_widget.setMaximumWidth(int(self.width() * 0.75))
            except Exception:
                pass

            # 重新定位可能依赖按钮位置的标签
            try:
                self.update_additional_game_name_label_position()
            except Exception:
                pass
            
            # 调整ScreenshotWindow的大小和位置（如果它存在）
            try:
                if hasattr(self, 'screenshot_window') and self.screenshot_window.isVisible():
                    # 先关闭旧窗口
                    try:
                        self.screenshot_window.close()
                    except Exception:
                        pass
                    # 创建新窗口
                    self.screenshot_window = ScreenshotWindow(self)
                    self.screenshot_window.show()
            except Exception:
                pass
            try:
                if hasattr(self, "debug_output_window") and self.debug_output_window:
                    self.debug_output_window.position_top_left()
            except Exception:
                pass
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            return
    def animate_scroll(self, orientation, target_value, duration=150):
        """平滑滚动到目标值。orientation: 'horizontal' 或 'vertical'。保留动画引用以防被回收。"""
        try:
            if orientation == 'horizontal':
                scrollbar = self.scroll_area.horizontalScrollBar()
            else:
                scrollbar = self.scroll_area.verticalScrollBar()
            start = scrollbar.value()
            if start == int(target_value):
                return
            anim = QPropertyAnimation(scrollbar, b"value")
            anim.setDuration(duration)
            anim.setStartValue(start)
            anim.setEndValue(int(target_value))
            try:
                from PyQt5.QtCore import QEasingCurve
                anim.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass
            if not hasattr(self, '_scroll_animations'):
                self._scroll_animations = []
            self._scroll_animations.append(anim)
            def _on_finished():
                try:
                    self._scroll_animations.remove(anim)
                    anim.deleteLater()
                except Exception:
                    pass
            anim.finished.connect(_on_finished)
            anim.start()
        except Exception:
            try:
                if orientation == 'horizontal':
                    self.scroll_area.horizontalScrollBar().setValue(int(target_value))
                else:
                    self.scroll_area.verticalScrollBar().setValue(int(target_value))
            except Exception:
                pass
    def animate_scroll_area_transition(self, new_height, show_controls=True, duration=180):
        """对 `self.scroll_area` 做淡出 -> 调整高度/显示控制按钮 -> 淡入 的过渡动画。
        new_height: 目标高度（像素）；show_controls: 切换后是否显示控制按钮。
        保留动画引用以防被垃圾回收。
        """
        try:
            # 确保有 opacity effect
            effect = self.scroll_area.graphicsEffect()
            if not isinstance(effect, QtWidgets.QGraphicsOpacityEffect):
                effect = QtWidgets.QGraphicsOpacityEffect(self.scroll_area)
                self.scroll_area.setGraphicsEffect(effect)
            # 淡出
            fade_out = QPropertyAnimation(effect, b"opacity")
            fade_out.setDuration(int(duration * 0.6))
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            try:
                from PyQt5.QtCore import QEasingCurve
                fade_out.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass
            # 淡入
            fade_in = QPropertyAnimation(effect, b"opacity")
            fade_in.setDuration(int(duration * 0.6))
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            try:
                from PyQt5.QtCore import QEasingCurve
                fade_in.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass

            # 保持引用
            if not hasattr(self, '_scroll_area_fade_anims'):
                self._scroll_area_fade_anims = []
            self._scroll_area_fade_anims.extend([fade_out, fade_in])
            try:
                fade_out.setParent(self)
                fade_in.setParent(self)
            except Exception:
                pass

            # 仅在本函数创建 effect 时，后续在动画完成后移除该 effect，避免影响外部已设置的 effect
            created_effect = False
            try:
                if self.scroll_area.graphicsEffect() is effect:
                    # 如果我们刚刚创建并设置了 effect，则标记为可清理
                    created_effect = True
            except Exception:
                created_effect = False

            def _after_fade_out():
                try:
                    # 调整高度并切换控制按钮
                    self.scroll_area.setFixedHeight(int(new_height))
                    self.toggle_control_buttons(show_controls)
                    # 触发界面重载以应用变化
                    try:
                        self.reload_interface()
                    except Exception:
                        pass
                except Exception:
                    pass
                # 开始淡入
                fade_in.start()

            def _after_fade_in():
                try:
                    # 如果是本函数创建的临时 effect，则移除它，避免影响后续动画或样式
                    if created_effect:
                        try:
                            # 移除 effect 并清理引用
                            self.scroll_area.setGraphicsEffect(None)
                        except Exception:
                            pass
                finally:
                    # 清理动画引用
                    try:
                        if fade_in in self._scroll_area_fade_anims:
                            self._scroll_area_fade_anims.remove(fade_in)
                            fade_in.deleteLater()
                    except Exception:
                        pass

            def _cleanup_fade_out():
                try:
                    if fade_out in self._scroll_area_fade_anims:
                        self._scroll_area_fade_anims.remove(fade_out)
                        fade_out.deleteLater()
                except Exception:
                    pass

            fade_out.finished.connect(_after_fade_out)
            fade_in.finished.connect(_after_fade_in)
            fade_out.finished.connect(_cleanup_fade_out)
            fade_out.start()
        except Exception:
            # 如果失败则回退到直接切换
            try:
                self.scroll_area.setFixedHeight(int(new_height))
                self.toggle_control_buttons(show_controls)
                self.reload_interface()
            except Exception:
                pass
    def startopenmaobackup(self, sysargv, game_name, exe_path):
        # 检查是否已有maobackup.exe进程在运行
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'maobackup.exe':
                    # 弹窗询问是否关闭
                    self.confirm_dialog = ConfirmDialog("maobackup已经启动，是否要关闭？", scale_factor=self.scale_factor)
                    result = self.confirm_dialog.exec_()
                    if result == QDialog.Accepted:
                        proc.terminate()
                        proc.wait()
                    else:
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        if os.path.exists(exe_path):
            process = QProcess(self)
            process.setProgram(exe_path)
            process.setArguments([sysargv, game_name])
            process.setProcessChannelMode(QProcess.MergedChannels)
            buffer = b''

            def handle_ready_read():
                nonlocal buffer
                buffer += process.readAllStandardOutput().data()
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        msg = json.loads(line.decode(errors='ignore'))
                        if msg.get("type") in ("error", "info", "warning"):
                            self.confirm_dialog = ConfirmDialog("※"+msg.get("message", ""), scale_factor=self.scale_factor)
                            result = self.confirm_dialog.exec_()
                        elif msg.get("type") == "confirm":
                            self.confirm_dialog = ConfirmDialog("※"+msg.get("message", ""))
                            result = self.confirm_dialog.exec_()
                            process.write(("yes\n" if result == QDialog.Accepted else "no\n").encode())
                            process.waitForBytesWritten(100)
                    except Exception as e:
                        print("解析JSON失败：", e)

            def handle_finished(exitCode, exitStatus):
                # 可在此处理进程结束后的逻辑
                pass

            process.readyReadStandardOutput.connect(handle_ready_read)
            process.finished.connect(handle_finished)
            process.start()
        else:
            self.confirm_dialog = ConfirmDialog(self.tr("未找到maobackup.exe"), scale_factor=self.scale_factor).exec_()
    def deep_reload_games(self):
        """深度刷新游戏库：重新读取apps.json并刷新界面"""
        load_apps()  # 重新加载有效应用列表
        self.reload_interface()

    def update_play_time(self):
        """每分钟记录当前活动窗口为游戏时的游玩时间"""
        if "play_time" not in settings:
            settings["play_time"] = {}

        try:
            hwnd = win32gui.GetForegroundWindow()
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            exe_name = os.path.basename(exe_path).lower()
        except Exception as e:
            print(f"获取活动窗口进程失败: {e}")
            return

        # 遍历当前运行的游戏名
        for game_name in self.player:
            print(f"检查游戏: {game_name}")
            # 在 valid_apps 里查找对应游戏的 exe
            for app in valid_apps:
                print(f"  valid_apps项: name={app.get('name')}, path={app.get('path')}")
                if app.get("name") == game_name:
                    game_exe = os.path.basename(app.get("path", "")).lower()
                    print(f"    匹配到游戏，game_exe={game_exe}, 当前窗口exe={exe_name}")
                    if game_exe and game_exe == exe_name:
                        print(f"    活动窗口是该游戏，累计时间+1分钟")
                        settings["play_time"][game_name] = settings["play_time"].get(game_name, 0) + 1
                        try:
                            with open(settings_path, "w", encoding="utf-8") as f:
                                json.dump(settings, f, indent=4)
                        except Exception as e:
                            print(f"保存游玩时间失败: {e}")
                        return  # 只记录一个游戏
    def open_selected_game_screenshot(self):
        current_time = pygame.time.get_ticks()
        self.ignore_input_until = current_time + 500
        if not hasattr(self, 'screenshot_window'):
            self.screenshot_window = ScreenshotWindow(self)
        # 获取当前选中的游戏名
        sorted_games = self.sort_games()
        #self.screenshot_window.clear_filter()
        if sorted_games and 0 <= self.current_index < len(sorted_games):
            game_name = sorted_games[self.current_index]["name"]
        else:
            game_name = None
        self.screenshot_window.show()
        self.screenshot_window.disable_left_panel_switch = False
        self.screenshot_window.current_index = 0
        self.screenshot_window.current_button_index = 0  # 当前焦点按钮索引
        self.screenshot_window.in_left_panel = True     # 是否在左侧按钮区域
        self.screenshot_window.load_all_images = False  # 不加载所有图片，仅加载前6个图片
        self.screenshot_window.update_left_panel_button_styles()
        if game_name:
            self.screenshot_window.start_filter_mode(game_name=game_name)
    def show_img_window(self):
        current_time = pygame.time.get_ticks()
        self.ignore_input_until = current_time + 500
        if not hasattr(self, 'screenshot_window'):
            self.screenshot_window = ScreenshotWindow(self)
        self.screenshot_window.disable_left_panel_switch = True 
        self.screenshot_window.current_index = 0
        self.screenshot_window.in_left_panel = False     # 是否在左侧按钮区域
        self.screenshot_window.load_all_images = True   # 加载所有图片
        self.screenshot_window.clear_filter()
        self.screenshot_window.show()
    def update_time(self):
        """更新时间显示"""
        current_time = QDateTime.currentDateTime().toString(" HH : mm   dddd")
        # 判断网络状态
        is_connected = ctypes.windll.wininet.InternetGetConnectedState(None, 0)
        network_status = "🛜" if is_connected else "✈️"
        text = f"{current_time}    {network_status}"
        if settings.get("show_battery", False):
            try:
                b = psutil.sensors_battery()
                if b is not None and b.percent is not None:
                    icon = "⚡" if getattr(b, "power_plugged", False) else ""
                    text = f"{text}    {int(b.percent)}%{icon}"
            except Exception:
                pass
        self.time_label.setText(text)
    def show_window(self):
        """显示窗口"""
        # 先设置透明度为0，避免闪烁
        self.setWindowOpacity(0.0) # 透明度为0
        ctypes.windll.user32.ShowWindow(GSHWND, 9) # 9=SW_RESTORE            
        ctypes.windll.user32.SetForegroundWindow(GSHWND)
        
        # 创建淡入动画
        self._show_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._show_anim.setStartValue(0.0) # 透明度为0
        self._show_anim.setEndValue(1.0)
        self._show_anim.setDuration(200) # 200ms
        try:
            from PyQt5.QtCore import QEasingCurve
            self._show_anim.setEasingCurve(QEasingCurve.OutCubic)
        except Exception:
            pass
        self._show_anim.start()
        self.update_highlight()

    def exitbutton(self):
        """退出按钮"""
        if self.more_section == 1:
            self.switch_to_main_interface()
        else:
            self.hide_window()

    def on_button_clicked(self):
        """按钮点击事件处理"""
        # 显示所有按钮的原始文本和边框
        self.more_button.setText(self.button_texts['more'])
        self.favorite_button.setText(self.button_texts['favorite'])
        self.quit_button.setText(self.button_texts['quit'])
        self.screenshot_button.setText(self.button_texts['screenshot'])
        
        # 为所有按钮设置显示样式
        button_style = f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #555555;
            }}
        """
        
        self.more_button.setStyleSheet(button_style)
        self.favorite_button.setStyleSheet(button_style)
        self.quit_button.setStyleSheet(button_style)
        self.screenshot_button.setStyleSheet(button_style)
        
        # 重启计时器
        self.button_timer.stop()
        self.button_timer.start(4000)  # 4秒后隐藏

    def hide_all_buttons(self):
        """隐藏所有按钮的边框并显示灰色横杠"""
        # 隐藏所有按钮的边框并显示灰色横杠
        self.more_button.setText("*")
        self.favorite_button.setText("*")
        self.quit_button.setText("*")
        self.screenshot_button.setText("*")
        
        # 为所有按钮设置隐藏样式
        hidden_style = f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: none;
                color: #888888;
                font-size: {int(16 * self.scale_factor)}px;
            }}
        """
        
        self.more_button.setStyleSheet(hidden_style)
        self.favorite_button.setStyleSheet(hidden_style)
        self.quit_button.setStyleSheet(hidden_style)
        self.screenshot_button.setStyleSheet(hidden_style)

    def hide_window(self):
        """隐藏窗口"""
        # 创建淡出动画
        self._hide_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._hide_anim.setStartValue(self.windowOpacity())
        self._hide_anim.setEndValue(0.0) # 透明度为0
        self._hide_anim.setDuration(200) # 200ms
        try:
            from PyQt5.QtCore import QEasingCurve
            self._hide_anim.setEasingCurve(QEasingCurve.InCubic)
        except Exception:
            pass
            
        def on_finished():
            self.current_index = 0
            self.current_section = 0
            self.update_highlight()
            if getattr(self, 'show_background_apps', False):  # 仅在处于后台应用模式时恢复
                self.restore_control_buttons()
            hwnd = int(self.winId())
            if settings.get("keep_on_taskbar_when_minimized", False):
                ctypes.windll.user32.ShowWindow(hwnd, 6)  # 6=SW_MINIMIZE
            else:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0=SW_HIDE
            # 恢复透明度
            self.setWindowOpacity(1.0)
            
        self._hide_anim.finished.connect(on_finished)
        self._hide_anim.start()
    def on_favorite_button_clicked(self):
        if getattr(self, 'current_section', 0) == 1 and getattr(self, 'more_section', 0) == 0:
            idx = getattr(self, 'current_index', 0)
            btn = None
            if hasattr(self, 'control_buttons') and 0 <= idx < len(self.control_buttons):
                btn = self.control_buttons[idx]
            if btn and hasattr(btn, 'window_info') and btn.window_info:
                info = btn.window_info
                app_title = info.get('title') or info.get('exe_name')
                self.confirm_dialog = ConfirmDialog(self.tr("是否关闭下列窗口？\n%1").replace('%1', app_title), scale_factor=self.scale_factor)
                result = self.confirm_dialog.exec_()
                self.ignore_input_until = pygame.time.get_ticks()
                if result != QDialog.Accepted:
                    return
                try:
                    hwnd = info.get('hwnd')
                    if hwnd and win32gui.IsWindow(hwnd):
                        try:
                            win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, 0)
                        except Exception:
                            pass
                        # try:
                        #     win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        # except Exception:
                        #     pass
                        start_time = time.time()
                        while True:
                            QApplication.processEvents()
                            time.sleep(0.05)
                            exists = False
                            try:
                                exists = win32gui.IsWindow(hwnd)
                            except Exception:
                                exists = False
                            if not exists:
                                break
                            if time.time() - start_time > 5:
                                break
                        QTimer.singleShot(100, self.update_highlight)
                except Exception:
                    pass
                else:
                    self.update_background_buttons()
                return
            return
        self.toggle_favorite()
    def switch_to_all_software(self):
        """切换到"所有软件"界面"""
        self.scale_factor2 = self.scale_factor  # 用于按钮和图像的缩放因数
        self.current_index = 0
        self.more_section = 1
        # 使用淡出过渡动画改变 scroll_area 大小并隐藏控制按钮
        try:
            target_h = int(self.height() * 0.85)
            self.animate_scroll_area_transition(target_h, show_controls=False, duration=200)
        except Exception:
            self.scroll_area.setFixedHeight(int(self.height() * 0.85))
            self.toggle_control_buttons(False)
            self.reload_interface()
    def switch_to_main_interface(self):
        """切换到主界面"""
        self.scale_factor2 = self.scale_factor * 2  # 用于按钮和图像的缩放因数
        self.current_section = 0
        self.current_index = 0
        self.more_section = 0
        target_h = int(320 * self.scale_factor * 2.4)
        try:
            self.animate_scroll_area_transition(target_h, show_controls=True, duration=200)
        except Exception:
            self.scroll_area.setFixedHeight(target_h)
            self.toggle_control_buttons(True)
            self.reload_interface()

    def toggle_control_buttons(self, show):
        """显示或隐藏控制按钮"""
        for btn in self.control_buttons:
            btn.setVisible(show)
        if hasattr(self, 'control_layout'):
            self.control_layout.setEnabled(show)
            # 获取control_layout所在的容器widget
            control_widget = self.control_layout.parentWidget()
            if control_widget:
                control_widget.setVisible(show)
            # 获取centered_layout
            for i in range(self.layout().count()):
                item = self.layout().itemAt(i)
                if isinstance(item, QHBoxLayout) and item.indexOf(control_widget) != -1:
                    # 找到了包含control_widget的centered_layout
                    for j in range(item.count()):
                        widget = item.itemAt(j).widget()
                        if widget:
                            widget.setVisible(show)


    # ==============================
    # 控制按钮：首次点击仅聚焦（使用 current_section/current_index），已聚焦则执行动作
    # ==============================
    def handle_control_button_click(self, idx):
        """如果当前焦点不是该控制按钮，则把焦点移动到它并返回；否则执行动作。"""
        try:
            # current_section: 0 = 游戏选择区域, 1 = 控制按钮区域
            if self.current_section != 1 or self.current_index != idx:
                self.current_section = 1
                self.current_index = idx
                try:
                    self.update_highlight()
                except Exception:
                    pass
                return
            # 已处于该焦点，执行动作
            self.perform_control_action(idx)
        except Exception:
            try:
                self.perform_control_action(idx)
            except Exception:
                pass

    def perform_control_action(self, idx):
        """根据按钮模式执行对应动作（假定这些方法在类中存在）。"""
        try:
            mode = self.control_button_modes.get(idx)
            if mode == 'background':
                try:
                    self.on_background_button_clicked(idx)
                except Exception:
                    pass
            elif mode == 'image':
                try:
                    self.show_img_window()
                except Exception:
                    pass
            elif mode == 'sleep':
                try:
                    self.confirm_dialog = ConfirmDialog("要进入睡眠吗", scale_factor=self.scale_factor, parent=self)
                    if self.confirm_dialog.exec_():
                        self.sleep_system()
                except Exception:
                    pass
            elif mode == 'settings':
                try:
                    self.show_settings_window()
                except Exception:
                    pass
        except Exception:
            pass
    # ==============================
    # 键盘覆盖层：创建/显示/关闭
    # ==============================
    def show_keyboard_overlay(self, mapping):
        if self.keyboard_overlay and self.keyboard_overlay.isVisible():
            return
        self.keyboard_overlay_mapping = mapping

        # 创建覆盖层窗口
        self.keyboard_overlay = QDialog(self)
        self.keyboard_overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.keyboard_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.keyboard_overlay.setWindowOpacity(0.9)
        self.keyboard_overlay.setFixedSize(675, 370)

        # 居中于屏幕底部
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        window_width = self.keyboard_overlay.width()
        window_height = self.keyboard_overlay.height()
        x = (screen_width - window_width) // 2
        y = screen_height * 3 // 4 - window_height // 2
        self.keyboard_overlay.move(x, y)

        # 内容
        wrapper = QWidget(self.keyboard_overlay)
        layout = QVBoxLayout(wrapper)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)

        self.keyboard_widget = type(self).KeyboardWidget()
        self.keyboard_widget.key_selected_callback = self.on_key_selected
        layout.addWidget(self.keyboard_widget)

        self.selected_key_label = QLabel(self.tr("快速拉摇杆两次切摇杆外圈，R1/A输入选中项。X键空格，B键删除，L1键启用粘滞键，Y键F区"))
        self.selected_key_label.setStyleSheet(
            "font-size: 16px; color: white; font-weight: bold; padding: 5px; background: rgba(0,0,0,0.5);"
        )
        self.selected_key_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.selected_key_label)

        v = QVBoxLayout(self.keyboard_overlay)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(wrapper)

        # 初始化键盘映射与状态
        self._kb_ignore_start_until = time.time() + 0.5
        self.setup_keyboard_mappings()
        self._kb_rb_last_pressed = False
        self._kb_left_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_right_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_last_outer_time = {'left': 0, 'right': 0}
        self._kb_last_zone = {'left': 'dead', 'right': 'dead'}
        self._kb_inner_ignore_until = {'left': 0, 'right': 0}
        self._kb_outer_mode_until = {'left': 0, 'right': 0}
        self._kb_outer_locked = {'left': False, 'right': False}
        self._kb_last_x_pressed = [False, False]
        self._kb_last_a_pressed = [False, False]
        self._kb_last_b_pressed = [False, False]
        self._kb_last_y_pressed = [False, False]
        self._kb_last_lb_pressed = [False, False]
        self._kb_last_key_time = [0.0, 0.0]
        self._kb_last_fkey_move_time = 0
        # 保存窗口原始位置和位移状态
        self._kb_original_position = (x, y)
        self._kb_window_offset = 600  # 位移的距离（像素）
        self._kb_window_shifted = False  # 窗口是否已向下位移
        self._kb_last_back_pressed = False  # 上次back键状态
        self.DOUBLE_OUTER_INTERVAL = 0.5  # 可调，建议 0.25~0.35

        # 启动手柄监听线程（用于键盘覆盖层）
        self.keyboard_overlay_thread = type(self).JoystickThread(self.keyboard_overlay_mapping)
        self.keyboard_overlay_thread.joystick_updated.connect(self.on_keyboard_overlay_joystick_updated)
        self.keyboard_overlay_thread.start()

        self.keyboard_overlay.show()

    def close_keyboard_overlay(self):
        # 在关闭时确保释放所有仍然按下的键，避免粘滞
        try:
            for jid in range(len(self._kb_last_a_pressed)):
                if self._kb_last_a_pressed[jid]:
                    pyautogui.keyUp('space')
                    self._kb_last_a_pressed[jid] = False
                if self._kb_last_b_pressed[jid]:
                    pyautogui.keyUp('backspace')
                    self._kb_last_b_pressed[jid] = False
                d = self._kb_last_dpad[jid] if jid < len(self._kb_last_dpad) else None
                if d:
                    if d.get('up'):
                        pyautogui.keyUp('up'); d['up'] = False
                    if d.get('down'):
                        pyautogui.keyUp('down'); d['down'] = False
                    if d.get('left'):
                        pyautogui.keyUp('left'); d['left'] = False
                    if d.get('right'):
                        pyautogui.keyUp('right'); d['right'] = False
        except Exception:
            pass
        if self.keyboard_overlay_thread:
            self.keyboard_overlay_thread.stop()
            self.keyboard_overlay_thread.wait()
            self.keyboard_overlay_thread = None
        if self.keyboard_overlay:
            self.keyboard_overlay.close()
            self.keyboard_overlay = None

    def is_keyboard_overlay_visible(self):
        return bool(self.keyboard_overlay and self.keyboard_overlay.isVisible())

    # ==============================
    # 键盘覆盖层：映射与事件（移植自 MainWindow）
    # ==============================
    def setup_keyboard_mappings(self):
        # 左摇杆映射
        self.left_joystick_mappings = {
            'inner': {
                'D': 'D',
                'S': 'S', 
                'W': 'W',
                'E': 'E'
            },
            'outer_yellow': [
                'F', 'V', 'C', 'X', 'Z', 'A',
                'Q', '1!', '2@', '3#', '4$', 'R'
            ],
            'outer_green': [
                'G', 'B', 'alt', 'ctrl', 'shift', 'Capslock', 'tab','`~','Esc', 'Win', '5%','T', 'G'
            ]
        }
        # 右摇杆映射
        self.right_joystick_mappings = {
            'inner': {
                'D': 'L',
                'S': 'K',
                'W': 'I', 
                'E': 'O'
            },
            'outer_yellow': [
                ';:', '/?', '.>', ',<', 'M', 'J', 'U',
                '7&', '8*', '9(', '0)', 'P'
            ],
            'outer_green': [
                 "'\"", '\\|', 'Enter', 'Del','N','H','Y','6^','-_'
                 , '=+', '[{', ']}'
            ]
        }

    def on_keyboard_overlay_joystick_updated(self, joystick_id, x_axis, y_axis, lb_pressed, rb_pressed):
        # 读取按键一次性事件
        if hasattr(self, 'keyboard_overlay_thread') and self.keyboard_overlay_thread and hasattr(self.keyboard_overlay_thread, 'joysticks'):
            if joystick_id < len(self.keyboard_overlay_thread.joysticks):
                joystick = self.keyboard_overlay_thread.joysticks[joystick_id]
                mapping = self.keyboard_overlay_mapping
                lt_val = joystick.get_axis(4)
                rt_val = joystick.get_axis(5)
                a_pressed = True if lt_val > 0.1 else joystick.get_button(mapping.button_a)
                b_pressed = True if rt_val > 0.1 else joystick.get_button(mapping.button_b)
                y_pressed = joystick.get_button(mapping.button_y)
                x_pressed = joystick.get_button(mapping.button_x)
                start_pressed = joystick.get_button(mapping.start)
                back_pressed = joystick.get_button(mapping.back)
                ls_pressed = joystick.get_button(mapping.left_stick_in)
                rs_pressed = joystick.get_button(mapping.right_stick_in)
                guide_pressed = joystick.get_button(mapping.guide)

                # D-Pad（hat 或 按钮）以及 A/B: 在按下时发送 keyDown，抬起时发送 keyUp（edge detection）
                now = time.time()

                # 确保状态列表足够长
                try:
                    _ = self._kb_last_a_pressed[joystick_id]
                except Exception:
                    # 扩展所有相关状态列表
                    extend_to = joystick_id + 1
                    while len(self._kb_last_a_pressed) < extend_to:
                        self._kb_last_a_pressed.append(False)
                    while len(self._kb_last_b_pressed) < extend_to:
                        self._kb_last_b_pressed.append(False)
                    while len(self._kb_last_x_pressed) < extend_to:
                        self._kb_last_x_pressed.append(False)
                    while len(self._kb_last_y_pressed) < extend_to:
                        self._kb_last_y_pressed.append(False)
                    while len(self._kb_last_lb_pressed) < extend_to:
                        self._kb_last_lb_pressed.append(False)
                    while len(self._kb_last_key_time) < extend_to:
                        self._kb_last_key_time.append(0.0)
                    while len(self._kb_last_hat) < extend_to:
                        self._kb_last_hat.append((0, 0))
                    while len(self._kb_last_dpad) < extend_to:
                        self._kb_last_dpad.append({'up': False, 'down': False, 'left': False, 'right': False})

                # 处理 hat / dpad 为 keyDown/keyUp
                if hasattr(mapping, 'has_hat') and mapping.has_hat and joystick.get_numhats() > 0:
                    hat = joystick.get_hat(0)
                    up = hat == (0, 1)
                    down = hat == (0, -1)
                    left = hat == (-1, 0)
                    right = hat == (1, 0)
                else:
                    up = bool(joystick.get_button(mapping.dpad_up))
                    down = bool(joystick.get_button(mapping.dpad_down))
                    left = bool(joystick.get_button(mapping.dpad_left))
                    right = bool(joystick.get_button(mapping.dpad_right))

                dpad_state = self._kb_last_dpad[joystick_id]
                # up
                if up and not dpad_state['up']:
                    pyautogui.keyDown('up'); dpad_state['up'] = True
                elif not up and dpad_state['up']:
                    pyautogui.keyUp('up'); dpad_state['up'] = False
                # down
                if down and not dpad_state['down']:
                    pyautogui.keyDown('down'); dpad_state['down'] = True
                elif not down and dpad_state['down']:
                    pyautogui.keyUp('down'); dpad_state['down'] = False
                # left
                if left and not dpad_state['left']:
                    pyautogui.keyDown('left'); dpad_state['left'] = True
                elif not left and dpad_state['left']:
                    pyautogui.keyUp('left'); dpad_state['left'] = False
                # right
                if right and not dpad_state['right']:
                    pyautogui.keyDown('right'); dpad_state['right'] = True
                elif not right and dpad_state['right']:
                    pyautogui.keyUp('right'); dpad_state['right'] = False

                # A = 输入选中项
                if a_pressed and not self._kb_last_a_pressed[joystick_id]:
                    self.input_selected_key()

                self._kb_last_a_pressed[joystick_id] = a_pressed

                # B 按键
                if b_pressed and not self._kb_last_b_pressed[joystick_id]:
                    pyautogui.keyDown('backspace')
                if not b_pressed and self._kb_last_b_pressed[joystick_id]:
                    pyautogui.keyUp('backspace')
                self._kb_last_b_pressed[joystick_id] = b_pressed

                # X = 空格
                if x_pressed and not self._kb_last_x_pressed[joystick_id]:
                    pyautogui.press('space')

                self._kb_last_x_pressed[joystick_id] = x_pressed

                # L1 = 粘滞键
                if lb_pressed and not self._kb_last_lb_pressed[joystick_id]:
                    self.keyboard_widget.toggle_sticky_mode()

                self._kb_last_lb_pressed[joystick_id] = lb_pressed

                # Y = F区
                if y_pressed and not self._kb_last_y_pressed[joystick_id]:
                    self.keyboard_widget.toggle_f_keys_mode()

                self._kb_last_y_pressed[joystick_id] = y_pressed

                # 退出键：Start 或 LS/RS/Guide
                if start_pressed and time.time() > self._kb_ignore_start_until:
                    self.close_keyboard_overlay(); return
                if any([ls_pressed, rs_pressed, guide_pressed]) and time.time() > self._kb_ignore_start_until:
                    self.close_keyboard_overlay(); return
                
                # Back键：切换窗口位置（位移/恢复原位置）
                # 只在joystick_id == 0时处理，避免重复触发
                if joystick_id == 0:
                    if back_pressed and not self._kb_last_back_pressed:
                        # 只在按键按下瞬间触发一次
                        if hasattr(self, '_kb_original_position') and self.keyboard_overlay:
                            if self._kb_window_shifted:
                                # 恢复原位置
                                self.keyboard_overlay.move(*self._kb_original_position)
                                self._kb_window_shifted = False
                            else:
                                # 位移
                                orig_x, orig_y = self._kb_original_position
                                offset_x = orig_x + self._kb_window_offset
                                self.keyboard_overlay.move(offset_x, orig_y)
                                self._kb_window_shifted = True
                    self._kb_last_back_pressed = back_pressed

        # 保存摇杆状态并驱动 UI 更新
        radius = math.sqrt(x_axis**2 + y_axis**2)
        if joystick_id == 0:
            self._kb_left_state = {'x': x_axis, 'y': y_axis, 'lb': lb_pressed, 'rb': rb_pressed, 'radius': radius}
        elif joystick_id == 1:
            self._kb_right_state = {'x': x_axis, 'y': y_axis, 'lb': lb_pressed, 'rb': rb_pressed, 'radius': radius}
        if self.keyboard_widget:
            self.keyboard_widget.set_joystick_state(
                {'x': self._kb_left_state['x'], 'y': self._kb_left_state['y']},
                {'x': self._kb_right_state['x'], 'y': self._kb_right_state['y']}
            )

        # F 区模式 or 普通模式
        if self.keyboard_widget and self.keyboard_widget.f_keys_enabled:
            self.handle_f_keys_selection_overlay(self._kb_left_state['rb'])
        else:
            left_r = self._kb_left_state['radius']
            right_r = self._kb_right_state['radius']
            if left_r >= right_r:
                s = self._kb_left_state
                self.update_keyboard_from_joystick_overlay(s['x'], s['y'], s['lb'], s['rb'], 'left')
            else:
                s = self._kb_right_state
                self.update_keyboard_from_joystick_overlay(s['x'], s['y'], s['lb'], s['rb'], 'right')

    def update_keyboard_from_joystick_overlay(self, x_axis, y_axis, lb_pressed, rb_pressed, side):
        radius = math.sqrt(x_axis**2 + y_axis**2)
        mapped_key = None
        now = time.time()
        zone = 'dead'
        if radius <= 0.2:
            zone = 'dead'
        elif radius < 0.75:
            zone = 'inner'
        else:
            zone = 'outer'
        mappings = self.left_joystick_mappings if side == 'left' else self.right_joystick_mappings
        angle = None
        if radius > 0.2:
            angle = math.degrees(math.atan2(y_axis, x_axis))
            if angle < 0:
                angle += 360
        # 外圈触发与内圈忽略
        if zone == 'outer' and self._kb_last_zone[side] != 'outer':
            # 双击检测 → 直接“锁定”
            if now - self._kb_last_outer_time[side] < self.DOUBLE_OUTER_INTERVAL:
                self._kb_outer_locked[side] = True

            self._kb_last_outer_time[side] = now
        if zone == 'inner' and self._kb_last_zone[side] == 'dead':
            self._kb_inner_ignore_until[side] = 0
        # RB 按键
        if rb_pressed:
            if not self._kb_rb_last_pressed:
                self.input_selected_key()

            self._kb_rb_last_pressed = True
            self.keyboard_widget.update_active_key(None)
            self._kb_last_zone[side] = zone
            return
        else:
            self._kb_rb_last_pressed = False
        # 内圈延迟
        if zone == 'inner':
            self._kb_outer_locked[side] = False

            if now < self._kb_inner_ignore_until[side]:
                self._kb_last_zone[side] = zone
                return
        # 正常映射
        if zone == 'inner' and angle is not None:
            if 0 <= angle < 90:
                direction = 'D'
            elif 90 <= angle < 180:
                direction = 'S'
            elif 180 <= angle < 270:
                direction = 'W'
            else:
                direction = 'E'
            mapped_key = mappings['inner'][direction]
        elif zone == 'outer' and angle is not None:
            sector = int(angle / 30) % 12

            if self._kb_outer_locked[side]:
                mapped_key = mappings['outer_green'][sector]
            else:
                mapped_key = mappings['outer_yellow'][sector]
        if mapped_key:
            self.keyboard_widget.update_active_key(mapped_key)
        self._kb_last_zone[side] = zone

    def handle_f_keys_selection_overlay(self, rb_pressed):
        # 选择使用X轴较大的一侧
        left_x = self._kb_left_state['x']
        right_x = self._kb_right_state['x']
        x_axis = left_x if abs(left_x) >= abs(right_x) else right_x
        threshold = 0.2
        now = time.time()
        if abs(x_axis) > threshold:
            if now - self._kb_last_fkey_move_time > 2:
                if x_axis > 0:
                    self.keyboard_widget.move_f_keys_selection(1)
                else:
                    self.keyboard_widget.move_f_keys_selection(-1)
                self._kb_last_fkey_move_time = now
        if rb_pressed:
            if not self._kb_rb_last_pressed:
                current_f_key = self.keyboard_widget.get_current_f_key()
                if current_f_key:
                    pyautogui.press(current_f_key.lower())
                self._kb_rb_last_pressed = True
        else:
            self._kb_rb_last_pressed = False
        current_f_key = self.keyboard_widget.get_current_f_key()
        if current_f_key:
            self.selected_key_label.setText(f"[{current_f_key}]")

    def on_key_selected(self, key_name):
        if hasattr(self, 'selected_key_label') and self.selected_key_label:
            self.selected_key_label.setText(f"[{key_name}]")
    # 键盘输入逻辑
    def input_selected_key(self):
        label_text = self.selected_key_label.text()

        if not (label_text.startswith('[') and label_text.endswith(']')):
            return

        selected_key = label_text[1:-1].strip()
        if not selected_key:
            return

        if len(selected_key) == 2:
            selected_key = selected_key[0]

        if self.keyboard_widget.sticky_enabled:
            if selected_key in self.keyboard_widget.sticky_key_names:
                if selected_key in self.keyboard_widget.sticky_keys:
                    self.keyboard_widget.sticky_keys.remove(selected_key)
                else:
                    self.keyboard_widget.sticky_keys.add(selected_key)

                self.keyboard_widget.update()
                return

            if self.keyboard_widget.sticky_keys:
                sticky_modifiers = []

                if 'shift' in self.keyboard_widget.sticky_keys:
                    sticky_modifiers.append('shift')
                if 'ctrl' in self.keyboard_widget.sticky_keys:
                    sticky_modifiers.append('ctrl')
                if 'alt' in self.keyboard_widget.sticky_keys:
                    sticky_modifiers.append('alt')
                if 'Win' in self.keyboard_widget.sticky_keys:
                    sticky_modifiers.append('win')

                if sticky_modifiers:
                    pyautogui.hotkey(*sticky_modifiers, selected_key.lower())
                else:
                    pyautogui.press(selected_key.lower())

                self.keyboard_widget.sticky_keys.clear()
                self.keyboard_widget.update()
            else:
                pyautogui.press(selected_key.lower())
        else:
            pyautogui.press(selected_key.lower())
    # ==============================
    # 鼠标映射主循环（非“键盘模拟”范围）
    # - 包含对系统快捷键的 pyautogui 触发，但不属于键盘模拟整理范畴
    # ==============================
    def mouse_simulation(self):
        """开启鼠标映射"""
        # 检查是否已经在运行
        if self.is_mouse_simulation_running:
            print("鼠标映射已在运行，忽略重复调用")
            return

        # 设置标志为 True，表示正在运行
        self.is_mouse_simulation_running = True

        if pygame.joystick.get_count() == 0:
            self.show_window()
            return
        joysticks = []
        for i in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            joysticks.append(joystick)
    
        if not joysticks:
            print("未检测到手柄")
        joystick_states = {joystick.get_instance_id(): {"scrolling_up": False, "scrolling_down": False} for joystick in joysticks}
        print("鼠标映射")

        # 鼠标移动灵敏度（高/低）
        SENS_HIGH = 100.0
        SENS_MEDIUM = 25.0
        SENS_LOW  = 10.0
        sensitivity = SENS_MEDIUM
        sensitivity1 = SENS_LOW
        DEADZONE = 0.1    # 摇杆死区阈值，防止轻微漂移
        clock = pygame.time.Clock()
        #mapping = ControllerMapping(joystick)
        # 初始化滚动状态变量
        scrolling_up = False
        scrolling_down = False
        window = type(self).MouseWindow()
        last_mouse_x, last_mouse_y = -1, -1  # 初始化上一次鼠标位置
        magnifier_open = False  # 初始化放大镜状态
        # 初始化鼠标按键状态变量
        left_button_down = False
        right_button_down = False
        screen_width, screen_height = pyautogui.size()
        pyautogui.moveTo(int(screen_width/2), int(screen_height/1.5))  # 移动鼠标到屏幕中心
        time.sleep(0.7) 
        #print(f'所有按键: {joystick.get_button(mapping.button_a)}, {joystick.get_button(mapping.button_b)}, {joystick.get_button(mapping.button_x)}, {joystick.get_button(mapping.button_y)}, {joystick.get_button(mapping.start)}, {joystick.get_button(mapping.back)}')
        #print(f"X轴: {x_axis:.2f}, Y轴: {y_axis:.2f}, 右扳机: {rt_val:.2f}, 左扳机: {lt_val:.2f}, 滚动: {scrolling_up}, {scrolling_down}")
        #print(f"{mapping.guide} {mapping.right_stick_in} {mapping.left_stick_in} {mapping.start} {mapping.back} {mapping.button_a} {mapping.button_b} {mapping.button_x} {mapping.button_y}")
        running = True  # 添加状态标志
        # 同时下压左右扳机计时切换标记窗口显示/隐藏
        both_triggers_start_time = None
        marker_hidden = False
        both_triggers_action_done = False  # 防抖：一次长按只触发一次
        try:
            while running:
                # 动态检测新手柄加入或移除
                for event in pygame.event.get():
                    if event.type == pygame.JOYDEVICEADDED:
                        joystick = pygame.joystick.Joystick(event.device_index)
                        joystick.init()
                        # 检查是否已在列表中
                        if joystick not in joysticks:
                            joysticks.append(joystick)
                            joystick_states[joystick.get_instance_id()] = {"scrolling_up": False, "scrolling_down": False}
                            print(f"手柄已连接: {joystick.get_name()}")
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        # 移除断开手柄及其状态
                        for joystick in joysticks[:]:
                            if joystick.get_instance_id() == event.instance_id:
                                print(f"手柄已断开: {joystick.get_name()}")
                                joysticks.remove(joystick)
                                joystick_states.pop(event.instance_id, None)
                                break
                # 检查当前所有手柄，自动补充新插入的手柄
                for i in range(pygame.joystick.get_count()):
                    joystick = pygame.joystick.Joystick(i)
                    if joystick not in joysticks:
                        joystick.init()
                        joysticks.append(joystick)
                        joystick_states[joystick.get_instance_id()] = {"scrolling_up": False, "scrolling_down": False}
                        print(f"检测到新手柄: {joystick.get_name()}")
                pygame.event.pump()
                mouse_x, mouse_y = pyautogui.position()
                # 仅当鼠标位置发生变化时更新窗口位置
                if (mouse_x, mouse_y) != (last_mouse_x, last_mouse_y):
                    # 更新窗口位置
                    window.label.move(mouse_x, mouse_y)
                    last_mouse_x, last_mouse_y = mouse_x, mouse_y
                # 遍历所有手柄，处理输入
                joycount = pygame.joystick.get_count()
                for joystick in joysticks:
                    mapping = ControllerMapping(joystick) #切换对应的手柄映射
                    # GUIDE 按钮退出
                    if joystick.get_button(mapping.guide) or joystick.get_button(mapping.right_stick_in) or joystick.get_button(mapping.left_stick_in) or self.is_mouse_simulation_running == False:
                        running = False  # 设置状态标志为 False，退出循环
                        # 设置右下角坐标
                        print("退出鼠标映射")
                        if self.is_magnifier_open():
                            self.close_magnifier()
                            magnifier_open = False
                        right_bottom_x = screen_width - 1  # 最右边
                        right_bottom_y = screen_height - 1  # 最底部
                        # 移动鼠标到屏幕右下角
                        pyautogui.moveTo(right_bottom_x, right_bottom_y)
                        #time.sleep(0.5)  
                        break

                    # 检查左键状态
                    if joystick.get_button(mapping.button_a) or joystick.get_button(mapping.right_bumper):  # A键模拟左键按下
                        if not left_button_down:  # 状态变化时触发
                            pyautogui.mouseDown()
                            left_button_down = True
                    else:
                        if left_button_down:  # 状态变化时触发
                            pyautogui.mouseUp()
                            left_button_down = False

                    # 检查右键状态
                    if joystick.get_button(mapping.button_b) or joystick.get_button(mapping.left_bumper):  # B键模拟右键按下
                        if not right_button_down:  # 状态变化时触发
                            pyautogui.mouseDown(button='right')
                            right_button_down = True
                    else:
                        if right_button_down:  # 状态变化时触发
                            pyautogui.mouseUp(button='right')
                            right_button_down = False
                    # 读取左摇杆轴值（0: X 轴，1: Y 轴）
                    x_axis = joystick.get_axis(0)
                    y_axis = joystick.get_axis(1)
                    # 读取扳机轴值
                    rt_val = joystick.get_axis(5)
                    lt_val = joystick.get_axis(4)
                    # 检查是否使用 hat 输入
                    if mapping.has_hat:
                        hat_value = joystick.get_hat(0)  # 获取第一个 hat 的值
                        if magnifier_open:
                            if not self.is_magnifier_open():
                                magnifier_open = False
                            # 放大镜打开时，方向键模拟 Ctrl+Alt+方向键
                            if hat_value == (-1, 0):  # 左
                                pyautogui.hotkey('ctrl', 'alt', 'left')
                                time.sleep(0.2)
                            elif hat_value == (1, 0):  # 右
                                pyautogui.hotkey('ctrl', 'alt', 'right')
                                time.sleep(0.2)
                            elif hat_value == (0, -1):  # 下
                                pyautogui.hotkey('ctrl', 'alt', 'down')
                                time.sleep(0.2)
                            elif hat_value == (0, 1):  # 上
                                pyautogui.hotkey('ctrl', 'alt', 'up')
                                time.sleep(0.2)
                            # 滚动行为不变
                            if joystick.get_button(mapping.button_x) or hat_value == (0, -1):
                                scrolling_down = True
                            else:
                                scrolling_down = False
                            if joystick.get_button(mapping.button_y) or hat_value == (0, 1):
                                scrolling_up = True
                            else:
                                scrolling_up = False
                        else:
                            if hat_value == (-1, 0):  # 左
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('left')
                                else:
                                    self.decrease_volume()
                                time.sleep(0.2)
                            elif hat_value == (1, 0):  # 右
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('right')
                                else:
                                    self.increase_volume()
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.button_x) or hat_value == (0, -1):  # 下
                                scrolling_down = True
                            elif joystick.get_button(mapping.button_y) or hat_value == (0, 1):  # 上
                                scrolling_up = True
                            else:
                                scrolling_down = False
                                scrolling_up = False
                    else:
                        if magnifier_open:
                            if not self.is_magnifier_open():
                                magnifier_open = False
                            # 放大镜打开时，方向键模拟 Ctrl+Alt+方向键
                            if joystick.get_button(mapping.dpad_left):
                                pyautogui.hotkey('ctrl', 'alt', 'left')
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_right):
                                pyautogui.hotkey('ctrl', 'alt', 'right')
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_down):
                                pyautogui.hotkey('ctrl', 'alt', 'down')
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_up):
                                pyautogui.hotkey('ctrl', 'alt', 'up')
                                time.sleep(0.2)
                            # 滚动行为不变
                            if joystick.get_button(mapping.button_x) or joystick.get_button(mapping.dpad_down):
                                scrolling_down = True
                            else:
                                scrolling_down = False
                            if joystick.get_button(mapping.button_y) or joystick.get_button(mapping.dpad_up):
                                scrolling_up = True
                            else:
                                scrolling_up = False
                        else:
                            if joystick.get_button(mapping.dpad_left):
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('left')
                                else:
                                    self.decrease_volume()
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_right):
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('right')
                                else:
                                    self.increase_volume()
                                time.sleep(0.2)
                            if joystick.get_button(mapping.button_x) or joystick.get_button(mapping.dpad_down):
                                scrolling_down = True
                            else:
                                scrolling_down = False
                            if joystick.get_button(mapping.button_y) or joystick.get_button(mapping.dpad_up):
                                scrolling_up = True
                            else:
                                scrolling_up = False

                    # 同时下压两个扳机时开始计时，满2秒后切换标志窗口显示/隐藏
                    if lt_val > 0.5 and rt_val > 0.5:
                        if both_triggers_start_time is None:
                            both_triggers_start_time = time.time()
                            both_triggers_action_done = False
                        elif not both_triggers_action_done and (time.time() - both_triggers_start_time) >= 1.0:
                            if marker_hidden:
                                # 重新显示并对齐当前位置
                                try:
                                    mx, my = pyautogui.position()
                                    window.label.move(mx, my)
                                except Exception:
                                    pass
                                window.show()
                                marker_hidden = False
                            else:
                                window.hide()
                                marker_hidden = True
                            both_triggers_action_done = True
                    else:
                        # 松手后重置，允许再次触发
                        both_triggers_start_time = None
                        both_triggers_action_done = False

                    # 读取右摇杆轴值（2: X 轴，3: Y 轴）
                    rx_axis = joystick.get_axis(2)  # 右摇杆 X 轴
                    ry_axis = joystick.get_axis(3)  # 右摇杆 Y 轴
                    def backandstart_pressed():
                        nonlocal magnifier_open
                        if joystick.get_button(mapping.back):
                            pyautogui.hotkey('win', 'a')
                            screen_width, screen_height = pyautogui.size()
                            pyautogui.moveTo(screen_width * 7 / 8, screen_height * 6 / 8)
                            time.sleep(0.5)
                        if joystick.get_button(mapping.start):
                            if not self.is_magnifier_open():
                                self.open_magnifier()
                                magnifier_open = True
                            else:
                                self.close_magnifier()
                                magnifier_open = False
                            time.sleep(0.5)
                    if lt_val > 0.5:
                        sensitivity = SENS_HIGH
                        backandstart_pressed()
                    elif rt_val > 0.5:
                        sensitivity = SENS_LOW
                        sensitivity1 = SENS_HIGH
                        backandstart_pressed()
                    else:
                        sensitivity = SENS_MEDIUM
                        sensitivity1 = SENS_LOW
                    
                    if joystick.get_button(mapping.start):
                        if magnifier_open:
                            if not self.is_magnifier_open():
                                magnifier_open = False
                            else:
                                self.close_magnifier()
                                magnifier_open = False
                                time.sleep(0.2)
                                break
                        print("切换到虚拟键盘覆盖层")
                        self.show_keyboard_overlay(mapping)
                        while self.is_keyboard_overlay_visible():
                            QApplication.processEvents()
                            time.sleep(0.05)
                        time.sleep(0.2)
                        break
                    if joystick.get_button(mapping.back):  # SELECT 键 → Win+Tab（非键盘模拟范围）
                        pyautogui.hotkey('win', 'tab')
                        pyautogui.moveTo(int(screen_width/2), int(screen_height/2))
                        time.sleep(0.5)  # 延迟0.2秒，避免重复触发

                    # 使用右摇杆控制鼠标移动（低灵敏度）
                    dx = dy = 0
                    if abs(rx_axis) > DEADZONE:
                        self.move_mouse_once()
                        dx = rx_axis * sensitivity1
                    if abs(ry_axis) > DEADZONE:
                        self.move_mouse_once()
                        dy = ry_axis * sensitivity1
                    # PyAutoGUI中 y 轴正值向下移动，与摇杆上推为负值刚好对应
                    pyautogui.moveRel(dx, dy)

                    # 根据摇杆值控制鼠标移动，加入死区处理
                    dx = dy = 0
                    if abs(x_axis) > DEADZONE:
                        self.move_mouse_once()
                        dx = x_axis * sensitivity
                    if abs(y_axis) > DEADZONE:
                        self.move_mouse_once()
                        dy = y_axis * sensitivity
                    # PyAutoGUI中 y 轴正值向下移动，与摇杆上推为负值刚好对应
                    pyautogui.moveRel(dx, dy)

                    # 在主循环中处理滚动
                    if scrolling_up:
                        pyautogui.scroll(50)  # 持续向上滚动
                    if scrolling_down:
                        pyautogui.scroll(-50)  # 持续向下滚动
                    #print(f'所有按键: {joystick.get_button(mapping.button_a)}, {joystick.get_button(mapping.button_b)}, {joystick.get_button(mapping.button_x)}, {joystick.get_button(mapping.button_y)}, {joystick.get_button(mapping.start)}, {joystick.get_button(mapping.back)}')
                    #print(f"X轴: {x_axis:.2f}, Y轴: {y_axis:.2f}, 右扳机: {rt_val:.2f}, 左扳机: {lt_val:.2f}, 滚动: {scrolling_up}, {scrolling_down}")
                    clock.tick(int(60*joycount))  # 稳定循环频率 (60 FPS)
        except KeyboardInterrupt:
            print("程序已退出。")
        finally:
            # 退出时重置标志
            window.close()
            #ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)  # SPI_SETCURSORS = 0x0057 还原鼠标光标
            self.is_mouse_simulation_running = False
            print("鼠标已退出")

    ########################
    def move_mouse_once(self):
        """模拟鼠标移动，避免光标不显示"""
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", ctypes.c_long),
                        ("dy", ctypes.c_long),
                        ("mouseData", ctypes.c_ulong),
                        ("dwFlags", ctypes.c_ulong),
                        ("time", ctypes.c_ulong),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong),
                        ("u", INPUT_UNION)]

        def send(dx, dy):
            extra = ctypes.c_ulong(0)
            mi = MOUSEINPUT(dx, dy, 0, 0x0001, 0, ctypes.pointer(extra))  # 0x0001 = MOUSEEVENTF_MOVE
            inp = INPUT(0, INPUT_UNION(mi))  # 0 = INPUT_MOUSE
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

        send(1, 0)   # 向右移动1像素
        send(-1, 0)  # 向左移动1像素
    def is_magnifier_open(self):
        """检查放大镜是否已打开"""
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] and process.info['name'].lower() == 'magnify.exe':
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def open_magnifier(self):
        """打开系统放大镜"""
        try:
            subprocess.Popen(['magnify.exe'], shell=True)
        except FileNotFoundError:
            print("无法找到放大镜程序")

    def close_magnifier(self):
        """关闭系统放大镜"""
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] and process.info['name'].lower() == 'magnify.exe':
                    process.terminate()
                    process.wait()
                    print("放大镜已关闭")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def toggle_mute(self):
        """静音或恢复声音"""
        try:
            # 调用 Windows 的音量静音快捷键
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)  # VK_VOLUME_MUTE
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)  # KEYEVENTF_KEYUP
            print("切换静音状态")
        except Exception as e:
            print(f"切换静音状态时出错: {e}")
    def increase_volume(self):
        """增加系统音量"""
        ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)  # VK_VOLUME_UP
        ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)  # KEYEVENTF_KEYUP
    
    def decrease_volume(self):
        """降低系统音量"""
        ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)  # VK_VOLUME_DOWN
        ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)  # KEYEVENTF_KEYUP
    #def lock_system(self):
    #    ctypes.windll.user32.LockWorkStation()

    def sleep_system(self):
        #os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        ctypes.windll.powrprof.SetSuspendState(0, 1, 0)

    def shutdown_system(self):
        if ADMIN:
            os.system("shutdown /s /t 0")
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "shutdown", "/s /t 0", None, 1)
            
    def handle_reload_signal(self):
        """处理信号时的逻辑"""
        QTimer.singleShot(100, self.reload_interface)

    def update_play_app_name(self, new_play_app_name):
        """更新主线程中的 play_app_name"""
        self.player = new_play_app_name
        print(f"更新后的 play_app_name: {self.play_app_name}")

    def create_game_button(self, game, index):
        """创建游戏按钮和容器"""
        # 创建容器
        button_container = QWidget()
        button_container.setFixedSize(int(220 * self.scale_factor2), int(300 * self.scale_factor2))  # 确保容器大小固定

        # 创建游戏按钮
        button = QPushButton()
        image_path = game["image-path"]
        # 自动判断图片路径是相对还是绝对
        if not os.path.isabs(image_path):
            image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
        
        pixmap = QPixmap(image_path).scaled(int(200 * self.scale_factor2), int(267 * self.scale_factor2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon = QIcon(pixmap)
        button.setIcon(icon)
        button.setIconSize(pixmap.size())
        button.setFixedSize(int(220 * self.scale_factor2), int(300 * self.scale_factor2))
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: #2e2e2e; 
                border-radius: {int(10 * self.scale_factor2)}px; 
                border: {int(2 * self.scale_factor2)}px solid #444444;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor2)}px solid #888888;
            }}
        """)

        # 修改：点击时先判断光标位置
        def on_button_clicked(checked=False, idx=index):
            if getattr(self, 'show_background_apps', False):  # 仅在处于后台应用模式时恢复
                self.restore_control_buttons()
            if self.current_index != idx or self.current_section != 0:
                self.current_section = 0
                self.current_index = idx
                self.update_highlight()
            else:
                self.launch_game(idx)
        button.clicked.connect(on_button_clicked)

        # 创建星标（如果已收藏）
        if game["name"] in settings["favorites"]:
            star_label = QLabel("✰", button)  # 将星标作为按钮的子控件
            star_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(10 * self.scale_factor2)}px;
                    padding: {int(5 * self.scale_factor2)}px;
                    background-color: rgba(46, 46, 46, 0.2);
                    border-radius: {int(10 * self.scale_factor2)}px;
                }}
            """)
            star_label.move(int(5 * self.scale_factor2), int(5 * self.scale_factor2)) 
        if game["name"] in self.player:
            star_label = QLabel("🌊运行中🌊\n点击恢复", button)  
            star_label.setAlignment(Qt.AlignCenter)
            star_label.setStyleSheet(f"""
                QLabel {{
                    color: yellow;
                    font-size: {int(20 * self.scale_factor2)}px;
                    padding: {int(5 * self.scale_factor2)}px;
                    background-color: rgba(46, 46, 46, 0.7);
                    border-radius: {int(5 * self.scale_factor2)}px;
                    border: {int(2 * self.scale_factor2)}px solid white;
                    text-align: center;
                }}
            """)
            star_label.move(int(45 * self.scale_factor2), int(190 * self.scale_factor2))
        # 需要选择进程的标签
        elif hasattr(self, 'need_select_process') and game["name"] in self.need_select_process:
            need_label = QLabel(self.tr("需要选择进程\n点击手动选择"), button)
            need_label.setAlignment(Qt.AlignCenter)
            need_label.setStyleSheet(f"""
                QLabel {{
                    color: #ff6b6b;
                    font-size: {int(18 * self.scale_factor2)}px;
                    padding: {int(5 * self.scale_factor2)}px;
                    background-color: rgba(46, 46, 46, 0.7);
                    border-radius: {int(5 * self.scale_factor2)}px;
                    border: {int(2 * self.scale_factor2)}px solid #ff6b6b;
                    text-align: center;
                }}
            """)
            need_label.move(int(35 * self.scale_factor2), int(190 * self.scale_factor2))
        
        return button

    def update_highlight(self):
        """高亮当前选中的游戏按钮，并更新游戏名称"""
        sorted_games = self.sort_games()
        
        # 检查是否有游戏
        if not sorted_games:
            self.game_name_label.setText(self.tr("没有找到游戏"))
            return
        
        # 确保 current_index 不超出范围
        if self.current_section == 0:  # 游戏选择区域
            if self.current_index >= len(sorted_games):
                self.current_index = len(sorted_games) - 1
        elif self.current_section == 1:  # 控制按钮区域
            if self.current_index >= len(self.control_buttons):
                self.current_index = len(self.control_buttons) - 1
        # 设置窗口透明度，当游戏运行时
        #if self.player:
        #    self.setWindowOpacity(0.95)
        #else:
        #    self.setWindowOpacity(1)
        # 更新游戏名称标签
        if self.current_section == 0:  # 游戏选择区域
            if self.more_section == 0 and self.current_index == self.buttonsindexset:  # 如果是"更多"按钮
                self.game_name_label.setText(self.tr("所有软件"))
            else:
                self.game_name_label.setText(sorted_games[self.current_index]["name"])

                # 检查当前游戏是否在运行
                current_game_name = sorted_games[self.current_index]["name"]
                is_running = current_game_name in self.player  # 假设 self.player 存储正在运行的游戏名称

                # 更新 favorite_button 的原始文本（存储在字典中）
                if is_running:
                    self.button_texts['favorite'] = self.tr("结束进程")
                else:
                    self.button_texts['favorite'] = self.tr("收藏")
                
                # 确保按钮在未点击时显示为灰色横杠
                if self.favorite_button.text() == "*":
                    # 保持灰色横杠状态
                    pass
                else:
                    # 如果按钮当前显示的是文本，则更新为正确的文本
                    self.favorite_button.setText(self.button_texts['favorite'])

        if self.current_section == 0: 
            for index, button in enumerate(self.buttons):
                if index == self.current_index:
                    if self.gsfocus():
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba(51, 51, 51, 0.75);
                                border-radius: {int(10 * self.scale_factor2)}px; 
                                border: {int(3 * self.scale_factor2)}px solid #93ffff;
                            }}
                            QPushButton:hover {{
                                border: {int(3 * self.scale_factor2)}px solid #25ade7;
                            }}
                        """)
                    else:
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba(51, 51, 51, 0.75);
                                border-radius: {int(10 * self.scale_factor2)}px; 
                                border: {int(3 * self.scale_factor2)}px solid #555555;
                            }}
                            QPushButton:hover {{
                                border: {int(3 * self.scale_factor2)}px solid #888888;
                            }}
                        """)

                else:
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(51, 51, 51, 0.75);
                            border-radius: {int(10 * self.scale_factor2)}px; 
                            border: {int(2 * self.scale_factor2)}px solid #444444;
                        }}
                        QPushButton:hover {{
                            border: {int(2 * self.scale_factor2)}px solid #888888;
                        }}
                    """)
                    # 移除之前可能存在的高亮动画
                    try:
                        if hasattr(self, '_highlight_anims') and button in self._highlight_anims:
                            old = self._highlight_anims.pop(button)
                            try:
                                old.stop()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # 可选：移除效果以还原默认外观
                    try:
                        eff = button.graphicsEffect()
                        if isinstance(eff, QtWidgets.QGraphicsDropShadowEffect):
                            button.setGraphicsEffect(None)
                    except Exception:
                        pass
            for index, btn in enumerate(self.control_buttons):
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(72, 72, 72, 0.75);
                        border-radius: 62%;
                        font-size: {int(40 * self.scale_factor)}px; 
                        border: {int(5 * self.scale_factor)}px solid #282828;
                    }}
                    QPushButton:hover {{
                        border: {int(2 * self.scale_factor)}px solid #888888;
                    }}
                """)
            # 如果离开控制按钮区域，则隐藏任何残留的控制按钮标签
            self._hide_control_button_labels()
        elif self.current_section == 1:  # 控制按钮区域
            # 先隐藏旧标签一次，避免在循环中被多次删除/覆盖
            self._hide_control_button_labels()
            for index, btn in enumerate(self.control_buttons):
                if index == self.current_index:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(72, 72, 72, 0.75);
                            border-radius: 62%;
                            font-size: {int(40 * self.scale_factor)}px; 
                            border: {int(4 * self.scale_factor)}px solid #93ffff;
                        }}
                        QPushButton:hover {{
                            border: {int(4 * self.scale_factor)}px solid #25ade7;
                        }}
                    """)
                    # 只为选中按钮显示标签（前4个显示窗口名，其余显示固定中文名）
                    self._show_control_button_label(btn, index)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(72, 72, 72, 0.75);
                            border-radius: 62%;
                            font-size: {int(40 * self.scale_factor)}px; 
                            border: {int(5 * self.scale_factor)}px solid #282828;
                        }}
                        QPushButton:hover {{
                            border: {int(2 * self.scale_factor)}px solid #888888;
                        }}
                    """)
            for index, button in enumerate(self.buttons):
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(51, 51, 51, 0.75);
                        border-radius: {int(10 * self.scale_factor2)}px; 
                        border: {int(2 * self.scale_factor2)}px solid #444444;
                    }}
                    QPushButton:hover {{
                        border: {int(2 * self.scale_factor2)}px solid #888888;
                    }}
                """)

        # 只在有按钮时进行滚动条调整
        #竖向滚动
        if self.buttons and self.current_section == 0 and self.more_section == 1:
            current_button = self.buttons[self.current_index]
            # 修正：获取按钮在scroll_widget中的准确位置
            button_pos = current_button.mapTo(self.scroll_widget, QPoint(0, 0))
            scroll_area_height = self.scroll_area.viewport().height()
            scroll_bar = self.scroll_area.verticalScrollBar()
            # 如果按钮顶部超出可视区域
            if button_pos.y() < scroll_bar.value():
                # 平滑滚动到目标位置
                self.animate_scroll('vertical', button_pos.y(), duration=150)
            # 如果按钮底部超出可视区域
            elif button_pos.y() + current_button.height() > scroll_bar.value() + scroll_area_height:
                self.animate_scroll('vertical', button_pos.y() + current_button.height() - scroll_area_height, duration=150)
        #固定2
        #if self.buttons:
        #    current_button = self.buttons[self.current_index]
        #    scroll_area_width = self.scroll_area.viewport().width()
        #    button_pos = current_button.mapTo(self.scroll_widget, QPoint(0, 0))
        #    button_width = current_button.width()
        #    
        #    if self.current_index == 0:
        #        # 第一个按钮，滚动到最左边
        #        self.scroll_area.horizontalScrollBar().setValue(0)
        #    elif self.current_index >= 1:
        #        # 从第二个按钮开始，将按钮对齐到第二个位置
        #        second_button_pos = self.buttons[1].mapTo(self.scroll_widget, QPoint(0, 0)).x()
        #        scroll_value = button_pos.x() - second_button_pos
        #        self.scroll_area.horizontalScrollBar().setValue(scroll_value)
        #横向排列
        if self.buttons and self.current_section == 0 and self.more_section == 0:
            current_button = self.buttons[self.current_index]
            scroll_area_width = self.scroll_area.viewport().width()
            button_pos = current_button.mapToGlobal(QPoint(0, 0))  # 获取按钮在屏幕中的绝对位置
            scroll_area_pos = self.scroll_area.mapToGlobal(QPoint(0, 0))  # 获取滚动区域在屏幕中的绝对位置
            button_width = current_button.width()
            offset = 100  # 偏移量，单位像素，可根据需要调整

            if self.current_index == 0:
                # 第一个按钮，平滑滚动到最左边
                self.animate_scroll('horizontal', 0, duration=150)
            elif self.current_index >= 1:
                button_pos = QPoint(current_button.mapToGlobal(QPoint(0, 0)))  # 获取当前按钮的精确位置
                scroll_value = self.scroll_area.horizontalScrollBar().value()  # 获取当前滚动值
                # 当靠近左边缘且左侧还有游戏时，稍微偏移一点让左侧游戏露出
                if button_pos.x() < scroll_area_pos.x() + offset and self.current_index > 0:
                    second_button_pos = self.buttons[0].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos - offset
                    self.animate_scroll('horizontal', scroll_value, duration=150)
                # 当靠近右边缘且移动距离大于3时调整滚动
                elif button_pos.x() + button_width > scroll_area_pos.x() + scroll_area_width:
                    second_button_pos = self.buttons[min(3, len(self.buttons) - 1)].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos
                    self.animate_scroll('horizontal', scroll_value, duration=150)
        #
        #self.game_name_label.move(button_pos.x(), button_pos.y() - self.game_name_label.height())
        #self.game_name_label.show()
        # 新增文本显示，复制game_name_label的内容
        if self.current_section == 0 and self.more_section == 0: 
            self.game_name_label.setStyleSheet(f"""QLabel {{color: transparent;}}""")
            button_pos = current_button.mapToGlobal(QPoint(0, 0))  # 重新加载按钮的最新位置
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                # 如果已有 label，则做淡出动画后删除
                try:
                    old_label = self.additional_game_name_label
                    try:
                        eff_old = old_label.graphicsEffect()
                        if not isinstance(eff_old, QtWidgets.QGraphicsOpacityEffect):
                            eff_old = None
                    except Exception:
                        eff_old = None
                    if eff_old is None:
                        try:
                            eff_old = QtWidgets.QGraphicsOpacityEffect(old_label)
                            old_label.setGraphicsEffect(eff_old)
                        except Exception:
                            eff_old = None
                    if eff_old is not None:
                        fade_out = QPropertyAnimation(eff_old, b"opacity")
                        fade_out.setDuration(180)
                        fade_out.setStartValue(1.0)
                        fade_out.setEndValue(0.0)
                        def _del_old():
                            try:
                                old_label.deleteLater()
                            except Exception:
                                pass
                        fade_out.finished.connect(_del_old)
                        # 保存引用并清理旧动画
                        if not hasattr(self, '_label_fade_anims'):
                            self._label_fade_anims = []
                        self._cleanup_label_animations()
                        self._label_fade_anims.append(fade_out)
                        fade_out.start()
                    else:
                        try:
                            old_label.deleteLater()
                        except Exception:
                            pass
                except RuntimeError:
                    pass  # 如果对象已被删除，忽略错误
            else:
                QTimer.singleShot(200, self.update_highlight)  # 延迟200毫秒后调用update_highlight
            self.additional_game_name_label = QLabel(self.game_name_label.text(), self)
            self.additional_game_name_label.setAlignment(Qt.AlignCenter)  # 设置文本居中
            self.additional_game_name_label.setStyleSheet(f"""
                QLabel {{
                    font-family: "Microsoft YaHei"; 
                    color: white;
                    font-size: {int(20 * self.scale_factor*1.5)}px;
                    background: transparent;
                }}
            """)
            # 添加不透明度效果并淡入
            try:
                eff = QtWidgets.QGraphicsOpacityEffect(self.additional_game_name_label)
                self.additional_game_name_label.setGraphicsEffect(eff)
                eff.setOpacity(0.0)
                fade_in_lbl = QPropertyAnimation(eff, b"opacity")
                fade_in_lbl.setDuration(180)
                fade_in_lbl.setStartValue(0.0)
                fade_in_lbl.setEndValue(1.0)
                if not hasattr(self, '_label_fade_anims'):
                    self._label_fade_anims = []
                self._cleanup_label_animations()
                self._label_fade_anims.append(fade_in_lbl)
                fade_in_lbl.start()
            except Exception:
                pass
        # background-color: #575757;    
        # border-radius: 10px;          
        # border: 2px solid #282828;
            self.additional_game_name_label.adjustSize()  # 调整标签大小以适应文本
            #print(self.game_name_label.text(), button_pos.x(), button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2, button_pos.y() - self.game_name_label.height() - 20)
            self.additional_game_name_label.move(button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2, button_pos.y() - self.game_name_label.height() - 20)  # 居中在按钮中央
            self.additional_game_name_label.show()
        elif self.current_section == 1:
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                try:
                    self.additional_game_name_label.deleteLater()  # 删除之前生成的 additional_game_name_label
                except RuntimeError:
                    pass
        else:
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                try:
                    self.additional_game_name_label.deleteLater()  # 删除之前生成的 additional_game_name_label
                    # 设置game_name_label的颜色
                    self.game_name_label.setStyleSheet(f"""
                        QLabel {{
                            font-family: "Microsoft YaHei";
                            color: white;
                            font-size: {int(20 * self.scale_factor*1.5)}px; 
                            background: transparent;
                        }}
                    """)
                except RuntimeError:
                    pass
        #    current_button = self.buttons[self.current_index]
        #    scroll_area_width = self.scroll_area.viewport().width()
        #    button_pos = current_button.mapTo(self.scroll_widget, QPoint(0, 0))
        #    button_width = current_button.width()
        #    if self.current_index == 0:
        #        # 第一个按钮，滚动到最左边
        #        self.scroll_area.horizontalScrollBar().setValue(0)
        #        self.last_scroll_index = 0
        #    elif self.current_index >= 1:
        #        # 使用QPoint实现精确定位并改进调整滚动的方式
        #        button_pos = QPoint(current_button.mapTo(self.scroll_widget, QPoint(0, 0)))  # 获取当前按钮的精确位置
        #        scroll_value = self.scroll_area.horizontalScrollBar().value()  # 获取当前滚动值
        #        
        #        # 计算移动距离
        #        move_distance = abs(self.current_index - (self.last_scroll_index or 0))
        #        print(button_pos.x(),button_width,scroll_area_width)
        #        # 当靠近左边缘且移动距离大于3时调整滚动 and move_distance < 3
        #        if button_pos.x() < 0:
        #            if self.current_index > self.last_scroll_index:
        #                return
        #            print('<',self.current_index, self.last_scroll_index, move_distance)
        #            scroll_value = max(0, button_pos.x())  # 确保滚动值不小于0
        #            self.scroll_area.horizontalScrollBar().setValue(scroll_value)
        #            self.last_scroll_index = self.current_index
        #        
        #        # 当靠近右边缘且移动距离大于3时调整滚动
        #        elif button_pos.x() + button_width > scroll_area_width:
        #            if self.current_index < self.last_scroll_index:
        #                return
        #            print(">",self.current_index, self.last_scroll_index, move_distance)
        #            scroll_value = button_pos.x() + button_width - scroll_area_width
        #            self.scroll_area.horizontalScrollBar().setValue(scroll_value)
        #            self.last_scroll_index = self.current_index
            #if button_pos.x() < 0:
            #    # 如果按钮超出左边界，调整滚动值
            #    self.scroll_area.horizontalScrollBar().setValue(scroll_value + button_pos.x())
            #elif button_pos.x() + button_width > scroll_area_width:
            #    # 如果按钮超出右边界，调整滚动值
            #    self.scroll_area.horizontalScrollBar().setValue(scroll_value + (button_pos.x() + button_width - scroll_area_width))
    # 暂时去除键盘导航功能
    def move_selection(self, offset):
        """移动选择的游戏"""
        total_buttons = len(self.buttons)
        new_index = self.current_index + offset

        # 上下键逻辑，循环跳转
        if offset == -self.row_count:  # 上移一行
            if new_index < 0:
                column = self.current_index % self.row_count
                new_index = (total_buttons - 1) - (total_buttons - 1) % self.row_count + column
                if new_index >= total_buttons:
                    new_index -= self.row_count
        elif offset == self.row_count:  # 下移一行
            if new_index >= total_buttons:
                column = self.current_index % self.row_count
                new_index = column

        # 左右键逻辑，循环跳转
        if offset == -1 and new_index < 0:
            new_index = total_buttons - 1
        elif offset == 1 and new_index >= total_buttons:
            new_index = 0

        # 更新索引并高亮
        self.current_index = new_index
        self.update_highlight()
    
    def _cleanup_label_animations(self):
        """清理已完成的标签淡入淡出动画，释放内存"""
        if hasattr(self, '_label_fade_anims'):
            # 过滤掉已停止或已完成的动画
            self._label_fade_anims = [anim for anim in self._label_fade_anims if anim.state() == QPropertyAnimation.Running]

    # ===== 控制按钮标签显示方法 =====
    def _capture_window_thumbnail(self, hwnd, width=160, height=120):
        """捕获窗口的缩略图（使用 PrintWindow + Pillow，返回 QPixmap）"""
        # 如果窗口最小化或不可见，跳过
        if ctypes.windll.user32.IsIconic(hwnd) or not ctypes.windll.user32.IsWindowVisible(hwnd):
            return None
    
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bitmap)
        ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)

        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        # 从 BGRA 原始字节创建 Pillow 图像（不依赖 numpy）
        pil_img = Image.frombuffer("RGBA", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRA", 0, 1)

        # 将 Pillow 图像数据转为 QtImage
        data = pil_img.tobytes("raw", "RGBA")
        try:
            qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_RGBA8888)
        except AttributeError:
            # 兼容老版 PyQt5，尝试 ARGB32 并交换通道
            qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_ARGB32)
            qimg = qimg.rgbSwapped()

        pixmap = QPixmap.fromImage(qimg)
        pixmap = pixmap.scaledToWidth(width, Qt.SmoothTransformation)
        
        # 显式清理资源
        try:
            pil_img.close()
            del pil_img
            del data
            del qimg
            del bmpstr
        except Exception:
            pass
            
        return pixmap

    def _show_control_button_label(self, btn, index):
        """在控制按钮上方显示窗口缩略图，下方显示文字标签"""
        # 先单独获取翻译，避免在 dict 字面量中调用 self.tr() 导致上下文问题
        tr_screenshots = self.tr("全部截图")
        tr_settings = self.tr("设置")
        tr_sleep = self.tr("系统休眠")
        labels_map = {
            4: tr_screenshots,
            5: tr_settings,
            6: tr_sleep
        }
        title = ''
        if hasattr(btn, 'window_info') and btn.window_info:
            title = btn.window_info.get('title', '')
        if not title:
            if index == 6 and getattr(self, 'show_background_apps', False):
                title = self.tr("全部应用")
            else:
                title = labels_map.get(index, '')
        if not title:
            return

        if len(title) > 15:
            title = title[:15] + '...'

        # 先隐藏旧标签（淡出）
        self._hide_control_button_labels()

        # 计算位置
        try:
            btn_pos = btn.mapToGlobal(QPoint(0, 0))
            btn_size = btn.size()
        except Exception:
            btn_pos = QPoint(0, 0)
            btn_size = btn.size() if hasattr(btn, 'size') else QSize(0, 0)

        # ===== 显示窗口缩略图（上方）=====
        if hasattr(btn, 'window_info') and btn.window_info:
            hwnd = btn.window_info.get('hwnd')
            if hwnd:
                thumbnail = self._capture_window_thumbnail(hwnd, width=160, height=120)
                if thumbnail:
                    thumbnail_label = QLabel(self)
                    thumbnail_label.setPixmap(thumbnail)
                    thumbnail_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: rgba(30, 30, 30, 0.9);
                            border: 2px solid #555555;
                            border-radius: {int(8 * self.scale_factor)}px;
                            padding: {int(4 * self.scale_factor)}px;
                        }}
                    """)
                    thumbnail_label.adjustSize()
                    
                    # 计算缩略图位置（按钮上方居中）
                    thumb_x = btn_pos.x() + (btn_size.width() - thumbnail.width()) // 2
                    thumb_y = btn_pos.y() - thumbnail.height() - int(20 * self.scale_factor)
                    thumbnail_label.move(thumb_x, thumb_y)
                    
                    # 淡入动画
                    try:
                        eff = QtWidgets.QGraphicsOpacityEffect(thumbnail_label)
                        thumbnail_label.setGraphicsEffect(eff)
                        eff.setOpacity(0.0)
                        fade_in = QPropertyAnimation(eff, b"opacity")
                        fade_in.setDuration(180)
                        fade_in.setStartValue(0.0)
                        fade_in.setEndValue(1.0)
                        if not hasattr(self, '_label_fade_anims'):
                            self._label_fade_anims = []
                        self._label_fade_anims.append(fade_in)
                        fade_in.start()
                    except Exception:
                        pass
                    
                    thumbnail_label.show()
                    self._current_control_button_thumbnail = thumbnail_label

        # ===== 显示文字标签（下方）=====
        # 创建并样式化标签
        label = QLabel(title, self)
        label.setAlignment(Qt.AlignCenter)
        # 使用与 game_name_label 相同的样式：白色、大号字体
        label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei";
                color: white;
                font-size: {int(16 * self.scale_factor * 1.5)}px;
                background: transparent;
            }}
        """)

        label.adjustSize()
        label_x = btn_pos.x() + (btn_size.width() - label.width()) // 2
        label_y = btn_pos.y() + btn_size.height() + int(10 * self.scale_factor)
        label.move(label_x, label_y)

        # 淡入动画
        try:
            eff = QtWidgets.QGraphicsOpacityEffect(label)
            label.setGraphicsEffect(eff)
            eff.setOpacity(0.0)
            fade_in = QPropertyAnimation(eff, b"opacity")
            fade_in.setDuration(180)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            if not hasattr(self, '_label_fade_anims'):
                self._label_fade_anims = []
            self._label_fade_anims.append(fade_in)
            fade_in.start()
        except Exception:
            pass

        label.show()
        self._current_control_button_label = label
    
    def _hide_control_button_labels(self):
        """隐藏所有控制按钮标签和缩略图"""
        # 隐藏缩略图
        if hasattr(self, '_current_control_button_thumbnail') and self._current_control_button_thumbnail:
            try:
                old_thumb = self._current_control_button_thumbnail
                try:
                    eff_old_thumb = old_thumb.graphicsEffect()
                    if not isinstance(eff_old_thumb, QtWidgets.QGraphicsOpacityEffect):
                        eff_old_thumb = None
                except Exception:
                    eff_old_thumb = None
                if eff_old_thumb is None:
                    try:
                        eff_old_thumb = QtWidgets.QGraphicsOpacityEffect(old_thumb)
                        old_thumb.setGraphicsEffect(eff_old_thumb)
                    except Exception:
                        eff_old_thumb = None
                if eff_old_thumb is not None:
                    fade_out_thumb = QPropertyAnimation(eff_old_thumb, b"opacity")
                    fade_out_thumb.setDuration(180)
                    fade_out_thumb.setStartValue(1.0)
                    fade_out_thumb.setEndValue(0.0)
                    def _del_old_thumb():
                        try:
                            old_thumb.deleteLater()
                        except Exception:
                            pass
                    fade_out_thumb.finished.connect(_del_old_thumb)
                    if not hasattr(self, '_label_fade_anims'):
                        self._label_fade_anims = []
                    self._cleanup_label_animations()
                    self._label_fade_anims.append(fade_out_thumb)
                    fade_out_thumb.start()
                else:
                    try:
                        old_thumb.deleteLater()
                    except Exception:
                        pass
            except RuntimeError:
                pass
            self._current_control_button_thumbnail = None
        
        # 隐藏标签
        if hasattr(self, '_current_control_button_label') and self._current_control_button_label:
            try:
                old_label = self._current_control_button_label
                try:
                    eff_old = old_label.graphicsEffect()
                    if not isinstance(eff_old, QtWidgets.QGraphicsOpacityEffect):
                        eff_old = None
                except Exception:
                    eff_old = None
                if eff_old is None:
                    try:
                        eff_old = QtWidgets.QGraphicsOpacityEffect(old_label)
                        old_label.setGraphicsEffect(eff_old)
                    except Exception:
                        eff_old = None
                if eff_old is not None:
                    fade_out = QPropertyAnimation(eff_old, b"opacity")
                    fade_out.setDuration(180)
                    fade_out.setStartValue(1.0)
                    fade_out.setEndValue(0.0)
                    def _del_old():
                        try:
                            old_label.deleteLater()
                        except Exception:
                            pass
                    fade_out.finished.connect(_del_old)
                    if not hasattr(self, '_label_fade_anims'):
                        self._label_fade_anims = []
                    self._cleanup_label_animations()
                    self._label_fade_anims.append(fade_out)
                    fade_out.start()
                else:
                    try:
                        old_label.deleteLater()
                    except Exception:
                        pass
            except RuntimeError:
                pass
            self._current_control_button_label = None
    
    # ===== 后台任务切换相关方法 =====
    def get_running_windows(self):
        """获取所有正在运行的窗口列表，排除系统窗口"""
        windows = []
        def enum_window_callback(hwnd, lParam):
            try:
                if not win32gui.IsWindowVisible(hwnd): return True
                try: style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                except: style = 0
                if style & win32con.WS_CHILD: return True
                try:
                    DWMWA_CLOAKED = 14
                    cloaked = ctypes.c_int(0)
                    res = ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                    if res == 0 and cloaked.value != 0: return True
                except: pass
                try: ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                except: ex_style = 0
                if (ex_style & win32con.WS_EX_TOOLWINDOW) and not (ex_style & win32con.WS_EX_APPWINDOW): return True
                owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
                if owner and not (ex_style & win32con.WS_EX_APPWINDOW): return True
                title = win32gui.GetWindowText(hwnd)
                if not title or not title.strip(): return True
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    exe_path = process.exe()
                    exe_name = os.path.basename(exe_path)
                    if exe_name.lower() in ['tabtip.exe','svchost.exe','csrss.exe','dwm.exe','taskhostw.exe','searchui.exe','searchprotocolhost.exe','runtimebroker.exe','shellexperiencehost.exe','systemsettings.exe','simplenite.exe']:
                        return True
                    windows.append({'hwnd': hwnd,'title': title,'pid': pid,'exe_path': exe_path,'exe_name': exe_name})
                except: return True
            except: return True
            return True
        win32gui.EnumWindows(enum_window_callback, None)
        return windows
    
    def get_window_icon(self, exe_path, size=40):
        """从可执行文件获取图标"""
        icon = QIcon()
        try:
            from icoextract import IconExtractor
            extractor = IconExtractor(exe_path)
            bio = extractor.get_icon(num=0)
            data = bio.getvalue()
            pix = QPixmap()
            if pix.loadFromData(data):
                pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon = QIcon(pix)
                return icon
        except Exception:
            pass
        
        # 尝试使用系统默认方式获取图标
        try:
            # 尝试从应用本身获取图标（通过文件管理器API）
            from PIL import Image
            import io
            
            # 使用 Windows 图标缓存
            result = ctypes.windll.shell32.ExtractIconW(None, exe_path, 0)
            if result:
                # 将句柄转换为 QPixmap（这比较复杂，通常不推荐）
                return QIcon()
        except Exception:
            pass
        
        return icon
    
    def _create_text_placeholder_icon(self, text, size_px):
        """根据文本生成占位图标"""
        ch = text.strip()[0] if text and text.strip() else '?'
        pix = QPixmap(QSize(size_px, size_px))
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        # 背景圆角矩形
        bg_color = QColor(80, 80, 80)
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        radius = int(size_px * 0.2)
        painter.drawRoundedRect(0, 0, size_px, size_px, radius, radius)
        # 绘制文字
        font = QFont("Microsoft YaHei", max(10, int(size_px * 0.5)))
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        fm = QtGui.QFontMetrics(font)
        w = fm.horizontalAdvance(ch)
        h = fm.height()
        painter.drawText((size_px - w) // 2, (size_px + h) // 2 - fm.descent(), ch)
        painter.end()
        return QIcon(pix)
    
    def update_background_buttons(self):
        """更新前3个按钮的显示，显示后台应用程序图标"""
        self.background_windows = self.get_running_windows()
        
        # 显示前3个后台应用图标
        for i in range(4):
            btn = self.control_buttons[i]
            if i < len(self.background_windows):
                window_info = self.background_windows[i]
                # 不设置文本，仅保存窗口信息
                btn.setText('')  # 清空文本
                
                # 尝试设置图标
                icon = self.get_window_icon(window_info['exe_path'], size=int(50 * self.scale_factor))
                # 如果有可用图标则直接使用，否则用窗口标题的第一个字符生成占位图标
                if icon and not icon.isNull():
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(int(50 * self.scale_factor), int(50 * self.scale_factor)))
                else:
                    title = window_info.get('title', '') if window_info else ''
                    size_px = int(50 * self.scale_factor)
                    icon = self._create_text_placeholder_icon(title, size_px)
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(size_px, size_px))

                # 保存窗口信息到按钮（用于点击时调用）
                btn.window_info = window_info
                btn.setVisible(True)
            else:
                btn.setText('')
                btn.setIcon(QIcon())
                btn.window_info = None
                btn.setVisible(True)
        
        # 无论后台应用数量多少，都更新额外按钮
        self.create_extra_background_buttons()
    
    def on_background_button_clicked(self, button_index):
        """处理后台任务按钮点击事件"""
        btn = self.control_buttons[button_index]
        if hasattr(btn, 'window_info') and btn.window_info:
            if not settings.get("skip_minimize_on_game_open", False):
                self.hide_window()
            def wake_window():
                window_info = btn.window_info
                hwnd = window_info['hwnd']
                # 检查窗口是否存在
                if not win32gui.IsWindow(hwnd):
                    # 如果窗口不存在，刷新后台窗口列表
                    self.update_background_buttons()
                    return
                # 恢复窗口
                if win32gui.IsIconic(hwnd):  # 窗口已最小化
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
            QTimer.singleShot(200, wake_window)
    
    def create_extra_background_buttons(self):
        """为超过3个的后台应用在 left_label 后面创建按钮"""
        # 确保texta_layout和left_label已经初始化
        if not hasattr(self, 'texta_layout') or not self.texta_layout or not hasattr(self, 'left_label') or not self.left_label:
            return
        
        # 如果少于等于4个应用，不需要额外按钮，确保移除所有额外按钮与相关引用
        if len(self.background_windows) <= 4:
            # 移除布局中除 left_label/right_label 外的 widget
            current_extra_buttons = []
            for i in range(self.texta_layout.count()):
                widget = self.texta_layout.itemAt(i).widget()
                if widget and widget != self.left_label and widget != self.right_label:
                    current_extra_buttons.append(widget)

            # 移除所有当前的额外按钮
            for widget in current_extra_buttons:
                try:
                    self.texta_layout.removeWidget(widget)
                    widget.deleteLater()
                except Exception as e:
                    print(f"Error removing extra buttons: {e}")

            # 额外保险：如果存在单独保存的 extra_background_button，显式移除并清理引用
            try:
                if hasattr(self, 'extra_background_button') and self.extra_background_button:
                    try:
                        self.texta_layout.removeWidget(self.extra_background_button)
                    except Exception:
                        pass
                    try:
                        self.extra_background_button.deleteLater()
                    except Exception:
                        pass
                    self.extra_background_button = None
            except Exception as e:
                print(f"Error clearing extra_background_button ref: {e}")

            # 更新布局
            try:
                self.texta_layout.update()
                if self.texta_layout.parentWidget():
                    self.texta_layout.parentWidget().update()
            except Exception:
                pass
            return
        
        # 移除旧的额外按钮（包括保存在实例变量中的按钮），确保干净地清理引用
        current_extra_buttons = []
        for i in range(self.texta_layout.count()):
            widget = self.texta_layout.itemAt(i).widget()
            if widget and widget != self.left_label and widget != self.right_label:
                current_extra_buttons.append(widget)

        # 移除所有当前的额外按钮
        for widget in current_extra_buttons:
            try:
                self.texta_layout.removeWidget(widget)
                widget.deleteLater()
            except Exception as e:
                print(f"Error removing old extra buttons: {e}")

        # 额外保险：如果存在单独保存的 extra_background_button，显式移除并清理引用
        try:
            if hasattr(self, 'extra_background_button') and self.extra_background_button:
                try:
                    self.texta_layout.removeWidget(self.extra_background_button)
                except Exception:
                    pass
                try:
                    self.extra_background_button.deleteLater()
                except Exception:
                    pass
                self.extra_background_button = None
        except Exception as e:
            print(f"Error clearing extra_background_button ref: {e}")
        
        # 为超过3个的应用添加一个大按钮
        if len(self.background_windows) > 4:
            # 计算可用宽度：屏幕宽度 - 左右标签的最小宽度 - 边距
            screen_width = QApplication.primaryScreen().geometry().width()
            left_label_width = self.left_label.sizeHint().width() if self.left_label else int(200 * self.scale_factor)
            right_label_width = self.right_label.sizeHint().width() if self.right_label else int(600 * self.scale_factor)
            margin_space = int(100 * self.scale_factor)  # 边距和间距
            max_available_width = screen_width - left_label_width - right_label_width - margin_space
            max_available_width = max(max_available_width, int(100 * self.scale_factor))  # 至少100px
            
            # 获取所有额外应用的图标（放大一倍）
            extra_icons = []
            for i in range(4, len(self.background_windows)):
                window_info = self.background_windows[i]
                icon = self.get_window_icon(window_info['exe_path'], size=int(36 * self.scale_factor))  # 放大一倍图标
                if icon and not icon.isNull():
                    extra_icons.append(icon.pixmap(QSize(int(36 * self.scale_factor), int(36 * self.scale_factor))))
                else:
                    # 图标加载失败，使用文字占位图标
                    title = window_info.get('title', '') if window_info else ''
                    icon = self._create_text_placeholder_icon(title, int(36 * self.scale_factor))
                    extra_icons.append(icon.pixmap(QSize(int(36 * self.scale_factor), int(36 * self.scale_factor))))
            
            btn = QPushButton()
            btn_height = int(50 * self.scale_factor)
            
            # 计算图标区域宽度
            icon_size = int(36 * self.scale_factor)
            icon_spacing = int(6 * self.scale_factor)
            total_icons_width = len(extra_icons) * icon_size + (len(extra_icons) - 1) * icon_spacing
            padding = int(24 * self.scale_factor)
            needed_width = total_icons_width + padding
            
            # 如果超出可用宽度，限制图标数量并显示 +N
            max_icons = 0
            display_count = 0
            if needed_width > max_available_width:
                # 计算能显示多少个图标
                max_icons = max(1, (max_available_width - padding - int(50 * self.scale_factor)) // (icon_size + icon_spacing))
                display_count = len(extra_icons) - max_icons
                btn_width = max_icons * icon_size + (max_icons - 1) * icon_spacing + padding + int(50 * self.scale_factor)
            else:
                max_icons = len(extra_icons)
                btn_width = needed_width
            
            btn_width = min(btn_width, max_available_width)
            btn_width = max(btn_width, int(60 * self.scale_factor))  # 最小宽度
            btn.setFixedSize(btn_width, btn_height)
            
            # 设置样式
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border-radius: {int(8 * self.scale_factor)}px;
                    border: 0px solid transparent;
                    margin-left: 0px;
                    margin-right: {int(10 * self.scale_factor)}px;
                    text-align: left;
                    padding-left: {int(12 * self.scale_factor)}px;
                    padding-right: {int(12 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.08);
                    border: {int(2 * self.scale_factor)}px solid rgba(85, 85, 85, 0.75);
                }}
            """)
            
            # 创建合成图标
            if extra_icons:
                # 限制显示的图标数量
                display_icons = extra_icons[:max_icons] if max_icons > 0 else extra_icons[:1]
                num_icons = len(display_icons)
                
                composite_size = QSize(
                    num_icons * icon_size + (num_icons - 1) * icon_spacing,
                    icon_size
                )
                
                # 创建合成图像
                composite_pixmap = QPixmap(composite_size)
                composite_pixmap.fill(Qt.transparent)  # 设置背景透明
                
                painter = QPainter(composite_pixmap)
                
                # 绘制图标
                for i, pixmap in enumerate(display_icons):
                    x = i * (icon_size + icon_spacing)
                    y = 0
                    painter.drawPixmap(x, y, pixmap)
                
                painter.end()
                
                # 设置合成图标到按钮
                btn.setIcon(QIcon(composite_pixmap))
                btn.setIconSize(composite_size)
                
                # 如果有更多图标，显示 +N 文本
                if display_count > 0:
                    btn.setText(f"+{display_count}")
                    # 调整样式以同时显示图标和文本
                    btn.setStyleSheet(btn.styleSheet() + f"""
                        QPushButton {{
                            font-size: {int(20 * self.scale_factor)}px;
                            color: white;
                        }}
                    """)
            else:
                # 如果没有图标，显示额外应用的数量
                extra_apps_count = len(self.background_windows) - 3
                btn_width = int(80 * self.scale_factor) + len(str(extra_apps_count)) * int(24 * self.scale_factor)
                btn_width = min(btn_width, max_available_width)
                btn.setFixedSize(btn_width, btn_height)
                btn.setText(f"+{extra_apps_count}")
                btn.setStyleSheet(btn.styleSheet() + f"font-size: {int(36 * self.scale_factor)}px;")
            # 点击额外按钮时，切换所有按钮到后台任务模式
            btn.clicked.connect(self.switch_all_buttons_to_background_mode)
            
            # 存储额外按钮引用
            self.extra_background_button = btn
            
            # 直接添加到texta_layout中，位于left_label之后，设置靠左对齐并设置固定宽度
            left_label_index = self.texta_layout.indexOf(self.left_label)
            if left_label_index >= 0:
                # 先移除右侧标签
                right_label_index = self.texta_layout.indexOf(self.right_label)
                if right_label_index >= 0:
                    self.texta_layout.takeAt(right_label_index)
                
                # 添加按钮
                self.texta_layout.insertWidget(left_label_index + 1, btn, alignment=Qt.AlignLeft)
                
                # 添加一个伸缩空间
                self.texta_layout.addStretch()
                
                # 重新添加右侧标签
                self.texta_layout.addWidget(self.right_label, alignment=Qt.AlignRight)
                
                # 添加从上至下飞入的动画
                # 强制布局更新以确保按钮有正确的几何位置
                QApplication.processEvents()
                self.texta_layout.update()
                if self.texta_layout.parentWidget():
                    self.texta_layout.parentWidget().update()
                QApplication.processEvents()
                
                # 获取按钮当前位置和大小
                end_geometry = btn.geometry()
                
                # 计算起始位置（上方，不可见）
                start_geometry = QRect(
                    end_geometry.x(),
                    end_geometry.y() - 20,  # 从上方20像素开始
                    end_geometry.width(),
                    end_geometry.height()
                )
                
                # 设置按钮到起始位置
                btn.setGeometry(start_geometry)
                btn.show()  # 确保按钮可见
                
                # 创建飞入动画并存储为实例变量以防被回收
                if hasattr(self, 'fly_in_animation') and self.fly_in_animation:
                    self.fly_in_animation.stop()
                    self.fly_in_animation.deleteLater()
                    
                self.fly_in_animation = QPropertyAnimation(btn, b"geometry")
                self.fly_in_animation.setDuration(300)
                self.fly_in_animation.setStartValue(start_geometry)
                self.fly_in_animation.setEndValue(end_geometry)
                self.fly_in_animation.setEasingCurve(QEasingCurve.OutCubic)
                self.fly_in_animation.start()
        
        # 更新布局
        self.texta_layout.update()
        if self.texta_layout.parentWidget():
            self.texta_layout.parentWidget().update()
    
    def switch_all_buttons_to_background_mode(self):
        """将前6个按钮设为任务按钮，第7个设为'显示全部'"""
        # 切换到控制按钮区域并设置当前索引
        if getattr(self, 'show_background_apps', True):
            return  # 已经是后台应用模式，直接返回
        # 隐藏额外按钮并添加向上消失的动画
        if hasattr(self, 'extra_background_button') and self.extra_background_button:
            # 检查按钮是否仍然有效
            try:
                # 尝试访问按钮的属性以检查其有效性
                _ = self.extra_background_button.isVisible()
            except RuntimeError:
                return
            # 创建向上消失的动画
            if hasattr(self, 'animation') and self.animation:
                self.animation.stop()
                self.animation.deleteLater()
                
            self.animation = QPropertyAnimation(self.extra_background_button, b"geometry")
            self.animation.setDuration(150)
            
            # 获取按钮当前位置和大小
            start_geometry = self.extra_background_button.geometry()
            
            # 计算结束位置（向上移动并缩小）
            end_geometry = QRect(
                start_geometry.x(),
                start_geometry.y() - 50,  # 向上移动50像素
                start_geometry.width(),
                start_geometry.height()
            )
            self.animation.setStartValue(start_geometry)
            self.animation.setEndValue(end_geometry)
            self.animation.setEasingCurve(QEasingCurve.OutCubic)
            
            # 动画结束后隐藏按钮和更新背景窗口
            def on_animation_finished():
                self.extra_background_button.hide()
                self.current_section = 1  # 切换到控制按钮区域
                self.current_index = 0  # 设置按钮索引
                self.update_highlight()
            
            self.animation.finished.connect(on_animation_finished)
            self.animation.start()
            # 直接更新后台窗口列表
            self.background_windows = self.get_running_windows()
            self.show_background_apps = True
            # 获取剩余的应用（跳过前3个）
            remaining_windows = self.background_windows[4:]
            # 存储剩余应用数量用于导航限制
            self.remaining_windows_count = len(remaining_windows)
            
            # 遍历前6个控制按钮作为任务按钮
            for i in range(6):
                btn = self.control_buttons[i]
                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass
                
                btn.setText('')
                btn.setIcon(QIcon())
                btn.window_info = None
                
                if i < len(remaining_windows):
                    window_info = remaining_windows[i]
                    icon = self.get_window_icon(window_info['exe_path'], size=int(50 * self.scale_factor))
                    if icon and not icon.isNull():
                        btn.setIcon(icon)
                        btn.setIconSize(QSize(int(50 * self.scale_factor), int(50 * self.scale_factor)))
                    else:
                        title = window_info.get('title', '') if window_info else ''
                        size_px = int(50 * self.scale_factor)
                        icon = self._create_text_placeholder_icon(title, size_px)
                        btn.setIcon(icon)
                        btn.setIconSize(QSize(size_px, size_px))
                    
                    btn.window_info = window_info
                    
                    def on_click(checked=False, idx=i, info=window_info):
                        if self.current_section != 1 or self.current_index != idx:
                            self.current_section = 1
                            self.current_index = idx
                            self.update_highlight()
                            return
                        self.restore_background_window(info)

                    btn.clicked.connect(on_click)
                    btn.setVisible(True)
                else:
                    btn.setVisible(False)

            # 处理第7个按钮
            show_all_btn = self.control_buttons[6]
            try:
                show_all_btn.clicked.disconnect()
            except TypeError:
                pass

            if len(remaining_windows) > 6:
                show_all_btn.setText("...")  # 或其他图标
                show_all_btn.setIcon(QIcon()) # 清除旧图标
                show_all_btn.setVisible(True)
                
                def show_all_apps():
                    self.hide_window()
                    # 模拟 Win + Tab
                    pyautogui.keyDown('win')
                    pyautogui.press('tab')
                    pyautogui.keyUp('win')

                show_all_btn.clicked.connect(show_all_apps)
            else:
                show_all_btn.setVisible(False)
    
    def restore_control_buttons(self):
        """将控制按钮区域恢复为初始模样（4后台+3功能键）"""
        # 重置显示状态
        self.show_background_apps = False
        
        # 恢复前3个按钮为后台任务按钮
        self.update_background_buttons()
        
        # 恢复所有按钮的点击事件和显示状态
        for i in range(7):
            btn = self.control_buttons[i]
            try:
                btn.clicked.disconnect()
            except TypeError:
                pass
            
            if i < 4:
                # 前3个按钮已通过update_background_buttons更新
                pass
            elif i == 4:
                btn.setText("🗺️")
                btn.setIcon(QIcon())
            elif i == 5:
                btn.setText("⚙️")
                btn.setIcon(QIcon())
            elif i == 6:
                btn.setText("💤")
                btn.setIcon(QIcon())
            
            # 重新连接到原始处理器
            btn.clicked.connect(lambda checked=False, idx=i: self.handle_control_button_click(idx))
            btn.setVisible(True)
        
        # 显示额外后台按钮（如果需要）
        if len(self.background_windows) > 3:
            self.create_extra_background_buttons()
    
    def restore_background_window(self, window_info):
        """恢复后台窗口"""
        hwnd = window_info['hwnd']
        try:
            if win32gui.IsIconic(hwnd):  # 窗口已最小化
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        if not settings.get("skip_minimize_on_game_open", False):
            self.hide_window()

    # 焦点检测
    def gsfocus(self):
        # 获取当前活动窗口句柄
        hwnd = win32gui.GetForegroundWindow()
        if hwnd == GSHWND or globals().get("FSPREVIEWHWND", None) is not None and hwnd == globals().get("FSPREVIEWHWND"):
            return True
        else:
            return False
    
    def restore_window(self, game_path):
        for process in psutil.process_iter(['pid', 'exe']):
                    try:
                        if process.info['exe'] and process.info['exe'].lower() == game_path.lower():
                            pid = process.info['pid']

                            # 查找进程对应的窗口
                            def enum_window_callback(hwnd, lParam):
                                _, current_pid = win32process.GetWindowThreadProcessId(hwnd)
                                if current_pid == pid:
                                    # 获取窗口的可见性
                                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                                    # 如果窗口的样式包含 WS_VISIBLE，则表示该窗口是可见的
                                    if style & win32con.WS_VISIBLE:
                                        # 恢复窗口并将其置前
                                        if win32gui.IsIconic(hwnd):  # 窗口已最小化
                                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                        win32gui.SetForegroundWindow(hwnd)
                                        print(f"已将进程 {pid} 的窗口带到前台")
                                        self.switch_to_main_interface()

                            # 枚举所有窗口
                            win32gui.EnumWindows(enum_window_callback, None)
                            return
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass

    def _show_process_selector_for_game(self, game_name):
        """为指定游戏弹出后台窗口选择器"""
        scale = self.scale_factor
        # 获取后台窗口列表
        windows = self.get_running_windows() if hasattr(self, 'get_running_windows') else []
        # 去重：同一个exe只保留一个
        seen_exes = set()
        unique_windows = []
        for w in windows:
            exe_lower = w['exe_path'].lower()
            if exe_lower not in seen_exes:
                seen_exes.add(exe_lower)
                unique_windows.append(w)

        # 创建选择对话框
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(self.tr("选择后台窗口"))
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(12 * scale)}px;
                border: {int(2 * scale)}px solid #444444;
            }}
        """)

        main_layout = QtWidgets.QVBoxLayout(dialog)
        main_layout.setSpacing(int(12 * scale))
        main_layout.setContentsMargins(int(20 * scale), int(20 * scale), int(20 * scale), int(20 * scale))

        # 标题
        title_label = QtWidgets.QLabel(self.tr("为 %1 选择进程").replace('%1', game_name))
        title_label.setStyleSheet(f"color: #aaa; font-size: {int(18 * scale)}px;")
        main_layout.addWidget(title_label)

        # 网格布局
        grid_widget = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid_widget)
        grid_layout.setSpacing(int(10 * scale))
        grid_layout.setContentsMargins(0, 0, 0, 0)

        dialog.buttons = []
        dialog.current_index = 0
        cols = 4

        def make_select_handler(win_info):
            return lambda: self._save_custom_valid_app_and_refresh(game_name, win_info['exe_path']) or dialog.accept()

        for idx, win in enumerate(unique_windows):
            row = idx // cols
            col = idx % cols
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(int(120 * scale), int(100 * scale))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #444444;
                    color: white;
                    border-radius: {int(8 * scale)}px;
                    font-size: {int(11 * scale)}px;
                    padding: {int(4 * scale)}px;
                }}
                QPushButton:hover {{
                    background-color: #555555;
                }}
            """)
            # 图标
            icon = self.get_window_icon(win['exe_path'], size=int(40 * scale)) if hasattr(self, 'get_window_icon') else QtGui.QIcon()
            if icon and not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(int(40 * scale), int(40 * scale)))
            # 文本：窗口标题（截断）
            title = win['title'][:12] + "..." if len(win['title']) > 12 else win['title']
            btn.setText(title)
            btn.setToolTip(f"{win['exe_name']}\n{win['exe_path']}")
            btn.clicked.connect(make_select_handler(win))
            grid_layout.addWidget(btn, row, col)
            dialog.buttons.append(btn)

        # 手动选择文件按钮（放在最后一行）
        manual_btn = QtWidgets.QPushButton(self.tr("+ 手动选择文件"))
        manual_btn.setFixedHeight(int(50 * scale))
        manual_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #5f5f5f;
                color: white;
                border-radius: {int(8 * scale)}px;
                font-size: {int(14 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #808080;
            }}
        """)
        manual_btn.clicked.connect(lambda: dialog.accept() or self._show_manual_file_picker_for_game(game_name))
        grid_layout.addWidget(manual_btn, (len(unique_windows) + cols - 1) // cols, 0, 1, cols)
        dialog.buttons.append(manual_btn)

        main_layout.addWidget(grid_widget)

        # 手柄高亮更新
        def update_highlight():
            for i, btn in enumerate(dialog.buttons):
                if i == dialog.current_index:
                    btn.setStyleSheet(btn.styleSheet().replace("background-color: #444444;", "background-color: #2E7D9B; border: 2px solid #93ffff;").replace("background-color: #5f5f5f;", "background-color: #2E7D9B; border: 2px solid #93ffff;"))
                else:
                    btn.setStyleSheet(btn.styleSheet().replace("background-color: #2E7D9B; border: 2px solid #93ffff;", "background-color: #444444;").replace("background-color: #2E7D9B; border: 2px solid #93ffff;", "background-color: #5f5f5f;"))
        dialog.update_highlight = update_highlight
        dialog.update_highlight()

        # 键盘事件
        def keyPressEvent(event):
            if event.key() in (Qt.Key_Up, Qt.Key_W):
                dialog.current_index = max(0, dialog.current_index - cols)
                dialog.update_highlight()
            elif event.key() in (Qt.Key_Down, Qt.Key_S):
                dialog.current_index = min(len(dialog.buttons) - 1, dialog.current_index + cols)
                dialog.update_highlight()
            elif event.key() in (Qt.Key_Left, Qt.Key_A):
                dialog.current_index = max(0, dialog.current_index - 1)
                dialog.update_highlight()
            elif event.key() in (Qt.Key_Right, Qt.Key_D):
                dialog.current_index = min(len(dialog.buttons) - 1, dialog.current_index + 1)
                dialog.update_highlight()
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                dialog.buttons[dialog.current_index].click()
            elif event.key() == Qt.Key_Escape:
                dialog.reject()
        dialog.keyPressEvent = keyPressEvent

        # 手柄事件
        def handle_gamepad_input(action):
            if action in ('UP', 'FIRST-UP'):
                dialog.current_index = max(0, dialog.current_index - cols)
                dialog.update_highlight()
            elif action in ('DOWN', 'FIRST-DOWN'):
                dialog.current_index = min(len(dialog.buttons) - 1, dialog.current_index + cols)
                dialog.update_highlight()
            elif action in ('LEFT', 'FIRST-LEFT'):
                dialog.current_index = max(0, dialog.current_index - 1)
                dialog.update_highlight()
            elif action in ('RIGHT', 'FIRST-RIGHT'):
                dialog.current_index = min(len(dialog.buttons) - 1, dialog.current_index + 1)
                dialog.update_highlight()
            elif action == 'A':
                dialog.buttons[dialog.current_index].click()
            elif action == 'B':
                dialog.reject()
        dialog.handle_gamepad_input = handle_gamepad_input

        self.active_dialog = dialog
        dialog.exec_()
        self.active_dialog = None

    def _save_custom_valid_app_and_refresh(self, game_name, path):
        """保存自定义进程并刷新界面"""
        if not game_name or not path:
            return
        if "custom_valid_apps" not in settings:
            settings["custom_valid_apps"] = []
        settings["custom_valid_apps"] = [
            item for item in settings["custom_valid_apps"] if item.get("name") != game_name
        ]
        settings["custom_valid_apps"].append({"name": game_name, "path": path})
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        global valid_apps
        valid_apps = [app for app in valid_apps if app.get("name") != game_name]
        valid_apps.append({"name": game_name, "path": path})
        load_apps()
        # 从 need_select_process 中移除并刷新界面
        if hasattr(self, 'need_select_process') and game_name in self.need_select_process:
            self.need_select_process.remove(game_name)
            self.reload_interface()
        if hasattr(self, "deep_reload_games"):
            self.deep_reload_games()

    def _show_manual_file_picker_for_game(self, game_name):
        """手动选择文件"""
        picker = CustomFilePickerDialog(
            parent=self,
            scale_factor=self.scale_factor,
            file_types=['.exe', '.lnk']
        )
        picker.setWindowTitle(self.tr("选择自定义进程"))
        picker.file_selected.connect(lambda path: self._save_custom_valid_app_and_refresh(game_name, path))
        # 使用 FileDialogManager 包装以支持手柄转发
        self.file_dialog_manager = FileDialogManager(self, scale_factor=self.scale_factor)
        self.file_dialog_manager.dialog = picker
        picker.dialog_closed.connect(lambda: setattr(self, 'file_dialog_manager', None))
        self.file_dialog_manager.show_dialog()

    def _on_floating_add_file_selected(self, selected_file):
        """处理 FloatingWindow 添加文件选择（在 GameSelector 上执行，确保 FloatingWindow 关闭后仍能处理）"""
        try:
            bat_dir = './morefloder'
            if not os.path.exists(bat_dir):
                os.makedirs(bat_dir)
            
            # 从文件名生成快捷方式名
            file_name = os.path.splitext(os.path.basename(selected_file))[0]
            shortcut_name = file_name + ".lnk"
            shortcut_path = os.path.join(bat_dir, shortcut_name)
            
            # 如果是lnk文件，直接复制
            if selected_file.endswith('.lnk'):
                shutil.copy(selected_file, shortcut_path)
            else:
                # 创建新的快捷方式
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.TargetPath = selected_file
                shortcut.WorkingDirectory = os.path.dirname(selected_file)
                shortcut.save()
            
            print(f"快捷方式已创建: {shortcut_path}")
            load_morefloder_shortcuts()
            
            # 重新加载 FloatingWindow 按钮
            if hasattr(self, 'floating_window') and self.floating_window:
                fw = self.floating_window
                if 0 in fw.tab_buttons:
                    for btn in fw.tab_buttons[0]:
                        if btn != fw.select_add_btn and btn != fw.select_del_btn:
                            btn.setParent(None)
                            if btn in fw.buttons:
                                fw.buttons.remove(btn)
                    fw.tab_buttons[0] = []
                fw.create_buttons()
                fw.update_highlight()
                fw.show()
        except Exception as e:
            print(f"添加文件出错: {e}")
        finally:
            # 清理 file_dialog_manager
            if hasattr(self, 'file_dialog_manager'):
                self.file_dialog_manager = None

    def _on_floating_add_file_dialog_closed(self):
        """文件选择对话框关闭后恢复 FloatingWindow"""
        if hasattr(self, 'floating_window') and self.floating_window and not self.floating_window.isVisible():
            self.floating_window.show()
        # 清理 file_dialog_manager
        if hasattr(self, 'file_dialog_manager'):
            self.file_dialog_manager = None

    def launch_game(self, index):
        """启动选中的游戏"""
        sorted_games = self.sort_games()
        game = sorted_games[index]
        game_cmd = game["cmd"]
        game_name = game["name"]
        image_path = game.get("image-path", "")
        if not os.path.isabs(image_path):
            image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
        self.ignore_input_until = pygame.time.get_ticks() + 600

        # 如果该游戏标记为需要选择进程，直接弹出后台窗口选择器
        if hasattr(self, 'need_select_process') and game_name in self.need_select_process:
            self._show_process_selector_for_game(game_name)
            return

        # 点击反馈：对被点击的按钮触发更大幅度的脉冲动画（保持引用以防被回收）
        try:
            if 0 <= index < len(self.buttons):
                clicked_btn = self.buttons[index]
                try:
                    eff = clicked_btn.graphicsEffect()
                    if not isinstance(eff, QtWidgets.QGraphicsDropShadowEffect):
                        eff = None
                except Exception:
                    eff = None
                if eff is None:
                    try:
                        eff = QtWidgets.QGraphicsDropShadowEffect(clicked_btn)
                        eff.setColor(QColor("#93ffff"))
                        eff.setBlurRadius(10)
                        eff.setOffset(0, 0)
                        clicked_btn.setGraphicsEffect(eff)
                    except Exception:
                        eff = None
                if eff is not None:
                    try:
                        pulse = QPropertyAnimation(eff, b"blurRadius")
                        pulse.setDuration(200)
                        pulse.setStartValue(10)
                        pulse.setKeyValueAt(0.2, 120)
                        pulse.setEndValue(10)
                        try:
                            from PyQt5.QtCore import QEasingCurve
                            pulse.setEasingCurve(QEasingCurve.OutCubic)
                        except Exception:
                            pass
                        if not hasattr(self, '_click_pulse_anims'):
                            self._click_pulse_anims = []
                        self._click_pulse_anims.append(pulse)
                        def _on_pulse_finished(effect=eff, button=clicked_btn):
                            try:
                                if button.graphicsEffect() is effect:
                                    button.setGraphicsEffect(None)
                                if hasattr(self, '_click_pulse_anims'):
                                    try:
                                        self._click_pulse_anims.remove(pulse)
                                    except ValueError:
                                        pass
                            except Exception:
                                pass
                        pulse.finished.connect(_on_pulse_finished)
                        pulse.start()
                        # 阻塞当前函数直到动画结束，但保持 UI 响应（使用本地事件循环）
                        try:
                            from PyQt5.QtCore import QEventLoop
                            loop = QEventLoop()
                            pulse.finished.connect(loop.quit)
                            try:
                                loop.exec_()
                            except AttributeError:
                                loop.exec()
                        except Exception:
                            pass
                    except Exception:
                        pass
        except Exception:
            pass

        if self.more_section == 0 and self.current_index == self.buttonsindexset: # 如果点击的是"更多"按钮
            self.switch_to_all_software()
            return
        #冻结相关
        if os.path.exists("./_internal/pssuspend64.exe") and self.freeze:
            for app in valid_apps:
                if app["name"] == game_name:
                    game_path = app["path"]
                    break
            else:
                game_path = None
            if game_path:
                for process in psutil.process_iter(['pid', 'exe', 'status']):
                    try:
                        if process.info['exe'] and process.info['exe'].lower() == game_path.lower():
                            # 检查进程状态是否为挂起（Windows下为 'stopped'）
                            if process.status() == psutil.STATUS_STOPPED:
                                # 恢复挂起
                                subprocess.Popen(
                                    ['./_internal/pssuspend64.exe', '-r', os.path.basename(game_path)],
                                    creationflags=subprocess.CREATE_NO_WINDOW
                                )
                                time.sleep(0.5)  # 等待恢复
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
        # 恢复窗口
        if game["name"] in self.player:
            for app in valid_apps:
                if app["name"] == game["name"]:
                    game_path = app["path"]
                    breakpoint
            if not settings.get("skip_minimize_on_game_open", False):
                self.hide_window()
            QTimer.singleShot(100, lambda: self.restore_window(game_path))
            return
        if self.player:
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog(self.tr("已经打开了一个游戏，还要再打开一个吗？"), scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            else:
                pass
        if not self.launch_overlay:
            self.launch_overlay = LaunchOverlay(self)
        self.launch_overlay.show_launch_window(game_name, image_path)
        self.switch_to_main_interface()
        self.current_index = 0  # 从第一个按钮开始
        # 更新最近游玩列表
        if game["name"] in settings["last_played"]:
            settings["last_played"].remove(game["name"])
        settings["last_played"].insert(0, game["name"])
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

        self.reload_interface()
        self.ignore_input_until = pygame.time.get_ticks() + 1000
        # 新增：如果该游戏在 on_mapping_clicked 里，自动开启鼠标映射
        if "on_mapping_clicked" in settings and game_name in settings["on_mapping_clicked"]:
            self.mouse_simulation()
        # 启动关联工具（避免重复启动）
        for item in settings.get("custom_tools", []):
            if item["name"] == game_name:
                for tool in item.get("tools", []):
                    tool_path = tool.get("path")
                    if tool_path and os.path.exists(tool_path):
                        # 检查是否已运行
                        already_running = False
                        for proc in psutil.process_iter(['exe']):
                            try:
                                if proc.info['exe'] and os.path.abspath(proc.info['exe']) == os.path.abspath(tool_path):
                                    already_running = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                continue
                        if not already_running:
                            run_as_user(tool_path)
        if game_cmd:
            #self.showMinimized()
            # subprocess.Popen(game_cmd, shell=True)
            run_as_user(game_cmd)  # 使用run_as_user启动游戏
            #self.showFullScreen()
            return
        # 新增：处理detached字段，优先启动detached中的.url
        detached_list = game.get("detached", [])
        if detached_list:
            url_path = detached_list[0].strip('"')  # 去掉前后引号
            if url_path.lower().endswith('.url'):
                run_as_user(url_path)
        # 检查 game["name"] 是否能在 valid_apps["name"] 里找到
        if not any(app["name"] == game["name"] for app in valid_apps):
            # 标记为需要选择进程（内存变量，不写入硬盘）
            if game["name"] not in self.need_select_process:
                self.need_select_process.append(game["name"])
            self.reload_interface()
            return
        
    # 判断当前窗口是否全屏(当设置中开启时)
    def is_current_window_fullscreen(self):
        try:
            # 获取当前活动窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                print("未找到活动窗口")
                return False  # 未找到活动窗口
    
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                exe_path = process.exe()
                exe_name = os.path.basename(exe_path)
            except e:
                print(f"获取进程信息失败: {e}")
            if exe_name == "explorer.exe":
                print("当前窗口为桌面")
                return False  # 忽略桌面
            # 获取屏幕分辨率
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    
            # 获取窗口位置和大小
            rect = win32gui.GetWindowRect(hwnd)
            window_width = rect[2] - rect[0]
            window_height = rect[3] - rect[1]
    
            # 判断窗口是否全屏
            if window_width == screen_width and window_height == screen_height:
                print(f"当前窗口已全屏{exe_name}")
                if not settings.get("skip_minimize_on_fullscreen_switch_front", False):
                    ShowWindow = ctypes.windll.user32.ShowWindow
                    SW_MINIMIZE = 6
                    # 最小化窗口
                    ShowWindow(hwnd, SW_MINIMIZE)
                #冻结相关
                if self.freeze:
                    if os.path.exists("./_internal/pssuspend64.exe"):
                        pass_exe=['Simplenite.exe', 'ZFGameBrowser.exe', 'amdow.exe', 'audiodg.exe', 'cmd.exe', 'cncmd.exe', 'copyq.exe', 'frpc.exe', 'gamingservicesnet.exe', 'memreduct.exe', 'mmcrashpad_handler64.exe','GameBarPresenceWriter.exe', 'HipsTray.exe', 'HsFreezer.exe', 'HsFreezerMagiaMove.exe', 'PhoneExperienceHost.exe','PixPin.exe', 'PresentMon-x64.exe','msedgewebview2.exe', 'plugin_host-3.3.exe', 'plugin_host-3.8.exe','explorer.exe','System Idle Process', 'System', 'svchost.exe', 'Registry', 'smss.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe', 'services.exe', 'lsass.exe', 'atiesrxx.exe', 'amdfendrsr.exe', 'atieclxx.exe', 'MemCompression', 'ZhuDongFangYu.exe', 'wsctrlsvc.exe', 'AggregatorHost.exe', 'wlanext.exe', 'conhost.exe', 'spoolsv.exe', 'reWASDService.exe', 'AppleMobileDeviceService.exe', 'ABService.exe', 'mDNSResponder.exe', 'Everything.exe', 'SunloginClient.exe', 'RtkAudUService64.exe', 'gamingservices.exe', 'SearchIndexer.exe', 'MoUsoCoreWorker.exe', 'SecurityHealthService.exe', 'HsFreezerEx.exe', 'GameInputSvc.exe', 'TrafficProt.exe', 'HipsDaemon.exe','python.exe', 'pythonw.exe', 'qmbrowser.exe', 'reWASDEngine.exe', 'sihost.exe', 'sublime_text.exe', 'taskhostw.exe', 'SearchProtocolHost.exe','crash_handler.exe', 'crashpad_handler.exe', 'ctfmon.exe', 'dasHost.exe', 'dllhost.exe', 'dwm.exe', 'fontdrvhost.exe','RuntimeBroker.exe','taskhostw.exe''WeChatAppEx.exe', 'WeChatOCR.exe', 'WeChatPlayer.exe', 'WeChatUtility.exe', 'WidgetService.exe', 'Widgets.exe', 'WmiPrvSE.exe', 'Xmp.exe','QQScreenshot.exe', 'RadeonSoftware.exe', 'SakuraFrpService.exe', 'SakuraLauncher.exe', 'SearchHost.exe', 'SecurityHealthSystray.exe', 'ShellExperienceHost.exe', 'StartMenuExperienceHost.exe', 'SystemSettings.exe', 'SystemSettingsBroker.exe', 'TextInputHost.exe', 'TrafficMonitor.exe', 'UserOOBEBroker.exe','WeChatAppEx.exe','360zipUpdate.exe', 'AMDRSServ.exe', 'AMDRSSrcExt.exe', 'APlayer.exe', 'ApplicationFrameHost.exe', 'CPUMetricsServer.exe', 'ChsIME.exe', 'DownloadSDKServer.exe','QMWeiyun.exe']
                        if exe_name in pass_exe:
                            print(f"当前窗口 {exe_name} 在冻结列表中，跳过冻结")
                            return True
                        # 仅当目标进程未挂起时才执行挂起
                        is_stopped = False
                        for proc in psutil.process_iter(['name', 'status']):
                            try:
                                if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                                    if proc.status() == psutil.STATUS_STOPPED:
                                        is_stopped = True
                                        break
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                continue
                        # 判断exe_path是否在valid_apps的path中
                        found_in_valid_apps = False
                        for app in valid_apps:
                            if exe_path and exe_path.lower() == app["path"].lower():
                                found_in_valid_apps = True
                                break
                        if not found_in_valid_apps:
                            is_stopped = True

                        if not is_stopped:
                            subprocess.Popen(
                                ['./_internal/pssuspend64.exe', exe_name],
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                    else:
                        QMessageBox.warning(self, self.tr("提示"), self.tr("未找到冻结工具，请检查路径"))
                return True
            else:
                print(f"当前窗口非全屏 {exe_name} 窗口大小：{window_width} x {window_height} 屏幕分辨率：{screen_width} x {screen_height}")
                return False
        except Exception as e:
            # 捕获异常，返回假
            print(f"错误: {e}")
            return False
    def guide_run(self):
        """置顶开启主页面"""
        try:
            # 将所有界面标记归零（没必要似乎
            #self.current_index = 0
            #self.current_section = 0
            #self.more_section = 0
            #if current_time < ((self.ignore_input_until)+2000):
            #    return
            #self.ignore_input_until = pygame.time.get_ticks() + 500 
            #if STARTUP:subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])#STARTUP = False
            if self.killexplorer == True:
                self.wintaskbarshow()
            #if STARTUP:
            #    self.exitdef(False)
            #    # 无参数重启
            #    subprocess.Popen([sys.executable])
            #self.showFullScreen()
            ## 记录当前窗口的 Z 顺序
            #z_order = []
            #def enum_windows_callback(hwnd, lParam):
            #    z_order.append(hwnd)
            #    return True
            #win32gui.EnumWindows(enum_windows_callback, None)
            self.is_current_window_fullscreen()
            hwnd = GSHWND
            # 尝试将窗口带到前台
            self.show_window()
            result = ctypes.windll.user32.SetForegroundWindow(hwnd)
            # 设置右下角坐标
            screen_width, screen_height = pyautogui.size()
            right_bottom_x = screen_width - 1  # 最右边
            right_bottom_y = screen_height - 1  # 最底部
            pyautogui.moveTo(right_bottom_x, right_bottom_y)
            QTimer.singleShot(200, lambda: (
                print("窗口已成功带到前台") if result else (
                    print("未能将窗口带到前台，正在尝试设置为最上层"),
                    SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE),
                    hide_taskbar() if self.killexplorer == False else None,
                    time.sleep(0.2),
                    pyautogui.rightClick(right_bottom_x, right_bottom_y),
                    show_taskbar() if self.killexplorer == False else None,
                    SetWindowPos(hwnd, -2, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE),
                    self.update_highlight()
                )
            ))
        except Exception as e:
            print(f"Error: {e}")
    def handle_gamepad_input(self, action):
        """处理手柄输入"""
        global STARTUP  # 声明 STARTUP 为全局变量
        if action:
            # 处理方向键FIRST事件
            if action.startswith('FIRST-'):
                firstinput = True
                action = action.split('-', 1)[1]  # 提取方向值
            else:
                firstinput = False
        # 标记是否为方向输入（允许绕过全局防抖/屏蔽）
        is_direction = action in ('UP', 'DOWN', 'LEFT', 'RIGHT') if action else False
        # 跟踪焦点状态
        current_time = pygame.time.get_ticks()

        # 如果文件选择对话框打开，优先转发手柄输入
        # 检查两个位置：floating_window.file_dialog_manager 和 self.file_dialog_manager
        # （FloatingWindow 使用 Qt.Popup，失焦会自动关闭导致 floating_window=None，
        #   所以 select_add 会将 manager 同时保存到 MainWindow 上）
        try:
            manager = None
            fw = getattr(self, 'floating_window', None)
            if fw is not None:
                mgr1 = getattr(fw, 'file_dialog_manager', None)
                if mgr1 is not None:
                    manager = mgr1
            mgr2 = getattr(self, 'file_dialog_manager', None)
            if manager is None and mgr2 is not None:
                manager = mgr2
            if manager and hasattr(manager, 'dialog') and manager.dialog and manager.dialog.isVisible():
                manager.handle_gamepad_input(action)
                self.ignore_input_until = pygame.time.get_ticks() + 300
                return
        except RuntimeError:
            pass

        # 如果在屏蔽输入的时间段内，则不处理（方向键除外）
        if current_time < self.ignore_input_until and not is_direction:
            return

        # 如果按键间隔太短，则不处理（方向键除外）
        if current_time - self.last_input_time < self.input_delay and not is_direction:
            return
        if self.is_mouse_simulation_running == True:
            return # 防止鼠标模拟运行时处理手柄输入
        # 检查 LS 和 RS 键是否同时按下
        if action in ('LS', 'RS'):
            # 获取当前手柄对象和映射
            for controller_data in self.controller_thread.controllers.values():
                controller = controller_data['controller']
                mapping = controller_data['mapping']
                ls_pressed = controller.get_button(mapping.left_stick_in)
                rs_pressed = controller.get_button(mapping.right_stick_in)
                if ls_pressed and rs_pressed:
                    self.ignore_input_until = pygame.time.get_ticks() + 3000 
                    print("LS和RS同时按下！正在截图...")
                    screenshot = pyautogui.screenshot()
                
                    # 智能识别当前游戏名称
                    def get_current_game_name():
                        try:
                            hwnd = win32gui.GetForegroundWindow()
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            exe_path = psutil.Process(pid).exe()
                            exe_path = exe_path.lower()
                            # 在 valid_apps 里查找匹配的游戏名
                            for app in valid_apps:
                                if app["path"].lower() == exe_path:
                                    return app["name"]
                        except Exception as e:
                            print(f"识别游戏名失败: {e}")
                        return "other"
                
                    game_name = get_current_game_name()
                    # 生成保存路径
                    now_str = time.strftime("%Y%m%d_%H%M%S")
                    screenshot_dir = os.path.join(program_directory, "screenshot", game_name)
                    os.makedirs(screenshot_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshot_dir, f"{now_str}.png")
                    screenshot.save(screenshot_path)
                    print(f"截图已保存到 {screenshot_path}")
                
                    # 新增：截图悬浮窗
                    class ScreenshotDialog(QDialog):
                        def __init__(self, image_path, parent=None):
                            super().__init__(parent)
                            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
                            self.setAttribute(Qt.WA_TranslucentBackground)
                            self.setModal(False)
                            self.setFixedSize(480, 160)
                    
                            # 用QWidget做内容容器，设置背景和圆角
                            content_widget = QWidget(self)
                            content_widget.setObjectName("content_widget")
                            content_widget.setGeometry(0, 0, 480, 160)
                            content_widget.setStyleSheet("""
                                QWidget#content_widget {
                                    background-color: rgba(30, 30, 30, 230);
                                    border-radius: 12px;
                                }
                            """)
                    
                            main_layout = QHBoxLayout(content_widget)
                            main_layout.setContentsMargins(16, 16, 16, 16)  # 适当内边距
                    
                            # 左侧图片
                            pixmap = QPixmap(image_path).scaled(180, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            img_label = QLabel()
                            img_label.setPixmap(pixmap)
                            img_label.setFixedSize(180, 120)
                            img_label.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
                            main_layout.addWidget(img_label)
                    
                            # 右侧文字
                            text_layout = QVBoxLayout()
                            text_layout.setContentsMargins(0, 0, 0, 0)
                            tip_label = QLabel(f"  截图已保存\n  {game_name}\n  {now_str}.png")
                            tip_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent; margin: 0px; padding: 0px;")
                            tip_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                            text_layout.addWidget(tip_label)
                            main_layout.addLayout(text_layout)
                    
                            self.move(20, 20)
                            self.show()
                    
                            QTimer.singleShot(2000, self.close)
                
                    ScreenshotDialog(screenshot_path, self)
        # 检查 Back 和 Start 键是否同时按下
        if action in ('BACK', 'START'):
            # 获取当前手柄对象和映射
            for controller_data in self.controller_thread.controllers.values():
                controller = controller_data['controller']
                mapping = controller_data['mapping']
                back_pressed = controller.get_button(mapping.back)
                start_pressed = controller.get_button(mapping.start)
                if back_pressed and start_pressed:
                    print("Back和Start同时按下！")
                    # 弹出进度条悬浮窗
                    class ProgressDialog(QDialog):
                        def __init__(self, parent=None):
                            super().__init__(parent)
                            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
                            self.setAttribute(Qt.WA_TranslucentBackground)
                            self.setWindowOpacity(0.85)
                            self.setModal(True)
                    
                            # 内容容器，设置背景和圆角
                            content_widget = QWidget(self)
                            content_widget.setObjectName("content_widget")
                            content_widget.setGeometry(0, 0, 420, 120)
                            content_widget.setStyleSheet("""
                                QWidget#content_widget {
                                    background-color: rgba(30, 30, 30, 230);
                                    border-radius: 10px;
                                }
                            """)
                    
                            # 主布局放在内容容器上
                            main_layout = QVBoxLayout(content_widget)
                            main_layout.setContentsMargins(10, 10, 10, 10)
                    
                            # 创建提示标签
                            self.prompt_label = QLabel(self.tr("持续按住触发鼠标模拟..."))
                            self.prompt_label.setStyleSheet("color: white; font-size: 14px; background: transparent;")
                            self.prompt_label.setAlignment(Qt.AlignCenter)
                            main_layout.addWidget(self.prompt_label)
                    
                            # 创建进度条容器
                            progress_container = QFrame()
                            progress_container.setStyleSheet("""
                                QFrame {
                                    background-color: rgba(0, 0, 0, 125);
                                    border: 1px solid black;
                                    border-radius: 5px;
                                }
                            """)
                            progress_layout = QVBoxLayout(progress_container)
                            progress_layout.setContentsMargins(10, 5, 10, 5)
                    
                            # 创建进度条标签
                            self.label = QLabel("0%")  # 百分比数字，无需翻译
                            self.label.setStyleSheet("""
                                QLabel {
                                    background-color: green;
                                    color: white;
                                    font-size: 16px;
                                    border-radius: 3px;
                                }
                            """)
                            self.label.setAlignment(Qt.AlignCenter)
                            self.label.setFixedHeight(30)
                            progress_layout.addWidget(self.label)
                    
                            main_layout.addWidget(progress_container)
                    
                            # 设置窗口大小
                            self.setFixedSize(440, 120)
                    
                            # 居中显示窗口
                            screen = QApplication.primaryScreen().geometry()
                            x = (screen.width() - self.width()) // 2
                            y = (screen.height() - self.height()) // 2
                            self.move(x, y)
                    
                            self.show()
                            
                        def update_progress(self, percent):
                            # 更新进度条宽度
                            width = int(400 * percent / 100)
                            self.label.setFixedWidth(width)
                            self.label.setText(f"{percent}%")
                            QApplication.processEvents()
                            
                    # 只弹出一次
                    if not hasattr(self, '_back_start_progress') or self._back_start_progress is None:
                        self._back_start_progress = ProgressDialog(self)
                        QApplication.processEvents()
                        pressed = True
                        for i in range(0, 101, 3):
                            # 实时检测按键是否松开
                            back_pressed = controller.get_button(mapping.back)
                            start_pressed = controller.get_button(mapping.start)
                            if not (back_pressed and start_pressed):
                                pressed = False
                                break
                            self._back_start_progress.update_progress(i)
                            time.sleep(0.01)
                        self._back_start_progress.close()
                        self._back_start_progress = None
                        if pressed:
                            print("Back和Start已持续按下2秒！")
                            # 执行鼠标模拟
                            self.mouse_simulation()
                        else:
                            # 按键提前松开，执行后续代码
                            self.back_start_pressed_time = None
                            break
                    break
                else:
                    self.back_start_pressed_time = None
                    break
        #print(f"处理手柄输入: {action}")
        try:
            if hasattr(self, 'confirm_dialog') and self.confirm_dialog and self.confirm_dialog.isVisible():  # 如果确认弹窗显示中
                print("确认弹窗显示中")
                self.ignore_input_until = current_time + 500
                self.confirm_dialog.handle_gamepad_input(action)
                return
        except RuntimeError:
            self.confirm_dialog = None
            
        # 优先检查所有可能的 confirm_dialog，无论窗口是否可见
        # 检查 screenshot_window 的 confirm_dialog
        try:
            if hasattr(self, 'screenshot_window') and hasattr(self.screenshot_window, 'confirm_dialog') and self.screenshot_window.confirm_dialog and self.screenshot_window.confirm_dialog.isVisible():
                self.screenshot_window.handle_gamepad_input(action)
                self.ignore_input_until = pygame.time.get_ticks() + 300 
                return
        except RuntimeError:
            if hasattr(self, 'screenshot_window'):
                self.screenshot_window.confirm_dialog = None
                
        # 检查 floating_window 的 confirm_dialog
        try:
            if getattr(self, 'floating_window', None) and hasattr(self.floating_window, 'confirm_dialog') and self.floating_window.confirm_dialog and self.floating_window.confirm_dialog.isVisible():
                self.floating_window.handle_gamepad_input(action, firstinput)
                self.ignore_input_until = pygame.time.get_ticks() + 300 
                return
        except RuntimeError:
            if getattr(self, 'floating_window', None):
                self.floating_window.confirm_dialog = None
                
        # 检查 settings_window 的 confirm_dialog
        try:
            if getattr(self, 'settings_window', None) and hasattr(self.settings_window, 'confirm_dialog') and self.settings_window.confirm_dialog and self.settings_window.confirm_dialog.isVisible():
                self.settings_window.handle_gamepad_input(action)
                self.ignore_input_until = pygame.time.get_ticks() + 300 
                return
        except RuntimeError:
            if getattr(self, 'settings_window', None):
                self.settings_window.confirm_dialog = None
        
        # 检查文件对话框
        try:
            if hasattr(self, 'file_dialog_manager') and self.file_dialog_manager and hasattr(self.file_dialog_manager, 'dialog') and self.file_dialog_manager.dialog and self.file_dialog_manager.dialog.isVisible():
                self.file_dialog_manager.handle_gamepad_input(action)
                self.ignore_input_until = pygame.time.get_ticks() + 300
                return
        except RuntimeError:
            if hasattr(self, 'file_dialog_manager'):
                self.file_dialog_manager = None

        # 检查 active_dialog（如后台窗口选择器等）
        try:
            if hasattr(self, 'active_dialog') and self.active_dialog and self.active_dialog.isVisible():
                if hasattr(self.active_dialog, 'handle_gamepad_input'):
                    self.active_dialog.handle_gamepad_input(action)
                    self.ignore_input_until = pygame.time.get_ticks() + 300
                    return
        except RuntimeError:
            self.active_dialog = None

        if not self.gsfocus():  # 检测当前窗口是否为游戏选择界面
            # 按键长按超过800ms时不触发，直到抬起才return
            if action == 'GUIDE':
                # 确保状态变量存在
                if not hasattr(self, '_guide_press_time'):
                    self._guide_press_time = 0
                if not hasattr(self, '_guide_last_state'):
                    self._guide_last_state = False
                current_ticks = pygame.time.get_ticks()

                # 检查当前所有手柄的GUIDE键状态
                guide_pressed = False
                for controller_data in self.controller_thread.controllers.values():
                    controller = controller_data['controller']
                    mapping = controller_data['mapping']
                    if controller.get_button(mapping.guide):
                        guide_pressed = True
                        break

                if guide_pressed:
                    # 刚开始按下，记录按下时间
                    if not self._guide_last_state:
                        self._guide_press_time = current_ticks
                        self._guide_last_state = True
                        # 清除长按标记
                        self._guide_long_pressed = False
                        # 如果没有正在轮询释放状态，创建一个轮询器以捕获可能缺失的释放事件
                        if not hasattr(self, '_guide_poll_timer') or self._guide_poll_timer is None:
                            def _poll_guide_release():
                                now = pygame.time.get_ticks()
                                # 检查当前所有手柄的GUIDE键状态
                                still_pressed = False
                                for controller_data in self.controller_thread.controllers.values():
                                    controller = controller_data['controller']
                                    mapping = controller_data['mapping']
                                    if controller.get_button(mapping.guide):
                                        still_pressed = True
                                        break
                                if still_pressed:
                                    # 标记为长按（若超过阈值）并继续等待释放
                                    if now - (self._guide_press_time or now) > 800:
                                        self._guide_long_pressed = True
                                    return
                                # 已释放，处理为短按或忽略长按
                                if self._guide_last_state:
                                    press_duration = now - (self._guide_press_time or now)
                                    self._guide_last_state = False
                                    self._guide_press_time = 0
                                    if getattr(self, '_guide_long_pressed', False):
                                        self._guide_long_pressed = False
                                    else:
                                        if press_duration <= 800:
                                            self.guide_run()
                                # 停止并清理定时器
                                try:
                                    self._guide_poll_timer.stop()
                                except Exception:
                                    pass
                                self._guide_poll_timer = None

                            self._guide_poll_timer = QTimer(self)
                            self._guide_poll_timer.timeout.connect(_poll_guide_release)
                            self._guide_poll_timer.start(50)
                    # 如果按下超过800ms，标记为长按并等待释放（不触发）
                    if current_ticks - self._guide_press_time > 800:
                        self._guide_long_pressed = True
                        return
                    # 在按下但未超时的期间，不在此触发，等待释放时判断短/长按
                else:
                    # 按键刚刚释放
                    if self._guide_last_state:
                        press_duration = current_ticks - (self._guide_press_time or current_ticks)
                        self._guide_last_state = False
                        self._guide_press_time = 0
                        # 如果之前标记为长按，则忽略本次释放事件
                        if getattr(self, '_guide_long_pressed', False):
                            self._guide_long_pressed = False
                            return
                        # 短按：在释放时触发一次
                        if press_duration <= 800:
                            self.guide_run()
                        return
                # 其它情况（仍在按下或无变化）不在此触发
            self.ignore_input_until = current_time + 500
            return
        
        # 若启动悬浮窗存在，关闭启动悬浮窗
        try:
            if getattr(self, 'launch_overlay', None):
                if self.launch_overlay.isVisible():
                    # hide() 会触发 hideEvent，其中已经包含了 _stop_launch_animations 和 self.launch_overlay = None
                    self.launch_overlay.hide()
                    return # 既然已经关闭了遮罩，就不要继续处理本次输入了，防止误触底层按钮
        except RuntimeError:
            self.launch_overlay = None
        # 正常窗口处理逻辑
        try:
            if hasattr(self, 'screenshot_window') and self.screenshot_window.isVisible():
                self.ignore_input_until = current_time + 200
                self.screenshot_window.handle_gamepad_input(action)
                return
        except RuntimeError:
            self.screenshot_window = None
        
        try:
            if getattr(self, 'floating_window', None) and self.floating_window.isVisible():
                self.ignore_input_until = current_time + 200
                self.floating_window.handle_gamepad_input(action, firstinput)
                return
        except RuntimeError:
            self.floating_window = None
        # 检查 settings_window
        try:
            if hasattr(self, 'settings_window') and self.settings_window.isVisible():
                self.ignore_input_until = current_time + 200
                self.settings_window.handle_gamepad_input(action)
                return
        except RuntimeError:
            self.settings_window = None
        

        # 新增焦点切换逻辑（基于位置：切换时选取最近的按钮）
        if action == 'DOWN' and self.current_section == 0 and self.more_section == 0:
            # 切换到控制按钮区域：根据当前选中游戏按钮的屏幕位置，选择最近的控制按钮
            self.current_section = 1
            try:
                if self.buttons and 0 <= self.current_index < len(self.buttons):
                    game_btn = self.buttons[self.current_index]
                    gp = game_btn.mapToGlobal(game_btn.rect().center())
                    best_idx = 0
                    best_dist = None
                    for i, cb in enumerate(self.control_buttons):
                        try:
                            cp = cb.mapToGlobal(cb.rect().center())
                            dx = gp.x() - cp.x()
                            dy = gp.y() - cp.y()
                            dist = dx * dx + dy * dy
                            if best_dist is None or dist < best_dist:
                                best_dist = dist
                                best_idx = i
                        except Exception:
                            continue
                    self.current_index = best_idx
                else:
                    self.current_index = 0
            except Exception:
                self.current_index = 0
            self.update_highlight()
            print("当前区域：控制按钮区域")
        elif action == 'UP' and self.current_section == 1 and self.more_section == 0:
            # 返回游戏选择区域：根据当前控制按钮位置，选择最近的游戏按钮
            self.current_section = 0
            try:
                if hasattr(self, 'control_buttons') and 0 <= self.current_index < len(self.control_buttons) and self.buttons:
                    cb = self.control_buttons[self.current_index]
                    cp = cb.mapToGlobal(cb.rect().center())
                    best_idx = 0
                    best_dist = None
                    for i, gb in enumerate(self.buttons):
                        try:
                            gp = gb.mapToGlobal(gb.rect().center())
                            dx = gp.x() - cp.x()
                            dy = gp.y() - cp.y()
                            dist = dx * dx + dy * dy
                            if best_dist is None or dist < best_dist:
                                best_dist = dist
                                best_idx = i
                        except Exception:
                            continue
                    self.current_index = best_idx
                else:
                    self.current_index = 0
            except Exception:
                self.current_index = 0
            self.update_highlight()
            print("当前区域：游戏选择区域")
            if getattr(self, 'show_background_apps', False):  # 仅在处于后台应用模式时恢复
                self.restore_control_buttons()
        elif action == 'DOWN' and firstinput and self.current_section == 1 and self.more_section == 0:
            if not getattr(self, 'show_background_apps', False) and hasattr(self, 'extra_background_button') and self.extra_background_button:
                self.switch_all_buttons_to_background_mode()
            else:
                if settings.get('open_quick_settings_on_bottom_down', False):
                    pyautogui.hotkey('win', 'a')
        elif action == 'UP' and firstinput and self.current_section == 0 and self.more_section == 0:
            self.show_more_window()  # 打开悬浮窗
            self.ignore_input_until = current_time + 400
        elif action == 'B' and self.more_section == 1:
            self.switch_to_main_interface()
        else:
            if action == 'GUIDE':  # 回桌面
                if current_time < ((self.ignore_input_until)+500):
                    return
                self.ignore_input_until = pygame.time.get_ticks() + 500 
                #self.exitdef()  # 退出程序
                self.hide_window()
                pyautogui.hotkey('win', 'd')
                return
            elif action in ('LB', 'RB'):
                for controller_data in self.controller_thread.controllers.values():
                    controller = controller_data['controller']
                    mapping = controller_data['mapping']
                    lb_pressed = controller.get_button(mapping.left_bumper)
                    rb_pressed = controller.get_button(mapping.right_bumper)
                    if lb_pressed and rb_pressed:
                        self.toggle_mute()
                        self.ignore_input_until = pygame.time.get_ticks() + 500 
                        return
                    # 仅 LB 或仅 RB：单独调整音量后返回
                    if action == 'LB':
                        self.decrease_volume()
                        self.ignore_input_until = pygame.time.get_ticks() + 200
                        return
                    elif action == 'RB':
                        self.increase_volume()
                        self.ignore_input_until = pygame.time.get_ticks() + 200 
                        return
            if self.current_section == 1:  # 控制按钮区域
                if action.lower() == "right":
                    # 限制导航范围：在后台应用模式下只允许导航到可见按钮
                    if getattr(self, 'show_background_apps', False):
                        # 在后台应用模式下
                        remaining_count = getattr(self, 'remaining_windows_count', 0)
                        # 计算最大可见索引
                        if remaining_count > 0:
                            max_visible_index = min(remaining_count - 1, 5)
                            # 如果有超过6个应用，显示"..."按钮
                            if remaining_count > 6:
                                max_visible_index = 6
                        else:
                            max_visible_index = -1  # 没有应用
                    else:
                        # 正常模式下
                        max_visible_index = len(self.control_buttons) - 1
                    
                    # 只有当还有可见按钮时才移动
                    if max_visible_index >= 0 and self.current_index < max_visible_index:
                        self.current_index += 1
                elif action.lower() == "left":
                    self.current_index = max(self.current_index - 1, 0)
                #elif action.lower() == "down":
                #    self.current_section = 0  # 返回游戏选择区域
                elif action == 'A':
                    self.control_buttons[self.current_index].click()
                elif action == 'X':  # X键开悬浮窗
                    self.control_buttons[self.current_index].click()
                    QTimer.singleShot(210, self.mouse_simulation)
                elif action == 'Y':
                    self.on_favorite_button_clicked()
                elif action == 'B':
                    #self.exitdef()  # 退出程序
                    self.hide_window()
                self.update_highlight()
            else:
                if action == 'UP' and self.more_section == 1:
                    self.move_selection(-self.row_count)  # 向上移动
                elif action == 'DOWN' and self.more_section == 1:
                    self.move_selection(self.row_count)  # 向下移动
                elif action == 'LEFT':
                    if self.current_index == 0:  # 如果当前是第一项
                        if firstinput:
                            self.move_selection(-1)  # 向左移动
                        return
                    self.move_selection(-1)  # 向左移动
                elif action == 'RIGHT':
                    if self.current_index < len(self.buttons) - 1:  # 检查是否已经是最后一个按钮
                        self.move_selection(1)  # 向右移动
                    else:
                        if firstinput:
                            self.move_selection(1)  # 向右移动
                elif action == 'A':
                    self.launch_game(self.current_index)  # 启动游戏
                elif action == 'B':
                    #self.exitdef()  # 退出程序
                    self.hide_window()
                elif action == 'Y':
                    self.toggle_favorite()  # 收藏/取消收藏游戏
                    self.ignore_input_until = pygame.time.get_ticks() + 300 
                elif action == 'X':  # X键开悬浮窗
                    if self.sort_games()[self.current_index]["name"] in self.player:
                        self.launch_game(self.current_index)  # 启动游戏
                    else:
                        self.hide_window()
                    QTimer.singleShot(210, self.mouse_simulation)
                elif action == 'START':  # START键打开游戏详情
                    self.open_selected_game_screenshot()
                elif action == 'BACK':  # SELECT键
                    pass

        # 更新最后一次按键时间
        self.last_input_time = current_time
    def sort_games(self):
        """根据收藏和最近游玩对游戏进行排序"""
        sorted_games = []

        # 如果有正在运行的应用，优先加入
        for game_name in self.player:
            for game in games:
                if game["name"] == game_name:
                    sorted_games.append(game)
                    break
        
        # 首先添加收藏的游戏
        for game_name in settings["favorites"]:
            for game in games:
                if game["name"] == game_name and game["name"] not in self.player:
                    sorted_games.append(game)
                    break
        
        # 然后添加最近游玩的游戏
        for game_name in settings["last_played"]:
            for game in games:
                if game["name"] == game_name and game["name"] not in settings["favorites"] and game["name"] not in self.player:
                    sorted_games.append(game)
                    break
        
        # 最后添加其他游戏
        for game in games:
            if game["name"] not in settings["favorites"] and game["name"] not in settings["last_played"] and game["name"] not in self.player:
                sorted_games.append(game)
        
        return sorted_games
    def exitdef(self):
        """退出程序"""
        # 停止所有线程
        if self.killexplorer == True and hasattr(self, 'winTaskbar'):
            self.winTaskbar.on_back_to_desktop()
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        if hasattr(self, 'controller_thread'):
            self.controller_thread.stop()
            self.controller_thread.wait()
        
            
        #self.close()
        QApplication.quit()
        #def exitdef(self,rerun=True):
        #if rerun:
        #    subprocess.Popen([sys.executable, "startup"])

    def toggle_favorite(self):
        """切换当前游戏的收藏状态"""
        current_game = self.sort_games()[self.current_index]
        game_name = current_game["name"]
        print(game_name)
        #删除逻辑
        if game_name in self.player:
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog(self.tr("是否关闭下列程序？\n%1").replace('%1', game_name), scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks()
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            for app in valid_apps:
                if app["name"] == game_name:
                    game_path = app["path"]
                    break
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    # 检查进程的执行文件路径是否与指定路径匹配
                    if proc.info['exe'] and os.path.abspath(proc.info['exe']) == os.path.abspath(game_path):
                        print(f"找到进程: {proc.info['name']} (PID: {proc.info['pid']})")
                        # 显示加载窗口
                        loading = LoadingDialog(self.tr("正在关闭程序......"), scale_factor=self.scale_factor, parent=self)
                        loading.show()
                        QApplication.processEvents()
                        try:
                            proc.terminate()  # 请求结束进程
                        except Exception:
                            pass
                        # 等待进程退出，同时让 UI 响应
                        start_time = time.time()
                        try:
                            while proc.is_running():
                                QApplication.processEvents()
                                time.sleep(0.05)
                                if time.time() - start_time > 5:
                                    try:
                                        proc.kill()
                                    except Exception:
                                        pass
                                    break
                        except Exception:
                            pass
                        loading.close()
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # 处理权限问题和进程已消失的异常
                    continue
            return

        if game_name in settings["favorites"]:
            settings["favorites"].remove(game_name)
        else:
            settings["favorites"].append(game_name)
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        
        # 重新加载界面
        self.reload_interface()
    
    def on_scale_factor_updated(self, new_scale_factor):
        """缩放因子更新时调用，更新界面控件尺寸与布局"""
        # 更新缩放因子
        self.scale_factor = new_scale_factor
        self.scale_factor2 = self.scale_factor * 2
        
        # 更新顶部按钮
        if hasattr(self, 'more_button'):
            self.more_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.more_button.setText("*")
            self.more_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: none;
                    color: #888888;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
            """)
        
        if hasattr(self, 'favorite_button'):
            self.favorite_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.favorite_button.setText("*")
            self.favorite_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: none;
                    color: #888888;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
            """)
        
        if hasattr(self, 'quit_button'):
            self.quit_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.quit_button.setText("*")
            self.quit_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: none;
                    color: #888888;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
            """)
        
        if hasattr(self, 'screenshot_button'):
            self.screenshot_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.screenshot_button.setText("*")
            self.screenshot_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: none;
                    color: #888888;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
            """)
        
        # 更新游戏名标签和时间标签
        if hasattr(self, 'game_name_label'):
            self.game_name_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(20 * self.scale_factor)}px;
                    font-weight: bold;
                    padding: 0 {int(20 * self.scale_factor)}px;
                }}
            """)
        
        if hasattr(self, 'time_label'):
            self.time_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(25 * self.scale_factor)}px;
                    padding-top: {int(10 * self.scale_factor)}px;
                    padding-bottom: {int(10 * self.scale_factor)}px;
                    padding-right: {int(20 * self.scale_factor)}px;
                }}
            """)

        # 更新底部右侧文字（帮助/提示）
        if hasattr(self, 'right_label'):
            try:
                self.right_label.setStyleSheet(f"""
                    QLabel {{
                        font-family: "Microsoft YaHei"; 
                        color: white;
                        font-size: {int(25 * self.scale_factor)}px;
                        padding-bottom: {int(10 * self.scale_factor)}px;
                        padding-right: {int(50 * self.scale_factor)}px;
                    }}
                """)
            except Exception:
                pass
        
        # 更新网格布局间距
        if hasattr(self, 'grid_layout'):
            self.grid_layout.setSpacing(int(20 * self.scale_factor))
        
        # 更新顶部布局边距
        if hasattr(self, 'top_layout'):
            self.top_layout.setContentsMargins(int(20 * self.scale_factor), 0, int(20 * self.scale_factor), 0)

        # 更新控制按钮区域（圆形按钮）
        if hasattr(self, 'control_layout'):
            try:
                self.control_layout.setSpacing(int(50 * self.scale_factor))
            except Exception:
                pass
        if hasattr(self, 'control_buttons'):
            for btn in self.control_buttons:
                try:
                    size = int(125 * self.scale_factor)
                    border_px = max(1, int(5 * self.scale_factor))
                    font_px = max(8, int(40 * self.scale_factor))
                    btn.setFixedSize(size, size)
                    # 圆形半径为宽度的一半，使用像素值避免百分比差异
                    radius_px = int(size / 2)
                    checked_border = max(1, int(6 * self.scale_factor))
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(87, 87, 87, 0.45);
                            border-radius: {radius_px}px;
                            font-size: {font_px}px; 
                            border: {border_px}px solid rgba(40, 40, 40, 0.9);
                            color: white;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 0.12);
                        }}
                        QPushButton:checked {{
                            background-color: rgba(69, 160, 73, 0.85);
                            border: {checked_border}px solid rgba(255, 255, 0, 0.9);
                        }}
                    """)
                except Exception:
                    pass
        
        # 更新游戏按钮
        if hasattr(self, 'buttons'):
            for button in self.buttons:
                # 跳过"更多"按钮
                if button.text() == "🟦🟦\n🟦🟦":
                    button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                elif button.text() in ["返回", "返回主页面"]:
                    # 处理返回按钮
                    button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                else:
                    # 更新游戏按钮
                    button.setFixedSize(int(220 * self.scale_factor2), int(300 * self.scale_factor2))
                    # 更新按钮样式
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border-radius: {int(10 * self.scale_factor2)}px;
                            border: {int(2 * self.scale_factor2)}px solid #444444;
                            color: white;
                            text-align: center;
                            padding: 0;
                        }}
                        QPushButton:hover {{
                            border: {int(2 * self.scale_factor2)}px solid #888888;
                        }}
                    """)
                    
                    # 更新按钮内的标签
                    for child in button.findChildren(QLabel):
                        if child.objectName() == "star_label":
                            # 更新收藏标签
                            child.setStyleSheet(f"""
                                QLabel {{
                                    background-color: rgba(0, 0, 0, 0.7);
                                    color: gold;
                                    font-size: {int(10 * self.scale_factor2)}px;
                                    padding: {int(5 * self.scale_factor2)}px;
                                    border-radius: {int(10 * self.scale_factor2)}px;
                                }}
                            """)
                            child.move(int(5 * self.scale_factor2), int(5 * self.scale_factor2))
        
        # 更新滚动区域高度和宽度
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setFixedHeight(int(320 * self.scale_factor * 2.4))
            self.scroll_area.setFixedWidth(int(self.width()))
        
        # 更新滚动区域中的图像
        if hasattr(self, 'buttons') and hasattr(self, 'sort_games'):
            sorted_games = self.sort_games()
            for idx, button in enumerate(self.buttons):
                # 跳过"更多"按钮和"返回"按钮
                if button.text() == "🟦🟦\n🟦🟦" or button.text() in ["返回", "返回主页面"]:
                    continue
                
                # 确保索引有效
                if idx < len(sorted_games):
                    game = sorted_games[idx]
                    image_path = game["image-path"]
                    # 自动判断图片路径是相对还是绝对
                    if not os.path.isabs(image_path):
                        image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
                    
                    # 重新加载并缩放图像
                    pixmap = QPixmap(image_path).scaled(int(200 * self.scale_factor2), int(267 * self.scale_factor2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon = QIcon(pixmap)
                    button.setIcon(icon)
                    button.setIconSize(pixmap.size())
        
        # 更新加载提示标签
        if hasattr(self, 'loading_label'):
            self.loading_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(30 * self.scale_factor)}px;
                }}
            """)
        
        # 更新没有游戏时的提示按钮
        if hasattr(self, 'no_games_button'):
            self.no_games_button.setFixedSize(int(700 * self.scale_factor), int(200 * self.scale_factor))
            self.no_games_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border-radius: {int(10 * self.scale_factor)}px;
                    border: {int(2 * self.scale_factor)}px solid #444444;
                    color: white;
                    font-size: {int(30 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #888888;
                }}
            """)
        
        # 更新分隔线
        if hasattr(self, 'divider'):
            self.divider.setFixedHeight(int(4 * self.scale_factor))
        
        # 更新左右标签
        if hasattr(self, 'left_label'):
            self.left_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(25 * self.scale_factor)}px;
                    padding-bottom: {int(10 * self.scale_factor)}px;
                    padding-left: {int(50 * self.scale_factor)}px;
                }}
            """)
        
        if hasattr(self, 'right_label'):
            self.right_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(25 * self.scale_factor)}px;
                    padding-bottom: {int(10 * self.scale_factor)}px;
                    padding-right: {int(50 * self.scale_factor)}px;
                }}
            """)

    def load_background_image(self):
        background_path = os.path.join(".", "screenshot", "background.png")
        if os.path.exists(background_path):
            pix = QPixmap(background_path)
            if not pix.isNull():
                self.background_label.setPixmap(pix)
                self.background_label.setGeometry(self.rect())
                self.background_label.lower()
                return
        self.background_label.clear()
        self.background_label.setStyleSheet("background-color: #1e1e1e;")

    def resizeEvent(self, event):
        if hasattr(self, 'background_label'):
            self.background_label.setGeometry(self.rect())
        return super().resizeEvent(event)

    def reload_interface(self):
        """重新加载界面"""
        # 优化：清除现有按钮的方式，使用更高效的布局处理
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.buttons.clear()
        if self.more_section == 1:
            #修改按钮文字为"返回"
            self.button_texts['quit'] = self.tr("返回主页面")
        else:
            self.button_texts['quit'] = self.tr("最小化")
        
        # 确保按钮在未点击时显示为灰色横杠
        if self.quit_button.text() != "*":
            # 如果按钮当前显示的是文本，则更新为正确的文本
            self.quit_button.setText(self.button_texts['quit'])
        # 重新添加按钮
        sorted_games = self.sort_games()
        if sorted_games:  # 只在有游戏时添加按钮
            if self.more_section == 0:
                for index, game in enumerate(sorted_games[:self.buttonsindexset]):
                    button = self.create_game_button(game, index)
                    #self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
                    self.grid_layout.addWidget(button, 0, index)
                    self.buttons.append(button)

                # 添加"更多"按钮
                more_button = QPushButton("🟦🟦\n🟦🟦")
                more_button.setFont(QFont("Microsoft YaHei", 40))
                more_button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                more_button.clicked.connect(self.switch_to_all_software)  # 绑定"更多"按钮的功能
                self.grid_layout.addWidget(more_button, 0, len(sorted_games[:self.buttonsindexset]))  # 添加到最后一列
                self.buttons.append(more_button)
            else:
                # 优化：使用批量加载方式
                self.load_all_games_optimized(sorted_games)

        # 使用 QTimer 延迟执行高亮更新
        QTimer.singleShot(25, self.update_highlight)
        #self.butto=False
    
    def load_all_games_optimized(self, sorted_games):
        """优化加载所有游戏的方法"""
        for index, game in enumerate(sorted_games):
            button = self.create_game_button(game, index)
            self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
            self.buttons.append(button)
            
            # 每创建10个按钮，让UI线程有机会处理其他事件
            if (index + 1) % 10 == 0:
                QApplication.processEvents()  # 处理待处理的事件，优化 `c:\Users\86150\Desktop\dist2\Simplenite.py`

    def show_more_window(self):
        """显示更多选项窗口"""
        # 每次打开时都创建一个新的FloatingWindow实例，确保懒加载状态正确
        self.floating_window = FloatingWindow(self)
        
        # 计算悬浮窗位置
        button_pos = self.more_button.mapToGlobal(self.more_button.rect().bottomLeft())
        self.floating_window.move(button_pos.x(), button_pos.y() + 10)
        
        # 初始加载工具标签页的按钮
        self.floating_window.load_tab_buttons(0)
        self.floating_window.tabs_loaded[0] = True
        self.floating_window.update_highlight()
        
        # 显示窗口（带打开动画）
        self.floating_window.show()

    def execute_more_item(self, file=None):
        """执行更多选项中的项目"""
        if not self.floating_window:
            return
    
        # 根据当前标签页获取文件列表
        if file:
            current_file = file
        else:
            if self.floating_window.current_tab_index == 0:  # 工具标签页
                sorted_files = self.floating_window.sort_files()
            elif self.floating_window.current_tab_index == 1:  # 桌面标签页
                sorted_files = self.floating_window.get_desktop_files()
            elif self.floating_window.current_tab_index == 2:  # 全部应用标签页
                sorted_files = self.floating_window.get_start_menu_items()
            else:
                return
            
            if self.floating_window.current_index >= len(sorted_files):
                return
            current_file = sorted_files[self.floating_window.current_index]
    
        # 处理文件路径
        if current_file.get("type") == "tool":
            # 工具标签页的文件路径是相对路径
            current_file["path"] = os.path.abspath(os.path.join("./morefloder/", current_file["path"]))
        else:
            # 桌面和开始菜单的文件路径已经是绝对路径
            current_file["path"] = os.path.abspath(current_file["path"])
            
            # 检查是否是exe、lnk或url文件
            file_path = current_file["path"]
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in [".exe", ".lnk", ".url"]:
                # 检查该文件的快捷方式是否已经存在于morefolder文件夹中
                morefolder_path = os.path.abspath("./morefloder/")
                shortcut_name = os.path.basename(file_path)
                shortcut_path = os.path.join(morefolder_path, shortcut_name)
                
                if not os.path.exists(shortcut_path):
                    # 创建快捷方式
                    try:
                        import win32com.client
                        shell = win32com.client.Dispatch("WScript.Shell")
                        shortcut = shell.CreateShortCut(shortcut_path)
                        if file_ext == ".lnk":
                            # 如果是lnk文件，直接复制
                            import shutil
                            shutil.copy2(file_path, shortcut_path)
                        else:
                            # 否则创建新的快捷方式
                            shortcut.Targetpath = file_path
                            shortcut.save()
                        print(f"已添加快捷方式到工具列表: {shortcut_name}")
                        
                        # 将新添加的应用添加到more_last_used列表的第一位，确保它排在工具列表的前面
                        app_name = os.path.splitext(shortcut_name)[0]
                        if "more_last_used" not in settings:
                            settings["more_last_used"] = []
                        # 如果已存在，先移除
                        if app_name in settings["more_last_used"]:
                            settings["more_last_used"].remove(app_name)
                        # 添加到第一位
                        settings["more_last_used"].insert(0, app_name)
                        # 保存设置
                        with open(settings_path, "w", encoding="utf-8") as f:
                            json.dump(settings, f, indent=4)
                        
                        # 重新加载工具标签页的按钮
                        if self.floating_window:
                            self.floating_window.create_buttons()
                    except Exception as e:
                        print(f"创建快捷方式失败: {e}")
        
        # 检查是否在运行中（仅工具标签页）
        if current_file.get("type") == "tool" and current_file["name"] in self.floating_window.current_running_apps:
            if not settings.get("skip_minimize_on_game_open", False):
                self.hide_window()
            QTimer.singleShot(100, lambda: self.restore_window(get_target_path(current_file["path"])))
            
        else:
            # 更新最近使用列表（仅工具标签页）
            if current_file.get("type") == "tool":
                if "more_last_used" not in settings:
                    settings["more_last_used"] = []
        
                if current_file["name"] in settings["more_last_used"]:
                    settings["more_last_used"].remove(current_file["name"])
                settings["more_last_used"].insert(0, current_file["name"])
        
                # 保存设置
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4)
    
            # 执行文件
            print(f"执行文件: {current_file['path']}")
            if not settings.get("skip_minimize_on_game_open", False):
                self.hide_window()
            run_as_user(current_file["path"])
        self.floating_window.current_index = 0
        self.floating_window.update_highlight()
        self.floating_window.close()

    def _apply_language(self, lang_code):
        """应用翻译：加载对应的 .qm 文件"""
        app = QApplication.instance()
        if self.translator:
            app.removeTranslator(self.translator)
        i18n_dir = os.path.join(program_directory, 'i18n')
        qm_path = os.path.join(i18n_dir, f'app_{lang_code}.qm')
        if os.path.exists(qm_path):
            self.translator.load(qm_path)
            app.installTranslator(self.translator)

    def switch_language(self, lang_code):
        """切换语言并提示重启"""
        save_language_to_config(lang_code)
        self._apply_language(lang_code)
        reply = QMessageBox.question(
            self,
            self.tr("重启应用"),
            self.tr("语言已更改，需要重启应用才能生效。是否立即重启？"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            app = QApplication.instance()
            app.quit()
            python = sys.executable
            os.execl(python, python, *sys.argv)

    def show_settings_window(self):
        """显示设置窗口"""
        if not hasattr(self, 'settings_window') or self.settings_window is None:
            self.settings_window = SettingsWindow(self)
        self.settings_window.show()
        self.ignore_input_until = pygame.time.get_ticks() + 300

    def apply_debug_output_setting(self):
        if not hasattr(self, "debug_output_window") or self.debug_output_window is None:
            return
        self.debug_output_window.position_top_left()
        if settings.get("debug_output_window", False):
            self.debug_output_window.show()
            self.debug_output_window.raise_()
        else:
            self.debug_output_window.hide()

    def is_admin(self):
        """检查当前进程是否具有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "debug_output_window") and self.debug_output_window:
            self.debug_output_window.position_top_left()

    def run_as_admin(self):
        """以管理员权限重新运行程序"""
        try:
            # 传递启动参数 'refresh'，以便在新程序中执行刷新逻辑
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv) + " refresh", None, 1
            )
            sys.exit()  # 关闭原程序
        except Exception as e:
            print(f"无法以管理员权限重新运行程序: {e}")

    def restart_program(self):
        """重启程序"""
        QApplication.quit()
        # 只传递可执行文件的路径，不传递其他参数
        subprocess.Popen([sys.executable])
    def addgamebutton(self):
        self.hide_window()
        self.addandrefresh_games()
    def addandrefresh_games(self, args=None):
        """添加游戏，处理 extra_paths 中的快捷方式（线程安全）"""
        self.qsaa_thread = SunshineAppManagerThread(args=args)
        self.qsaa_thread.finished_signal.connect(self.deep_reload_games)
        self.qsaa_thread.start()
        return

    def update_controller_status(self, controller_name):
        """更新左侧标签显示的手柄名称"""
        if hasattr(self, 'left_label') and isinstance(self.left_label, QLabel):
            self.left_label.setText(f"🎮️ {controller_name}")
        else:
            print("left_label 未正确初始化")
    
    def on_controller_disconnected(self):
        """当手柄断开时更新左侧标签"""
        if hasattr(self, 'left_label') and isinstance(self.left_label, QLabel):
            # 检查是否还有其他连接的手柄
            if hasattr(self, 'controller_thread') and hasattr(self.controller_thread, 'controllers') and len(self.controller_thread.controllers) > 0:
                # 如果还有其他手柄，显示第一个手柄的名称
                for controller_data in self.controller_thread.controllers.values():
                    controller_name = controller_data['controller'].get_name()
                    self.left_label.setText(f"🎮️ {controller_name}")
                    break
            else:
                # 如果没有其他手柄，显示"未连接手柄"
                self.left_label.setText(self.tr("🎮️未连接手柄"))
    
    def on_controller_error(self, error_msg):
        """当手柄执行出错时更新左侧标签为错误信息"""
        if hasattr(self, 'left_label') and isinstance(self.left_label, QLabel):
            # 将左侧标签的文字改成错误信息
            self.left_label.setText(f"❌ {error_msg}")
    class KeyboardWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setFixedSize(700, 320)
            self.setStyleSheet("background-color: lightgray;")
            self.keys = {"Esc": [66,36,104,40,"green"],"Win": [172,36,104,40,"green"],"Del": [378,268,104,40,"green"],"Enter": [484,268,104,40,"green"],"1!": [68,80,50,40,"yellow"],"2@": [120,80,50,40,"yellow"],"3#": [172,80,50,40,"yellow"],"4$": [224,80,50,40,"yellow"],"5%": [276,80,50,40,"green"],"6^": [328,80,50,40,"green"],"7&": [380,80,50,40,"yellow"],"8*": [432,80,50,40,"yellow"],"9(": [484,80,50,40,"yellow"],"0)": [536,80,50,40,"yellow"],"`~": [16,80,50,40,"green"],"Q": [68,128,50,40,"yellow"],"W": [120,128,50,40,"white"],"E": [172,128,50,40,"white"],"R": [224,128,50,40,"yellow"],"T": [276,128,50,40,"green"],"Y": [328,128,50,40,"green"],"U": [380,128,50,40,"yellow"],"I": [432,128,50,40,"white"],"O": [484,128,50,40,"white"],"P": [536,128,50,40,"yellow"],"-_": [378,36,104,40,"green"],"tab": [16,128,50,40,"green"],"A": [68,176,50,40,"yellow"],"S": [120,176,50,40,"white"],"D": [172,176,50,40,"white"],"F": [224,176,50,40,"yellow"],"G": [276,176,50,40,"green"],"H": [328,176,50,40,"green"],"J": [380,176,50,40,"yellow"],"K": [432,176,50,40,"white"],"L": [484,176,50,40,"white"],";:": [536,176,50,40,"yellow"],"\\|": [588,224,50,40,"green"],"Capslock": [16,176,50,40,"green"],"Z": [68,224,50,40,"yellow"],"X": [120,224,50,40,"yellow"],"C": [172,224,50,40,"yellow"],"V": [224,224,50,40,"yellow"],"B": [276,224,50,40,"green"],"N": [328,224,50,40,"green"],"M": [380,224,50,40,"yellow"],",<": [432,224,50,40,"yellow"],".>": [484,224,50,40,"yellow"],"/?": [536,224,50,40,"yellow"],"shift": [16,224,50,40,"green"],"ctrl": [66,268,104,40,"green"],"alt": [172,268,104,40,"green"],"=+": [484,36,104,40,"green"],"[{": [588,80,50,40,"green"],"]}": [588,128,50,40,"green"],"'\"": [588,176,50,40,"green"]}
            self.active_key = None
            self.key_selected_callback = None
            self.sticky_enabled = False
            self.sticky_keys = set()
            self.sticky_key_names = {'shift', 'ctrl', 'alt', 'Win'}
            self.f_keys_enabled = False
            self.f_keys_active = 0
            self.f_keys = {}
            self.setup_f_keys()
            self.left_joystick_state = {'x': 0.0, 'y': 0.0}
            self.right_joystick_state = {'x': 0.0, 'y': 0.0}
        def set_joystick_state(self, left_state, right_state):
            self.left_joystick_state = left_state
            self.right_joystick_state = right_state
            self.update()
        def setup_f_keys(self):
            for i in range(12):
                x = (i * 52) + 16
                self.f_keys[f'F{i+1}'] = [x, 0, 50, 32, "blue"]
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            # -- 底层添加带圆角的灰色遮罩 --
            rounded_rect = self.rect().adjusted(10, 30, -55, -5)  # 留出些内边距
            radius = 60
            mask_color = QColor(120, 120, 120, 90)  # 灰色且半透明
            painter.setBrush(QBrush(mask_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rounded_rect, radius, radius)

            if self.f_keys_enabled:
                painter.setBrush(QBrush(QColor(100, 150, 255, 180)))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawRect(16, 0, 620, 32)
                for i, (key_name, (x, y, w, h, color)) in enumerate(self.f_keys.items()):
                    brush_color = QColor(255, 0, 0) if i == self.f_keys_active else QColor(100, 150, 255)
                    painter.setBrush(QBrush(brush_color))
                    painter.setPen(QPen(Qt.black))
                    painter.drawRect(x, y, w, h)
                    painter.setPen(QPen(Qt.white))
                    font = QFont("Arial", 12, QFont.Bold)
                    painter.setFont(font)
                    painter.drawText(x, y, w, h, Qt.AlignCenter, key_name)
            if self.sticky_enabled:
                painter.setBrush(QBrush(QColor(255, 255, 0, 180)))
                painter.setPen(QPen(Qt.black, 2))
                painter.drawRect(10, 280, 200, 30)
                painter.setPen(QPen(Qt.black))
                font = QFont("Arial", 10, QFont.Bold)
                painter.setFont(font)
                painter.drawText(15, 300, "粘滞键: 开启")
                if self.sticky_keys:
                    sticky_text = "激活: " + ", ".join(self.sticky_keys)
                    painter.setPen(QPen(Qt.red))
                    painter.drawText(15, 315, sticky_text)
            for key_name, (x, y, w, h, color) in self.keys.items():
                # 精简：合并颜色生成逻辑，减少代码行数，全部字体改为白色
                base_color = QColor(200, 200, 200) if color == 'white' else (
                    QColor(180, 180, 180) if color == 'yellow' else (
                        QColor(140, 140, 140) if color == 'green' else QColor(100, 100, 100)))
                if key_name == self.active_key:
                    overlay = QColor(255, 30, 30, 120)
                    brush_color = QColor(
                        min(base_color.red() + overlay.red()//3, 255),
                        min(base_color.green() + overlay.green()//3, 255),
                        min(base_color.blue() + overlay.blue()//3, 255),
                        210
                    )
                    pen_color = QColor(255, 90, 90)
                elif key_name in self.sticky_keys and self.sticky_enabled:
                    overlay = QColor(255, 220, 64, 100)
                    brush_color = QColor(
                        min(base_color.red() + overlay.red()//5, 255),
                        min(base_color.green() + overlay.green()//5, 255),
                        min(base_color.blue() + overlay.blue()//5, 255),
                        180
                    )
                    pen_color = QColor(255, 220, 80)
                else:
                    # 半透明黑作为普通按键叠加
                    alpha = 125
                    brush_color = QColor(
                        max(base_color.red() - alpha//4, 0),
                        max(base_color.green() - alpha//4, 0),
                        max(base_color.blue() - alpha//4, 0),
                        210
                    )
                    pen_color = QColor(60, 60, 60)
                painter.setBrush(QBrush(brush_color))
                painter.setPen(QPen(pen_color, 2))
                painter.drawRect(x, y, w, h)
                painter.setFont(QFont("Arial", 12))
                painter.setPen(QPen(QColor(255, 255, 255)))  # 白色字体
                display_name = "Caps" if key_name == "Capslock" else key_name
                painter.drawText(x, y, w, h, Qt.AlignCenter, display_name)
            def circle_to_square_progress(x: float, y: float):
                r = math.hypot(x, y)
                if r == 0.0:
                    return 0.0, 0.0
                m = max(abs(x), abs(y))
                if m == 0.0:
                    return 0.0, 0.0
                def nonlinear_radius_mapping(r: float) -> float:
                    if r <= 0.75:
                        return (r / 0.75) * 0.5
                    else:
                        return 0.5 + ((r - 0.75) / 0.25) * 0.5
                r_nl = nonlinear_radius_mapping(r)
                k = r_nl / m
                u = max(-1.0, min(1.0, x * k))
                v = max(-1.0, min(1.0, y * k))
                return u, v
            max_x = 100
            max_y = 90
            center_left = QPoint(170, 168)
            lx = self.left_joystick_state.get('x', 0.0)
            ly = self.left_joystick_state.get('y', 0.0)
            ux, uy = circle_to_square_progress(lx, ly)
            end_left = QPoint(int(center_left.x() + ux * max_x), int(center_left.y() + uy * max_y))
            painter.setPen(QPen(QColor(120, 120, 120), 4))
            painter.drawLine(center_left, end_left)
            painter.setBrush(QBrush(QColor(120, 120, 120)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(end_left, 6, 6)
            center_right = QPoint(482, 172)
            rx = self.right_joystick_state.get('x', 0.0)
            ry = self.right_joystick_state.get('y', 0.0)
            ux, uy = circle_to_square_progress(rx, ry)
            end_right = QPoint(int(center_right.x() + ux * max_x), int(center_right.y() + uy * max_y))
            painter.setPen(QPen(QColor(120, 120, 120), 4))
            painter.drawLine(center_right, end_right)
            painter.setBrush(QBrush(QColor(120, 120, 120)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(end_right, 6, 6)
        def update_active_key(self, key):
            if self.active_key == key:
                return
            self.active_key = key
            self.update()
            if self.key_selected_callback:
                self.key_selected_callback(key)
        def toggle_sticky_mode(self):
            self.sticky_enabled = not self.sticky_enabled
            if not self.sticky_enabled:
                self.sticky_keys.clear()
            self.update()
        def toggle_f_keys_mode(self):
            self.f_keys_enabled = not self.f_keys_enabled
            if not self.f_keys_enabled:
                self.f_keys_active = 0
            self.update()
        def move_f_keys_selection(self, direction):
            if self.f_keys_enabled:
                self.f_keys_active = (self.f_keys_active + direction) % 12
                self.update()
        def get_current_f_key(self):
            if self.f_keys_enabled:
                f_key_names = list(self.f_keys.keys())
                return f_key_names[self.f_keys_active]
            return None
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                pos = event.pos()
                from PyQt5.QtCore import QRect
                for key_name, (x, y, w, h, color) in self.keys.items():
                    rect = QRect(x, y, w, h)
                    if rect.contains(pos):
                        self.update_active_key(key_name)
                        break

    # 迁移：覆盖层用手柄线程作为内部类
    class JoystickThread(QThread):
        joystick_updated = pyqtSignal(int, float, float, bool, bool)
        def __init__(self, mapping=None):
            super().__init__()
            self.mapping = mapping
            self.running = True
            self.joysticks = []
        def run(self):
            for i in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(i)
                joy.init()
                self.joysticks.append(joy)
                print(f"手柄 {i} 已连接: {joy.get_name()}")
            while self.running:
                pygame.event.pump()
                for i, joystick in enumerate(self.joysticks):
                    left_x = joystick.get_axis(0)
                    left_y = joystick.get_axis(1)
                    right_x = joystick.get_axis(2)
                    right_y = joystick.get_axis(3)
                    lb_pressed = joystick.get_button(self.mapping.left_bumper) if joystick.get_numbuttons() > self.mapping.left_bumper else False
                    rb_pressed = joystick.get_button(self.mapping.right_bumper) if joystick.get_numbuttons() > self.mapping.right_bumper else False
                    self.joystick_updated.emit(0, left_x, left_y, lb_pressed, rb_pressed)
                    self.joystick_updated.emit(1, right_x, right_y, lb_pressed, rb_pressed)
                self.msleep(16)
        def stop(self):
            self.running = False
            print("键盘操作已停止")

    # 迁移：鼠标提示窗口作为内部类
    class MouseWindow(QDialog):
        def __init__(self):
            super().__init__()
            self.initUI()
        def initUI(self):
            self.label = QLabel("↖🎮️", self)
            self.label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 15px; color: white; border: 1px solid black; border-radius: 0px; background-color: rgba(0, 0, 0, 125);")
            self.label.adjustSize()
            screen_geometry = QApplication.primaryScreen().geometry()
            label_width = self.label.width()
            label_height = self.label.height()
            self.label.move(screen_geometry.width() - label_width - 30, screen_geometry.height() - label_height - 30)
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setWindowOpacity(0.7)
            self.setGeometry(screen_geometry)
            self.show()

class ProgressWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(10 * parent.scale_factor)}px;
                border: {int(2 * parent.scale_factor)}px solid #444444;
            }}
        """)
        self.setFixedSize(int(300 * parent.scale_factor), int(100 * parent.scale_factor))

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(int(10 * parent.scale_factor))

        self.label = QLabel(self.tr("正在刷新游戏列表..."))
        self.label.setStyleSheet(f"color: white; font-size: {int(16 * parent.scale_factor)}px;")
        self.layout.addWidget(self.label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: {int(2 * parent.scale_factor)}px solid #444444;
                border-radius: {int(5 * parent.scale_factor)}px;
                background: #2e2e2e;
            }}
            QProgressBar::chunk {{
                background-color: #00ff00;
                width: {int(20 * parent.scale_factor)}px;
            }}
        """)
        self.layout.addWidget(self.progress_bar)

    def update_progress(self, current, total):
        """更新进度条"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

class GameControllerThread(QThread):
    """子线程用来监听手柄输入"""
    gamepad_signal = pyqtSignal(str)
    controller_connected_signal = pyqtSignal(str)  # 新增信号，用于通知主线程手柄连接
    controller_error_signal = pyqtSignal(str)  # 新增信号，用于通知主线程发生错误
    controller_disconnected_signal = pyqtSignal()  # 新增信号，用于通知主线程手柄断开

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        pygame.init()
        self.controllers = {}
        self._running = True  # 添加运行标志
        self.last_move_time = 0
        self.move_delay = 0.1
        self.axis_threshold = 0.5
        self.last_hat_time = 0
        self.hat_delay = 0.05
        self.last_hat_value = (0, 0)

    def stop(self):
        """停止线程"""
        self._running = False
        
    # ---- DAS / ARR repeat helpers ----
    def _init_repeat_state_for_controller(self, instance_id):
        # state for directional DAS/ARR handling per controller
        self.controllers[instance_id].setdefault('repeat', {
            'dirs': {
                'UP':    {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'DOWN':  {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'LEFT':  {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'RIGHT': {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
            }
        })

    def _handle_direction_state(self, instance_id, up, down, left, right):
        """Centralized handling of directional inputs with DAS/ARR.
        Emits 'FIRST-<DIR>' on initial press, then waits DAS seconds,
        then emits repeated '<DIR>' every ARR seconds. If ARR==0 emits '<DIR>_EDGE' once.
        """
        now = time.time()
        das = getattr(self, 'das', 0.3)  # seconds before auto-repeat starts
        arr = getattr(self, 'arr', 0.07)  # repeat interval in seconds; 0 => edge jump

        repeat = self.controllers[instance_id].setdefault('repeat', {})
        dirs = repeat.setdefault('dirs', {})

        booleans = {'UP': up, 'DOWN': down, 'LEFT': left, 'RIGHT': right}

        for dname, is_pressed in booleans.items():
            state = dirs.setdefault(dname, {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False})

            if is_pressed:
                if not state['pressed']:
                    # initial press
                    state['pressed'] = True
                    state['first_sent'] = True
                    state['edge_sent'] = False
                    state['next_time'] = now + das
                    # emit FIRST event
                    self.gamepad_signal.emit(f'FIRST-{dname}')
                else:
                    # already pressed, check for repeat
                    if now >= state['next_time']:
                        if arr == 0:
                            # edge behavior: emit once
                            if not state.get('edge_sent', False):
                                state['edge_sent'] = True
                                self.gamepad_signal.emit(f'{dname}_EDGE')
                        else:
                            # emit normal repeat and schedule next
                            self.gamepad_signal.emit(dname)
                            state['next_time'] = now + arr
            else:
                # released
                if state['pressed']:
                    state['pressed'] = False
                    state['first_sent'] = False
                    state['edge_sent'] = False
                    state['next_time'] = 0
    def run(self):
        """监听手柄输入"""
        while self._running:  # 使用运行标志控制循环
            try:
                pygame.event.pump()  # 确保事件队列被更新

                # 处理事件
                for event in pygame.event.get():
                    # 处理手柄连接事件
                    if event.type == pygame.JOYDEVICEADDED:
                        try:
                            controller = pygame.joystick.Joystick(event.device_index)
                            controller.init()
                            mapping = ControllerMapping(controller)
                            self.controllers[controller.get_instance_id()] = {
                                'controller': controller,
                                'mapping': mapping
                            }
                            # 初始化 DAS/ARR 状态
                            try:
                                self._init_repeat_state_for_controller(controller.get_instance_id())
                            except Exception:
                                pass
                            print(f"Controller {controller.get_instance_id()} connected: {controller.get_name()}")
                            self.controller_connected_signal.emit(controller.get_name())
                        except pygame.error as e:
                            print(f"Failed to initialize controller {event.device_index}: {e}")
                
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        if event.instance_id in self.controllers:
                            print(f"Controller {event.instance_id} disconnected")
                            del self.controllers[event.instance_id]
                            # 发出手柄断开信号
                            self.controller_disconnected_signal.emit()
                        # 清理方向状态
                        try:
                            if event.instance_id in self.direction_states:
                                del self.direction_states[event.instance_id]
                        except Exception:
                            pass

                # 处理所有已连接手柄的输入
                for controller_data in self.controllers.values():
                    controller = controller_data['controller']
                    mapping = controller_data['mapping']
                    
                    # 汇总方向输入（hat, 摇杆, D-pad 按钮），统一交给 DAS/ARR 处理
                    try:
                        cid = controller.get_instance_id()
                    except Exception:
                        cid = None

                    # 初始化方向标记
                    up_pressed = down_pressed = left_pressed = right_pressed = False

                    # hat (D-pad) 处理：任何 hat 非零都会设置对应方向
                    try:
                        for i in range(controller.get_numhats()):
                            hat = controller.get_hat(i)
                            if hat != (0, 0):
                                up_pressed = up_pressed or (hat[1] == 1)
                                down_pressed = down_pressed or (hat[1] == -1)
                                left_pressed = left_pressed or (hat[0] == -1)
                                right_pressed = right_pressed or (hat[0] == 1)
                    except Exception:
                        pass

                    # 摇杆轴：合并左右两个摇杆的输入
                    try:
                        left_x = controller.get_axis(mapping.left_stick_x)
                        left_y = controller.get_axis(mapping.left_stick_y)
                        right_x = controller.get_axis(mapping.right_stick_x)
                        right_y = controller.get_axis(mapping.right_stick_y)
                    except:
                        left_x = left_y = right_x = right_y = 0

                    if left_y < -self.axis_threshold or right_y < -self.axis_threshold:
                        up_pressed = True
                    if left_y > self.axis_threshold or right_y > self.axis_threshold:
                        down_pressed = True
                    if left_x < -self.axis_threshold or right_x < -self.axis_threshold:
                        left_pressed = True
                    if left_x > self.axis_threshold or right_x > self.axis_threshold:
                        right_pressed = True

                    # D-pad 按钮（PS4 / 其他）
                    try:
                        buttons = [controller.get_button(i) for i in range(controller.get_numbuttons())]
                    except Exception:
                        buttons = []

                    try:
                        if mapping.controller_type == 'ps4' or mapping.controller_type != 'xbox360':
                            # 对于 ps4 和其他手柄，都支持 mapping 中的 dpad 按钮索引
                            if buttons and mapping.dpad_up is not None and buttons[mapping.dpad_up]:
                                up_pressed = True
                            if buttons and mapping.dpad_down is not None and buttons[mapping.dpad_down]:
                                down_pressed = True
                            if buttons and mapping.dpad_left is not None and buttons[mapping.dpad_left]:
                                left_pressed = True
                            if buttons and mapping.dpad_right is not None and buttons[mapping.dpad_right]:
                                right_pressed = True
                    except Exception:
                        pass

                    # 最后：统一处理方向状态（如果有 controller id）
                    if cid is not None:
                        # 初始化 repeat 状态（如果尚未初始化）
                        if cid not in self.controllers or 'repeat' not in self.controllers.get(cid, {}):
                            try:
                                if cid in self.controllers:
                                    self._init_repeat_state_for_controller(cid)
                            except Exception:
                                pass
                        try:
                            self._handle_direction_state(cid, up_pressed, down_pressed, left_pressed, right_pressed)
                        except Exception:
                            pass

                    # 检查动作按钮
                    if buttons[mapping.button_a]:  # A/Cross/○
                        self.gamepad_signal.emit('A')
                    if buttons[mapping.button_b]:  # B/Circle/×
                        self.gamepad_signal.emit('B')
                    if buttons[mapping.button_x]:  # X/Square/□
                        self.gamepad_signal.emit('X')
                    if buttons[mapping.button_y]:  # Y/Triangle/△
                        self.gamepad_signal.emit('Y')
                    if buttons[mapping.guide]:
                        self.gamepad_signal.emit('GUIDE')
                    if buttons[mapping.back]:  # Back
                        self.gamepad_signal.emit('BACK')
                    if buttons[mapping.start]:  # Start
                        self.gamepad_signal.emit('START')
                    if buttons[mapping.left_bumper]:  # LB
                        self.gamepad_signal.emit('LB')
                    if buttons[mapping.right_bumper]:  # RB
                        self.gamepad_signal.emit('RB')
                    #if buttons[mapping.left_trigger]:  # LT
                    #    self.gamepad_signal.emit('LT')
                    #if buttons[mapping.right_trigger]:  # RT
                    #    self.gamepad_signal.emit('RT')
                    if buttons[mapping.left_stick_in]:  # LS
                        self.gamepad_signal.emit('LS')
                    if buttons[mapping.right_stick_in]:  # RS
                        self.gamepad_signal.emit('RS')

                time.sleep(0.01)
            except Exception as e:
                self.controller_error_signal.emit('手柄读取出错')
                print(f"Error in event loop: {e}")
                time.sleep(5)  # 出错时稍微等待
                self.run()  # 重新进入循环
class CustomFilePickerDialog(QDialog):
    """自制文件选择器，支持手柄导航和快速访问"""
    file_selected = pyqtSignal(str)
    dialog_closed = pyqtSignal()
    
    def __init__(self, parent=None, scale_factor=1.0, file_types=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.scale_factor = scale_factor
        self.file_types = file_types or ['.exe', '.lnk']
        
        self.setWindowTitle(self.tr("选择要启动的文件"))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(int(900 * scale_factor), int(600 * scale_factor))
        
        # 初始化状态
        self.current_path = ""
        self.current_file_index = 0
        self.current_sidebar_index = -1  # -1 表示焦点在文件列表
        self.selected_file = None
        self.file_list = []
        self.sidebar_items = []
        
        # 手柄状态
        self.last_input_time = 0
        self.input_delay = 200  # 防抖延迟
        self.ignore_input_until = 0
        
        # 初始化UI
        self.init_ui()
        self.build_sidebar()
        self.navigate_to(self.get_initial_path())
        
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(int(10 * self.scale_factor), int(10 * self.scale_factor), 
                                      int(10 * self.scale_factor), int(10 * self.scale_factor))
        main_layout.setSpacing(int(10 * self.scale_factor))
        
        # ========== 左侧边栏 ==========
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(int(5 * self.scale_factor))
        
        sidebar_label = QLabel(self.tr("快速访问"))
        sidebar_label.setStyleSheet(f"color: #93ffff; font-size: {int(14 * self.scale_factor)}px; font-weight: bold;")
        sidebar_layout.addWidget(sidebar_label)
        
        self.sidebar_list = QListWidget()
        self.sidebar_list.setStyleSheet(self.get_sidebar_qss())
        self.sidebar_list.itemClicked.connect(self.on_sidebar_item_clicked)
        sidebar_layout.addWidget(self.sidebar_list)
        
        # ========== 右侧主区域 ==========
        right_layout = QVBoxLayout()
        right_layout.setSpacing(int(5 * self.scale_factor))
        
        # 路径栏
        path_layout = QHBoxLayout()
        path_label = QLabel(self.tr("位置:"))
        path_label.setStyleSheet(f"color: white; font-size: {int(12 * self.scale_factor)}px;")
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setStyleSheet(self.get_path_input_qss())
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_display)
        right_layout.addLayout(path_layout)
        
        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setStyleSheet(self.get_file_list_qss())
        self.file_list_widget.itemClicked.connect(self.on_file_item_clicked)
        self.file_list_widget.itemDoubleClicked.connect(self.on_file_item_double_clicked)
        right_layout.addWidget(self.file_list_widget)
        
        # 选择栏
        selection_layout = QHBoxLayout()
        selection_label = QLabel(self.tr("选择:"))
        selection_label.setStyleSheet(f"color: white; font-size: {int(12 * self.scale_factor)}px;")
        self.selection_display = QLineEdit()
        self.selection_display.setReadOnly(True)
        self.selection_display.setStyleSheet(self.get_path_input_qss())
        selection_layout.addWidget(selection_label)
        selection_layout.addWidget(self.selection_display)
        right_layout.addLayout(selection_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.navigate_up_button = QPushButton(self.tr("⬆ 返回上级（手柄x键）"))
        self.navigate_up_button.setStyleSheet(self.get_button_qss("#2E7D9B"))
        self.navigate_up_button.clicked.connect(self.on_navigate_up)
        button_layout.addWidget(self.navigate_up_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton(self.tr("取消"))
        self.cancel_button.setStyleSheet(self.get_button_qss("#666666"))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.confirm_button = QPushButton(self.tr("选择"))
        self.confirm_button.setStyleSheet(self.get_button_qss("#2E7D9B"))
        self.confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(self.confirm_button)
        
        right_layout.addLayout(button_layout)
        
        # 添加侧边栏和右侧区域
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(int(200 * self.scale_factor))
        
        main_layout.addWidget(sidebar_widget)
        main_layout.addLayout(right_layout)
        
        self.setLayout(main_layout)
        self.setStyleSheet(self.get_dialog_qss())
        
    def get_dialog_qss(self):
        """对话框样式表"""
        return f"""
            CustomFilePickerDialog {{
                background-color: #2e2e2e;
                color: white;
            }}
        """
    
    def get_sidebar_qss(self):
        """侧边栏样式表"""
        return f"""
            QListWidget {{
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555555;
                border-radius: {int(5 * self.scale_factor)}px;
                outline: none;
            }}
            QListWidget::item {{
                padding: {int(8 * self.scale_factor)}px;
                border-radius: {int(3 * self.scale_factor)}px;
                margin: {int(2 * self.scale_factor)}px;
            }}
            QListWidget::item:selected {{
                background-color: #2E7D9B;
                color: #93ffff;
                border: 1px solid #93ffff;
            }}
            QListWidget::item:hover {{
                background-color: #444444;
            }}
        """
    
    def get_file_list_qss(self):
        """文件列表样式表"""
        return f"""
            QListWidget {{
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555555;
                border-radius: {int(5 * self.scale_factor)}px;
                outline: none;
            }}
            QListWidget::item {{
                padding: {int(6 * self.scale_factor)}px;
                border-radius: {int(3 * self.scale_factor)}px;
                margin: {int(1 * self.scale_factor)}px;
                height: {int(32 * self.scale_factor)}px;
            }}
            QListWidget::item:selected {{
                background-color: #2E7D9B;
                color: #93ffff;
                border: 1px solid #93ffff;
            }}
            QListWidget::item:hover {{
                background-color: #444444;
            }}
        """
    
    def get_path_input_qss(self):
        """路径输入框样式表"""
        return f"""
            QLineEdit {{
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555555;
                border-radius: {int(3 * self.scale_factor)}px;
                padding: {int(5 * self.scale_factor)}px;
            }}
        """
    
    def get_button_qss(self, color):
        """按钮样式表"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 1px solid #555555;
                border-radius: {int(5 * self.scale_factor)}px;
                padding: {int(8 * self.scale_factor)}px {int(16 * self.scale_factor)}px;
                font-size: {int(12 * self.scale_factor)}px;
                min-width: {int(80 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self.lighten_color(color, -20)};
            }}
        """
    
    @staticmethod
    def lighten_color(color_hex, offset):
        """调整颜色亮度"""
        color_hex = color_hex.lstrip('#')
        r, g, b = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
        r = max(0, min(255, r + offset))
        g = max(0, min(255, g + offset))
        b = max(0, min(255, b + offset))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def build_sidebar(self):
        """构建侧边栏快速访问项"""
        self.sidebar_items = []
        
        # 常用路径
        quick_access = [
            (self.tr("桌面"), os.path.expanduser("~/Desktop")),
            (self.tr("下载"), os.path.expanduser("~/Downloads")),
            (self.tr("文档"), os.path.expanduser("~/Documents")),
            (self.tr("图片"), os.path.expanduser("~/Pictures")),
        ]
        
        for name, path in quick_access:
            if os.path.exists(path):
                self.sidebar_items.append((name, path))
        
        # 驱动器
        for drive in self.get_available_drives():
            self.sidebar_items.append((drive, drive + "\\"))
        
        # 刷新侧边栏显示
        self.refresh_sidebar_display()
    
    @staticmethod
    def get_available_drives():
        """获取可用的驱动器"""
        drives = []
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f'{letter}:'
            if os.path.exists(drive):
                drives.append(drive)
        return drives
    
    def refresh_sidebar_display(self):
        """刷新侧边栏显示"""
        self.sidebar_list.clear()
        for name, path in self.sidebar_items:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, path)
            self.sidebar_list.addItem(item)
    
    def get_initial_path(self):
        """获取初始路径"""
        initial_paths = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            "C:\\Program Files",
            "C:\\",
        ]
        for path in initial_paths:
            if os.path.exists(path):
                return path
        return "C:\\"
    
    def navigate_to(self, path):
        """导航到指定目录"""
        try:
            if not os.path.exists(path) or not os.path.isdir(path):
                path = self.get_initial_path()
            
            self.current_path = path
            self.path_display.setText(path)
            self.file_list = []
            self.current_file_index = 0
            
            # 列出目录内容
            try:
                items = os.listdir(path)
            except PermissionError:
                self.file_list_widget.clear()
                item = QListWidgetItem("⚠ 无权限访问此目录")
                self.file_list_widget.addItem(item)
                return
            
            # 按优先级排序（文件夹优先）
            dirs = []
            files = []
            
            for item_name in items:
                item_path = os.path.join(path, item_name)
                try:
                    if os.path.isdir(item_path):
                        dirs.append(("📁 " + item_name, item_path, True))
                    else:
                        # 检查文件类型
                        _, ext = os.path.splitext(item_name)
                        if ext.lower() in self.file_types:
                            icon = "📄" if ext.lower() == '.exe' else "🔗"
                            files.append((icon + " " + item_name, item_path, False))
                except:
                    pass
            
            self.file_list = dirs + files
            self.refresh_file_list_display()
            
            # 更新按钮状态
            parent_path = os.path.dirname(path.rstrip('\\'))
            self.navigate_up_button.setEnabled(parent_path and parent_path != path)
            
        except Exception as e:
            print(f"导航错误: {e}")
    
    def refresh_file_list_display(self):
        """刷新文件列表显示"""
        self.file_list_widget.clear()
        for display_name, full_path, is_dir in self.file_list:
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, full_path)
            item.setData(Qt.UserRole + 1, is_dir)
            self.file_list_widget.addItem(item)
        
        # 恢复上次的选择位置
        if self.file_list and self.current_file_index < len(self.file_list):
            self.file_list_widget.setCurrentRow(self.current_file_index)
        elif self.file_list:
            self.file_list_widget.setCurrentRow(0)
    
    def on_sidebar_item_clicked(self, item):
        """侧边栏项点击"""
        path = item.data(Qt.UserRole)
        if path:
            self.navigate_to(path)
    
    def on_file_item_clicked(self, item):
        """文件列表项点击"""
        full_path = item.data(Qt.UserRole)
        is_dir = item.data(Qt.UserRole + 1)
        
        if is_dir:
            self.navigate_to(full_path)
        else:
            self.selected_file = full_path
            self.selection_display.setText(os.path.basename(full_path))
            self.confirm_button.setStyleSheet(self.get_button_qss("#4CAF50"))
    
    def on_file_item_double_clicked(self, item):
        """文件列表项双击"""
        full_path = item.data(Qt.UserRole)
        is_dir = item.data(Qt.UserRole + 1)
        
        if is_dir:
            self.navigate_to(full_path)
        else:
            self.selected_file = full_path
            self.accept()
    
    def on_navigate_up(self):
        """返回上层目录"""
        parent = os.path.dirname(self.current_path.rstrip('\\'))
        if parent and parent != self.current_path:
            self.navigate_to(parent)
    
    def handle_gamepad_input(self, action):
        """处理手柄输入"""
        try:
            current_time = pygame.time.get_ticks()
            
            # 防抖检查
            if current_time < self.ignore_input_until:
                return
            if current_time - self.last_input_time < self.input_delay:
                return
            
            # 焦点在侧边栏 (-1) 或文件列表 (0)
            focus_area = getattr(self, '_focus_area', 0)  # 0=文件列表, -1=侧边栏
            
            # 处理导航
            if action in ('UP', 'FIRST-UP'):
                if focus_area == -1:
                    self.move_sidebar_selection(-1)
                else:
                    self.move_file_selection(-1)
            elif action in ('DOWN', 'FIRST-DOWN'):
                if focus_area == -1:
                    self.move_sidebar_selection(1)
                else:
                    self.move_file_selection(1)
            elif action in ('LEFT', 'FIRST-LEFT'):
                if focus_area == 0:
                    # 从文件列表切换到侧边栏
                    self._focus_area = -1
                    self.update_focus_highlight()
                # 在侧边栏按左：不做任何操作
            elif action in ('RIGHT', 'FIRST-RIGHT'):
                if focus_area == -1:
                    # 从侧边栏切换到文件列表
                    self._focus_area = 0
                    self.update_focus_highlight()
                else:
                    # 在文件列表按右：进入目录
                    item = self.file_list_widget.currentItem()
                    if item:
                        is_dir = item.data(Qt.UserRole + 1)
                        if is_dir:
                            full_path = item.data(Qt.UserRole)
                            self.navigate_to(full_path)
            elif action == 'A':
                if focus_area == -1:
                    # 选择侧边栏项
                    item = self.sidebar_list.currentItem()
                    if item:
                        self.on_sidebar_item_clicked(item)
                        # 切换到文件列表
                        self._focus_area = 0
                        self.update_focus_highlight()
                else:
                    # 选择文件列表项
                    item = self.file_list_widget.currentItem()
                    if item:
                        is_dir = item.data(Qt.UserRole + 1)
                        if is_dir:
                            full_path = item.data(Qt.UserRole)
                            self.navigate_to(full_path)
                        else:
                            self.on_file_item_clicked(item)
                            if self.selected_file:
                                self.accept()
            elif action == 'B':
                self.reject()
            elif action == 'X':
                # X键返回上级目录
                self.navigate_to(os.path.dirname(self.current_path.rstrip('\\')))
            
            self.last_input_time = current_time
        except Exception as e:
            print(f"CustomFilePickerDialog 手柄输入异常: {e}")
    
    def move_sidebar_selection(self, offset):
        """移动侧边栏选择"""
        current_row = self.sidebar_list.currentRow()
        new_row = max(0, min(self.sidebar_list.count() - 1, current_row + offset))
        self.sidebar_list.setCurrentRow(new_row)
    
    def update_focus_highlight(self):
        """更新焦点高亮显示"""
        focus_area = getattr(self, '_focus_area', 0)
        if focus_area == -1:
            # 侧边栏高亮（替换 border: 1px solid #555555; 为高亮色）
            self.sidebar_list.setStyleSheet(
                self.get_sidebar_qss().replace("border: 1px solid #555555;", "border: 2px solid #93ffff;")
            )
            self.file_list_widget.setStyleSheet(self.get_file_list_qss())
        else:
            # 文件列表高亮
            self.sidebar_list.setStyleSheet(self.get_sidebar_qss())
            self.file_list_widget.setStyleSheet(
                self.get_file_list_qss().replace("border: 1px solid #555555;", "border: 2px solid #93ffff;")
            )
    
    def move_file_selection(self, offset):
        """移动文件选择"""
        current_row = self.file_list_widget.currentRow()
        new_row = max(0, min(len(self.file_list) - 1, current_row + offset))
        self.file_list_widget.setCurrentRow(new_row)
    
    def showEvent(self, event):
        """窗口显示时"""
        super().showEvent(event)
        self.ignore_input_until = pygame.time.get_ticks() + 300
        self.file_list_widget.setFocus()
    
    def accept(self):
        """确认选择"""
        if self.selected_file:
            self.file_selected.emit(self.selected_file)
        super().accept()
    
    def reject(self):
        """取消选择"""
        self.dialog_closed.emit()
        super().reject()


class FileDialogManager(QObject):
    """文件选择对话框管理器（在主线程中操作 GUI）"""
    file_selected = pyqtSignal(str)
    dialog_closed = pyqtSignal()

    def __init__(self, parent=None, scale_factor=1.0):
        super().__init__(parent)
        self.parent_widget = parent
        self.scale_factor = scale_factor
        self.dialog = None
        self._create_dialog()

    def _create_dialog(self):
        """在主线程中创建对话框"""
        self.dialog = CustomFilePickerDialog(
            parent=self.parent_widget,
            scale_factor=self.scale_factor,
            file_types=['.exe', '.lnk']
        )
        self.dialog.setWindowModality(Qt.ApplicationModal)
        
        # 连接信号
        self.dialog.file_selected.connect(self.on_file_selected)
        self.dialog.dialog_closed.connect(self.on_dialog_closed)
    
    def show_dialog(self):
        """显示对话框"""
        if self.dialog:
            self.dialog.show()
            self.dialog.raise_()
            self.dialog.activateWindow()
    
    def on_file_selected(self, file_path):
        """文件选择后"""
        self.file_selected.emit(file_path)
    
    def on_dialog_closed(self):
        """对话框关闭后"""
        self.dialog_closed.emit()
    
    def handle_gamepad_input(self, action):
        """代理手柄输入到对话框"""
        if self.dialog and self.dialog.isVisible():
            self.dialog.handle_gamepad_input(action)
class FloatingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)  # 确保窗口关闭时会被销毁
        bat_dir = './morefloder'
        self.current_running_apps = set()
        if not os.path.exists(bat_dir):
            os.makedirs(bat_dir)  # 创建目录
        self.select_add_btn = None  # 在初始化方法中定义
        self.select_del_btn = None  # 同样定义删除按钮
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(10 * parent.scale_factor * 1.4)}px;
                border: {int(2 * parent.scale_factor * 1.4)}px solid #444444;
            }}
        """)
        
        self.current_index = 0
        self.current_tab_index = 0  # 当前标签页索引
        self.buttons = []  # 所有标签页的按钮列表
        self.tab_buttons = {}  # 存储每个标签页的按钮列表 {tab_index: [buttons]}
        
        # 添加懒加载相关属性
        self.tab_widgets = {}  # 存储每个标签页的widget
        self.tab_layouts = {}  # 存储每个标签页的layout
        self.tabs_loaded = {}  # 存储每个标签页是否已加载
        
        # 添加字母表选择模式相关属性
        self.in_alphabet_mode = False  # 是否处于字母表选择模式
        self.current_alphabet_index = 0  # 当前选中的字母索引
        
        # 添加防抖相关属性
        self.last_input_time = 0
        self.input_delay = 200  # 设置200毫秒的防抖延迟
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建一个水平布局来包含标签页和字母排序表
        tab_with_alphabet_layout = QHBoxLayout()
        tab_with_alphabet_layout.setContentsMargins(0, 0, 0, 0)
        tab_with_alphabet_layout.setSpacing(0)
        
        # 创建标签页
        self.tab_widget = QTabWidget(self)
        # 设置标签栏为伸展模式，让标签平均分配宽度
        self.tab_widget.setTabBarAutoHide(False)
        self.tab_widget.tabBar().setExpanding(True)
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar {{
                background-color: rgba(50, 50, 50, 0.8);
            }}
            QTabBar::tab {{
                background-color: rgba(60, 60, 60, 0.8);
                color: white;
                padding: {int(12 * parent.scale_factor * 1.4)}px {int(16 * parent.scale_factor * 1.4)}px;
                margin-right: {int(2 * parent.scale_factor * 1.4)}px;
                border-top-left-radius: {int(5 * parent.scale_factor * 1.4)}px;
                border-top-right-radius: {int(5 * parent.scale_factor * 1.4)}px;
                font-size: {int(14 * parent.scale_factor * 1.4)}px;
                min-width: {int(98 * parent.scale_factor * 1.4)}px;
            }}
            QTabBar::tab:selected {{
                background-color: rgba(80, 80, 80, 0.9);
            }}
            QTabBar::tab:hover {{
                background-color: rgba(70, 70, 70, 0.9);
            }}
        """)
        
        # 创建字母排序表
        self.alphabet_widget = QWidget(self)
        self.alphabet_widget.setFixedWidth(int(200 * parent.scale_factor * 1.4))
        self.alphabet_layout = QGridLayout(self.alphabet_widget)
        self.alphabet_layout.setContentsMargins(int(5 * parent.scale_factor * 1.4), int(10 * parent.scale_factor * 1.4), int(5 * parent.scale_factor * 1.4), int(10 * parent.scale_factor * 1.4))
        self.alphabet_layout.setSpacing(0)
        self.alphabet_widget.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(40, 40, 40, 0.8);
            }}
        """)
        
        # 定义字母表，按照图示排列
        alphabet = [
            ['&', '#', 'A', 'B'],
            ['C', 'D', 'E', 'F'],
            ['G', 'H', 'I', 'J'],
            ['K', 'L', 'M', 'N'],
            ['O', 'P', 'Q', 'R'],
            ['S', 'T', 'U', 'V'],
            ['W', 'X', 'Y', 'Z']
        ]
        
        # 创建字母按钮
        self.alphabet_buttons = {}
        for row, letters in enumerate(alphabet):
            for col, letter in enumerate(letters):
                btn = QPushButton(letter)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        font-size: {int(20 * parent.scale_factor * 1.4)}px;
                        min-width: {int(48 * parent.scale_factor * 1.4)}px;
                        min-height: {int(64 * parent.scale_factor * 1.4)}px;
                        border: none;
                        border-radius: {int(4 * parent.scale_factor * 1.4)}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.2);
                    }}
                    QPushButton:pressed {{
                        background-color: rgba(255, 255, 255, 0.3);
                    }}
                """)
                btn.clicked.connect(lambda checked, l=letter: self.jump_to_letter(l))
                self.alphabet_layout.addWidget(btn, row, col)
                self.alphabet_buttons[letter] = btn
        
        # 初始隐藏字母排序表
        self.alphabet_widget.setVisible(False)
        
        # 将标签页和字母排序表添加到水平布局
        tab_with_alphabet_layout.addWidget(self.tab_widget, 1)  # 标签页占据主要空间
        tab_with_alphabet_layout.addWidget(self.alphabet_widget)  # 字母排序表在右侧
        
        # 将水平布局添加到主布局
        main_layout.addLayout(tab_with_alphabet_layout)
        
        # 创建三个标签页
        self.create_tool_tab()  # 工具标签页
        self.create_desktop_tab()  # 桌面标签页
        self.create_all_apps_tab()  # 全部应用标签页
        
        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 设置窗口大小
        self.setFixedSize(int(400 * parent.scale_factor * 1.4), int(500 * parent.scale_factor * 1.4))
        
        # 添加动画相关属性
        self._show_anim_group = None  # 显示动画组
        self._hide_anim_group = None  # 隐藏动画组
        self._final_position = None   # 最终位置缓存
        self.setWindowOpacity(0)      # 初始透明度为0
        
        # 删除模式相关属性
        self.in_delete_mode = False
        self.delete_file_index = 0
        self.delete_files = []
    
    def show(self):
        """显示窗口，带打开动画效果"""
        # 如果正在播放隐藏动画，停止它
        if self._hide_anim_group:
            self._hide_anim_group.stop()
        
        # 设置初始透明度
        self.setWindowOpacity(0)
        
        # 缓存最终位置
        self._final_position = self.pos()
        initial_pos = QPoint(self._final_position.x(), self._final_position.y() - self.height())
        
        # 显示窗口但保持透明
        super().show()
        
        # 创建动画组
        self._show_anim_group = QParallelAnimationGroup()
        
        # 位置动画：从顶部滑入
        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setDuration(100)
        pos_anim.setStartValue(initial_pos)
        pos_anim.setEndValue(self._final_position)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # 透明度动画：逐渐显示
        opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        opacity_anim.setDuration(200)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # 添加动画到组
        self._show_anim_group.addAnimation(pos_anim)
        self._show_anim_group.addAnimation(opacity_anim)
        
        # 启动动画
        self._show_anim_group.start()
    
    def hide(self):
        """隐藏窗口，带关闭动画效果"""
        # 如果正在播放显示动画，停止它
        if self._show_anim_group:
            self._show_anim_group.stop()
        
        # 获取当前位置
        current_pos = self.pos()
        final_pos = QPoint(current_pos.x(), current_pos.y() - self.height())
        
        # 创建动画组
        self._hide_anim_group = QParallelAnimationGroup()
        
        # 位置动画：向顶部滑出
        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setDuration(200)
        pos_anim.setStartValue(current_pos)
        pos_anim.setEndValue(final_pos)
        pos_anim.setEasingCurve(QEasingCurve.InCubic)
        
        # 透明度动画：逐渐隐藏
        opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        opacity_anim.setDuration(200)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.InCubic)
        
        # 添加动画到组
        self._hide_anim_group.addAnimation(pos_anim)
        self._hide_anim_group.addAnimation(opacity_anim)
        
        # 动画完成后隐藏窗口
        self._hide_anim_group.finished.connect(self.close)  # 改为 close() 以触发销毁
        
        # 启动动画
        self._hide_anim_group.start()
    
    def closeEvent(self, event):
        """窗口关闭时，清理资源"""
        # 清理父窗口的引用
        if self.parent() and hasattr(self.parent(), 'floating_window') and self.parent().floating_window is self:
            self.parent().floating_window = None
        
        # 停止并清理动画
        if self._show_anim_group:
            self._show_anim_group.stop()
            self._show_anim_group.deleteLater()
            self._show_anim_group = None
        if self._hide_anim_group:
            self._hide_anim_group.stop()
            self._hide_anim_group.deleteLater()
            self._hide_anim_group = None
            
        super().closeEvent(event)
    
    def handle_gamepad_input(self, action, firstinput):
        """处理手柄输入"""
        # 优先将手柄输入转发到当前打开的文件选择对话框
        try:
            if getattr(self, 'file_dialog_manager', None) and getattr(self.file_dialog_manager, 'dialog', None) and self.file_dialog_manager.dialog.isVisible():
                self.file_dialog_manager.handle_gamepad_input(action)
                return
        except RuntimeError:
            self.file_dialog_manager = None

        if hasattr(self, 'confirm_dialog') and self.confirm_dialog and self.confirm_dialog.isVisible():
            self.confirm_dialog.handle_gamepad_input(action)
            return
        
        # 检查是否可以处理输入（方向键可绕过防抖以获得更灵敏的导航）
        is_direction = action in ('UP', 'DOWN', 'LEFT', 'RIGHT')
        if not is_direction and not self.can_process_input():
            return
        
        # 删除模式优先处理
        if self.in_delete_mode:
            self.handle_delete_mode_input(action)
            return
        
        # 字母表选择模式
        if self.in_alphabet_mode:
            # 定义字母表顺序
            alphabet_order = ['&', '#', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
            
            if action == 'UP':
                # 向上移动（减少索引）
                self.current_alphabet_index = max(0, self.current_alphabet_index - 4)  # 一行4个字母
                if self.current_alphabet_index < len(alphabet_order):
                    letter = alphabet_order[self.current_alphabet_index]
                    if letter in self.alphabet_buttons:
                        # 高亮显示当前字母
                        for btn_letter, btn in self.alphabet_buttons.items():
                            if btn_letter == letter:
                                btn.setStyleSheet(f"""
                                    QPushButton {{
                                        background-color: rgba(255, 255, 255, 0.2);
                                        color: white;
                                        font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                        min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                        min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                        border: none;
                                        border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                    }}
                                    QPushButton:hover {{
                                        background-color: rgba(255, 255, 255, 0.3);
                                    }}
                                    QPushButton:pressed {{
                                        background-color: rgba(255, 255, 255, 0.4);
                                    }}
                                """)
                            else:
                                btn.setStyleSheet(f"""
                                    QPushButton {{
                                        background-color: transparent;
                                        color: white;
                                        font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                        min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                        min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                        border: none;
                                        border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                    }}
                                    QPushButton:hover {{
                                        background-color: rgba(255, 255, 255, 0.2);
                                    }}
                                    QPushButton:pressed {{
                                        background-color: rgba(255, 255, 255, 0.3);
                                    }}
                                """)
            elif action == 'DOWN':
                # 向下移动（增加索引）
                self.current_alphabet_index = min(len(alphabet_order) - 1, self.current_alphabet_index + 4)  # 一行4个字母
                if self.current_alphabet_index < len(alphabet_order):
                    letter = alphabet_order[self.current_alphabet_index]
                    if letter in self.alphabet_buttons:
                        # 高亮显示当前字母
                        for btn_letter, btn in self.alphabet_buttons.items():
                            if btn_letter == letter:
                                btn.setStyleSheet(f"""
                                    QPushButton {{
                                        background-color: rgba(255, 255, 255, 0.2);
                                        color: white;
                                        font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                        min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                        min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                        border: none;
                                        border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                    }}
                                    QPushButton:hover {{
                                        background-color: rgba(255, 255, 255, 0.3);
                                    }}
                                    QPushButton:pressed {{
                                        background-color: rgba(255, 255, 255, 0.4);
                                    }}
                                """)
                            else:
                                btn.setStyleSheet(f"""
                                    QPushButton {{
                                        background-color: transparent;
                                        color: white;
                                        font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                        min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                        min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                        border: none;
                                        border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                    }}
                                    QPushButton:hover {{
                                        background-color: rgba(255, 255, 255, 0.2);
                                    }}
                                    QPushButton:pressed {{
                                        background-color: rgba(255, 255, 255, 0.3);
                                    }}
                                """)
            elif action == 'LEFT':
                # 向左移动（减少索引）
                if self.current_alphabet_index % 4 > 0:  # 不是行首
                    self.current_alphabet_index -= 1
                    if self.current_alphabet_index < len(alphabet_order):
                        letter = alphabet_order[self.current_alphabet_index]
                        if letter in self.alphabet_buttons:
                            # 高亮显示当前字母
                            for btn_letter, btn in self.alphabet_buttons.items():
                                if btn_letter == letter:
                                    btn.setStyleSheet(f"""
                                        QPushButton {{
                                            background-color: rgba(255, 255, 255, 0.2);
                                            color: white;
                                            font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                            min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                            min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                            border: none;
                                            border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                        }}
                                        QPushButton:hover {{
                                            background-color: rgba(255, 255, 255, 0.3);
                                        }}
                                        QPushButton:pressed {{
                                            background-color: rgba(255, 255, 255, 0.4);
                                        }}
                                    """)
                                else:
                                    btn.setStyleSheet(f"""
                                        QPushButton {{
                                            background-color: transparent;
                                            color: white;
                                            font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                            min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                            min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                            border: none;
                                            border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                        }}
                                        QPushButton:hover {{
                                            background-color: rgba(255, 255, 255, 0.2);
                                        }}
                                        QPushButton:pressed {{
                                            background-color: rgba(255, 255, 255, 0.3);
                                        }}
                                    """)
                else:
                    if firstinput:
                        # 是行首，退出字母表选择模式
                        self.in_alphabet_mode = False
                        self.update_highlight()  # 更新高亮为蓝色
                        # 恢复所有字母按钮的样式
                        for btn in self.alphabet_buttons.values():
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: transparent;
                                    color: white;
                                    font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                    min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                    min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                    border: none;
                                    border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                }}
                                QPushButton:hover {{
                                    background-color: rgba(255, 255, 255, 0.2);
                                }}
                                QPushButton:pressed {{
                                    background-color: rgba(255, 255, 255, 0.3);
                                }}
                            """)
            elif action == 'RIGHT':
                # 向右移动（增加索引）
                if (self.current_alphabet_index + 1) % 4 > 0:  # 不是行尾
                    self.current_alphabet_index = min(len(alphabet_order) - 1, self.current_alphabet_index + 1)
                    if self.current_alphabet_index < len(alphabet_order):
                        letter = alphabet_order[self.current_alphabet_index]
                        if letter in self.alphabet_buttons:
                            # 高亮显示当前字母
                            for btn_letter, btn in self.alphabet_buttons.items():
                                if btn_letter == letter:
                                    btn.setStyleSheet(f"""
                                        QPushButton {{
                                            background-color: rgba(255, 255, 255, 0.2);
                                            color: white;
                                            font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                            min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                            min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                            border: none;
                                            border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                        }}
                                        QPushButton:hover {{
                                            background-color: rgba(255, 255, 255, 0.3);
                                        }}
                                        QPushButton:pressed {{
                                            background-color: rgba(255, 255, 255, 0.4);
                                        }}
                                    """)
                                else:
                                    btn.setStyleSheet(f"""
                                        QPushButton {{
                                            background-color: transparent;
                                            color: white;
                                            font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                            min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                            min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                            border: none;
                                            border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                                        }}
                                        QPushButton:hover {{
                                            background-color: rgba(255, 255, 255, 0.2);
                                        }}
                                        QPushButton:pressed {{
                                            background-color: rgba(255, 255, 255, 0.3);
                                        }}
                                    """)
            elif action == 'A':
                # 确认选择字母
                if self.current_alphabet_index < len(alphabet_order):
                    letter = alphabet_order[self.current_alphabet_index]
                    self.jump_to_letter(letter)
                    # 退出字母表选择模式
                    self.in_alphabet_mode = False
                    self.update_highlight()  # 更新高亮为蓝色
                    # 恢复所有字母按钮的样式
                    for btn in self.alphabet_buttons.values():
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: white;
                                font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                                min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                                min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                                border: none;
                                border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 255, 255, 0.2);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 255, 255, 0.3);
                            }}
                        """)
            elif action in ('B', 'X'):
                # 退出字母表选择模式
                self.in_alphabet_mode = False
                # 恢复所有字母按钮的样式
                for btn in self.alphabet_buttons.values():
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            color: white;
                            font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                            min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                            min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                            border: none;
                            border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 0.2);
                        }}
                        QPushButton:pressed {{
                            background-color: rgba(255, 255, 255, 0.3);
                        }}
                    """)
            return
        # 正常模式
        if action == 'UP':
            if self.current_index == 0 and firstinput:
                self.hide() # 在第一个按钮按上键关闭悬浮窗
            current_tab_buttons = self.tab_buttons.get(self.current_tab_index, [])
            if current_tab_buttons:
                self.current_index = max(0, self.current_index - 1)
                self.update_highlight()
        elif action == 'DOWN':
            current_tab_buttons = self.tab_buttons.get(self.current_tab_index, [])
            if current_tab_buttons:
                self.current_index = min(
                    len(current_tab_buttons) - 1,
                    self.current_index + 1
                )
                self.update_highlight()
        elif action == 'LEFT' and firstinput:
            # 切换到上一个标签页
            if self.current_tab_index == 0:
                self.hide()  # 在第一个标签页按左键关闭悬浮窗
            new_index = max(0, self.current_tab_index - 1)
            self.tab_widget.setCurrentIndex(new_index)
        elif action == 'RIGHT' and firstinput:
            if self.current_tab_index == 2:  # 全部应用标签页
                # 进入字母表手柄选择模式
                self.in_alphabet_mode = True
                self.update_highlight()  # 更新高亮为灰色
                self.current_alphabet_index = 0  # 从第一个字母开始
                # 高亮显示第一个字母
                alphabet_order = ['&', '#', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
                if alphabet_order and alphabet_order[0] in self.alphabet_buttons:
                    self.alphabet_buttons[alphabet_order[0]].setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.2);
                            color: white;
                            font-size: {int(20 * self.parent().scale_factor * 1.4)}px;
                            min-width: {int(48 * self.parent().scale_factor * 1.4)}px;
                            min-height: {int(64 * self.parent().scale_factor * 1.4)}px;
                            border: none;
                            border-radius: {int(4 * self.parent().scale_factor * 1.4)}px;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 0.3);
                        }}
                        QPushButton:pressed {{
                            background-color: rgba(255, 255, 255, 0.4);
                        }}
                    """)
            else:
                # 切换到下一个标签页
                new_index = (self.current_tab_index + 1) % self.tab_widget.count()
                self.tab_widget.setCurrentIndex(new_index)
        elif action == 'A':
            # 获取当前标签页的按钮列表
            current_tab_buttons = self.tab_buttons.get(self.current_tab_index, [])
            if not current_tab_buttons or self.current_index >= len(current_tab_buttons):
                return
            
            # 获取当前高亮的按钮
            current_button = current_tab_buttons[self.current_index]
            
            # 检查是否是返回按钮
            button_text = current_button.text()
            if button_text.startswith("⬅️ 返回|"):
                # 点击返回按钮
                current_button.click()
            else:
                # 非返回按钮，直接模拟鼠标点击
                current_button.click()
        elif action == 'X':
            self.parent().execute_more_item()
            self.parent().mouse_simulation()
        elif action == 'B':  # B键或X键都可以关闭悬浮窗
            self.hide()
        elif action == 'Y':
            self.toggle_favorite()
        
        # 更新最后输入时间
        self.last_input_time = pygame.time.get_ticks()
        
    def can_process_input(self):
        """检查是否可以处理输入"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_input_time < self.input_delay:
            return False
        self.last_input_time = current_time
        return True
    
    def on_tab_changed(self, index):
        """标签页切换时的处理"""
        self.current_tab_index = index
        self.current_index = 0
        
        # 显示或隐藏字母排序表，并调整窗口大小
        if index == 2:  # 全部应用标签页
            self.alphabet_widget.setVisible(True)
            # 增加窗口宽度以容纳字母表
            new_width = int(600 * self.parent().scale_factor * 1.4)
            new_height = int(500 * self.parent().scale_factor * 1.4)
            self.setFixedSize(new_width, new_height)
        else:
            self.alphabet_widget.setVisible(False)
            # 恢复窗口原始宽度
            new_width = int(400 * self.parent().scale_factor * 1.4)
            new_height = int(500 * self.parent().scale_factor * 1.4)
            self.setFixedSize(new_width, new_height)
        
        # 检查标签页是否已加载，如果没有则加载
        if not self.tabs_loaded.get(index, False):
            self.load_tab_buttons(index)
            self.tabs_loaded[index] = True
        
        # 确保按钮列表已初始化
        current_tab_buttons = self.tab_buttons.get(index, [])
        print(f"切换到标签页 {index}, 按钮数量: {len(current_tab_buttons)}")
        if current_tab_buttons:
            self.update_highlight()
        else:
            print(f"警告: 标签页 {index} 没有按钮")
    
    def jump_to_letter(self, letter):
        """跳转到对应字母开头的应用"""
        if self.current_tab_index != 2:  # 只在全部应用标签页生效
            return
        
        # 获取当前标签页的按钮列表
        current_tab_buttons = self.tab_buttons.get(2, [])
        if not current_tab_buttons:
            return
        
        # 定义字母表顺序，用于向前查找
        alphabet_order = ['&', '#', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        
        # 获取当前字母在字母表中的索引
        try:
            current_letter_index = alphabet_order.index(letter)
        except ValueError:
            return
        
        # 尝试从当前字母开始，向前查找有对应按钮的字母
        for i in range(current_letter_index, -1, -1):
            search_letter = alphabet_order[i]
            
            # 遍历按钮，找到第一个以对应字母开头的应用
            for index, btn in enumerate(current_tab_buttons):
                # 跳过非QPushButton对象（如分隔线）
                if not isinstance(btn, QtWidgets.QPushButton):
                    continue
                
                # 跳过返回按钮
                if btn.text().startswith("⬅️"):
                    continue
                
                # 获取按钮文本，移除可能的前缀（如📁）
                btn_text = btn.text()
                if btn_text.startswith("📁"):
                    btn_text = btn_text[2:]  # 移除📁和空格
                
                # 检查是否以对应字母开头
                if btn_text.strip().upper().startswith(search_letter.upper()):
                    # 更新当前索引并高亮
                    self.current_index = index
                    self.update_highlight()
                    # 滚动到对应按钮
                    scroll_area = self.tab_widget.widget(2)
                    if scroll_area and hasattr(scroll_area, 'verticalScrollBar'):
                        # 计算按钮位置并滚动
                        btn_pos = btn.pos()
                        scroll_area.verticalScrollBar().setValue(btn_pos.y() - 50)
                    return
    
    def load_tab_buttons(self, tab_index):
        """加载指定标签页的按钮"""
        layout = self.tab_layouts.get(tab_index)
        if not layout:
            print(f"警告: 标签页 {tab_index} 的布局未找到")
            return
        
        # 清空布局中的所有按钮（保留添加和删除按钮）
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget != self.select_add_btn and widget != self.select_del_btn:
                    widget.setParent(None)
        
        # 移除弹性空间（如果有）
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and isinstance(item, QtWidgets.QSpacerItem):
                layout.removeItem(item)
        
        # 加载对应标签页的按钮
        if tab_index == 0:  # 工具标签页
            # 获取当前运行的所有进程
            self.current_running_apps.clear()
            for process in psutil.process_iter(['pid', 'exe']):
                try:
                    exe_path = process.info['exe']
                    if exe_path:
                        for app in more_apps:
                            if exe_path.lower() == app['path'].lower():
                                self.current_running_apps.add(app['name'])
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # 创建按钮
            self.files = self.get_files()
            sorted_files = self.sort_files()
            for file in sorted_files:
                self.create_button_for_item(file, layout, 0)
            
            # 确保添加和删除按钮在底部
            # 先移除添加和删除按钮（如果存在）
            if self.select_add_btn:
                try:
                    layout.removeWidget(self.select_add_btn)
                except Exception:
                    pass
            if self.select_del_btn:
                try:
                    layout.removeWidget(self.select_del_btn)
                except Exception:
                    pass
            
            # 然后重新添加到布局底部
            if self.select_add_btn:
                layout.addWidget(self.select_add_btn)
            if self.select_del_btn:
                layout.addWidget(self.select_del_btn)
            
            # 更新按钮列表
            self.tab_buttons[tab_index] = []
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QtWidgets.QPushButton):
                    self.tab_buttons[tab_index].append(item.widget())
        
        elif tab_index == 1:  # 桌面标签页
            desktop_files = self.get_desktop_files()
            for file in desktop_files:
                self.create_button_for_item(file, layout, 1)
            
            # 更新按钮列表
            self.tab_buttons[tab_index] = []
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QtWidgets.QPushButton):
                    self.tab_buttons[tab_index].append(item.widget())
        
        elif tab_index == 2:  # 全部应用标签页
            # 显示加载动画
            from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget
            from PyQt5.QtCore import Qt, QTimer
            from PyQt5.QtGui import QMovie
            
            # 清空当前布局
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    widget.setParent(None)
                elif item and isinstance(item, QtWidgets.QSpacerItem):
                    layout.removeItem(item)
            
            # 创建加载动画组件
            loading_widget = QWidget()
            loading_layout = QVBoxLayout(loading_widget)
            loading_layout.setAlignment(Qt.AlignCenter)
            
            # 添加加载图标
            loading_movie = QMovie(":/loading.gif")  # 假设我们有一个加载图标
            if not loading_movie.isValid():
                # 如果没有加载图标，使用文本
                loading_label = QLabel(self.tr("加载中..."))
                loading_label.setStyleSheet("color: white; font-size: 16px;")
                loading_layout.addWidget(loading_label)
            else:
                loading_label = QLabel()
                loading_label.setMovie(loading_movie)
                loading_movie.start()
                loading_layout.addWidget(loading_label)
            
            layout.addWidget(loading_widget)
            
            # 强制更新界面
            QApplication.processEvents()
            
            # 只加载顶层项目，不加载子文件夹内容
            start_menu_items = self.get_start_menu_items()
            
            # 移除加载动画
            loading_widget.setParent(None)
            
            # 创建按钮
            for i, item in enumerate(start_menu_items):
                btn = self.create_button_for_item(item, layout, 2)
            
            # 更新按钮列表
            self.tab_buttons[tab_index] = []
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QtWidgets.QPushButton):
                    self.tab_buttons[tab_index].append(item.widget())
        
        # 添加弹性空间
        layout.addStretch()
        
        # 更新高亮
        self.current_index = 0
        self.update_highlight()
    
    def get_desktop_files(self):
        """获取用户桌面和公共桌面文件列表"""
        files = []
        try:
            # 用户桌面路径
            user_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            # 公共桌面路径
            public_desktop = os.path.join(os.environ.get('PUBLIC', ''), 'Desktop')
            desktop_paths = []
            if os.path.exists(user_desktop):
                desktop_paths.append(user_desktop)
            if os.path.exists(public_desktop):
                desktop_paths.append(public_desktop)
            # 去重
            desktop_paths = list(dict.fromkeys(desktop_paths))
            for desktop_path in desktop_paths:
                all_files = os.listdir(desktop_path)
                for file in all_files:
                    file_path = os.path.join(desktop_path, file)
                    if os.path.isfile(file_path):
                        file_lower = file.lower()
                        if file_lower == "回收站" or file_lower == "recycle bin":
                            continue
                        if file_lower.endswith('.ini'):
                            continue
                        if file.startswith('~$'):
                            continue
                        files.append({
                            "name": os.path.splitext(file)[0],
                            "path": file_path,
                            "type": "desktop"
                        })
        except Exception as e:
            print(f"获取桌面文件失败: {e}")
        return files
    
    def get_start_menu_pinned_apps(self):
        """获取固定到开始菜单的应用"""
        files = []
        seen_names = set()  # 用于去重
        try:
            # 用户开始菜单固定应用路径
            start_menu_paths = [
                os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
                os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
            ]
            
            for start_menu_path in start_menu_paths:
                if os.path.exists(start_menu_path):
                    # 只获取根目录下的 .lnk 文件（固定应用通常在根目录）
                    for file in os.listdir(start_menu_path):
                        file_path = os.path.join(start_menu_path, file)
                        if os.path.isfile(file_path) and file.lower().endswith('.lnk'):
                            name = os.path.splitext(file)[0]
                            if name not in seen_names:
                                seen_names.add(name)
                                files.append({
                                    "name": name,
                                    "path": file_path,
                                    "type": "start_menu"
                                })
        except Exception as e:
            print(f"获取开始菜单固定应用失败: {e}")
        return files
    
    def get_start_menu_items(self):
        """获取开始菜单的顶层项目（文件和文件夹）"""
        items = []
        seen_names = set()  # 用于去重
        try:
            start_menu_paths = [
                os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
                os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
            ]
            
            for start_menu_path in start_menu_paths:
                if os.path.exists(start_menu_path):
                    for item in os.listdir(start_menu_path):
                        item_path = os.path.join(start_menu_path, item)
                        if os.path.isfile(item_path) and item.lower().endswith('.lnk'):
                            name = os.path.splitext(item)[0]
                            if name not in seen_names:
                                seen_names.add(name)
                                items.append({
                                    "name": name,
                                    "path": item_path,
                                    "type": "start_menu_file"
                                })
                        elif os.path.isdir(item_path):
                            name = item
                            if name not in seen_names:
                                seen_names.add(name)
                                items.append({
                                    "name": name,
                                    "path": item_path,
                                    "type": "start_menu_folder"
                                })
        except Exception as e:
            print(f"获取开始菜单项目失败: {e}")
        
        # 按名称字母顺序排序
        items.sort(key=lambda x: x['name'].lower())
        
        return items
    
    def get_folder_contents(self, folder_path):
        """获取文件夹中的内容"""
        items = []
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path) and item.lower().endswith('.lnk'):
                    items.append({
                        "name": os.path.splitext(item)[0],
                        "path": item_path,
                        "type": "start_menu_file"
                    })
                elif os.path.isdir(item_path):
                    items.append({
                        "name": item,
                        "path": item_path,
                        "type": "start_menu_folder"
                    })
        except Exception as e:
            print(f"获取文件夹内容失败: {e}")
        return items
    

    
    def get_files(self):
        """获取目录中的文件（工具标签页）"""
        files = []
        # 获取当前目录的文件
        try:
            all_files = os.listdir('./morefloder/')
            # 过滤掉文件夹，保留文件
            filess = [f for f in all_files if os.path.isfile(os.path.join('./morefloder/', f))]
            for file in filess:
                files.append({
                    "name": os.path.splitext(file)[0],
                    "path": file,
                    "type": "tool"
                })
        except Exception as e:
            print(f"获取工具文件失败: {e}")
        return files
    
    def _create_text_placeholder_icon(self, text, size_px): 
        """根据文本生成占位图标"""
        ch = text.strip()[0] if text and text.strip() else '?' 
        pix = QPixmap(QSize(size_px, size_px)) 
        pix.fill(Qt.transparent) 
        painter = QPainter(pix) 
        painter.setRenderHint(QPainter.Antialiasing) 
        # 背景圆角矩形 
        bg_color = QColor(80, 80, 80) 
        painter.setBrush(bg_color) 
        painter.setPen(Qt.NoPen) 
        radius = int(size_px * 0.2) 
        painter.drawRoundedRect(0, 0, size_px, size_px, radius, radius) 
        # 绘制文字 
        font = QFont("Microsoft YaHei", max(10, int(size_px * 0.5))) 
        painter.setFont(font) 
        painter.setPen(QColor(255, 255, 255)) 
        fm = QtGui.QFontMetrics(font) 
        w = fm.horizontalAdvance(ch) 
        h = fm.height() 
        painter.drawText((size_px - w) // 2, (size_px + h) // 2 - fm.descent(), ch) 
        painter.end() 
        return QIcon(pix)
    
    def _get_icon_for_file(self, file_path, size=24):
        """获取文件图标（通用方法）"""
        import os
        try:
            abs_path = os.path.abspath(file_path) if not os.path.isabs(file_path) else file_path
            # 如果是快捷方式，解析目标
            if abs_path.lower().endswith('.lnk'):
                try:
                    shell = win32com.client.Dispatch('WScript.Shell')
                    shortcut = shell.CreateShortCut(abs_path)
                    target = shortcut.Targetpath
                    if target and os.path.exists(target):
                        abs_path = target
                except Exception:
                    pass
            # 处理url文件，其图标路径可能明文写在文件中
            elif abs_path.lower().endswith('.url'):
                try:
                    with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    # 查找IconFile或IconIndex行
                    import re
                    icon_file_match = re.search(r'IconFile=(.*)', content)
                    if icon_file_match:
                        icon_path = icon_file_match.group(1).strip()
                        # 处理可能的环境变量
                        if icon_path.startswith('%') and '%' in icon_path[1:]:
                            try:
                                import os
                                icon_path = os.path.expandvars(icon_path)
                            except Exception:
                                pass
                        # 处理相对路径
                        if not os.path.isabs(icon_path):
                            icon_path = os.path.join(os.path.dirname(abs_path), icon_path)
                        # 尝试加载图标
                        if os.path.exists(icon_path):
                            try:
                                pix = QPixmap(icon_path)
                                if not pix.isNull():
                                    pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                    return QIcon(pix)
                            except Exception:
                                pass
                except Exception:
                    pass
            # 如果目标存在且可能为可执行文件，尝试用 icoextract 提取
            if os.path.exists(abs_path):
                try:
                    from icoextract import IconExtractor
                    extractor = IconExtractor(abs_path)
                    bio = extractor.get_icon(num=0)
                    data = bio.getvalue()
                    pix = QPixmap()
                    if pix.loadFromData(data):
                        pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        return QIcon(pix)
                except Exception:
                    pass
                # 回退：尝试作为图片加载（例如 .ico/.png/.jpg）
                try:
                    pix = QPixmap(abs_path)
                    if not pix.isNull():
                        pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        return QIcon(pix)
                except Exception:
                    pass
        except Exception:
            pass
        
        # 生成占位图标
        file_name = os.path.basename(file_path)
        return self._create_text_placeholder_icon(file_name, size)
    
    def truncate_text(self, text, max_length=37):
        """截断文本，超过长度显示省略号"""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
    
    def create_button_for_item(self, item, layout, tab_index):
        """为项目创建按钮（通用方法）"""
        file_path = item.get("path", "")
        if item.get("type") == "tool":
            # 工具标签页的文件路径是相对路径
            file_path = os.path.join('./morefloder/', file_path)
        
        # 截断文本，避免按钮拉伸
        truncated_name = self.truncate_text(item["name"])
        
        # 为文件夹添加特殊标记
        if item.get("type") == "start_menu_folder":
            btn = QPushButton(f"📁 {truncated_name}")
        else:
            btn = QPushButton(truncated_name)
            # 只有非文件夹才获取图标
            icon = self._get_icon_for_file(file_path, size=int(24 * self.parent().scale_factor * 1.4))
            if not icon.isNull():
                btn.setIcon(icon)
                try:
                    btn.setIconSize(QSize(int(24 * self.parent().scale_factor * 1.4), int(24 * self.parent().scale_factor * 1.4)))
                except Exception:
                    pass
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: white;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
                max-width: {int(350 * self.parent().scale_factor * 1.4)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        
        # 检查是否在运行中（仅工具标签页）
        if item.get("type") == "tool":
            truncated_name = self.truncate_text(item["name"])
            if item["name"] in settings.get("more_favorites", []):
                btn.setText(f"⭐ {truncated_name}")
            if item["name"] in self.current_running_apps:
                btn.setText(f"🟢 {truncated_name}")
            if item["name"] in settings.get("more_favorites", []) and item["name"] in self.current_running_apps:
                btn.setText(f"⭐🟢 {truncated_name}")
        
        # 为文件夹添加特殊的点击事件处理
        if item.get("type") == "start_menu_folder":
            btn.clicked.connect(lambda checked, f=item: self.handle_folder_click(f))
        else:
            btn.clicked.connect(lambda checked, f=item: self.parent().execute_more_item(f))
        layout.addWidget(btn)
        
        # 确保按钮可见
        btn.setVisible(True)
        btn.show()
        
        if tab_index not in self.tab_buttons:
            self.tab_buttons[tab_index] = []
        self.tab_buttons[tab_index].append(btn)
        self.buttons.append(btn)
        return btn
    
    def handle_folder_click(self, folder_item):
        """处理文件夹点击事件"""
        folder_path = folder_item.get("path", "")
        if not folder_path:
            return
        
        # 获取文件夹内容
        folder_contents = self.get_folder_contents(folder_path)
        print(f"加载文件夹 {folder_item['name']} 的内容，找到 {len(folder_contents)} 个项目")
        
        # 获取当前标签页的布局
        layout = self.tab_layouts.get(2)  # 全部应用标签页的索引是2
        if not layout:
            return
        
        # 清空布局中的所有按钮
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget.setParent(None)
                if widget in self.buttons:
                    self.buttons.remove(widget)
        
        # 移除弹性空间（如果有）
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and isinstance(item, QtWidgets.QSpacerItem):
                layout.removeItem(item)
        
        # 添加返回按钮
        back_btn = QPushButton(f"⬅️ 返回|📁 {folder_item['name']}")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: white;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
                max-width: {int(350 * self.parent().scale_factor * 1.4)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        back_btn.clicked.connect(lambda: self.load_tab_buttons(2))
        layout.addWidget(back_btn)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { color: #444444; }")
        layout.addWidget(separator)

        # 添加文件夹内容
        for i, item in enumerate(folder_contents):
            self.create_button_for_item(item, layout, 2)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 更新按钮列表
        self.tab_buttons[2] = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QtWidgets.QPushButton):
                self.tab_buttons[2].append(item.widget())
        
        # 更新高亮
        self.current_index = 0
        self.update_highlight()
    
    def create_tool_tab(self):
        """创建工具标签页"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        
        tool_widget = QWidget()
        tool_layout = QVBoxLayout(tool_widget)
        tool_layout.setSpacing(int(5 * self.parent().scale_factor * 1.4))
        tool_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加添加和删除按钮
        self.select_add_btn = QPushButton(self.tr("➕ 添加项目"))
        self.select_add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """)
        self.select_add_btn.clicked.connect(self.select_add)
        tool_layout.addWidget(self.select_add_btn)
        
        self.select_del_btn = QPushButton(self.tr("❌ 删除项目"))
        self.select_del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """)
        self.select_del_btn.clicked.connect(self.select_del)
        tool_layout.addWidget(self.select_del_btn)
        
        # 添加弹性空间
        tool_layout.addStretch()
        
        scroll_area.setWidget(tool_widget)
        self.tab_widget.addTab(scroll_area, self.tr("工具"))
        
        # 存储标签页的widget和layout，用于后续加载按钮
        self.tab_widgets[0] = tool_widget
        self.tab_layouts[0] = tool_layout
        self.tabs_loaded[0] = False
    
    def create_desktop_tab(self):
        """创建桌面标签页"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        
        desktop_widget = QWidget()
        desktop_layout = QVBoxLayout(desktop_widget)
        desktop_layout.setSpacing(int(5 * self.parent().scale_factor * 1.4))
        desktop_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加弹性空间
        desktop_layout.addStretch()
        
        scroll_area.setWidget(desktop_widget)
        self.tab_widget.addTab(scroll_area, self.tr("桌面"))
        
        # 存储标签页的widget和layout，用于后续加载按钮
        self.tab_widgets[1] = desktop_widget
        self.tab_layouts[1] = desktop_layout
        self.tabs_loaded[1] = False
    
    def create_all_apps_tab(self):
        """创建全部应用标签页（开始菜单所有应用）"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        
        all_apps_widget = QWidget()
        all_apps_layout = QVBoxLayout(all_apps_widget)
        all_apps_layout.setSpacing(int(5 * self.parent().scale_factor * 1.4))
        all_apps_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加弹性空间
        all_apps_layout.addStretch()
        
        scroll_area.setWidget(all_apps_widget)
        self.tab_widget.addTab(scroll_area, self.tr("全部应用"))
        
        # 存储标签页的widget和layout，用于后续加载按钮
        self.tab_widgets[2] = all_apps_widget
        self.tab_layouts[2] = all_apps_layout
        self.tabs_loaded[2] = False
    
    #create_buttons()可刷新按钮
    def create_buttons(self, settitype=True): 
        """创建按钮（仅用于工具标签页）"""
        # 直接调用load_tab_buttons方法来加载工具标签页的按钮
        self.load_tab_buttons(0)
        
        # 标记工具标签页为已加载
        self.tabs_loaded[0] = True

    def select_add(self):
        """直接打开文件选择器添加"""
        # 先隐藏悬浮窗口，避免弹窗被当前 Popup 窗口遮挡或失去焦点
        self.hide()
        dialog_parent = self.parent() if self.parent() is not None else self
        self.file_dialog_manager = FileDialogManager(dialog_parent, scale_factor=self.parent().scale_factor * 1.4)
        # 将 file_dialog_manager 同时保存到 MainWindow，防止 FloatingWindow
        # 因 Qt.Popup 失焦自动关闭导致 closeEvent 将 floating_window 置为 None
        if dialog_parent is not None:
            dialog_parent.file_dialog_manager = self.file_dialog_manager
        # 将信号连接到 GameSelector，确保 FloatingWindow 关闭后仍能处理
        game_selector = self.parent()
        if game_selector is not None:
            self.file_dialog_manager.file_selected.connect(game_selector._on_floating_add_file_selected)
            self.file_dialog_manager.dialog_closed.connect(game_selector._on_floating_add_file_dialog_closed)
        self.file_dialog_manager.show_dialog()
    
    def select_del(self):
        """进入删除模式（在原窗口中实现手柄支持）"""
        self.in_delete_mode = True
        self.delete_file_index = 0
        # 使用与按钮创建相同的排序逻辑
        self.files = self.get_files()
        self.delete_files = self.sort_files()
        self.last_input_time = pygame.time.get_ticks()
        self.update_highlight()

    def exit_delete_mode(self):
        """退出删除模式"""
        self.in_delete_mode = False
        self.delete_file_index = 0
        self.delete_files = []
        self.current_index = 0
        self.update_highlight()
    
    def delete_file_at_index(self, index):
        """删除指定索引的文件"""
        if 0 <= index < len(self.delete_files):
            file = self.delete_files[index]
            file_path = os.path.join('./morefloder/', file["path"])
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"已删除: {file['name']}")
                    
                    # 重新加载文件列表和按钮
                    load_morefloder_shortcuts()
                    if 0 in self.tab_buttons:
                        for btn in self.tab_buttons[0]:
                            if btn != self.select_add_btn and btn != self.select_del_btn:
                                btn.setParent(None)
                                if btn in self.buttons:
                                    self.buttons.remove(btn)
                        self.tab_buttons[0] = []
                    self.create_buttons()
            except Exception as e:
                print(f"删除文件出错: {e}")
    
    def handle_delete_mode_input(self, action):
        """处理删除模式下的手柄输入"""
        if not self.in_delete_mode or not self.delete_files:
            return
        
        if action in ('UP', 'FIRST-UP'):
            self.delete_file_index = max(0, self.delete_file_index - 1)
            self.update_highlight()
        elif action in ('DOWN', 'FIRST-DOWN'):
            self.delete_file_index = min(len(self.delete_files) - 1, self.delete_file_index + 1)
            self.update_highlight()
        elif action == 'A':
            # 确认删除
            self.delete_file_at_index(self.delete_file_index)
            self.delete_files = self.get_files()
            if self.delete_files:
                self.delete_file_index = min(self.delete_file_index, len(self.delete_files) - 1)
                self.update_highlight()
            else:
                self.exit_delete_mode()
                self.update_highlight()
        elif action == 'B':
            # 取消删除
            self.exit_delete_mode()
            self.update_highlight()

    def sort_files(self):
        """排序文件"""
        sorted_files = []
        
        # 获取收藏和最近使用的列表
        favorites = settings.get("more_favorites", [])
        last_used = settings.get("more_last_used", [])
        
        # 添加收藏的文件
        for name in favorites:
            for file in self.files:
                if file["name"] == name:
                    sorted_files.append(file)
                    break
        
        # 添加最近使用的文件
        for name in last_used:
            for file in self.files:
                if file["name"] == name and file["name"] not in favorites:
                    sorted_files.append(file)
                    break
        
        # 添加其他文件
        for file in self.files:
            if file["name"] not in favorites and file["name"] not in last_used:
                sorted_files.append(file)
        
        return sorted_files
    
    def update_highlight(self):
        """更新高亮状态"""
        # 获取当前标签页的按钮列表
        current_tab_buttons = self.tab_buttons.get(self.current_tab_index, [])
        if not current_tab_buttons:
            return
        
        # 确保索引在有效范围内
        if self.current_index >= len(current_tab_buttons):
            self.current_index = 0
        elif self.current_index < 0:
            self.current_index = len(current_tab_buttons) - 1
        
        # 根据是否处于字母表模式选择边框颜色
        border_color = "#808080" if self.in_alphabet_mode else "#93ffff"
        
        # 删除模式下使用红色边框
        if self.in_delete_mode:
            border_color = "#ff0000"
            # 在删除模式下，应该显示delete_files的高亮
            for i, file in enumerate(self.delete_files):
                # 从tab_buttons中找到对应的按钮（考虑前缀⭐🟢）
                for j, btn in enumerate(current_tab_buttons):
                    if hasattr(btn, 'text'):
                        btn_text = btn.text()
                        # 去除可能的前缀后匹配
                        clean_text = btn_text.replace("⭐ ", "").replace("🟢 ", "").replace("⭐🟢 ", "")
                        if clean_text == file['name'] or btn_text.startswith(file['name']):
                            if i == self.delete_file_index:
                                btn.setStyleSheet(f"""
                                    QPushButton {{
                                        background-color: transparent;
                                        color: white;
                                        text-align: left;
                                        padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                                        border: {int(2 * self.parent().scale_factor * 1.4)}px solid {border_color};
                                        font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
                                    }}
                                """)
                            else:
                                btn.setStyleSheet(f"""
                                    QPushButton {{
                                        background-color: transparent;
                                        color: white;
                                        text-align: left;
                                        padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                                        border: none;
                                        font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
                                    }}
                                    QPushButton:hover {{
                                        background-color: rgba(255, 255, 255, 0.1);
                                    }}
                                """)
                            break
            return
        
        for i, button in enumerate(current_tab_buttons):
            if i == self.current_index:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                        border: {int(2 * self.parent().scale_factor * 1.4)}px solid {border_color};
                        font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: {int(10 * self.parent().scale_factor * 1.4)}px;
                        border: none;
                        font-size: {int(16 * self.parent().scale_factor * 1.4)}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.1);
                    }}
                """)
        
        # 调整滚动位置，确保当前高亮的按钮在窗口可见范围内
        if current_tab_buttons and self.current_index < len(current_tab_buttons):
            current_button = current_tab_buttons[self.current_index]
            # 获取当前标签页的滚动区域
            if 0 <= self.current_tab_index < self.tab_widget.count():
                tab_widget = self.tab_widget.widget(self.current_tab_index)
                if tab_widget and hasattr(tab_widget, 'verticalScrollBar'):
                    scroll_bar = tab_widget.verticalScrollBar()
                    if scroll_bar:
                        # 获取按钮的几何信息
                        button_geometry = current_button.geometry()
                        # 计算按钮的绝对位置
                        button_global_pos = current_button.mapToGlobal(button_geometry.topLeft())
                        tab_global_pos = tab_widget.mapToGlobal(tab_widget.rect().topLeft())
                        button_pos_in_tab = button_global_pos - tab_global_pos
                        
                        # 获取滚动区域的可见高度
                        # viewport_height = tab_widget.viewport().height()
                        viewport_height = 800 * self.parent().scale_factor * 1.4
                        
                        # 计算按钮的顶部和底部位置
                        button_top = button_pos_in_tab.y()
                        button_bottom = button_pos_in_tab.y() + button_geometry.height()
                        
                        # 计算当前滚动位置
                        current_scroll = scroll_bar.value()
                        
                        # 调整滚动位置，确保按钮在可见范围内
                        if button_top < current_scroll:
                            # 按钮在可见区域上方，向上滚动
                            scroll_bar.setValue(button_top)
                        elif button_bottom > current_scroll + viewport_height:
                            # 按钮在可见区域下方，向下滚动
                            scroll_bar.setValue(button_bottom - viewport_height)
    
    def toggle_favorite(self):
        """切换收藏状态"""
        # 根据当前标签页获取文件列表
        if self.current_tab_index == 0:  # 工具标签页
            sorted_files = self.sort_files()
        elif self.current_tab_index == 1:  # 桌面标签页
            sorted_files = self.get_desktop_files()
        elif self.current_tab_index == 2:  # 全部应用标签页
            sorted_files = self.get_start_menu_items()
        else:
            return
        
        if self.current_index >= len(sorted_files):
            return
        
        current_file = sorted_files[self.current_index]
        # 只有工具标签页才支持收藏和运行状态检查
        if current_file.get("type") != "tool":
            return
        
        if current_file["name"] in self.current_running_apps:
            # 创建确认弹窗
            if not self.parent().is_mouse_simulation_running == True:
                self.confirm_dialog = ConfirmDialog(self.tr("是否关闭下列程序？\n%1").replace('%1', current_file['name']), scale_factor=self.parent().scale_factor * 1.4)
                result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
                self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
            else:
                result = False
            # 关闭窗口
            self.current_index = 0
            self.update_highlight()
            self.hide()
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            # 修正：用 more_apps 查找真实路径
            exe_path = None
            for app in more_apps:
                if app["name"] == current_file["name"]:
                    exe_path = app["path"]
                    break
            if exe_path:
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        if proc.info['exe'] and os.path.abspath(proc.info['exe']) == os.path.abspath(exe_path):
                            print(f"找到进程: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.terminate()  # 结束进程
                            proc.wait()  # 等待进程完全终止
                            return
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
            return
        else:
            if "more_favorites" not in settings:
                settings["more_favorites"] = []

            if current_file["name"] in settings["more_favorites"]:
                settings["more_favorites"].remove(current_file["name"])
            else:
                settings["more_favorites"].append(current_file["name"])

            # 保存设置
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            
        # 重新加载按钮（仅工具标签页）
        tool_widget = self.tab_widget.widget(0)
        if tool_widget:
            tool_layout = tool_widget.layout()
            if tool_layout:
                # 清除工具标签页的按钮
                if 0 in self.tab_buttons:
                    for btn in self.tab_buttons[0]:
                        if btn != self.select_add_btn and btn != self.select_del_btn:
                            btn.setParent(None)
                            if btn in self.buttons:
                                self.buttons.remove(btn)
                    self.tab_buttons[0] = []
        self.create_buttons()
        self.update_highlight()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        current_tab_buttons = self.tab_buttons.get(self.current_tab_index, [])
        if not current_tab_buttons:
            return
        
        if event.key() == Qt.Key_Up:
            self.current_index = (self.current_index - 1) % len(current_tab_buttons)
            self.update_highlight()
        elif event.key() == Qt.Key_Down:
            self.current_index = (self.current_index + 1) % len(current_tab_buttons)
            self.update_highlight()
        elif event.key() == Qt.Key_Left:
            # 切换到上一个标签页
            self.current_tab_index = (self.current_tab_index - 1) % self.tab_widget.count()
            self.tab_widget.setCurrentIndex(self.current_tab_index)
            self.current_index = 0
            self.update_highlight()
        elif event.key() == Qt.Key_Right:
            # 切换到下一个标签页
            self.current_tab_index = (self.current_tab_index + 1) % self.tab_widget.count()
            self.tab_widget.setCurrentIndex(self.current_tab_index)
            self.current_index = 0
            self.update_highlight()

class ControllerMapping:
    """手柄按键映射类"""
    #https://www.pygame.org/docs/ref/joystick.html
    def __init__(self, controller):
        self.controller = controller
        self.controller_name = controller.get_name()
        self.setup_mapping()
        
    def setup_mapping(self):
        """根据手柄类型设置按键映射"""
        # 默认映射（用于未识别的手柄）
        self.button_a = 0
        self.button_b = 1
        self.button_x = 2
        self.button_y = 3
        
        # 摇杆映射
        self.left_stick_x = 0   # 左摇杆左右
        self.left_stick_y = 1   # 左摇杆上下
        self.right_stick_x = 2  # 右摇杆左右
        self.right_stick_y = 3  # 右摇杆上下
        
        # 扳机键映射（如果需要）
        self.left_trigger = 2   # 左扳机
        self.right_trigger = 5  # 右扳机
        
        # 其他按钮映射（如果需要）
        self.left_bumper = 4    # 左肩键
        self.right_bumper = 5   # 右肩键
        self.back = 6           # Back 键
        self.start = 7          # Start 键
        self.left_stick_in = 8  # 左摇杆按下
        self.right_stick_in = 9 # 右摇杆按下
        self.guide = 10         # Guide 键
            
        # D-pad 使用 hat
        self.has_hat = True
        self.controller_type = "unknown"  # 添加控制器类型标识
        
        # Xbox 360 Controller
        if "Xbox 360 Controller" in self.controller_name:
            self.controller_type = "xbox360"
            # 按钮映射
            self.button_a = 0
            self.button_b = 1
            self.button_x = 2
            self.button_y = 3
            
            # 摇杆映射
            self.left_stick_x = 0   # 左摇杆左右
            self.left_stick_y = 1   # 左摇杆上下
            self.right_stick_x = 2  # 右摇杆左右
            self.right_stick_y = 3  # 右摇杆上下
            
            # 扳机键映射（如果需要）
            self.left_trigger = 2   # 左扳机
            self.right_trigger = 5  # 右扳机
            
            # 其他按钮映射（如果需要）
            self.left_bumper = 4    # 左肩键
            self.right_bumper = 5   # 右肩键
            self.back = 6           # Back 键
            self.start = 7          # Start 键
            self.left_stick_in = 8  # 左摇杆按下
            self.right_stick_in = 9 # 右摇杆按下
            self.guide = 10         # Guide 键
            
            # D-pad 使用 hat
            self.has_hat = True
        
        # PS4 Controller
        elif "PS4 Controller" in self.controller_name:
            self.controller_type = "ps4"
            self.button_a = 0  # Cross
            self.button_b = 1  # Circle
            self.button_x = 2  # Square
            self.button_y = 3  # Triangle
            self.left_bumper = 9    # 左肩键
            self.right_bumper = 10   # 右肩键
            self.dpad_up = 11
            self.dpad_down = 12
            self.dpad_left = 13
            self.dpad_right = 14
            self.left_stick_x = 0
            self.left_stick_y = 1
            self.right_stick_x = 2
            self.right_stick_y = 3
            self.guide = 5         # PS 键
            self.back = 4
            self.start = 6
            self.left_stick_in = 7  # 左摇杆按下
            self.right_stick_in = 8 # 右摇杆按下
            self.has_hat = False  # PS4手柄的D-pad不使用hat，而是作为按钮输入

            
        # PS5 Controller
        elif "Sony Interactive Entertainment Wireless Controller" in self.controller_name:
            self.button_a = 0  # Cross
            self.button_b = 1  # Circle
            self.button_x = 2  # Square
            self.button_y = 3  # Triangle
            self.has_hat = True
            self.left_stick_x = 0
            self.left_stick_y = 1
            self.right_stick_x = 3
            self.right_stick_y = 4
            self.guide = 10         # PS 键
            
        # Nintendo Switch Joy-Con (Left)
        elif "Wireless Gamepad" in self.controller_name and self.controller.get_numbuttons() == 11:
            self.dpad_up = 0
            self.dpad_down = 1
            self.dpad_left = 2
            self.dpad_right = 3
            self.left_stick_x = 0
            self.left_stick_y = 1
            
        # Nintendo Switch Joy-Con (Right)
        elif "Wireless Gamepad" in self.controller_name:
            self.button_a = 0
            self.button_b = 1
            self.button_x = 2
            self.button_y = 3
            self.right_stick_x = 0
            self.right_stick_y = 1
            self.guide = 12
            
        #print(f"Detected controller: {self.controller_name}")

class SettingsWindow(QWidget):
    """
    仿 Nintendo Switch 设置界面风格的设置窗口。
    左侧为类别列表，右侧为当前类别的详细设置。
    当前仅实现“主机”页，其它类别为占位。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # 设置为子窗口，附着于主窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup )
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #1e1e1e;
            }}
        """)

        scale = parent.scale_factor
        # 设置与主窗口相同的大小
        self.setFixedSize(parent.width(),(parent.height() - int(80 * scale)))  # 高度略小于主窗口，留出顶部空间
        # 定位到主窗口的位置
        self.move(parent.x(), parent.y())

        self.focused_index = 0
        self.focusable_widgets = []
        self.is_control_selected = False  # 标记是否选中了控件
        self.current_area = 'right'  # 当前焦点区域：'left'（左侧类别栏）或 'right'（右侧按钮区域）

        # 整体水平布局：左侧类别列表 + 右侧内容
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(
            int(40 * scale), int(25 * scale), int(40 * scale), int(25 * scale)
        )
        main_layout.setSpacing(int(30 * scale))

        # 左侧：类别列表区域（模仿 Switch 左边栏）
        left_container = QWidget()
        left_container.setFixedWidth(int(520 * scale))  # 左侧宽度设置为现在的2倍
        left_container.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 6px;
            }
        """)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(int(10 * scale), int(10 * scale), int(10 * scale), int(10 * scale))
        left_layout.setSpacing(int(4 * scale))

        # 顶部“设置”标题行（带齿轮图标）
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(int(8 * scale))
        
        # 齿轮图标
        gear_icon = QLabel()
        gear_icon.setText("⚙")
        gear_icon.setStyleSheet(f"font-size: {int(32 * scale)}px; color: #ffffff;")
        gear_icon.setFixedSize(int(48 * scale), int(48 * scale))
        title_layout.addWidget(gear_icon)
        
        # 设置标题
        title_label = QLabel(self.tr("设置"))
        title_label.setStyleSheet(f"color: #ffffff; font-size: {int(44 * scale)}px;")
        title_layout.addWidget(title_label)
        
        title_widget = QWidget()
        title_widget.setLayout(title_layout)
        title_widget.setFixedHeight(int(80 * scale))
        left_layout.addWidget(title_widget)

        # 类别按钮（这里只实现“主机”，其余是占位）
        self.category_buttons = []

        def add_category(text, key, selected=False):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setChecked(selected)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding-left: {int(16 * scale)}px;
                    padding-top: {int(24 * scale)}px;
                    padding-bottom: {int(24 * scale)}px;
                    border-radius: {int(4 * scale)}px;
                    border: {int(2 * scale)}px solid transparent;
                    color: #ffffff;
                    font-size: {int(24 * scale)}px;
                    background-color: transparent;
                }}
                QPushButton:hover {{
                    background-color: #3d3d3d;
                }}
                QPushButton:checked {{
                    border: {int(2 * scale)}px solid #00bfff;
                    background-color: #1e3a5f;
                }}
            """)
            btn.clicked.connect(lambda _=None, k=key: self.switch_category(k))
            left_layout.addWidget(btn)
            self.category_buttons.append((key, btn))

        add_category(self.tr("主机"), "console", True)
        add_category(self.tr("主页功能"), "home_feature")
        add_category(self.tr("游玩时长"), "play_time")
        add_category(self.tr("关于"), "about")
        add_category(self.tr("开发者选项"), "developer")

        left_layout.addStretch()

        # 右侧：内容区域（StackedWidget）
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(int(10 * scale))

        # 右上角当前类别标题
        self.current_title = QLabel(self.tr("主机"))
        self.current_title.setStyleSheet(f"color: #ffffff; font-size: {int(22 * scale)}px;")
        self.current_title.setFixedHeight(int(80 * scale))
        right_layout.addWidget(self.current_title)

        # 标题下方的细线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #444444;")
        line.setFixedHeight(int(1 * scale))
        right_layout.addWidget(line)

        self.pages = QStackedWidget()
        right_layout.addWidget(self.pages)

        # 创建各个页面
        self.console_page = self._create_console_page(scale)
        self.home_feature_page = self._create_home_feature_page(scale)
        self.background_selection_page = self._create_background_selection_page(scale)
        self.placeholder_page = self._create_placeholder_page(scale)
        self.play_time_page = self._create_play_time_page(scale)
        self.about_page = self._create_about_page(scale)
        self.developer_page = self._create_developer_page(scale)

        self.pages.addWidget(self.console_page)     # index 0 - 主机
        self.pages.addWidget(self.home_feature_page) # index 1 - 主页功能
        self.pages.addWidget(self.background_selection_page) # index 2 - 自定义背景图
        self.pages.addWidget(self.placeholder_page) # index 3 - 其它
        self.pages.addWidget(self.play_time_page)   # index 4 - 游玩时长
        self.pages.addWidget(self.about_page)       # index 5 - 关于
        self.pages.addWidget(self.developer_page)   # index 6 - 开发者选项

        main_layout.addWidget(left_container)
        main_layout.addWidget(right_container, 1)

        # 默认选中主机
        self.switch_category("console")

    # -------------------- 页面构建 --------------------
    def _create_console_page(self, scale: float) -> QWidget:
        """主机设置页：将原先所有设置项整理到此处"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(8 * scale))

        # 分割线
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet("color: #444444;")
        layout.addWidget(line1)

        # 行：重启程序
        self.restart_button = QPushButton(self.tr("重启程序"))
        self.restart_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #00bfff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #1e3a5f;
            }}
        """)
        self.restart_button.clicked.connect(self.restart_program)
        layout.addWidget(self.restart_button)

        # 行：管理（刷新游戏）
        self.refresh_button = QPushButton(self.tr("添加新游戏/管理游戏"))
        self.refresh_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #00bfff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #1e3a5f;
            }}
        """)
        self.refresh_button.clicked.connect(self.addandrefresh)
        layout.addWidget(self.refresh_button)

        # 说明文字
        info_label = QLabel(self.tr("该软件和Sunshine共享游戏库，若未安装Sunshine游戏库信息会保存在软件同级位置"))
        info_label.setStyleSheet(f"color: #aaaaaa; font-size: {int(18 * scale)}px;")
        layout.addWidget(info_label)

        # 分割线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("color: #444444;")
        layout.addWidget(line2)

        # 行：沉浸模式
        self.killexplorer_button = QPushButton(
            self.tr("沉浸模式  %1").replace('%1', '开' if settings.get('killexplorer', False) else '关')
        )
        self.killexplorer_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.killexplorer_button.clicked.connect(self.toggle_killexplorer)
        layout.addWidget(self.killexplorer_button)

        hint1 = QLabel(self.tr("开启后会隐藏桌面图标和任务栏，若出现问题关闭此功能后重启即可"))
        hint1.setWordWrap(True)
        hint1.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint1)

        # 行：回主页时尝试冻结游戏
        self.freeze_button = QPushButton(
            self.tr("回主页时尝试冻结游戏  %1").replace('%1', '开' if settings.get('freeze', False) else '关')
        )
        self.freeze_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.freeze_button.clicked.connect(self.toggle_freeze)
        layout.addWidget(self.freeze_button)

        hint2 = QLabel(self.tr("开启后按手柄主页键或快捷键时会尝试冻结全屏游戏进程，部分游戏无法冻结"))
        hint2.setWordWrap(True)
        hint2.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint2)

        self.show_battery_button = QPushButton(
            self.tr("时间栏显示电量  %1").replace('%1', '开' if settings.get('show_battery', False) else '关')
        )
        self.show_battery_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.show_battery_button.clicked.connect(self.toggle_show_battery)
        layout.addWidget(self.show_battery_button)

        hint1 = QLabel(self.tr("开启后时间栏会显示电量，充电时显示充电图标"))
        hint1.setWordWrap(True)
        hint1.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint1)

        # 行：开机自启
        self.open_folder_button = QPushButton(self.tr("开启/关闭开机自启"))
        self.open_folder_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.open_folder_button.clicked.connect(self.is_startup_enabled)
        layout.addWidget(self.open_folder_button)

        # 说明文字
        info_label = QLabel(self.tr("程序使用任务计划实现开机自启"))
        info_label.setStyleSheet(f"color: #aaaaaa; font-size: {int(18 * scale)}px;")
        layout.addWidget(info_label)
        # 分割线
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setStyleSheet("color: #444444;")
        layout.addWidget(line3)

        # 行：主页快捷键（可点击的按钮）
        self.hotkey_row_button = QPushButton()
        hotkey_layout = QHBoxLayout(self.hotkey_row_button)
        hotkey_layout.setContentsMargins(0, 0, 0, 0)
        hotkey_layout.setSpacing(int(12 * scale))

        hotkey_title = QLabel(self.tr("打开主页面快捷键"))
        hotkey_title.setStyleSheet(f"color: #ffffff; font-size: {int(28 * scale)}px;")
        hotkey_layout.addWidget(hotkey_title)
        hotkey_layout.addStretch()

        self.home_page_hotkey = settings.get("home_page_hotkey", None)
        hotkey_text = self.home_page_hotkey if self.home_page_hotkey else self.tr("未设置")
        self.hotkey_label = QLabel(hotkey_text)
        self.hotkey_label.setStyleSheet(f"color: #00bfff; font-size: {int(28 * scale)}px;")
        hotkey_layout.addWidget(self.hotkey_label)

        self.hotkey_row_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.hotkey_row_button.clicked.connect(self.set_home_page_hotkey)
        layout.addWidget(self.hotkey_row_button)

        # 分割线
        line4 = QFrame()
        line4.setFrameShape(QFrame.HLine)
        line4.setStyleSheet("color: #444444;")
        layout.addWidget(line4)

        # 行：语言设置
        self.language_row_button = QPushButton()
        language_layout = QHBoxLayout(self.language_row_button)
        language_layout.setContentsMargins(0, 0, 0, 0)
        language_layout.setSpacing(int(12 * scale))

        language_title = QLabel(self.tr("语言"))
        language_title.setStyleSheet(f"color: #ffffff; font-size: {int(28 * scale)}px;")
        language_layout.addWidget(language_title)
        language_layout.addStretch()

        self.language_label = QLabel("中文" if language == "zh_CN" else "English")
        self.language_label.setStyleSheet(f"color: #00bfff; font-size: {int(28 * scale)}px;")
        language_layout.addWidget(self.language_label)

        self.language_row_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.language_row_button.clicked.connect(self.set_language)
        layout.addWidget(self.language_row_button)

        # 分割线
        line5 = QFrame()
        line5.setFrameShape(QFrame.HLine)
        line5.setStyleSheet("color: #444444;")
        layout.addWidget(line5)

        # 行：关闭程序（红色）
        self.close_program_button = QPushButton(self.tr("关闭程序"))
        self.close_program_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #ff4b4b;
                color: white;
                text-align: center;
                padding: {int(16 * scale)}px 0;
                border-radius: {int(4 * scale)}px;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #ff6666;
            }}
        """)
        self.close_program_button.clicked.connect(self.close_program)
        layout.addWidget(self.close_program_button)

        layout.addStretch()

        # 定义可聚焦控件列表
        self.focusable_widgets_console = [
            self.restart_button,
            self.refresh_button,
            self.killexplorer_button,
            self.freeze_button,
            self.show_battery_button,
            self.open_folder_button,
            self.hotkey_row_button,
            self.language_row_button,
            self.close_program_button
        ]

        return page

    def _create_home_feature_page(self, scale: float) -> QWidget:
        """主页功能设置页：主页游戏数量和每行游戏数量"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(8 * scale))

        # 自定义背景图按钮
        self.custom_background_button = QPushButton(self.tr("自定义背景图片"))
        self.custom_background_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.custom_background_button.clicked.connect(self.open_background_selector)
        layout.addWidget(self.custom_background_button)

        hint = QLabel(self.tr("自定义背景图片可以设置主页面的背景图片。"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #444444;")
        layout.addWidget(line)
        
        hint0 = QLabel(self.tr("以下选项可调整部分操作习惯，在某些场景下可能会比较有用，可根据自己的使用习惯调整。"))
        hint0.setWordWrap(True)
        hint0.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint0)

        # 行：最小化时保留主窗口在任务栏
        self.keep_taskbar_button = QPushButton(
            self.tr("最小化时保留主窗口在任务栏 %1").replace('%1', '√' if settings.get('keep_on_taskbar_when_minimized', False) else '×')
        )
        self.keep_taskbar_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.keep_taskbar_button.clicked.connect(self.toggle_keep_on_taskbar)
        layout.addWidget(self.keep_taskbar_button)

        hint1 = QLabel(self.tr("开启后最小化主窗口时会保留在任务栏，这在xbox全屏模式下相当于不会自动关闭窗口。"))
        hint1.setWordWrap(True)
        hint1.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint1)

        # 行：开启游戏/切换窗口时不执行最小化
        self.no_minimize_on_open_button = QPushButton(
            self.tr("开启游戏/切换窗口时不执行最小化 %1").replace('%1', '√' if settings.get('skip_minimize_on_game_open', False) else '×')
        )
        self.no_minimize_on_open_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.no_minimize_on_open_button.clicked.connect(self.toggle_no_minimize_on_open)
        layout.addWidget(self.no_minimize_on_open_button)

        hint2 = QLabel(self.tr("开启后在打开游戏或切换窗口时不会自动最小化主窗口。"))
        hint2.setWordWrap(True)
        hint2.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint2)

        # 行：全屏应用按键切换回前端时不最小化应用
        self.no_minimize_on_fullscreen_switch_button = QPushButton(
            self.tr("全屏应用按键切换回前端时不最小化应用 %1").replace('%1', '√' if settings.get('skip_minimize_on_fullscreen_switch_front', False) else '×')
        )
        self.no_minimize_on_fullscreen_switch_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.no_minimize_on_fullscreen_switch_button.clicked.connect(self.toggle_no_minimize_on_fullscreen_switch)
        layout.addWidget(self.no_minimize_on_fullscreen_switch_button)

        hint3 = QLabel(self.tr("开启后在全屏应用中使用手柄主页键或键盘快捷键切换回前端时不会自动最小化该全屏应用。"))
        hint3.setWordWrap(True)
        hint3.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint3)

        # 行：主页面底部再次下移可打开快速设置
        self.open_quick_settings_button = QPushButton(
            self.tr("主页面底部再次下移可打开快速设置 %1").replace('%1', '√' if settings.get('open_quick_settings_on_bottom_down', False) else '×')
        )
        self.open_quick_settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.open_quick_settings_button.clicked.connect(self.toggle_open_quick_settings)
        layout.addWidget(self.open_quick_settings_button)

        hint4 = QLabel(self.tr("开启后在主页面底部再次下移时会打开Windows快速设置（win+a菜单），在Xbox全屏模式下也是可用的。"))
        hint4.setWordWrap(True)
        hint4.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint4)

        # 分割线
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet("color: #444444;")
        layout.addWidget(line1)

        hint5 = QLabel(self.tr("以下调整可改变主页容器显示数量"))
        hint5.setWordWrap(True)
        hint5.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint5)

        # 一行：主页游戏数量
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(int(12 * scale))

        label1 = QLabel(self.tr("主页游戏数量"))
        label1.setStyleSheet(f"color: #ffffff; font-size: {int(28 * scale)}px;")
        row1_layout.addWidget(label1)
        row1_layout.addStretch()

        self.buttonsindexset_label = QLabel(f"{self.parent_window.buttonsindexset}")
        self.buttonsindexset_label.setStyleSheet(f"color: #00bfff; font-size: {int(28 * scale)}px;")
        row1_layout.addWidget(self.buttonsindexset_label)

        layout.addWidget(row1)

        self.buttonsindexset_slider = QSlider(Qt.Horizontal)
        self.buttonsindexset_slider.setMinimum(4)
        self.buttonsindexset_slider.setMaximum(12)
        self.buttonsindexset_slider.setValue(self.parent_window.buttonsindexset)
        self.buttonsindexset_slider.valueChanged.connect(self.update_buttonsindexset)
        self.buttonsindexset_slider.setFixedHeight(int(24 * scale))
        layout.addWidget(self.buttonsindexset_slider)
        # 一行：每行游戏数量
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(int(12 * scale))

        label2 = QLabel(self.tr("每行游戏数量（所有处）"))
        label2.setStyleSheet(f"color: #ffffff; font-size: {int(28 * scale)}px;")
        row2_layout.addWidget(label2)
        row2_layout.addStretch()

        self.row_count_label = QLabel(f"{self.parent_window.row_count}")
        self.row_count_label.setStyleSheet(f"color: #00bfff; font-size: {int(28 * scale)}px;")
        row2_layout.addWidget(self.row_count_label)

        layout.addWidget(row2)

        self.row_count_slider = QSlider(Qt.Horizontal)
        self.row_count_slider.setMinimum(4)
        self.row_count_slider.setMaximum(10)
        self.row_count_slider.setValue(self.parent_window.row_count)
        self.row_count_slider.valueChanged.connect(self.update_row_count)
        self.row_count_slider.setFixedHeight(int(24 * scale))
        layout.addWidget(self.row_count_slider)

        layout.addStretch()

        # 定义可聚焦控件列表
        self.focusable_widgets_home_feature = [
            self.custom_background_button,
            self.keep_taskbar_button,
            self.no_minimize_on_open_button,
            self.no_minimize_on_fullscreen_switch_button,
            self.open_quick_settings_button,
            self.buttonsindexset_slider,
            self.row_count_slider
        ]

        return page

    def _create_background_selection_page(self, scale: float) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(10 * scale))

        title_label = QLabel(self.tr("选择背景图来源"))
        title_label.setStyleSheet(f"color: #ffffff; font-size: {int(32 * scale)}px;")
        layout.addWidget(title_label)

        hint_label = QLabel(self.tr("请选择一个来源，将背景图保存为 ./screenshot/background.png ，并立即应用到主页。"))
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet(f"color: #aaaaaa; font-size: {int(18 * scale)}px;")
        layout.addWidget(hint_label)

        self.local_wallpaper_button = QPushButton(self.tr("本机电脑壁纸"))
        self.local_wallpaper_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.local_wallpaper_button.clicked.connect(self.apply_desktop_wallpaper_background)
        layout.addWidget(self.local_wallpaper_button)

        self.random_landscape_button = QPushButton(self.tr("随机摄影风景（Lorem Picsum）"))
        self.random_landscape_button.setStyleSheet(self.local_wallpaper_button.styleSheet())
        self.random_landscape_button.clicked.connect(self.apply_random_landscape_background)
        layout.addWidget(self.random_landscape_button)

        self.random_anime_button = QPushButton(self.tr("随机二次元壁纸（Pipw）"))
        self.random_anime_button.setStyleSheet(self.local_wallpaper_button.styleSheet())
        self.random_anime_button.clicked.connect(self.apply_random_anime_background)
        layout.addWidget(self.random_anime_button)

        self.choose_local_file_button = QPushButton(self.tr("从本地选择图片"))
        self.choose_local_file_button.setStyleSheet(self.local_wallpaper_button.styleSheet())
        self.choose_local_file_button.clicked.connect(self.choose_local_background_file)
        layout.addWidget(self.choose_local_file_button)

        # 新增：清除背景按钮
        self.clear_background_button = QPushButton(self.tr("清除自定义背景"))
        self.clear_background_button.setStyleSheet(self.local_wallpaper_button.styleSheet())
        self.clear_background_button.clicked.connect(self._clear_background)
        layout.addWidget(self.clear_background_button)

        self.background_selector_back_button = QPushButton(self.tr("返回主页功能"))
        self.background_selector_back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(16 * scale)}px 0;
                border-radius: {int(8 * scale)}px;
                border: none;
                font-size: {int(28 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #5a5a5a;
            }}
        """)
        self.background_selector_back_button.clicked.connect(self.return_to_home_feature)
        layout.addWidget(self.background_selector_back_button)

        layout.addStretch()

        self.focusable_widgets_background_selector = [
            self.local_wallpaper_button,
            self.random_landscape_button,
            self.random_anime_button,
            self.choose_local_file_button,
            self.clear_background_button,
            self.background_selector_back_button,
        ]

        return page

    def open_background_selector(self):
        # 保持主页功能分类仍被高亮，但显示自定义背景页面
        for k, btn in self.category_buttons:
            btn.setChecked(k == "home_feature")
        self.current_title.setText(self.tr("自定义背景图"))
        self.pages.setCurrentWidget(self.background_selection_page)
        self.focusable_widgets = getattr(self, 'focusable_widgets_background_selector', [])
        self.focused_index = 0
        if self.focusable_widgets:
            self.focusable_widgets[0].setFocus()

    def return_to_home_feature(self):
        self.switch_category("home_feature")

    def _save_background_from_path(self, source_path: str):
        try:
            if not os.path.exists(source_path):
                self.hide()
                self.confirm_dialog = ConfirmDialog(self.tr("背景设置失败：未找到指定图片文件。"), scale_factor=self.parent_window.scale_factor)
                self.confirm_dialog.exec_()
                return
            target_dir = os.path.join(".", "screenshot")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "background.png")
            shutil.copy(source_path, target_path)
            if hasattr(self.parent(), 'load_background_image'):
                self.parent().load_background_image()
            self.hide()
            self.confirm_dialog = ConfirmDialog(self.tr("背景设置成功：已将背景图保存为 ./screenshot/background.png。"), scale_factor=self.parent_window.scale_factor)
            self.confirm_dialog.exec_()
        except Exception as e:
            self.hide()
            self.confirm_dialog = ConfirmDialog(self.tr("背景设置失败：保存背景图片时发生错误：%1").replace('%1', str(e)), scale_factor=self.parent_window.scale_factor)
            self.confirm_dialog.exec_()

    def _download_background_image(self, url: str, headers=None):
        try:
            request = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read()
            target_dir = os.path.join(".", "screenshot")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "background.png")
            with open(target_path, "wb") as f:
                f.write(data)
            if hasattr(self.parent(), 'load_background_image'):
                self.parent().load_background_image()
            self.hide()
            self.confirm_dialog = ConfirmDialog(self.tr("背景设置成功：已下载并保存背景图到 ./screenshot/background.png。"), scale_factor=self.parent_window.scale_factor)
            self.confirm_dialog.exec_()
        except Exception as e:
            self.hide()
            self.confirm_dialog = ConfirmDialog(self.tr("背景下载失败：下载背景图失败：%1").replace('%1', str(e)), scale_factor=self.parent_window.scale_factor)
            self.confirm_dialog.exec_()

    def _clear_background(self):
        """移除已保存的自定义背景并刷新主页背景显示。"""
        try:
            target_path = os.path.join('.', 'screenshot', 'background.png')
            if os.path.exists(target_path):
                os.remove(target_path)
                if hasattr(self.parent(), 'load_background_image'):
                    self.parent().load_background_image()
                self.hide()
                self.confirm_dialog = ConfirmDialog(self.tr("已清除背景：已移除 ./screenshot/background.png"), scale_factor=self.parent_window.scale_factor)
                self.confirm_dialog.exec_()
            else:
                self.hide()
                self.confirm_dialog = ConfirmDialog(self.tr("未找到自定义背景文件，未做任何更改。"), scale_factor=self.parent_window.scale_factor)
                self.confirm_dialog.exec_()
        except Exception as e:
            self.hide()
            self.confirm_dialog = ConfirmDialog(self.tr("清除背景失败：%1").replace('%1', str(e)), scale_factor=self.parent_window.scale_factor)
            self.confirm_dialog.exec_()

    def apply_desktop_wallpaper_background(self):
        wallpaper_path = self._get_desktop_wallpaper_path()
        if wallpaper_path:
            self._save_background_from_path(wallpaper_path)
        else:
            self.hide()
            self.confirm_dialog = ConfirmDialog(self.tr("背景设置失败：未能获取当前桌面壁纸路径。"), scale_factor=self.parent_window.scale_factor)
            self.confirm_dialog.exec_()

    def apply_random_landscape_background(self):
        self._download_background_image("https://picsum.photos/1920/1080")

    def apply_random_anime_background(self):
        self._download_background_image("https://img-api.pipw.top")

    def choose_local_background_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle(self.tr("选择本地背景图片"))
        file_dialog.setNameFilter(self.tr("图像文件 (*.png *.jpg *.jpeg *.bmp *.gif)"))
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            selected = file_dialog.selectedFiles()
            if selected:
                self._save_background_from_path(selected[0])

    def _get_desktop_wallpaper_path(self):
        try:
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.user32.SystemParametersInfoW(0x0073, 260, buf, 0)
            return buf.value if buf.value and os.path.exists(buf.value) else None
        except Exception:
            return None

    def _create_placeholder_page(self, scale: float) -> QWidget:
        """暂未实现的类别占位页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(10 * scale))

        label = QLabel(self.tr("此类别暂未提供可配置项目。"))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: #777777; font-size: {int(18 * scale)}px;")
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()
        return page

    def _create_play_time_page(self, scale: float) -> QWidget:
        """游玩时长汇总页（支持滚动和触摸滑动）"""

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 触摸惯性滚动
        QScroller.grabGesture(
            scroll.viewport(),
            QScroller.LeftMouseButtonGesture
        )

        # 内容容器
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            int(10 * scale),
            int(10 * scale),
            int(10 * scale),
            int(10 * scale)
        )
        layout.setSpacing(int(15 * scale))

        # 获取并排序游戏时长
        play_time_dict = settings.get("play_time", {})
        sorted_games = sorted(
            play_time_dict.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # 总时长
        total_minutes = sum(play_time for _, play_time in sorted_games)

        if total_minutes < 60:
            total_time_str = self.tr("总游戏时长：%1 分钟").replace('%1', str(total_minutes))
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            total_time_str = self.tr("总游戏时长：%1 小时 %2 分钟").replace('%1', str(hours)).replace('%2', str(minutes))

        total_label = QLabel(total_time_str)
        total_label.setStyleSheet(
            f"color:#FFD700;font-size:{int(15*scale)}px;"
            "font-weight:bold;border:none;"
        )
        layout.addWidget(total_label)

        if not sorted_games:
            label = QLabel(self.tr("暂无游戏时长数据"))
            label.setStyleSheet(
                "color:white;font-size:18px;border:none;"
            )
            layout.addWidget(label)

        else:
            max_time = max(sorted_games[0][1], 1)

            for idx, (game, play_time) in enumerate(sorted_games):

                # 每个游戏一个固定高度容器
                item_widget = QWidget()
                item_widget.setFixedHeight(int(60 * scale))

                item_layout = QVBoxLayout(item_widget)
                item_layout.setContentsMargins(0, 0, 0, 0)
                item_layout.setSpacing(int(4 * scale))

                # 游戏名
                name_label = QLabel(game)
                name_label.setStyleSheet(
                    f"color:white;"
                    f"font-size:{int(18*scale)}px;"
                    "font-weight:bold;border:none;"
                )
                item_layout.addWidget(name_label)

                # 时长
                if play_time < 60:
                    play_time_str = self.tr("游玩时间：%1 分钟").replace('%1', str(play_time))
                else:
                    hours = play_time // 60
                    minutes = play_time % 60
                    play_time_str = (
                        self.tr("游玩时间：%1 小时 %2 分钟").replace('%1', str(hours)).replace('%2', str(minutes))
                    )

                time_label = QLabel(play_time_str)
                time_label.setStyleSheet(
                    f"color:white;"
                    f"font-size:{int(16*scale)}px;"
                    "border:none;"
                )
                item_layout.addWidget(time_label)

                # 进度条
                progress = int(play_time / max_time * 100)

                progress_bar = QProgressBar()
                progress_bar.setMaximum(100)
                progress_bar.setValue(progress)
                progress_bar.setTextVisible(False)

                if progress >= 90:
                    bar_color = "#FE8601"
                elif progress >= 80:
                    bar_color = "#A62ECD"
                elif progress >= 40:
                    bar_color = "#3F84DF"
                else:
                    bar_color = "#9DC464"

                progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border:{int(1*scale)}px solid #444444;
                        border-radius:{int(5*scale)}px;
                        background:#2e2e2e;
                        height:{int(4*scale)}px;
                    }}
                    QProgressBar::chunk {{
                        background-color:{bar_color};
                    }}
                """)

                item_layout.addWidget(progress_bar)

                layout.addWidget(item_widget)

                if idx < len(sorted_games) - 1:
                    line = QFrame()
                    line.setFrameShape(QFrame.HLine)
                    line.setStyleSheet("""
                        background:#444;
                        min-height:1px;
                        max-height:1px;
                        border:none;
                    """)
                    layout.addWidget(line)

        layout.addStretch()

        # 放入滚动区域
        scroll.setWidget(content)

        self.focusable_widgets_play_time = []

        return scroll

    def _create_about_page(self, scale: float) -> QWidget:
        """关于页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(int(18 * scale))
        layout.setContentsMargins(
            int(30 * scale),
            int(30 * scale),
            int(30 * scale),
            int(30 * scale)
        )
    
        # 顶部图标和标题
        icon_title_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_pix = QPixmap("./_internal/fav.ico").scaled(int(36 * scale), int(36 * scale), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(icon_pix)
        icon_label.setFixedSize(int(36 * scale), int(36 * scale))
        icon_title_layout.addWidget(icon_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        title_label = QLabel("Simplenite")  # 软件名称，无需翻译
        title_label.setStyleSheet(f"color: white; font-size: {int(26 * scale)}px; font-weight: bold;")
        icon_title_layout.addWidget(title_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        icon_title_layout.addStretch()
        layout.addLayout(icon_title_layout)
    
        # 软件简介
        intro = QLabel("[一个追求简洁而全面的游戏启动器，让你的游戏库井井有条，打开即玩。]\n\n"
                       "本启动器的核心功能是手柄模拟鼠标，主页按X或长按start+back可打开鼠标映射，\n"
                       "按下LS/RS来取消手柄模拟，灵活运用该功能可实现手柄对电脑的全局掌控。\n"
                       "程序使用手柄主页键呼出主页面，推荐关闭Xbox,Steam等程序的手柄按键呼出实现最佳体验\n"
                       "主页面肩键可以调节系统音量，两肩键一起按住可以静音。主页面上移摇杆可以打开工具菜单\n"
                       "程序不断改进中，欢迎加入QQ群反馈建议和问题，或在GitHub提交issue。\n"
                       "\n"
                       "手柄鼠标映射键位操作示意图：")
        intro.setStyleSheet(f"color: white; font-size: {int(18 * scale)}px;")
        intro.setWordWrap(True)
        layout.addWidget(intro)
    
        # 手柄映射示意图
        #'<a href="https://wwse.lanzn.com/b00uz4bjmd" style="color:#93ffff;">蓝奏（密码:85jl）</a>　|　'
        title_label = QLabel(
            '<a href="https://qm.qq.com/q/pSHQTlnbJQ" style="color:#93ffff;">QQ群</a>　|　'
            '<a href="https://github.com/gmaox/DeskGamix" style="color:#93ffff;">GitHub</a>　|　'
            '<a href="https://space.bilibili.com/258889407" style="color:#93ffff;">B站主页</a>'
        )
        title_label.setStyleSheet(f"color: white; font-size: {int(26 * scale)}px; ")
        title_label.setOpenExternalLinks(True)
        icon_title_layout.addWidget(title_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        img_label = QLabel()
        try:
            pixmap = QPixmap("./_internal/1.png").scaled(
                int(1150 * scale),
                int(660 * scale),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            img_label.setPixmap(pixmap)
        except Exception:
            img_label.setText(self.tr("未找到1.png"))
        img_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(img_label)
    
        layout.addStretch()

        self.focusable_widgets_about = []

        return page

    def _create_developer_page(self, scale: float) -> QWidget:
        """开发者选项页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(10 * scale), int(20 * scale), int(10 * scale), int(20 * scale))
        layout.setSpacing(int(12 * scale))

        self.peer_launch_button = QPushButton(
            self.tr("使用同级权限启动应用而非桌面权限  %1").replace('%1', '开' if settings.get('use_peer_level_launch', False) else '关')
        )
        self.peer_launch_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(26 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.peer_launch_button.clicked.connect(self.toggle_peer_launch_mode)
        layout.addWidget(self.peer_launch_button)

        hint1 = QLabel(self.tr("该选项可解决部分环境下启动游戏库管理工具/应用游戏时启动对应应用失败问题，但会导致启动的应用附带管理员权限"))
        hint1.setWordWrap(True)
        hint1.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint1)

        self.debug_window_button = QPushButton(
            self.tr("启用调试输出窗口  %1").replace('%1', '开' if settings.get('debug_output_window', False) else '关')
        )
        self.debug_window_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(26 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
            }}
        """)
        self.debug_window_button.clicked.connect(self.toggle_debug_output_window)
        layout.addWidget(self.debug_window_button)

        hint = QLabel(self.tr("该选项用于开启调试输出窗口。"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint)

        self.manage_ignored_apps_button = QPushButton(self.tr("管理忽略的应用"))
        self.manage_ignored_apps_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: white;
                text-align: left;
                padding: {int(16 * scale)}px 0;
                border: none;
                font-size: {int(26 * scale)}px;
            }}
            QPushButton:hover {{
                background-color: #1e3a5f;
            }}
        """)
        self.manage_ignored_apps_button.clicked.connect(self.show_manage_ignored_apps_dialog)
        layout.addWidget(self.manage_ignored_apps_button)

        hint_ignore = QLabel(self.tr("打开单独窗口管理忽略的应用名称，会影响游戏库过滤结果。"))
        hint_ignore.setWordWrap(True)
        hint_ignore.setStyleSheet(f"color: #aaaaaa; font-size: {int(16 * scale)}px;")
        layout.addWidget(hint_ignore)

        layout.addStretch()

        self.focusable_widgets_developer = [
            self.peer_launch_button,
            self.debug_window_button,
            self.manage_ignored_apps_button,
        ]
        return page
    def switch_category(self, key: str):
        """切换左侧类别"""
        for k, btn in self.category_buttons:
            btn.setChecked(k == key)

        if key == "console":
            self.current_title.setText(self.tr("主机"))
            self.pages.setCurrentIndex(0)
        elif key == "home_feature":
            self.current_title.setText(self.tr("主页功能"))
            self.pages.setCurrentIndex(1)
        elif key == "background_selector":
            self.current_title.setText(self.tr("自定义背景图"))
            self.pages.setCurrentIndex(2)
        elif key == "play_time":
            self.current_title.setText(self.tr("游玩时长"))
            self.pages.setCurrentIndex(4)
        elif key == "about":
            self.current_title.setText(self.tr("关于"))
            self.pages.setCurrentIndex(5)
        elif key == "developer":
            self.current_title.setText(self.tr("开发者选项"))
            self.pages.setCurrentIndex(6)
        else:
            # 其它类别暂时复用同一个占位页
            btn = next((b for k2, b in self.category_buttons if k2 == key), None)
            self.current_title.setText(btn.text() if btn else self.tr("设置"))
            self.pages.setCurrentIndex(3)

        # 设置可聚焦控件
        self.focusable_widgets = getattr(self, f'focusable_widgets_{key}', [])
        self.focused_index = 0
        if self.focusable_widgets:
            self.focusable_widgets[0].setFocus()
        # 更新焦点的视觉反馈
        self.update_focus_visual()

    #def show_del_custom_valid_apps_dialog(self):
    #    """显示删除自定义valid_apps条目的窗口"""
    #    self.del_dialog = QDialog(self)
    #    self.del_dialog.setWindowTitle("删除自定义游戏进程")
    #    self.del_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
    #    self.del_dialog.setStyleSheet(f"""
    #        QDialog {{
    #            background-color: rgba(46, 46, 46, 0.95);
    #            border-radius: {int(15 * self.parent().scale_factor)}px;
    #            border: {int(2 * self.parent().scale_factor)}px solid #444444;
    #        }}
    #    """)
    #    layout = QVBoxLayout(self.del_dialog)
    #    layout.setSpacing(int(15 * self.parent().scale_factor))
    #    layout.setContentsMargins(
    #        int(20 * self.parent().scale_factor),
    #        int(20 * self.parent().scale_factor),
    #        int(20 * self.parent().scale_factor),
    #        int(20 * self.parent().scale_factor)
    #    )
    #
    #    # 添加"+添加自定义进程"按钮
    #    add_btn = QPushButton("+添加自定义进程")
    #    add_btn.setStyleSheet(f"""
    #        QPushButton {{
    #            background-color: #008CBA;
    #            color: white;
    #            border-radius: {int(8 * self.parent().scale_factor)}px;
    #            font-size: {int(16 * self.parent().scale_factor)}px;
    #            padding: {int(10 * self.parent().scale_factor)}px;
    #        }}
    #        QPushButton:hover {{
    #            background-color: #007B9E;
    #        }}
    #    """)
    #    add_btn.clicked.connect(lambda: [self.del_dialog.accept(), self.show_custom_valid_apps_dialog()])
    #    layout.addWidget(add_btn)
    #
    #    # 获取自定义条目列表
    #    custom_list = settings.get("custom_valid_apps", [])
    #    if not custom_list:
    #        label = QLabel("暂无自定义条目")
    #        label.setStyleSheet("color: white; font-size: 16px;")
    #        layout.addWidget(label)
    #    else:
    #        for idx, item in enumerate(custom_list):
    #            btn = QPushButton(f"{item['name']} ({item['path']})")
    #            btn.setStyleSheet(f"""
    #                QPushButton {{
    #                    background-color: #444444;
    #                    color: white;
    #                    text-align: left;
    #                    padding: {int(10 * self.parent().scale_factor)}px;
    #                    border: none;
    #                    font-size: {int(16 * self.parent().scale_factor)}px;
    #                }}
    #                QPushButton:hover {{
    #                    background-color: #3f3f3f;
    #                    color: white;
    #                }}
    #            """)
    #            def handle_del(i=idx, b=btn, current_item=item):
    #                # 第一次点击变红
    #                if not hasattr(b, "_clicked_once"):
    #                    b.setStyleSheet(f"""
    #                        QPushButton {{
    #                            background-color: #ff4444;
    #                            color: yellow;
    #                            text-align: left;
    #                            padding: {int(10 * self.parent().scale_factor)}px;
    #                            border: none;
    #                            font-size: {int(16 * self.parent().scale_factor)}px;
    #                        }}
    #                    """)
    #                    b.setText("确认删除？(再次点击)")
    #                    b._clicked_once = True
    #                else:
    #                    # 第二次点击删除
    #                    del settings["custom_valid_apps"][i]
    #                    # 从 valid_apps 中删除对应项（用 name 和 path 匹配）
    #                    valid_apps[:] = [app for app in valid_apps if not (app["name"] == current_item["name"] and app["path"] == current_item["path"])]
    #                    with open(settings_path, "w", encoding="utf-8") as f:
    #                        json.dump(settings, f, indent=4)
    #                    self.del_dialog.accept()
    #            btn.clicked.connect(handle_del)
    #            layout.addWidget(btn)
    #    self.del_dialog.setLayout(layout)
    #    x = 350 * self.parent().scale_factor
    #    y = 100 * self.parent().scale_factor
    #    self.del_dialog.move(x, y)
    #    self.del_dialog.show()



    def set_home_page_hotkey(self):
        """设置打开主页面的快捷键"""
        # 创建快捷键设置对话框
        hotkey_dialog = QDialog(self)
        hotkey_dialog.setWindowTitle(self.tr("设置打开主页面快捷键"))
        hotkey_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        hotkey_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(10 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        hotkey_dialog.setFixedSize(int(500 * self.parent().scale_factor), int(200 * self.parent().scale_factor))
        layout = QVBoxLayout(hotkey_dialog)
        layout.setSpacing(int(20 * self.parent().scale_factor))
        layout.setContentsMargins(
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor)
        )

        # 添加提示标签
        hint_label = QLabel(self.tr("请按下要设置的快捷键（任意键）"))
        hint_label.setStyleSheet(f"color: white; font-size: {int(18 * self.parent().scale_factor)}px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)

        # 添加显示当前按键的标签
        key_label = QLabel(self.tr("等待按键..."))
        key_label.setStyleSheet(f"color: #93ffff; font-size: {int(24 * self.parent().scale_factor)}px; font-weight: bold;")
        key_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(key_label)

        # 用于存储用户按下的键
        selected_key = None

        # 重写keyPressEvent方法，捕获用户按下的键
        def keyPressEvent(event):
            nonlocal selected_key
            key = event.key()
            # 检查是否有修饰键（Ctrl, Alt, Shift, Win）
            modifiers = []
            if event.modifiers() & Qt.ControlModifier:
                modifiers.append("Ctrl")
            if event.modifiers() & Qt.AltModifier:
                modifiers.append("Alt")
            if event.modifiers() & Qt.ShiftModifier:
                modifiers.append("Shift")
            if event.modifiers() & Qt.MetaModifier:
                modifiers.append("Win")
            
            # 获取主按键
            # 过滤掉修饰键作为主按键的情况
            if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
                # 如果只有修饰键被按下，不设置主按键
                return
            
            # 直接使用键码转换为字符
            if key >= Qt.Key_Space and key <= Qt.Key_AsciiTilde:
                # 对于可打印字符，直接转换
                main_key = chr(key)
            elif key >= Qt.Key_F1 and key <= Qt.Key_F12:
                main_key = f"F{key - Qt.Key_F1 + 1}"
            else:
                # 对于其他特殊键，使用键名
                # 键码到键名的映射
                key_name_map = {
                    Qt.Key_Escape: "Escape",
                    Qt.Key_Tab: "Tab",
                    Qt.Key_Backspace: "Backspace",
                    Qt.Key_Return: "Enter",
                    Qt.Key_Enter: "Enter",
                    Qt.Key_Space: "Space",
                    Qt.Key_Up: "Up",
                    Qt.Key_Down: "Down",
                    Qt.Key_Left: "Left",
                    Qt.Key_Right: "Right",
                    Qt.Key_Home: "Home",
                    Qt.Key_End: "End",
                    Qt.Key_PageUp: "PageUp",
                    Qt.Key_PageDown: "PageDown",
                    Qt.Key_Insert: "Insert",
                    Qt.Key_Delete: "Delete",
                    Qt.Key_CapsLock: "CapsLock",
                    Qt.Key_NumLock: "NumLock",
                    Qt.Key_ScrollLock: "ScrollLock",
                    Qt.Key_Pause: "Pause",
                }
                if key in key_name_map:
                    main_key = key_name_map[key]
                else:
                    # 对于无法获取文本的键，使用键码
                    main_key = f"Key_{key}"
            
            # 组合键格式：Mod1+Mod2+Key
            if modifiers:
                selected_key = "+".join(modifiers + [main_key])
            else:
                selected_key = main_key
            
            key_label.setText(self.tr("已选择: '%1'").replace('%1', selected_key))

        hotkey_dialog.keyPressEvent = keyPressEvent

        # 添加确认和取消按钮
        button_layout = QHBoxLayout()
        confirm_button = QPushButton(self.tr("确认"))
        confirm_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #2E7D9B;
                color: white;
                text-align: center;
                padding: {int(10 * self.parent().scale_factor)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor)}px;
                border-radius: {int(5 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
        """)

        cancel_button = QPushButton(self.tr("取消"))
        cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #f44336;
                color: white;
                text-align: center;
                padding: {int(10 * self.parent().scale_factor)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor)}px;
                border-radius: {int(5 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #da190b;
            }}
        """)

        def confirm():
            nonlocal selected_key
            if selected_key:
                # 保存快捷键设置
                settings["home_page_hotkey"] = selected_key
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                # 更新标签显示
                self.hotkey_label.setText(self.tr("打开主页面快捷键: %1").replace('%1', selected_key))
                # 更新QShortcut设置
                self.parent().update_shortcut()
                hotkey_dialog.accept()

        confirm_button.clicked.connect(confirm)
        cancel_button.clicked.connect(hotkey_dialog.reject)

        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # 居中显示对话框
        parent_geom = self.parent().geometry()
        x = parent_geom.x() + (parent_geom.width() - hotkey_dialog.width()) // 2
        y = parent_geom.y() + (parent_geom.height() - hotkey_dialog.height()) // 2
        hotkey_dialog.move(x, y)

        # 显示对话框并获取结果
        hotkey_dialog.exec_()

    def set_language(self):
        """设置语言"""
        global language
        lang_dialog = QDialog(self)
        lang_dialog.setWindowTitle(self.tr("选择语言"))
        lang_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        lang_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(10 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        lang_dialog.setFixedSize(int(500 * self.parent().scale_factor), int(250 * self.parent().scale_factor))
        layout = QVBoxLayout(lang_dialog)
        layout.setSpacing(int(20 * self.parent().scale_factor))
        layout.setContentsMargins(
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor)
        )

        hint_label = QLabel(self.tr("请选择界面语言"))
        hint_label.setStyleSheet(f"color: white; font-size: {int(18 * self.parent().scale_factor)}px;")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)

        # 语言选项
        btn_layout = QHBoxLayout()
        zh_btn = QPushButton("中文")
        en_btn = QPushButton("English")

        for btn in (zh_btn, en_btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2E7D9B;
                    color: white;
                    text-align: center;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                    border-radius: {int(5 * self.parent().scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: #45a049;
                }}
            """)

        def select_zh():
            self.language_label.setText("中文")
            self.parent().switch_language("zh_CN")
            lang_dialog.accept()

        def select_en():
            self.language_label.setText("English")
            self.parent().switch_language("en_US")
            lang_dialog.accept()

        zh_btn.clicked.connect(select_zh)
        en_btn.clicked.connect(select_en)
        btn_layout.addWidget(zh_btn)
        btn_layout.addWidget(en_btn)
        layout.addLayout(btn_layout)

        # 取消按钮
        cancel_btn = QPushButton(self.tr("取消"))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #f44336;
                color: white;
                text-align: center;
                padding: {int(10 * self.parent().scale_factor)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor)}px;
                border-radius: {int(5 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #da190b;
            }}
        """)
        cancel_btn.clicked.connect(lang_dialog.reject)
        layout.addWidget(cancel_btn)

        # 居中显示
        parent_geom = self.parent().geometry()
        x = parent_geom.x() + (parent_geom.width() - lang_dialog.width()) // 2
        y = parent_geom.y() + (parent_geom.height() - lang_dialog.height()) // 2
        lang_dialog.move(x, y)
        lang_dialog.exec_()

    def addandrefresh(self):
        """添加并刷新主页游戏"""
        self.hide()
        self.parent_window.hide_window()
        self.parent_window.addandrefresh_games()
    # 检查程序是否设置为开机自启
    def is_startup_enabled(self):
        self.hide()
        command = ['schtasks', '/query', '/tn', "DesktopGameStartup"]
        try:
            # 如果任务存在，将返回0
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return self.set_startup_enabled(enable=False)
        except subprocess.CalledProcessError:
            return self.set_startup_enabled(enable=True)
    
    # 设置程序开机自启
    def set_startup_enabled(self, enable):
        tn = "DesktopGameStartup"
        if enable:
            # 弹窗询问是否开机唤出主页面
            self.confirm_dialog = ConfirmDialog(self.tr("开机启动时是否打开主页面？\n（选择'取消'使用后台静默启动）"), scale_factor=self.parent_window.scale_factor)
            result = self.confirm_dialog.exec_()
            if result == QDialog.Accepted:
                args = ""  # 唤出主页面
            else:
                args = "startup"  # 不唤出主页面
            app_path = sys.executable
            import tempfile, datetime, getpass
            # 构建任务的 XML（确保电源相关设置为 false）
            xml = f'''<?xml version="1.0" encoding="utf-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{datetime.datetime.now().isoformat()}</Date>
    <Author>{getpass.getuser()}</Author>
    <Description>Simplenite auto start on logon</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{app_path}"</Command>
      <Arguments>{args}</Arguments>
    </Exec>
  </Actions>
</Task>'''
            # 在 Windows 上确保写入并关闭临时文件后再调用 schtasks
            fd, path = tempfile.mkstemp(suffix=".xml")
            try:
                with os.fdopen(fd, "w", encoding="utf-16") as f:
                    f.write(xml)
                # 使用文本模式捕获输出，便于诊断失败原因
                res = subprocess.run(['schtasks', '/create', '/tn', tn, '/xml', path, '/f'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    # 抛出包含 stderr 的异常，便于上层或日志查看
                    raise subprocess.CalledProcessError(res.returncode, res.args, output=res.stdout, stderr=res.stderr)
            finally:
                try:
                    os.remove(path)
                except Exception:
                    pass
        else:
            try:
                subprocess.run(['schtasks', '/delete', '/tn', tn, '/f'], check=True)
                # 添加取消开机自启成功弹窗
                self.confirm_dialog = ConfirmDialog(self.tr("已取消开机自启"), scale_factor=self.parent_window.scale_factor)
                self.confirm_dialog.exec_()
            except subprocess.CalledProcessError:
                pass
    def toggle_killexplorer(self):
        """切换 killexplorer 状态并保存设置"""
        settings["killexplorer"] = not settings.get("killexplorer", False)
        self.killexplorer_button.setText(self.tr("沉浸模式: %1").replace('%1', '√' if settings['killexplorer'] else '×'))
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        self.parent().killexplorer = settings["killexplorer"]
        if self.parent().killexplorer == True:
            hide_desktop_icons()
            hide_taskbar()
            self.parent().winTaskbar.show()

    def toggle_freeze(self):
        """切换 freeze 状态并保存设置"""
        settings["freeze"] = not settings.get("freeze", False)
        self.freeze_button.setText(self.tr("回主页时尝试冻结游戏 %1").replace('%1', '√' if settings['freeze'] else '×'))
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        self.parent().freeze = settings["freeze"]

    def toggle_show_battery(self):
        settings["show_battery"] = not settings.get("show_battery", False)
        self.show_battery_button.setText(self.tr("时间栏显示电量 %1").replace('%1', '√' if settings['show_battery'] else '×'))
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        try:
            if self.parent() and hasattr(self.parent(), "update_time"):
                self.parent().update_time()
        except Exception:
            pass

    def toggle_keep_on_taskbar(self):
        settings["keep_on_taskbar_when_minimized"] = not settings.get("keep_on_taskbar_when_minimized", False)
        self.keep_taskbar_button.setText(
            f"最小化时保留主窗口在任务栏 {'√' if settings['keep_on_taskbar_when_minimized'] else '×'}"
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def toggle_no_minimize_on_open(self):
        settings["skip_minimize_on_game_open"] = not settings.get("skip_minimize_on_game_open", False)
        self.no_minimize_on_open_button.setText(
            f"开启游戏/切换窗口时不执行最小化 {'√' if settings['skip_minimize_on_game_open'] else '×'}"
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def toggle_no_minimize_on_fullscreen_switch(self):
        settings["skip_minimize_on_fullscreen_switch_front"] = not settings.get("skip_minimize_on_fullscreen_switch_front", False)
        self.no_minimize_on_fullscreen_switch_button.setText(
            f"全屏应用按键切换回前端时不最小化应用 {'√' if settings['skip_minimize_on_fullscreen_switch_front'] else '×'}"
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def toggle_open_quick_settings(self):
        settings["open_quick_settings_on_bottom_down"] = not settings.get("open_quick_settings_on_bottom_down", False)
        self.open_quick_settings_button.setText(
            f"主页面底部再次下移可打开快速设置 {'√' if settings['open_quick_settings_on_bottom_down'] else '×'}"
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def toggle_peer_launch_mode(self):
        settings["use_peer_level_launch"] = not settings.get("use_peer_level_launch", False)
        self.peer_launch_button.setText(
            f"使用同级权限启动应用而非桌面权限  {'开' if settings['use_peer_level_launch'] else '关'}"
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def toggle_debug_output_window(self):
        settings["debug_output_window"] = not settings.get("debug_output_window", False)
        self.debug_window_button.setText(
            f"启用调试输出窗口  {'开' if settings['debug_output_window'] else '关'}"
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        if self.parent() and hasattr(self.parent(), "apply_debug_output_setting"):
            self.parent().apply_debug_output_setting()

    def show_manage_ignored_apps_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("管理忽略的应用"))
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(12 * self.parent().scale_factor)}px;
                border: 2px solid #444444;
            }}
        """)
        dialog.setFixedSize(int(680 * self.parent().scale_factor), int(420 * self.parent().scale_factor))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor))
        layout.setSpacing(int(12 * self.parent().scale_factor))

        label = QLabel(self.tr("忽略列表会过滤游戏库中的指定应用名称，适用于去除 Desktop/Steam Xbox 等系统条目。"))
        label.setWordWrap(True)
        label.setStyleSheet(f"color: #ffffff; font-size: {int(18 * self.parent().scale_factor)}px;")
        layout.addWidget(label)

        ignored_apps_list = QListWidget()
        ignored_apps_list.setStyleSheet(f"QListWidget {{ background-color: #2b2b2b; color: white; border: 1px solid #444444; border-radius: {int(8 * self.parent().scale_factor)}px; padding: {int(8 * self.parent().scale_factor)}px; }} QListWidget::item:selected {{ background-color: #3d6b8f; }}")
        layout.addWidget(ignored_apps_list)

        ignored_input_row = QWidget()
        ignored_input_layout = QHBoxLayout(ignored_input_row)
        ignored_input_layout.setContentsMargins(0, 0, 0, 0)
        ignored_input_layout.setSpacing(int(8 * self.parent().scale_factor))

        ignored_input = QLineEdit()
        ignored_input.setPlaceholderText("输入要忽略的应用名称")
        ignored_input.setFixedHeight(int(48 * self.parent().scale_factor))
        ignored_input.setStyleSheet(f"QLineEdit {{ background-color: rgba(255, 255, 255, 0.1); color: white; border: 1px solid #444444; border-radius: {int(10 * self.parent().scale_factor)}px; padding: {int(10 * self.parent().scale_factor)}px; font-size: {int(18 * self.parent().scale_factor)}px; }}")
        ignored_input_layout.addWidget(ignored_input)

        add_button = QPushButton(self.tr("添加"))
        add_button.setFixedHeight(int(48 * self.parent().scale_factor))
        add_button.setStyleSheet(f"QPushButton {{ background-color: #008CBA; color: white; border-radius: {int(10 * self.parent().scale_factor)}px; font-size: {int(18 * self.parent().scale_factor)}px; padding: 0 {int(16 * self.parent().scale_factor)}px; }} QPushButton:hover {{ background-color: #0073a1; }}")
        ignored_input_layout.addWidget(add_button)

        remove_button = QPushButton(self.tr("删除选中"))
        remove_button.setFixedHeight(int(48 * self.parent().scale_factor))
        remove_button.setStyleSheet(f"QPushButton {{ background-color: #ff4444; color: white; border-radius: {int(10 * self.parent().scale_factor)}px; font-size: {int(18 * self.parent().scale_factor)}px; padding: 0 {int(16 * self.parent().scale_factor)}px; }} QPushButton:hover {{ background-color: #d23a3a; }}")
        ignored_input_layout.addWidget(remove_button)
        layout.addWidget(ignored_input_row)

        def refresh_list():
            ignored_apps_list.clear()
            for item in settings.get("ignored_apps", []):
                ignored_apps_list.addItem(str(item))

        def save_settings_and_reload():
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            load_apps()
            if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                self.parent().deep_reload_games()

        def add_item():
            name = ignored_input.text().strip()
            if not name:
                return
            ignored = settings.get("ignored_apps", [])
            if name in ignored:
                return
            ignored.append(name)
            settings["ignored_apps"] = ignored
            ignored_input.clear()
            refresh_list()
            save_settings_and_reload()

        def remove_item():
            selected = ignored_apps_list.selectedItems()
            if not selected:
                return
            ignored = [item for item in settings.get("ignored_apps", []) if item not in [w.text() for w in selected]]
            settings["ignored_apps"] = ignored
            refresh_list()
            save_settings_and_reload()

        add_button.clicked.connect(add_item)
        remove_button.clicked.connect(remove_item)
        refresh_list()

        close_button = QPushButton(self.tr("关闭"))
        close_button.setFixedHeight(int(48 * self.parent().scale_factor))
        close_button.setStyleSheet(f"QPushButton {{ background-color: #5f5f5f; color: white; border-radius: {int(10 * self.parent().scale_factor)}px; font-size: {int(18 * self.parent().scale_factor)}px; padding: 0 {int(16 * self.parent().scale_factor)}px; }} QPushButton:hover {{ background-color: #7d7d7d; }}")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.move(self.parent().x() + int(80 * self.parent().scale_factor), self.parent().y() + int(80 * self.parent().scale_factor))
        dialog.exec_()

    def update_buttonsindexset(self, value):
        """更新主页游戏数量并保存设置"""
        self.parent().buttonsindexset = value
        self.buttonsindexset_label.setText(f"主页游戏数量: {value}")
        self.parent().reload_interface()

        # 保存 buttonsindexset 设置
        settings["buttonsindexset"] = value
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def update_row_count(self, value):
        """更新每行游戏数量并保存设置"""
        self.parent().row_count = value
        self.row_count_label.setText(f"每行游戏数量: {value}")
        self.parent().reload_interface()

        # 保存 row_count 设置
        settings["row_count"] = value
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)



    def restart_program(self):
        """重启程序"""
        QApplication.quit()
        # 只传递可执行文件的路径，不传递其他参数
        subprocess.Popen([sys.executable])

    def close_program(self):
        """完全关闭程序"""
        self.close_program_button.setText(self.tr("正在退出程序..."))
        self.close_program_button.setEnabled(False)  # 禁用按钮以防止重复点击
        # 如果开启了沉浸模式
        if self.parent().killexplorer and hasattr(self.parent(), 'winTaskbar'):
            self.parent().winTaskbar.on_back_to_desktop()
        # 退出程序
        QTimer.singleShot(500, QApplication.quit)

    def handle_gamepad_input(self, action):
        """处理手柄输入"""
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog and self.confirm_dialog.isVisible():
            self.confirm_dialog.handle_gamepad_input(action)
            return
        if action == 'B':
            if self.is_control_selected:
                # 退出选中状态
                self.is_control_selected = False
                self.update_focus_visual()
            else:
                # 关闭设置窗口
                self.hide()
        elif action == 'A':
            if self.current_area == 'right' and self.focusable_widgets and 0 <= self.focused_index < len(self.focusable_widgets):
                widget = self.focusable_widgets[self.focused_index]
                if hasattr(widget, 'click'):
                    widget.click()
                else:
                    # 选中控件，进入调整模式
                    self.is_control_selected = True
                    self.update_focus_visual()
            elif self.current_area == 'left':
                # 在左侧区域按 A 键确认当前类别
                current_index = next((i for i, (k, btn) in enumerate(self.category_buttons) if btn.isChecked()), 0)
                key, btn = self.category_buttons[current_index]
                self.switch_category(key)
                # 切换到右侧区域
                self.current_area = 'right'
                # 清除左侧类别按钮的焦点
                for _, b in self.category_buttons:
                    b.clearFocus()
                # 取消选中状态
                self.is_control_selected = False
        elif action == 'UP':
            # 取消选中状态
            self.is_control_selected = False
            if self.current_area == 'left':
                # 在左侧区域向上切换类别
                current_index = next((i for i, (k, btn) in enumerate(self.category_buttons) if btn.isChecked()), 0)
                new_index = (current_index - 1) % len(self.category_buttons)
                key, btn = self.category_buttons[new_index]
                self.switch_category(key)
            elif self.current_area == 'right':
                if self.focusable_widgets:
                    # 在右侧区域向上切换控件
                    self.focused_index = (self.focused_index - 1) % len(self.focusable_widgets)
                    self.focusable_widgets[self.focused_index].setFocus()
                    self.update_focus_visual()
                else:
                    # 右侧区域没有可聚焦控件，切换到左侧区域
                    self.current_area = 'left'
        elif action == 'DOWN':
            # 取消选中状态
            self.is_control_selected = False
            if self.current_area == 'left':
                # 在左侧区域向下切换类别
                current_index = next((i for i, (k, btn) in enumerate(self.category_buttons) if btn.isChecked()), 0)
                new_index = (current_index + 1) % len(self.category_buttons)
                key, btn = self.category_buttons[new_index]
                self.switch_category(key)
            elif self.current_area == 'right':
                if self.focusable_widgets:
                    # 在右侧区域向下切换控件
                    self.focused_index = (self.focused_index + 1) % len(self.focusable_widgets)
                    self.focusable_widgets[self.focused_index].setFocus()
                    self.update_focus_visual()
                else:
                    # 右侧区域没有可聚焦控件，切换到左侧区域
                    self.current_area = 'left'
        elif action == 'LEFT':
            if self.is_control_selected and self.current_area == 'right' and self.focusable_widgets and 0 <= self.focused_index < len(self.focusable_widgets):
                # 选中状态下，调整滑块值
                widget = self.focusable_widgets[self.focused_index]
                if isinstance(widget, QSlider):
                    widget.setValue(widget.value() - 1)
            else:
                # 切换到左侧区域
                self.current_area = 'left'
                # 取消选中状态
                self.is_control_selected = False
                # 清除右侧区域的焦点
                if self.focusable_widgets and self.focused_index < len(self.focusable_widgets):
                    widget = self.focusable_widgets[self.focused_index]
                    widget.clearFocus()
                # 更新焦点的视觉反馈
                self.update_focus_visual()
        elif action == 'RIGHT':
            if self.is_control_selected and self.current_area == 'right' and self.focusable_widgets and 0 <= self.focused_index < len(self.focusable_widgets):
                # 选中状态下，调整滑块值
                widget = self.focusable_widgets[self.focused_index]
                if isinstance(widget, QSlider):
                    widget.setValue(widget.value() + 1)
            else:
                # 切换到右侧区域
                self.current_area = 'right'
                # 清除左侧类别按钮的焦点
                for _, b in self.category_buttons:
                    b.clearFocus()
                # 取消选中状态
                self.is_control_selected = False
                # 设置焦点到第一个可聚焦控件
                if self.focusable_widgets:
                    self.focused_index = 0
                    self.focusable_widgets[0].setFocus()
                # 更新焦点的视觉反馈
                self.update_focus_visual()

    def update_focus_visual(self):
        """更新焦点的视觉反馈"""
        # 只有在右侧区域时才显示右侧控件的聚焦样式。
        # 切换到左侧区域（当前区域为 'left'）时应清除右侧控件的任何聚焦样式。
        if self.current_area != 'right':
            for widget in self.focusable_widgets:
                if isinstance(widget, QPushButton):
                    style = widget.styleSheet()
                    style = style.replace('border: 2px solid #00bfff;', 'border: none;')
                    style = style.replace('border: 2px solid #ff00ff;', 'border: none;')
                    widget.setStyleSheet(style)
                elif isinstance(widget, QSlider):
                    widget.setStyleSheet("")
            return

        # 移除所有控件的焦点样式
        for widget in self.focusable_widgets:
            if isinstance(widget, QPushButton):
                # 移除所有边框样式
                style = widget.styleSheet()
                style = style.replace('border: 2px solid #00bfff;', 'border: none;')
                style = style.replace('border: 2px solid #ff00ff;', 'border: none;')
                widget.setStyleSheet(style)
            elif isinstance(widget, QSlider):
                # 恢复滑块的默认样式
                widget.setStyleSheet("")
        
        # 为当前聚焦的控件添加焦点样式
        if self.focusable_widgets and 0 <= self.focused_index < len(self.focusable_widgets):
            widget = self.focusable_widgets[self.focused_index]
            if isinstance(widget, QPushButton):
                # 保存原始样式
                original_style = widget.styleSheet()
                # 根据是否选中状态设置不同的边框颜色
                if self.is_control_selected:
                    # 选中状态：紫色边框
                    if 'border: 2px solid #ff00ff;' not in original_style:
                        original_style = original_style.replace('border: none;', 'border: 2px solid #ff00ff;')
                        widget.setStyleSheet(original_style)
                else:
                    # 普通聚焦状态：蓝色边框
                    if 'border: 2px solid #00bfff;' not in original_style:
                        original_style = original_style.replace('border: none;', 'border: 2px solid #00bfff;')
                        widget.setStyleSheet(original_style)
            elif isinstance(widget, QSlider):
                # 为滑块添加焦点样式
                if self.is_control_selected:
                    # 选中状态：紫色手柄和轨道
                    widget.setStyleSheet("""
                        QSlider::groove:horizontal {
                            height: 10px;
                            border: 1px solid #ff00ff;
                            background: qlineargradient(
                                x1:0, y1:0, x2:1, y2:0,
                                stop:0 #ff99ff, stop:1 #ff00ff
                            );
                            border-radius: 5px;
                        }
                        QSlider::handle:horizontal {
                            background: #ff00ff;
                            border: 2px solid #ffffff;
                            width: 14px;
                            height: 14px;
                            margin: -5px 0;
                            border-radius: 7px;
                        }
                        QSlider::chunk:horizontal {
                            background-color: #ff00ff;
                        }
                    """)
                else:
                    # 普通聚焦状态：蓝色手柄和轨道
                    widget.setStyleSheet("""
                        QSlider::groove:horizontal {
                            height: 10px;
                            border: 1px solid #00bfff;
                            background: qlineargradient(
                                x1:0, y1:0, x2:1, y2:0,
                                stop:0 #99ccff, stop:1 #00bfff
                            );
                            border-radius: 5px;
                        }
                        QSlider::handle:horizontal {
                            background: #00bfff;
                            border: 2px solid #ffffff;
                            width: 14px;
                            height: 14px;
                            margin: -5px 0;
                            border-radius: 7px;
                        }
                        QSlider::chunk:horizontal {
                            background-color: #00bfff;
                        }
                    """)


# 应用程序入口
if __name__ == "__main__":
    global STARTUP  # 声明 STARTUP 为全局变量
    # 获取程序所在目录
    z_order = []
    def enum_windows_callback(hwnd, lParam):
        z_order.append(hwnd)
        return True
    win32gui.EnumWindows(enum_windows_callback, None)
    
    # 打印当前工作目录
    print("当前工作目录:", os.getcwd())
    unique_args = list(dict.fromkeys(sys.argv))
    if len(unique_args) > 1 and unique_args[1] == "startup":
        STARTUP = True
    else:
        STARTUP = False
    # 避免重复运行
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        if proc.info['exe'] == sys.executable and proc.info['pid'] != current_pid:
            proc.terminate()
            proc.wait()
    app = QApplication(sys.argv)
    selector = GameSelector()
    selector.show()
    # 去除重复的路径

    sys.exit(app.exec_())
