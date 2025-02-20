import sys
import json
import threading
import pygame
import configparser
import win32gui,win32process,psutil
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QDialog, QGridLayout, QWidget, QPushButton, QLabel, QDesktopWidget, QHBoxLayout, QFileDialog, QSlider, QTextEdit, QProgressBar, QScrollArea, QFrame
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import subprocess
import time
import os,win32con
import ctypes
import glob,re
import win32com.client  # 用于解析 .lnk 文件
from icoextract import IconExtractor, IconExtractorError
from PIL import Image, ImageDraw
from colorthief import ColorThief
from io import BytesIO
import ctypes
import time,pyautogui
from ctypes import wintypes
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
# 读取 JSON 数据
json_path = r"C:\Program Files\Sunshine\config\apps.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
    ###下面俩行代码用于QuickStreamAppAdd的伪排序清除，若感到困惑可删除###
    for idx, entry in enumerate(data["apps"]):
        entry["name"] = re.sub(r'^\d{2} ', '', entry["name"])  # 去掉开头的两位数字和空格

if ctypes.windll.shell32.IsUserAnAdmin()==0:
    ADMIN = False
elif ctypes.windll.shell32.IsUserAnAdmin()==1:
    ADMIN = True
# 筛选具有 "output_image" or "igdb" 路径的条目
games = [
    app for app in data["apps"]
    if "output_image" in app.get("image-path", "") or "igdb" in app.get("image-path", "") or "steam/appcache/librarycache/" in app.get("image-path", "")
]

# 读取设置文件
settings_path = "set.json"
settings = {
    "favorites": [],
    "last_played": [],
    "more_favorites": [],
    "more_last_used": [],
    "extra_paths": [],
    "scale_factor": 1.0  # 添加缩放因数的默认值
}

try:
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
except Exception as e:
    print(f"Error loading settings: {e}")

def get_lnk_files():
    # 获取当前工作目录下的所有 .lnk 文件
    lnk_files = glob.glob("*.lnk")
    valid_lnk_files = []
    
    # 过滤掉指向文件夹的快捷方式
    for lnk in lnk_files:
        try:
            target_path = get_target_path_from_lnk(lnk)
            # 只保留指向可执行文件的快捷方式
            if os.path.isdir(target_path):
                print(f"跳过文件夹快捷方式: {lnk} -> {target_path}")
            else:
                valid_lnk_files.append(lnk)
        except Exception as e:
            print(f"无法获取 {lnk} 的目标路径: {e}")
    
    print("找到的 .lnk 文件:")
    for idx, lnk in enumerate(valid_lnk_files):
        print(f"{idx+1}. {lnk}")
    return valid_lnk_files

def get_target_path_from_lnk(lnk_file):
    # 使用 win32com 获取快捷方式目标路径
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_file)
    return shortcut.TargetPath

def extract_icon(exe_path):
    try:
        extractor = IconExtractor(exe_path)
        output_icon_path = "temp_icon.ico"
        extractor.export_icon(output_icon_path, num=0)
        return output_icon_path
    except IconExtractorError as e:
        print(f"提取图标失败: {e}")
        return None

def get_dominant_colors(image, num_colors=2):
    with BytesIO() as output:
        image.save(output, format="PNG")
        img_bytes = output.getvalue()

    color_thief = ColorThief(BytesIO(img_bytes))
    return color_thief.get_palette(color_count=num_colors)

def create_image_with_icon(exe_path, output_path):
    try:
        icon_path = extract_icon(exe_path)
        if (icon_path is None):
            print(f"无法提取图标: {exe_path}")
            return

        with Image.open(icon_path) as icon_img:
            icon_width, icon_height = icon_img.size
            dominant_colors = get_dominant_colors(icon_img)
            color1, color2 = dominant_colors[0], dominant_colors[1]

            img = Image.new('RGBA', (600, 800), color=(255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            for y in range(800):
                for x in range(600):
                    ratio_x = x / 600
                    ratio_y = y / 800
                    ratio = (ratio_x + ratio_y) / 2
                    r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                    g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                    b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                    draw.point((x, y), fill=(r, g, b, 255))

            icon_x = (600 - icon_width) // 2
            icon_y = (800 - icon_height) // 2
            img.paste(icon_img, (icon_x, icon_y), icon_img)

            img.save(output_path, format="PNG")
            print(f"图像已保存至 {output_path}")

        try:
            os.remove(icon_path)
            print(f"\n {exe_path}\n")
        except PermissionError:
            print(f"无法删除临时图标文件: {icon_path}. 稍后再试.")
            time.sleep(1)
            os.remove(icon_path)

    except Exception as e:
        print(f"创建图像时发生异常，跳过此文件: {exe_path}\n异常信息: {e}")

def load_apps_json(json_path):
    # 加载已有的 apps.json
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 如果文件不存在，返回一个空的基础结构
        return {"env": "", "apps": []}

def generate_app_entry(lnk_file, index):
    # 为每个快捷方式生成对应的 app 条目
    entry = {
        "name": os.path.splitext(lnk_file)[0],  # 使用快捷方式文件名作为名称
        "output": "",
        "cmd": f"{os.path.abspath(lnk_file)}",
        "exclude-global-prep-cmd": "false",
        "elevated": "false",
        "auto-detach": "true",
        "wait-all": "true",
        "exit-timeout": "5",
        "menu-cmd": "",
        "image-path": f"C:\\Program Files\\Sunshine\\assets\\output_image\\output_image{index}.png",
    }
    return entry

def add_entries_to_apps_json(valid_lnk_files, apps_json):
    # 删除现有 apps.json 中与有效 .lnk 文件 name 相同的条目
    app_names = {entry['name'] for entry in apps_json['apps']}
    for lnk_file in valid_lnk_files:
        # 如果 name 已存在，则删除
        if lnk_file in app_names:
            apps_json['apps'] = [entry for entry in apps_json['apps'] if entry['name'] != lnk_file]
    
    # 为每个有效的快捷方式生成新的条目并添加到 apps 中
    for index, lnk_file in enumerate(valid_lnk_files):
        app_entry = generate_app_entry(lnk_file, index)
        apps_json["apps"].append(app_entry)

def remove_entries_with_output_image(apps_json):
    # 删除 apps.json 中包含 "output_image" 的条目
    apps_json['apps'] = [
        entry for entry in apps_json['apps'] if "output_image" not in entry.get("image-path", "")
    ]
    print("已删除包含 'output_image' 的条目")

def save_apps_json(apps_json, file_path):
    # 将更新后的 apps.json 保存到文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(apps_json, f, ensure_ascii=False, indent=4)

# 存储解析后的有效软件条目
valid_apps = []
def get_target_path(lnk_file):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_file)
    return shortcut.TargetPath
for app in data.get("apps", []):
    cmda = app.get("cmd")
    cmd = cmda.strip('"')
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
print(valid_apps)

# 游戏运行状态监听线程
class RefreshThread(QThread):
    progress_signal = pyqtSignal(int, int)  # 当前进度和总数

    def __init__(self, extra_paths, parent=None):
        super().__init__(parent)
        self.extra_paths = extra_paths

    def run(self):
        valid_lnk_files = []
        for path in self.extra_paths:
            if os.path.exists(path):
                os.chdir(path)  # 切换到路径
                valid_lnk_files.extend(get_lnk_files())

        target_paths = [get_target_path_from_lnk(lnk) for lnk in valid_lnk_files]

        output_folder = r"C:\Program Files\Sunshine\assets\output_image"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        apps_json_path = r"C:\Program Files\Sunshine\config\apps.json"
        apps_json = load_apps_json(apps_json_path)

        remove_entries_with_output_image(apps_json)

        total_files = len(target_paths)
        for idx, target_path in enumerate(target_paths):
            output_path = os.path.join(output_folder, f"output_image{idx}.png")
            create_image_with_icon(target_path, output_path)
            self.progress_signal.emit(idx + 1, total_files)  # 发射进度信号

        add_entries_to_apps_json(valid_lnk_files, apps_json)
        save_apps_json(apps_json, apps_json_path)
# 焦点判断线程的标志变量
focus = True
focus_lock = threading.Lock()
# 游戏运行状态监听线程
class MonitorRunningAppsThread(QThread):
    play_reload_signal = pyqtSignal()  # 用于通知主线程重载
    play_app_name_signal = pyqtSignal(list)  # 用于传递 play_app_name 到主线程

    def __init__(self, play_lock, play_app_name, valid_apps):
        super().__init__()
        self.play_lock = play_lock
        self.play_app_name = play_app_name
        self.valid_apps = valid_apps
        self.running = True

    def check_running_apps(self):
        """检查当前运行的应用"""
        current_running_apps = set()

        # 获取当前运行的所有进程
        for process in psutil.process_iter(['pid', 'exe']):
            try:
                exe_path = process.info['exe']
                if exe_path:
                    # 检查进程路径是否在 valid_apps 中
                    for app in self.valid_apps:
                        if exe_path.lower() == app['path'].lower():
                            current_running_apps.add(app['name'])
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        print(current_running_apps)

        # 如果当前运行的应用和 play_app_name 中的内容不同，更新 play_app_name
        with self.play_lock:  # 加锁，确保修改时线程安全
            if current_running_apps != set(self.play_app_name):
                self.play_app_name = list(current_running_apps)
                self.play_reload_signal.emit()  # 发出信号通知主线程
                self.play_app_name_signal.emit(self.play_app_name)  # 将 play_app_name 发送到主线程
            else:
                play_reload = False

    def run(self):
        """后台线程的运行方法"""
        while self.running:
            self.check_running_apps()  # 检查运行的应用
            time.sleep(1)  # 每秒检查一次进程

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束

class ConfirmDialog(QDialog):
    def __init__(self, variable1, scale_factor=1.0):
        super().__init__()
        self.variable1 = variable1
        self.scale_factor = scale_factor
        self.setWindowTitle("游戏确认")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(int(800 * self.scale_factor), int(400 * self.scale_factor))  # 更新后的固定尺寸
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                border: 5px solid #4CAF50;
            }
            QLabel {
                font-size: 36px;
                color: #FFFFFF;
                margin-bottom: 40px;
                text-align: center;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 20px 0;
                font-size: 32px;
                margin: 0;
                width: 100%;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #388e3c;
            }
            QVBoxLayout {
                margin: 40px;
                spacing: 0;
            }
            QHBoxLayout {
                justify-content: center;
                spacing: 0;
            }
        """)

        self.init_ui()
        self.current_index = 0  # 当前选中的按钮索引
        self.buttons = [self.cancel_button, self.confirm_button]  # 按钮列表
        self.last_input_time = 0  # 最后一次处理输入的时间
        self.input_delay = 300  # 去抖延迟时间，单位：毫秒
        self.ignore_input_until = 0  # 忽略输入的时间戳
        self.update_highlight()  # 初始化时更新高亮状态

    def init_ui(self):
        layout = QVBoxLayout()

        # 显示提示文本
        self.label = QLabel(self.variable1)
        self.label.setAlignment(Qt.AlignCenter)  # 设置文本居中
        layout.addWidget(self.label)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_action)
        button_layout.addWidget(self.cancel_button)

        # 确认按钮
        self.confirm_button = QPushButton("确认")
        self.confirm_button.clicked.connect(self.confirm_action)
        button_layout.addWidget(self.confirm_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def confirm_action(self): 
        print("用户点击了确认按钮")
        self.accept()

    def cancel_action(self):
        print("用户点击了取消按钮")
        self.reject()
    
    def showEvent(self, event):
        """窗口显示时的事件处理"""
        super().showEvent(event)
        self.ignore_input_until = pygame.time.get_ticks() + 350  # 打开窗口后1秒内忽略输入

    def keyPressEvent(self, event):
        """处理键盘事件"""
        current_time = pygame.time.get_ticks()  # 获取当前时间（毫秒）
        # 如果在忽略输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
            return
        
        if event.key() == Qt.Key_Left:
            self.current_index = max(0, self.current_index - 1)
            self.update_highlight()
        elif event.key() == Qt.Key_Right:
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
        if action == 'LEFT':
            self.current_index = max(0, self.current_index - 1)
            self.update_highlight()
        elif action == 'RIGHT':
            self.current_index = min(len(self.buttons) - 1, self.current_index + 1)
            self.update_highlight()
        elif action == 'A':
            self.buttons[self.current_index].click()
        # 更新最后一次按键时间
        self.last_input_time = current_time

    def update_highlight(self):
        """更新按钮高亮状态"""
        for index, button in enumerate(self.buttons):
            if index == self.current_index:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #45a049;
                        color: white;
                        border: none;
                        padding: 20px 0;
                        font-size: 32px;
                        margin: 0;
                        width: 100%;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 20px 0;
                        font-size: 32px;
                        margin: 0;
                        width: 100%;
                    }
                """)

class GameSelector(QWidget): 
    def __init__(self):
        global play_reload
        super().__init__()
        self.setWindowIcon(QIcon('fav.ico'))
        self.scale_factor = settings.get("scale_factor", 1.0)  # 从设置中读取缩放因数
        self.setWindowTitle("游戏选择器")
        
        # 获取屏幕的分辨率
        screen = QDesktopWidget().screenGeometry()

        # 设置窗口大小为屏幕分辨率
        self.resize(screen.width(), screen.height())
        self.setWindowFlags(Qt.FramelessWindowHint)  # 全屏无边框
        self.setStyleSheet("background-color: #1e1e1e;")  # 设置深灰背景色
        self.killexplorer = settings.get("killexplorer", False)
        if self.killexplorer == True:
            subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
        self.showFullScreen()
        # 确保窗口捕获焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.activateWindow()
        self.raise_()

        self.ignore_input_until = 0  # 添加变量以记录输入屏蔽的时间戳
        # 游戏索引和布局
        self.player = {}
        self.current_index = 0  # 从第一个按钮开始
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(int(20 * self.scale_factor))  # 设置按钮之间的间距

        # 从设置中读取 row_count，如果不存在则使用默认值
        self.row_count = settings.get("row_count", 6)  # 每行显示的按钮数量

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

        # 创建更多按钮
        self.more_button = QPushButton("更多 X/□")
        self.more_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.more_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #ffff88;
            }}
        """)
        self.more_button.clicked.connect(self.show_more_window)

        # 添加收藏按钮
        self.favorite_button = QPushButton("收藏 Y/△")
        self.favorite_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.favorite_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: yellow;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #ffff88;
            }}
        """)
        self.favorite_button.clicked.connect(self.toggle_favorite)

        # 创建退出按钮
        self.quit_button = QPushButton("退出 B/O")
        self.quit_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.quit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #ffff88;
            }}
        """)
        self.quit_button.clicked.connect(self.exitdef)
        # 创建游戏标题标签
        sorted_games = self.sort_games()
        if sorted_games:  # 检查是否有游戏
            self.game_name_label = QLabel(sorted_games[self.current_index]["name"])
        else:
            self.game_name_label = QLabel("没有找到游戏")  # 显示提示信息
        
        self.game_name_label.setAlignment(Qt.AlignCenter)
        self.game_name_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {int(20 * self.scale_factor)}px;
                font-weight: bold;
                padding: 0 {int(20 * self.scale_factor)}px;
            }}
        """)

        # 将按钮和标签添加到对应的布局
        self.left_layout.addWidget(self.more_button)
        self.center_layout.addWidget(self.game_name_label)
        self.right_layout.addWidget(self.favorite_button)
        self.right_layout.addWidget(self.quit_button)

        # 将三个布局添加到顶部布局
        self.top_layout.addLayout(self.left_layout, 1)  # stretch=1
        self.top_layout.addLayout(self.center_layout, 2)  # stretch=2，让中间部分占据更多空间
        self.top_layout.addLayout(self.right_layout, 1)  # stretch=1

        # 创建悬浮窗
        self.floating_window = None
        self.in_floating_window = False
        
        # 添加游戏按钮
        self.buttons = []
        if sorted_games:  # 只在有游戏时添加按钮
            for index, game in enumerate(sorted_games):
                button = self.create_game_button(game, index)
                self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
                self.buttons.append(button)
        else:
            # 添加一个提示按钮
            no_games_button = QPushButton("请点击-更多-按钮添加含有快捷方式的目录后\n使用-设置-刷新游戏-按钮添加主页面游戏")
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
            self.grid_layout.addWidget(no_games_button, 0, 0)
            self.buttons.append(no_games_button)

        # 获取排序后的游戏列表
        sorted_games = self.sort_games()
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.top_layout)  # 添加顶部布局

        # 创建一个新的布局容器用于放置游戏按钮网格
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(int(self.height() * 0.9))  # 设置高度为90%
        self.scroll_area.setFixedWidth(int(self.width()))  # 设置宽度为100%
        self.scroll_area.setAttribute(Qt.WA_AcceptTouchEvents)  #滚动支持

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

        # 启动游戏运行状态监听线程
        self.play_reload = False
        self.play_lock = threading.Lock()
        self.play_app_name = []
        self.valid_apps = valid_apps  # 在这里填充 valid_apps
        self.monitor_thread = MonitorRunningAppsThread(self.play_lock, self.play_app_name, self.valid_apps)
        self.monitor_thread.play_app_name_signal.connect(self.update_play_app_name)  # 连接信号到槽
        self.monitor_thread.play_reload_signal.connect(self.handle_reload_signal)  # 连接信号到槽
        self.monitor_thread.start() 
        # 启动手柄输入监听线程
        self.controller_thread = GameControllerThread(self)
        self.controller_thread.gamepad_signal.connect(self.handle_gamepad_input)
        self.controller_thread.start()

        # 按键去抖的间隔时间（单位：毫秒）
        self.last_input_time = 0  # 最后一次处理输入的时间
        self.input_delay = 300  # 去抖延迟时间，单位：毫秒

        # 初始化完成后立即高亮第一个项目
        self.update_highlight()

        # 添加悬浮窗开关防抖
        self.last_window_toggle_time = 0
        self.window_toggle_delay = 300  # 设置300毫秒的防抖延迟

        # 创建设置按钮
        self.settings_button = QPushButton("设置")
        self.settings_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #ffff88;
            }}
        """)
        self.settings_button.clicked.connect(self.show_settings_window)

        # 将设置按钮添加到左侧布局
        self.left_layout.addWidget(self.settings_button)

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
        button_container.setFixedSize(int(220 * self.scale_factor), int(300 * self.scale_factor))  # 确保容器大小固定
        
        # 创建游戏按钮
        button = QPushButton()
        pixmap = QPixmap(game["image-path"]).scaled(int(200 * self.scale_factor), int(267 * self.scale_factor), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon = QIcon(pixmap)
        button.setIcon(icon)
        button.setIconSize(pixmap.size())
        button.setFixedSize(int(220 * self.scale_factor), int(300 * self.scale_factor))
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: #2e2e2e; 
                border-radius: {int(10 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #444444;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #888888;
            }}
        """)
        button.clicked.connect(lambda checked, idx=index: self.launch_game(idx))
        
        # 创建星标（如果已收藏）
        if game["name"] in settings["favorites"]:
            star_label = QLabel("⭐", button)  # 将星标作为按钮的子控件
            star_label.setStyleSheet(f"""
                QLabel {{
                    color: yellow;
                    font-size: {int(20 * self.scale_factor)}px;
                    padding: {int(5 * self.scale_factor)}px;
                    background-color: rgba(46, 46, 46, 0.7);
                    border-radius: {int(5 * self.scale_factor)}px;
                }}
            """)
            star_label.move(int(5 * self.scale_factor), int(5 * self.scale_factor)) 
        if game["name"] in self.player:
            star_label = QLabel("🌊运行中🌊\n点击恢复", button)  
            star_label.setAlignment(Qt.AlignCenter)
            star_label.setStyleSheet(f"""
                QLabel {{
                    color: yellow;
                    font-size: {int(20 * self.scale_factor)}px;
                    padding: {int(5 * self.scale_factor)}px;
                    background-color: rgba(46, 46, 46, 0.7);
                    border-radius: {int(5 * self.scale_factor)}px;
                    border: {int(2 * self.scale_factor)}px solid white;
                    text-align: center;
                }}
            """)
            star_label.move(int(45 * self.scale_factor), int(190 * self.scale_factor)) 
        
        return button

    def update_highlight(self):
        """高亮当前选中的游戏按钮，并更新游戏名称"""
        sorted_games = self.sort_games()
        
        # 检查是否有游戏
        if not sorted_games:
            self.game_name_label.setText("没有找到游戏")
            return
        
        # 确保 current_index 不超出范围
        if self.current_index >= len(sorted_games):
            self.current_index = len(sorted_games) - 1
        
        # 更新游戏名称标签
        self.game_name_label.setText(sorted_games[self.current_index]["name"])
        
        # 检查当前游戏是否在运行
        current_game_name = sorted_games[self.current_index]["name"]
        is_running = current_game_name in self.player  # 假设 self.player 存储正在运行的游戏名称

        # 更新 favorite_button 的文本和样式
        if is_running:
            self.favorite_button.setText("结束进程")
            self.favorite_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: red; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #888888;
                    color: white;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #ffff88;
                }}
            """)
        else:
            self.favorite_button.setText("收藏 Y/△")
            self.favorite_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #888888;
                    color: yellow;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #ffff88;
                }}
            """)

        for index, button in enumerate(self.buttons):
            if index == self.current_index:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2e2e2e; 
                        border-radius: {int(10 * self.scale_factor)}px; 
                        border: {int(3 * self.scale_factor)}px solid yellow;
                    }}
                    QPushButton:hover {{
                        border: {int(3 * self.scale_factor)}px solid #ffff88;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2e2e2e; 
                        border-radius: {int(10 * self.scale_factor)}px; 
                        border: {int(2 * self.scale_factor)}px solid #444444;
                    }}
                    QPushButton:hover {{
                        border: {int(2 * self.scale_factor)}px solid #888888;
                    }}
                """)

        # 只在有按钮时进行滚动条调整
        if self.buttons:
            current_button = self.buttons[self.current_index]
            button_pos = current_button.mapTo(self.scroll_widget, current_button.pos())
            scroll_area_height = self.scroll_area.viewport().height()

            if button_pos.y() < self.scroll_area.verticalScrollBar().value():
                self.scroll_area.verticalScrollBar().setValue(button_pos.y())
            elif button_pos.y() + current_button.height() > self.scroll_area.verticalScrollBar().value() + scroll_area_height:
                self.scroll_area.verticalScrollBar().setValue(button_pos.y() + current_button.height() - scroll_area_height)

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if getattrs:
            with focus_lock:  #焦点检查-只有打包后才能使用
                if not focus: 
                    return
        if self.in_floating_window and self.floating_window:
            # 添加防抖检查
            if not self.floating_window.can_process_input():
                return
            
            if event.key() == Qt.Key_Up:
                self.floating_window.current_index = max(0, self.floating_window.current_index - 1)
                self.floating_window.update_highlight()
            elif event.key() == Qt.Key_Down:
                self.floating_window.current_index = min(
                    len(self.floating_window.buttons) - 1,
                    self.floating_window.current_index + 1
                )
                self.floating_window.update_highlight()
            elif event.key() == Qt.Key_Return:
                self.execute_more_item()
            elif event.key() == Qt.Key_Escape:
                self.floating_window.hide()
                self.in_floating_window = False
            return
            
        current_time = pygame.time.get_ticks()  # 获取当前时间（毫秒）
        # 如果在忽略输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
            return

        if event.key() == Qt.Key_Up:
            self.move_selection(-self.row_count)  # 向上移动
        elif event.key() == Qt.Key_Down:
            self.move_selection(self.row_count)  # 向下移动
        elif event.key() == Qt.Key_Left:
            self.move_selection(-1)  # 向左移动
        elif event.key() == Qt.Key_Right:
            self.move_selection(1)  # 向右移动
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.launch_game(self.current_index)  # 启动游戏
        elif event.key() == Qt.Key_Escape:
            self.exitdef()  # 退出程序

        # 更新最后一次按键时间
        self.last_input_time = current_time

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
    # 焦点检测线程
    def focus_thread():
        global focus
        while True:
            # 获取当前活动窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                print("未找到活动窗口")
                return False  # 未找到活动窗口
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            exe_path = process.exe()
            exe_name = os.path.basename(exe_path)
            with focus_lock:
                if exe_name == "DesktopGame.exe":
                    focus = True
                else:
                    focus = False
            time.sleep(0.05)  # 稍微休眠，避免线程占用过多 CPU
    
    # 启动焦点判断线程
    thread = threading.Thread(target=focus_thread, daemon=True)
    thread.start()   

    def launch_game(self, index):
        """启动选中的游戏"""
        sorted_games = self.sort_games()
        game = sorted_games[index]
        game_cmd = game["cmd"]
        game_name = game["name"]
        image_path = game.get("image-path", "")

        if game["name"] in self.player:
            for app in valid_apps:
                if app["name"] == game["name"]:
                    game_path = app["path"]
                    break
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
                                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                    win32gui.SetForegroundWindow(hwnd)
                                    print(f"已将进程 {pid} 的窗口带到前台")

                        # 枚举所有窗口
                        win32gui.EnumWindows(enum_window_callback, None)
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return
        if self.player:
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog("已经打开了一个游戏，还要再打开一个吗？")
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            else:
                pass
        self.controller_thread.show_launch_window(game_name, image_path)
        self.current_index = 0  # 从第一个按钮开始
        # 更新最近游玩列表
        if game["name"] in settings["last_played"]:
            settings["last_played"].remove(game["name"])
        settings["last_played"].insert(0, game["name"])
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

        self.reload_interface()
        if game_cmd:
            #self.showMinimized()
            subprocess.Popen(game_cmd, shell=True)
            #self.showFullScreen()
            self.ignore_input_until = pygame.time.get_ticks() + 1000
    
    def handle_gamepad_input(self, action):
        """处理手柄输入"""
        # 跟踪焦点状态
        current_time = pygame.time.get_ticks()
        # 如果在屏蔽输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        
        if current_time - self.last_input_time < self.input_delay:
            return
        if getattrs:
            with focus_lock:  #焦点检查-只有打包后才能使用
                if not focus: 
                    if action == 'GUIDE':
                        if ADMIN:
                            try:
                                if current_time < ((self.ignore_input_until)+2000):
                                    return
                                self.ignore_input_until = pygame.time.get_ticks() + 500
                                hwnd = int(self.winId())
                                #win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                #self.showFullScreen()
                                ## 记录当前窗口的 Z 顺序
                                #z_order = []
                                #def enum_windows_callback(hwnd, lParam):
                                #    z_order.append(hwnd)
                                #    return True
                                #win32gui.EnumWindows(enum_windows_callback, None)

                                SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                                time.sleep(0.2)
                                screen_width, screen_height = pyautogui.size()
                                pyautogui.FAILSAFE = False
                                # 设置右下角坐标
                                right_bottom_x = screen_width - 1  # 最右边
                                right_bottom_y = screen_height - 1  # 最底部
                                # 移动鼠标到屏幕右下角并进行右键点击
                                pyautogui.rightClick(right_bottom_x, right_bottom_y)
                                # 恢复原来的 Z 顺序
                                #for hwnd in reversed(z_order):
                                SetWindowPos(hwnd, -2, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                            except Exception as e:
                                print(f"Error: {e}")
                        else:
                            self.showFullScreen()
                            self.last_input_time = current_time
                    return
        
        if self.in_floating_window and self.floating_window:
            # 添加防抖检查
            if not self.floating_window.can_process_input():
                return
            
            if action == 'UP':
                self.floating_window.current_index = max(0, self.floating_window.current_index - 1)
                self.floating_window.update_highlight()
            elif action == 'DOWN':
                self.floating_window.current_index = min(
                    len(self.floating_window.buttons) - 1,
                    self.floating_window.current_index + 1
                )
                self.floating_window.update_highlight()
            elif action == 'A':
                self.execute_more_item()
            elif action in ('B', 'X'):  # B键或X键都可以关闭悬浮窗
                if self.can_toggle_window():
                    self.floating_window.hide()
                    self.in_floating_window = False
            elif action == 'Y':
                self.floating_window.toggle_favorite()
            return
        
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog.isVisible():  # 如果确认弹窗显示中
            print("确认弹窗显示中")
            self.confirm_dialog.handle_gamepad_input(action)
            return

        if action == 'UP':
            self.move_selection(-self.row_count)  # 向上移动
        elif action == 'DOWN':
            self.move_selection(self.row_count)  # 向下移动
        elif action == 'LEFT':
            self.move_selection(-1)  # 向左移动
        elif action == 'RIGHT':
            self.move_selection(1)  # 向右移动
        elif action == 'A':
            self.launch_game(self.current_index)  # 启动游戏
        elif action == 'B':
            if not self.in_floating_window and self.can_toggle_window():
                self.exitdef()  # 退出程序
        elif action == 'Y':
            self.toggle_favorite()  # 收藏/取消收藏游戏
        elif action == 'X':  # X键开悬浮窗
            self.show_more_window()  # 打开悬浮窗

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
        if self.killexplorer == True:
            subprocess.run(["start", "explorer.exe"], shell=True)
        self.close()
    def toggle_favorite(self):
        """切换当前游戏的收藏状态"""
        current_game = self.sort_games()[self.current_index]
        game_name = current_game["name"]
        print(game_name)
        #删除逻辑
        if game_name in self.player:
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog(f"是否关闭下列程序？\n{game_name}")
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
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
                        proc.terminate()  # 结束进程
                        proc.wait()  # 等待进程完全终止
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
    
    def reload_interface(self):
        """重新加载界面"""
        # 清除现有按钮
        #if self.butto:
        #    return
        #self.butto=True
        for button in self.buttons:
            button.setParent(None)
        self.buttons.clear()
        
        # 重新添加按钮
        sorted_games = self.sort_games()
        for index, game in enumerate(sorted_games):
            button = self.create_game_button(game, index)
            self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
            self.buttons.append(button)
        
        self.update_highlight()
        #time.sleep(1)
        #self.butto=False

    def show_more_window(self):
        """显示更多选项窗口"""
        if not self.can_toggle_window():
            return
            
        if not self.floating_window:
            self.floating_window = FloatingWindow(self)
            
        # 计算悬浮窗位置
        button_pos = self.more_button.mapToGlobal(self.more_button.rect().bottomLeft())
        self.floating_window.move(button_pos.x(), button_pos.y() + 10)
        
        self.floating_window.show()
        self.in_floating_window = True
        self.floating_window.update_highlight()
        
    def execute_more_item(self):
        """执行更多选项中的项目"""
        if not self.floating_window:
            return
            
        sorted_files = self.floating_window.sort_files()
        current_file = sorted_files[self.floating_window.current_index]
        
        # 更新最近使用列表
        if "more_last_used" not in settings:
            settings["more_last_used"] = []
            
        if current_file["name"] in settings["more_last_used"]:
            settings["more_last_used"].remove(current_file["name"])
        settings["more_last_used"].insert(0, current_file["name"])
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        
        # 执行文件
        subprocess.Popen(current_file["path"], shell=True)
        self.exitdef()

    def can_toggle_window(self):
        """检查是否可以切换悬浮窗状态"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_window_toggle_time < self.window_toggle_delay:
            return False
        self.last_window_toggle_time = current_time
        return True

    def show_settings_window(self):
        """显示设置窗口"""
        if not hasattr(self, 'settings_window') or self.settings_window is None:
            self.settings_window = SettingsWindow(self)
        
        # 计算悬浮窗位置
        button_pos = self.settings_button.mapToGlobal(self.settings_button.rect().bottomLeft())
        self.settings_window.move(button_pos.x(), button_pos.y() + 10)
        
        self.settings_window.show()
        self.settings_window.update_highlight()

    def is_admin(self):
        """检查当前进程是否具有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

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

    def refresh_games(self):
        """刷新游戏列表，处理 extra_paths 中的快捷方式"""
        subprocess.Popen("QuickStreamAppAdd.exe", shell=True)
        return
        if not self.is_admin():
            print("需要管理员权限才能刷新游戏列表。尝试获取管理员权限...")
            self.run_as_admin()
            return

        progress_window = ProgressWindow(self)
        progress_window.show()

        extra_paths = settings.get("extra_paths", [])
        self.refresh_thread = RefreshThread(extra_paths)
        self.refresh_thread.progress_signal.connect(progress_window.update_progress)
        self.refresh_thread.finished.connect(progress_window.close)
        self.refresh_thread.finished.connect(self.restart_program)
        self.refresh_thread.start()

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

        self.label = QLabel("正在刷新游戏列表...")
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

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        pygame.init()
        self.controllers = {}
        self.last_move_time = 0
        self.move_delay = 0.1
        self.axis_threshold = 0.5
        self.last_hat_time = 0
        self.hat_delay = 0.05
        self.last_hat_value = (0, 0)
        
        # 预创建 launch_overlay
        self.create_launch_overlay()

    def create_launch_overlay(self):
        """预创建启动游戏的悬浮窗"""
        self.parent.launch_overlay = QWidget(self.parent)
        self.parent.launch_overlay.setObjectName("launchOverlay")
        self.parent.launch_overlay.setStyleSheet("""
            QWidget#launchOverlay {
                background-color: rgba(46, 46, 46, 0.9);
            }
            QLabel {
                font-size: 36px;
                color: #FFFFFF;
                margin-bottom: 40px;
                text-align: center;
                background: transparent;  /* 设置文字背景透明 */
            }
        """)

        # 设置悬浮窗大小为父窗口大小
        self.parent.launch_overlay.setFixedSize(self.parent.size())

        # 创建垂直布局
        self.overlay_layout = QVBoxLayout(self.parent.launch_overlay)
        self.overlay_layout.setAlignment(Qt.AlignCenter)

        # 创建图片标签和文本标签
        self.overlay_image = QLabel()
        self.overlay_image.setAlignment(Qt.AlignCenter)
        self.overlay_layout.addWidget(self.overlay_image)

        self.overlay_text = QLabel()
        self.overlay_text.setAlignment(Qt.AlignCenter)
        self.overlay_layout.addWidget(self.overlay_text)

        # 初始时隐藏
        self.parent.launch_overlay.hide()

    def show_launch_window(self, game_name, image_path):
        """显示启动游戏的悬浮窗"""

        # 将悬浮窗置于最上层并显示
        self.parent.launch_overlay.raise_()
        self.parent.launch_overlay.show()

        # 更新图片
        if image_path:
            pixmap = QPixmap(image_path).scaled(
                int(400 * self.parent.scale_factor),
                int(533 * self.parent.scale_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.overlay_image.setPixmap(pixmap)
            self.overlay_image.show()
        else:
            self.overlay_image.hide()

        # 更新文本
        self.overlay_text.setText(f"正在启动 {game_name}")

        # 将悬浮窗置于最上层并显示
        self.parent.launch_overlay.raise_()
        self.parent.launch_overlay.show()
        QTimer.singleShot(6000, self.parent.launch_overlay.hide)

    def run(self):
        """监听手柄输入"""
        while True:
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
                            print(f"Controller {controller.get_instance_id()} connected: {controller.get_name()}")
                        except pygame.error as e:
                            print(f"Failed to initialize controller {event.device_index}: {e}")
                
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        if event.instance_id in self.controllers:
                            print(f"Controller {event.instance_id} disconnected")
                            del self.controllers[event.instance_id]

                # 处理所有已连接手柄的输入
                for controller_data in self.controllers.values():
                    controller = controller_data['controller']
                    mapping = controller_data['mapping']
                    
                    # 处理 hat 输入（D-pad）
                    if mapping.controller_type == "xbox360":
                        try:
                            for i in range(controller.get_numhats()):
                                hat = controller.get_hat(i)
                                if hat != (0, 0):  # 只在 hat 不在中心位置时处理
                                    current_time = time.time()
                                    if current_time - self.last_hat_time > self.hat_delay:
                                        if hat[1] == 1:  # 上
                                            print("HAT UP signal emitted")  # hat 上
                                            self.gamepad_signal.emit('UP')
                                        elif hat[1] == -1:  # 下
                                            print("HAT DOWN signal emitted")  # hat 下
                                            self.gamepad_signal.emit('DOWN')
                                        if hat[0] == -1:  # 左
                                            print("HAT LEFT signal emitted")  # hat 左
                                            self.gamepad_signal.emit('LEFT')
                                        elif hat[0] == 1:  # 右
                                            print("HAT RIGHT signal emitted")  # hat 右
                                            self.gamepad_signal.emit('RIGHT')
                                        self.last_hat_time = current_time
                                    else:
                                        self.last_hat_value = (0, 0)  # 重置上一次的 hat 值
                        except Exception as e:
                            print(f"Hat error: {e}")

                    # 读取摇杆
                    try:
                        left_x = controller.get_axis(mapping.left_stick_x)
                        left_y = controller.get_axis(mapping.left_stick_y)
                        right_x = controller.get_axis(mapping.right_stick_x)
                        right_y = controller.get_axis(mapping.right_stick_y)
                    except:
                        left_x = left_y = right_x = right_y = 0
                    
                    buttons = [controller.get_button(i) for i in range(controller.get_numbuttons())]
                    current_time = time.time()

                    # 检查摇杆移动
                    if time.time() - self.last_move_time > self.move_delay:
                        # 左摇杆
                        if left_y < -self.axis_threshold:
                            print("LEFT STICK UP signal emitted")  # 左摇杆上
                            self.gamepad_signal.emit('UP')
                            self.last_move_time = current_time
                        elif left_y > self.axis_threshold:
                            print("LEFT STICK DOWN signal emitted")  # 左摇杆下
                            self.gamepad_signal.emit('DOWN')
                            self.last_move_time = current_time
                        if left_x < -self.axis_threshold:
                            self.gamepad_signal.emit('LEFT')
                            self.last_move_time = current_time
                        elif left_x > self.axis_threshold:
                            self.gamepad_signal.emit('RIGHT')
                            self.last_move_time = current_time
                        
                        # 右摇杆
                        if right_y < -self.axis_threshold:
                            print(f"RIGHT STICK UP signal emitted{right_y}")  # 右摇杆上
                            self.gamepad_signal.emit('UP')
                            self.last_move_time = current_time
                        elif right_y > self.axis_threshold:
                            print("RIGHT STICK DOWN signal emitted")  # 右摇杆下
                            self.gamepad_signal.emit('DOWN')
                            self.last_move_time = current_time
                        if right_x < -self.axis_threshold:
                            self.gamepad_signal.emit('LEFT')
                            self.last_move_time = current_time
                        elif right_x > self.axis_threshold:
                            self.gamepad_signal.emit('RIGHT')
                            self.last_move_time = current_time

                    # 根据不同手柄类型处理 D-pad
                    if mapping.controller_type == "ps4":
                        # PS4 使用按钮
                        try:
                            if buttons[mapping.dpad_up]:
                                print("PS4 DPAD UP signal emitted")  # PS4 D-pad 上
                                self.gamepad_signal.emit('UP')
                            if buttons[mapping.dpad_down]:
                                print("PS4 DPAD DOWN signal emitted")  # PS4 D-pad 下
                                self.gamepad_signal.emit('DOWN')
                            if buttons[mapping.dpad_left]:
                                self.gamepad_signal.emit('LEFT')
                            if buttons[mapping.dpad_right]:
                                self.gamepad_signal.emit('RIGHT')
                        except:
                            pass
                    elif mapping.controller_type != "xbox360":  # 其他手柄（除了 Xbox 360）
                        # 其他手柄使用默认按钮方式
                        try:
                            if buttons[mapping.dpad_up]:
                                print("OTHER DPAD UP signal emitted")  # 其他手柄 D-pad 上
                                self.gamepad_signal.emit('UP')
                            if buttons[mapping.dpad_down]:
                                print("OTHER DPAD DOWN signal emitted")  # 其他手柄 D-pad 下
                                self.gamepad_signal.emit('DOWN')
                            if buttons[mapping.dpad_left]:
                                self.gamepad_signal.emit('LEFT')
                            if buttons[mapping.dpad_right]:
                                self.gamepad_signal.emit('RIGHT')
                        except:
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

                time.sleep(0.01)
            except Exception as e:
                print(f"Error in event loop: {e}")

class FloatingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        bat_dir = './bat'
        if not os.path.exists(bat_dir):
            os.makedirs(bat_dir)  # 创建目录
        self.select_add_btn = None  # 在初始化方法中定义
        self.select_del_btn = None  # 同样定义删除按钮
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(10 * parent.scale_factor)}px;
                border: {int(2 * parent.scale_factor)}px solid #444444;
            }}
        """)
        
        self.current_index = 0
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(int(5 * parent.scale_factor))
        self.buttons = []
        
        # 添加防抖相关属性
        self.last_input_time = 0
        self.input_delay = 200  # 设置200毫秒的防抖延迟
        
        # 读取目录中的文件
        self.files = self.get_files()
        self.create_buttons(False)
    
    def can_process_input(self):
        """检查是否可以处理输入"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_input_time < self.input_delay:
            return False
        self.last_input_time = current_time
        return True
    
    def get_files(self):
        """获取目录中的文件"""
        files = []
        # 获取当前目录的文件
            # 获取目录中的所有文件和文件夹
        all_files = os.listdir('./bat/')

        # 过滤掉文件夹，保留文件
        filess = [f for f in all_files if os.path.isfile(os.path.join('./bat/', f))]
        for file in filess:
            #if file.endswith(('.bat', '.url')) and not file.endswith('.lnk'):
            files.append({
                "name": os.path.splitext(file)[0],
                "path": file
            })

        return files
    #create_buttons()可刷新按钮
    def create_buttons(self, settitype=True): 
        """创建按钮"""
        self.files = self.get_files()
        if settitype:
            time.sleep(0.1)
            if self.select_add_btn:  # 确保按钮已经定义
                self.layout.removeWidget(self.select_add_btn)
            if self.select_del_btn:  # 确保按钮已经定义
                self.layout.removeWidget(self.select_del_btn)

        sorted_files = self.sort_files()
        for file in sorted_files:
            btn = QPushButton(file["name"])
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: white;
                    text-align: left;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
            """)
            if file["name"] in settings.get("more_favorites", []):
                btn.setText(f"⭐ {file['name']}")
            
            self.buttons.append(btn)
            self.layout.addWidget(btn)

        if settitype:
            # 重新添加按钮到布局
            if self.select_add_btn:
                self.layout.addWidget(self.select_add_btn)
            if self.select_del_btn:
                self.layout.addWidget(self.select_del_btn)
            return

        # 这里将按钮作为实例属性定义
        self.select_add_btn = QPushButton("➕ 添加项目")
        self.select_add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """)
        self.select_add_btn.clicked.connect(self.select_add)
        self.layout.addWidget(self.select_add_btn)

        self.select_del_btn = QPushButton("❌ 删除项目")
        self.select_del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """)
        self.select_del_btn.clicked.connect(self.select_del)
        self.layout.addWidget(self.select_del_btn)

    def select_add(self):
        self.show_add_item_window()
    def select_del(self):
        self.show_del_item_window()

    def show_add_item_window(self):
        """显示添加项目的悬浮窗"""
        # 创建悬浮窗口
        self.add_item_window = QWidget(self, Qt.Popup)
        self.add_item_window.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.add_item_window.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)

        layout = QVBoxLayout(self.add_item_window)
        layout.setSpacing(int(15 * self.parent().scale_factor))
        layout.setContentsMargins(int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor))

        # 第一行：编辑名称
        self.name_edit = QTextEdit()
        self.name_edit.setPlaceholderText("输入名称")
        self.name_edit.setFixedHeight(int(50 * self.parent().scale_factor))  # 设置固定高度为 30 像素
        self.name_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: {int(1 * self.parent().scale_factor)}px solid #444444;
                border-radius: {int(10 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px;
            }}
        """)
        layout.addWidget(self.name_edit)

        # 第二行：显示选择的项目
        self.selected_item_label = QLabel("")
        self.selected_item_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {int(16 * self.parent().scale_factor)}px;
                font-weight: 400;
            }}
        """)
        layout.addWidget(self.selected_item_label)

        # 第三行：选择bat、创建自定义bat按钮
        button_layout = QHBoxLayout()

        self.select_bat_button = QPushButton("选择文件")
        self.select_bat_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #5f5f5f;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(8 * self.parent().scale_factor)}px {int(16 * self.parent().scale_factor)}px;
                font-size: {int(14 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #808080;
            }}
            QPushButton:pressed {{
                background-color: #333333;
            }}
        """)
        self.select_bat_button.clicked.connect(self.select_bat_file)
        button_layout.addWidget(self.select_bat_button)

        self.create_custom_bat_button = QPushButton("创建自定义bat")
        self.create_custom_bat_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #404040;
                color: #999999;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(8 * self.parent().scale_factor)}px {int(16 * self.parent().scale_factor)}px;
                font-size: {int(14 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #606060;
            }}
            QPushButton:pressed {{
                background-color: #505050;
            }}
        """)
        self.create_custom_bat_button.clicked.connect(self.show_custom_bat_editor)
        button_layout.addWidget(self.create_custom_bat_button)

        layout.addLayout(button_layout)

        # 第四行：保存按钮
        self.save_button = QPushButton("保存")
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #008CBA;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #007B9E;
            }}
            QPushButton:pressed {{
                background-color: #006F8A;
            }}
        """)
        self.save_button.clicked.connect(self.save_item)
        layout.addWidget(self.save_button)

        self.add_item_window.setLayout(layout)
        self.add_item_window.show()
    def show_del_item_window(self): 
        """显示删除项目的悬浮窗"""
        # 创建悬浮窗口
        self.del_item_window = QWidget(self, Qt.Popup)
        self.del_item_window.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.del_item_window.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        self.del_item_window.move(30, 100)

        # 使用QVBoxLayout来管理布局
        layout = QVBoxLayout(self.del_item_window)
        layout.setSpacing(int(15 * self.parent().scale_factor))
        layout.setContentsMargins(int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor))

        # 获取文件列表并创建按钮
        files = self.get_files()  # 获取文件列表
        for file in files:
            file_button = QPushButton(file["name"])
            file_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #444444;
                    color: white;
                    text-align: center;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: #555555;
                }}
            """)
            # 连接每个按钮点击事件到处理函数
            file_button.clicked.connect(lambda checked, f=file, btn=file_button: self.handle_del_file_button_click(f, btn))
            layout.addWidget(file_button)

        # 设置布局
        self.del_item_window.setLayout(layout)
        self.del_item_window.show()

    def handle_del_file_button_click(self, file, button):
        """处理删除文件按钮点击事件"""
        if button.property("clicked_once"):
            # 第二次点击，删除文件
            self.remove_file(file)
            # 重新加载按钮
            for button in self.buttons:
                button.setParent(None)
            self.buttons.clear()
            self.create_buttons()
            self.update_highlight()
            self.adjustSize()  # 调整窗口大小以适应内容

        else:
            # 第一次点击，变红色并更改文本
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: red;
                    color: white;
                    text-align: center;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
            """)
            button.setText("删除？(再次点击确认)")
            button.setProperty("clicked_once", True)

    def remove_file(self, file):
        """删除文件并更新设置"""
        file_path = os.path.join('./bat/', file["path"])  # 获取文件的完整路径
        if os.path.exists(file_path):
            os.remove(file_path)  # 删除文件

            # 重新加载删除项窗口，确保界面更新
            self.del_item_window.close()  # 关闭删除项目窗口
            self.show_del_item_window()  # 重新加载删除项目窗口
        else:
            print(f"文件 {file['name']} 不存在！")
    def select_bat_file(self):
        """选择bat文件"""
        file_dialog = QFileDialog(self, "选择要启动的文件", "", "All Files (*.*)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
            self.selected_item_label.setText(selected_file)
            self.name_edit.setText(os.path.splitext(os.path.basename(selected_file))[0])  # 只填入文件名部分
            # 保持悬浮窗可见
            self.add_item_window.show()

    def show_custom_bat_editor(self):
        """显示自定义bat编辑器"""
        # 创建自定义 BAT 编辑器窗口
        self.custom_bat_editor = QWidget(self, Qt.Popup)
        self.custom_bat_editor.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.custom_bat_editor.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)

        layout = QVBoxLayout(self.custom_bat_editor)
        layout.setSpacing(int(15 * self.parent().scale_factor))
        layout.setContentsMargins(int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor))

        # 文本框：显示和编辑 bat 脚本
        self.bat_text_edit = QTextEdit()
        self.bat_text_edit.setPlaceholderText("请输入脚本内容...")
        self.bat_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: {int(1 * self.parent().scale_factor)}px solid #444444;
                border-radius: {int(10 * self.parent().scale_factor)}px;
                padding: {int(12 * self.parent().scale_factor)}px;
                font-size: {int(14 * self.parent().scale_factor)}px;           
            }}
        """)
        layout.addWidget(self.bat_text_edit)

        # 添加程序按钮
        self.add_program_button = QPushButton("添加程序")
        self.add_program_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #5f5f5f;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
                font-size: {int(14 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #808080;
            }}
            QPushButton:pressed {{
                background-color: #333333;
            }}
        """)
        self.add_program_button.clicked.connect(self.add_program_to_bat)
        layout.addWidget(self.add_program_button)

        # 保存bat按钮
        self.save_bat_button = QPushButton("保存bat")
        self.save_bat_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #388e3c;
            }}
        """)
        self.save_bat_button.clicked.connect(self.save_custom_bat)
        layout.addWidget(self.save_bat_button)
        self.custom_bat_editor.move(0, 100)
        self.custom_bat_editor.setLayout(layout)
        self.custom_bat_editor.show()


    def add_program_to_bat(self):
        """添加程序到bat"""
        file_dialog = QFileDialog(self, "选择一个可执行文件", "", "Executable Files (*.exe)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
            program_dir = os.path.dirname(selected_file)
            self.bat_text_edit.append(f'cd /d "{program_dir}"\nstart "" "{selected_file}"\n')
            self.add_item_window.show()
            self.custom_bat_editor.show()

    def save_custom_bat(self):
        """保存自定义bat"""
        bat_dir = './bat/Customize'
        if not os.path.exists(bat_dir):
            os.makedirs(bat_dir)  # 创建目录
        bat_content = self.bat_text_edit.toPlainText()
        bat_path = os.path.join(program_directory, "./bat/Customize/Customize.bat")
        counter = 1
        while os.path.exists(bat_path):
            bat_path = os.path.join(program_directory, f"./bat/Customize/Customize_{counter}.bat")
            counter += 1
        bat_path = os.path.abspath(bat_path)
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        self.selected_item_label.setText(bat_path)
        self.custom_bat_editor.hide()
        self.add_item_window.show()

    def save_item(self):
        """保存项目"""
        name = self.name_edit.toPlainText()
        path = self.selected_item_label.text()  
        bat_dir = './bat'
        if not os.path.exists(bat_dir):
            os.makedirs(bat_dir)

        # 创建 bat 文件的路径
        bat_file_path = os.path.join(bat_dir, f"{name}.bat")

        # 写入内容到 bat 文件
        with open(bat_file_path, 'w') as bat_file:
            bat_file.write(f'start "" "{path}"\n')

        print(f"成功创建 bat 文件: {bat_file_path}")  
        self.add_item_window.hide()

        # 重新加载按钮
        for button in self.buttons:
            button.setParent(None)
        self.buttons.clear()
        self.create_buttons()
        self.update_highlight()
        self.show()
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
        for i, button in enumerate(self.buttons):
            if i == self.current_index:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: {int(10 * self.parent().scale_factor)}px;
                        border: {int(2 * self.parent().scale_factor)}px solid yellow;
                        font-size: {int(16 * self.parent().scale_factor)}px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: {int(10 * self.parent().scale_factor)}px;
                        border: none;
                        font-size: {int(16 * self.parent().scale_factor)}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.1);
                    }}
                """)
    
    def toggle_favorite(self):
        """切换收藏状态"""
        sorted_files = self.sort_files()
        current_file = sorted_files[self.current_index]
        
        if "more_favorites" not in settings:
            settings["more_favorites"] = []
            
        if current_file["name"] in settings["more_favorites"]:
            settings["more_favorites"].remove(current_file["name"])
        else:
            settings["more_favorites"].append(current_file["name"])
            
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
            
        # 重新加载按钮
        for button in self.buttons:
            button.setParent(None)
        self.buttons.clear()
        self.create_buttons()
        self.update_highlight()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Up:
            self.current_index = (self.current_index - 1) % len(self.buttons)
            self.update_highlight()
        elif event.key() == Qt.Key_Down:
            self.current_index = (self.current_index + 1) % len(self.buttons)
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
        self.dpad_up = 11
        self.dpad_down = 12
        self.dpad_left = 13
        self.dpad_right = 14
        self.guide = 5
        self.left_stick_x = 0
        self.left_stick_y = 1
        self.right_stick_x = 3
        self.right_stick_y = 4
        self.has_hat = False
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
            self.dpad_up = 11
            self.dpad_down = 12
            self.dpad_left = 13
            self.dpad_right = 14
            self.left_stick_x = 0
            self.left_stick_y = 1
            self.right_stick_x = 2
            self.right_stick_y = 3
            self.guide = 5         # PS 键

            
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
            
        print(f"Detected controller: {self.controller_name}")

class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(10 * parent.scale_factor)}px;
                border: {int(2 * parent.scale_factor)}px solid #444444;
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(int(5 * parent.scale_factor))

        # 添加调整 row_count 的选项
        self.row_count_label = QLabel(f"每行游戏数量: {parent.row_count}")
        self.row_count_label.setStyleSheet(f"color: white; font-size: {int(16 * parent.scale_factor)}px;")
        self.row_count_label.setFixedHeight(int(30 * parent.scale_factor))  # 固定高度为30像素
        self.layout.addWidget(self.row_count_label)

        self.row_count_slider = QSlider(Qt.Horizontal)
        self.row_count_slider.setMinimum(4)
        self.row_count_slider.setMaximum(10)
        self.row_count_slider.setValue(parent.row_count)
        self.row_count_slider.valueChanged.connect(self.update_row_count)
        self.layout.addWidget(self.row_count_slider)

        # 添加调整缩放因数的选项
        self.scale_factor_label = QLabel(f"界面缩放因数: {parent.scale_factor:.1f}")
        self.scale_factor_label.setStyleSheet(f"color: white; font-size: {int(16 * parent.scale_factor)}px;")
        self.scale_factor_label.setFixedHeight(int(30 * parent.scale_factor))  # 固定高度为30像素
        self.layout.addWidget(self.scale_factor_label)

        self.scale_factor_slider = QSlider(Qt.Horizontal)
        self.scale_factor_slider.setMinimum(5)
        self.scale_factor_slider.setMaximum(30)
        self.scale_factor_slider.setValue(int(parent.scale_factor * 10))
        self.scale_factor_slider.valueChanged.connect(self.update_scale_factor)
        self.layout.addWidget(self.scale_factor_slider)

        # 添加重启程序按钮
        restart_button = QPushButton("重启程序")
        restart_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        restart_button.clicked.connect(self.restart_program)
        self.layout.addWidget(restart_button)

        # 添加编辑 extra_paths 的选项
        self.extra_paths_button = QPushButton("查看作用文件夹路径")
        self.extra_paths_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.extra_paths_button.clicked.connect(self.toggle_extra_paths)
        #self.layout.addWidget(self.extra_paths_button)

        # 添加刷新游戏按钮
        self.refresh_button = QPushButton("---管理---")
        self.refresh_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(15 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.refresh_button.clicked.connect(parent.refresh_games)
        self.layout.addWidget(self.refresh_button)

        # 添加切换 killexplorer 状态的按钮
        self.killexplorer_button = QPushButton(f"沉浸模式 {'√' if settings.get('killexplorer', False) else '×'}")
        self.killexplorer_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.killexplorer_button.clicked.connect(self.toggle_killexplorer)
        self.layout.addWidget(self.killexplorer_button)

        # 添加打开快捷方式文件夹按钮
        self.open_folder_button = QPushButton("打开目标文件夹")
        self.open_folder_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.open_folder_button.clicked.connect(self.open_shortcut_folder)
        #self.layout.addWidget(self.open_folder_button)

        # 添加新增快捷方式按钮
        self.add_shortcut_button = QPushButton("新增快捷方式到首文件夹")
        self.add_shortcut_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.add_shortcut_button.clicked.connect(self.add_shortcut)
        #self.layout.addWidget(self.add_shortcut_button)

        # 创建一个 QFrame 来容纳路径按钮
        self.paths_frame = QFrame(self)
        self.paths_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #333333;
                border-radius: {int(5 * parent.scale_factor)}px;
                border: {int(1 * parent.scale_factor)}px solid #444444;
            }}
        """)
        self.paths_frame.setVisible(False)  # 初始时隐藏
        self.paths_layout = QVBoxLayout(self.paths_frame)
        self.layout.addWidget(self.paths_frame)

    def toggle_killexplorer(self):
        """切换 killexplorer 状态并保存设置"""
        settings["killexplorer"] = not settings.get("killexplorer", False)
        self.killexplorer_button.setText(f"沉浸模式: {'开启' if settings['killexplorer'] else '关闭'}")
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def toggle_extra_paths(self):
        """切换显示或隐藏 extra_paths"""
        if self.paths_frame.isVisible():
            # 隐藏文件夹路径
            self.paths_frame.setVisible(False)
        else:
            # 显示文件夹路径
            self.edit_extra_paths()
            self.paths_frame.setVisible(True)

    def edit_extra_paths(self):
        """编辑 extra_paths"""
        # 清除现有的路径按钮
        for i in reversed(range(self.paths_layout.count())):
            widget = self.paths_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # 为每个路径创建一个按钮
        for path in settings["extra_paths"]:
            path_button = QPushButton(path)
            path_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #444444;
                    color: white;
                    text-align: center;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: #555555;
                }}
            """)
            path_button.clicked.connect(lambda checked, p=path, btn=path_button: self.handle_path_button_click(p, btn))
            self.paths_layout.addWidget(path_button)

    def handle_path_button_click(self, path, button):
        """处理路径按钮点击事件"""
        if button.property("clicked_once"):
            # 第二次点击，删除路径
            self.remove_path(path)
        else:
            # 第一次点击，变红色并更改文本
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: red;
                    color: white;
                    text-align: center;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
            """)
            button.setText("删除？(再次点击确认)")
            button.setProperty("clicked_once", True)

    def remove_path(self, path):
        """删除路径并更新设置"""
        if path in settings["extra_paths"]:
            settings["extra_paths"].remove(path)

            # 保存设置
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)

            # 重新加载按钮
            self.edit_extra_paths()

    def update_highlight(self):
        """更新高亮状态（当前未实现）"""
        pass

    def open_shortcut_folder(self):
        """打开 extra_paths 的第一个文件夹"""
        if settings["extra_paths"]:
            first_path = settings["extra_paths"][0]
            if os.path.exists(first_path):
                os.startfile(first_path)
            else:
                print(f"路径不存在: {first_path}")

    def add_shortcut(self):
        """新增快捷方式到 extra_paths 的第一个文件夹"""
        if not settings["extra_paths"]:
            print("没有可用的目标文件夹")
            return

        first_path = settings["extra_paths"][0]
        if not os.path.exists(first_path):
            print(f"路径不存在: {first_path}")
            return

        # 弹出文件选择框
        file_dialog = QFileDialog(self, "选择一个可执行文件", "", "Executable Files (*.exe)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
            shortcut_name = os.path.splitext(os.path.basename(selected_file))[0] + ".lnk"
            shortcut_path = os.path.join(first_path, shortcut_name)

            # 创建快捷方式
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = selected_file
            shortcut.WorkingDirectory = os.path.dirname(selected_file)
            shortcut.save()
            print(f"快捷方式已创建: {shortcut_path}")

    def update_row_count(self, value):
        """更新每行游戏数量并保存设置"""
        self.parent().row_count = value
        self.row_count_label.setText(f"每行游戏数量: {value}")
        self.parent().reload_interface()

        # 保存 row_count 设置
        settings["row_count"] = value
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def update_scale_factor(self, value):
        """更新缩放因数并保存设置"""
        scale_factor = value / 10.0
        self.parent().scale_factor = scale_factor
        self.scale_factor_label.setText(f"界面缩放因数: {scale_factor:.1f}")
        self.parent().reload_interface()
        # 保存缩放因数设置
        settings["scale_factor"] = scale_factor
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def restart_program(self):
        """重启程序"""
        QApplication.quit()
        # 只传递可执行文件的路径，不传递其他参数
        subprocess.Popen([sys.executable])



# 应用程序入口
if __name__ == "__main__":
    # 获取程序所在目录
    z_order = []
    def enum_windows_callback(hwnd, lParam):
        z_order.append(hwnd)
        return True
    win32gui.EnumWindows(enum_windows_callback, None)
    print(z_order)
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
    
    # 打印当前工作目录
    print("当前工作目录:", os.getcwd())
    app = QApplication(sys.argv)
    selector = GameSelector()
    selector.show()
    # 去除重复的路径
    unique_args = list(dict.fromkeys(sys.argv))

    # 检查启动参数，如果包含 'refresh'，则立即执行刷新逻辑
    if len(unique_args) > 1 and unique_args[1] == "refresh":
        selector.refresh_games()

    sys.exit(app.exec_())