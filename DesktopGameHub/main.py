import sys
import json
import pygame
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QGridLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QFileDialog, QSlider, QTextEdit, QProgressBar, QScrollArea, QFrame
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess
import time
import os
import ctypes
import glob
import win32com.client  # 用于解析 .lnk 文件
from icoextract import IconExtractor, IconExtractorError
from PIL import Image, ImageDraw
from colorthief import ColorThief
from io import BytesIO

# 读取 JSON 数据
json_path = r"C:\Program Files\Sunshine\config\apps.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 筛选具有 "output_image" 路径的条目
games = [
    app for app in data["apps"]
    if "output_image" in app.get("image-path", "")
]

# 读取设置文件
settings_path = "set.json"
settings = {
    "favorites": [],
    "last_played": [],
    "more_favorites": [],
    "more_last_used": [],
    "extra_paths": []
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
        if icon_path is None:
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

class GameSelector(QWidget): 
    def __init__(self):
        super().__init__()
        self.setWindowTitle("游戏选择器")
        self.setGeometry(100, 100, 1280, 720)  # 默认窗口大小
        self.setWindowFlags(Qt.FramelessWindowHint)  # 全屏无边框
        self.showFullScreen()

        # 设置背景颜色
        self.setStyleSheet("background-color: #1e1e1e;")  # 设置深灰背景色

        # 确保窗口捕获焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # 游戏索引和布局
        self.current_index = 0  # 从第一个按钮开始
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)  # 设置按钮之间的间距

        # 从设置中读取 row_count，如果不存在则使用默认值
        self.row_count = settings.get("row_count", 6)  # 每行显示的按钮数量

        # 创建顶部布局
        self.top_layout = QHBoxLayout()
        self.top_layout.setContentsMargins(20, 0, 20, 0)  # 添加左右边距

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
        self.more_button.setFixedSize(120, 40)
        self.more_button.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border-radius: 20px; 
                border: 2px solid #888888;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 2px solid #ffff88;
            }
        """)
        self.more_button.clicked.connect(self.show_more_window)

        # 添加收藏按钮
        self.favorite_button = QPushButton("收藏 Y/△")
        self.favorite_button.setFixedSize(120, 40)
        self.favorite_button.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border-radius: 20px; 
                border: 2px solid #888888;
                color: yellow;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 2px solid #ffff88;
            }
        """)
        self.favorite_button.clicked.connect(self.toggle_favorite)

        # 创建退出按钮
        self.quit_button = QPushButton("退出 B/O")
        self.quit_button.setFixedSize(120, 40)
        self.quit_button.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border-radius: 20px; 
                border: 2px solid #888888;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 2px solid #ffff88;
            }
        """)
        self.quit_button.clicked.connect(self.close)

        # 创建游戏标题标签
        sorted_games = self.sort_games()
        if sorted_games:  # 检查是否有游戏
            self.game_name_label = QLabel(sorted_games[self.current_index]["name"])
        else:
            self.game_name_label = QLabel("没有找到游戏")  # 显示提示信息
        
        self.game_name_label.setAlignment(Qt.AlignCenter)
        self.game_name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 0 20px;
            }
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
            no_games_button.setFixedSize(700, 200)
            no_games_button.setStyleSheet("""
                QPushButton {
                    background-color: #2e2e2e; 
                    border-radius: 10px; 
                    border: 2px solid #444444;
                    color: white;
                    font-size: 30px;
                }
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
        self.settings_button.setFixedSize(120, 40)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border-radius: 20px; 
                border: 2px solid #888888;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 2px solid #ffff88;
            }
        """)
        self.settings_button.clicked.connect(self.show_settings_window)

        # 将设置按钮添加到左侧布局
        self.left_layout.addWidget(self.settings_button)

    def create_game_button(self, game, index):
        """创建游戏按钮和容器"""
        # 创建容器
        button_container = QWidget()
        button_container.setFixedSize(220, 300)  # 确保容器大小固定
        
        # 创建游戏按钮
        button = QPushButton()
        pixmap = QPixmap(game["image-path"]).scaled(200, 267, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon = QIcon(pixmap)
        button.setIcon(icon)
        button.setIconSize(pixmap.size())
        button.setFixedSize(220, 300)
        button.setStyleSheet("""
            QPushButton {
                background-color: #2e2e2e; 
                border-radius: 10px; 
                border: 2px solid #444444;
            }
            QPushButton:hover {
                border: 2px solid #888888;
            }
        """)
        button.clicked.connect(lambda checked, idx=index: self.launch_game(idx))
        
        # 创建星标（如果已收藏）
        if game["name"] in settings["favorites"]:
            star_label = QLabel("⭐", button)  # 将星标作为按钮的子控件
            star_label.setStyleSheet("""
                QLabel {
                    color: yellow;
                    font-size: 20px;
                    padding: 5px;
                    background-color: rgba(46, 46, 46, 0.7);
                    border-radius: 5px;
                }
            """)
            # 设置星标位置在左上角
            star_label.move(5, 5)  # 从 (180, 5) 改为 (5, 5)
        
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
        
        for index, button in enumerate(self.buttons):
            if index == self.current_index:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #2e2e2e; 
                        border-radius: 10px; 
                        border: 3px solid yellow;
                    }
                    QPushButton:hover {
                        border: 3px solid #ffff88;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #2e2e2e; 
                        border-radius: 10px; 
                        border: 2px solid #444444;
                    }
                    QPushButton:hover {
                        border: 2px solid #888888;
                    }
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
            self.close()

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

    def launch_game(self, index):
        """启动选中的游戏"""
        sorted_games = self.sort_games()
        game = sorted_games[index]
        game_cmd = game["cmd"]
        
        # 更新最近游玩列表
        if game["name"] in settings["last_played"]:
            settings["last_played"].remove(game["name"])
        settings["last_played"].insert(0, game["name"])
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        
        if game_cmd:
            self.close()
            subprocess.Popen(game_cmd, shell=True)

    def handle_gamepad_input(self, action):
        """处理手柄输入"""
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
            
        current_time = pygame.time.get_ticks()

        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
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
                self.close()
        elif action == 'Y':
            self.toggle_favorite()  # 收藏/取消收藏游戏
        elif action == 'X':  # X键开悬浮窗
            self.show_more_window()  # 打开悬浮窗

        # 更新最后一次按键时间
        self.last_input_time = current_time

    def sort_games(self):
        """根据收藏和最近游玩对游戏进行排序"""
        sorted_games = []
        
        # 首先添加收藏的游戏
        for game_name in settings["favorites"]:
            for game in games:
                if game["name"] == game_name:
                    sorted_games.append(game)
                    break
        
        # 然后添加最近游玩的游戏
        for game_name in settings["last_played"]:
            for game in games:
                if game["name"] == game_name and game["name"] not in settings["favorites"]:
                    sorted_games.append(game)
                    break
        
        # 最后添加其他游戏
        for game in games:
            if game["name"] not in settings["favorites"] and game["name"] not in settings["last_played"]:
                sorted_games.append(game)
        
        return sorted_games

    def toggle_favorite(self):
        """切换当前游戏的收藏状态"""
        current_game = self.sort_games()[self.current_index]
        game_name = current_game["name"]
        
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
        self.close()

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
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: 10px;
                border: 2px solid #444444;
            }
        """)
        self.setFixedSize(300, 100)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)

        self.label = QLabel("正在刷新游戏列表...")
        self.label.setStyleSheet("color: white; font-size: 16px;")
        self.layout.addWidget(self.label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444444;
                border-radius: 5px;
                background: #2e2e2e;
            }
            QProgressBar::chunk {
                background-color: #00ff00;
                width: 20px;
            }
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
        self.hat_delay = 0.05  # 将 hat 事件的防抖延迟减小到 50 毫秒
        self.last_hat_value = (0, 0)

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

                time.sleep(0.01)
            except Exception as e:
                print(f"Error in event loop: {e}")

class FloatingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: 10px;
                border: 2px solid #444444;
            }
        """)
        
        self.current_index = 0
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(5)
        self.buttons = []
        
        # 添加防抖相关属性
        self.last_input_time = 0
        self.input_delay = 200  # 设置200毫秒的防抖延迟
        
        # 读取目录中的文件
        self.files = self.get_files()
        self.create_buttons()
    
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
        for file in os.listdir('.'):
            if file.endswith(('.bat', '.url')) and not file.endswith('.lnk'):
                files.append({
                    "name": os.path.splitext(file)[0],
                    "path": file
                })
        
        # 获取额外目录中的文件
        extra_paths = settings.get("extra_paths", [])
        for path in extra_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith(('.bat', '.url')) and not file.endswith('.lnk'):
                        full_path = os.path.join(path, file)
                        files.append({
                            "name": os.path.splitext(file)[0],
                            "path": full_path
                        })
        
        return files
    
    def create_buttons(self):
        """创建按钮"""
        sorted_files = self.sort_files()
        for file in sorted_files:
            btn = QPushButton(file["name"])
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    text-align: left;
                    padding: 10px;
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)
            if file["name"] in settings.get("more_favorites", []):
                btn.setText(f"⭐ {file['name']}")
            
            self.buttons.append(btn)
            self.layout.addWidget(btn)
        
        # 添加选择文件夹按钮
        select_folder_btn = QPushButton("➕ 添加文件夹")
        select_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                text-align: left;
                padding: 10px;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)
        select_folder_btn.clicked.connect(self.select_folder)
        self.layout.addWidget(select_folder_btn)
    
    def select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            # 确保 extra_paths 存在
            if "extra_paths" not in settings:
                settings["extra_paths"] = []
            
            # 添加新路径（如果不存在）
            if folder not in settings["extra_paths"]:
                settings["extra_paths"].append(folder)
                
                # 保存设置
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4)
                
                # 重新加载按钮
                for button in self.buttons:
                    button.setParent(None)
                self.buttons.clear()
                self.create_buttons()
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
        for i, button in enumerate(self.buttons):
            if i == self.current_index:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: 10px;
                        border: 2px solid yellow;
                        font-size: 16px;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: 10px;
                        border: none;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 0.1);
                    }
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
            
        print(f"Detected controller: {self.controller_name}")

class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: 10px;
                border: 2px solid #444444;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(5)

        # 添加调整 row_count 的选项
        self.row_count_label = QLabel(f"每行游戏数量: {parent.row_count}")
        self.row_count_label.setStyleSheet("color: white; font-size: 16px;")
        self.row_count_label.setFixedHeight(30)  # 固定高度为30像素
        self.layout.addWidget(self.row_count_label)

        self.row_count_slider = QSlider(Qt.Horizontal)
        self.row_count_slider.setMinimum(4)
        self.row_count_slider.setMaximum(10)
        self.row_count_slider.setValue(parent.row_count)
        self.row_count_slider.valueChanged.connect(self.update_row_count)
        self.layout.addWidget(self.row_count_slider)

        # 添加重启程序按钮
        restart_button = QPushButton("重启程序")
        restart_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                text-align: center;
                padding: 10px;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        restart_button.clicked.connect(self.restart_program)
        self.layout.addWidget(restart_button)

        # 添加编辑 extra_paths 的选项
        self.extra_paths_button = QPushButton("查看作用文件夹路径")
        self.extra_paths_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                text-align: center;
                padding: 10px;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.extra_paths_button.clicked.connect(self.toggle_extra_paths)
        self.layout.addWidget(self.extra_paths_button)

        # 添加刷新游戏按钮
        self.refresh_button = QPushButton("---刷新游戏---")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                text-align: center;
                padding: 15px;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.refresh_button.clicked.connect(parent.refresh_games)
        self.layout.addWidget(self.refresh_button)

        # 添加打开快捷方式文件夹按钮
        self.open_folder_button = QPushButton("打开目标文件夹")
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                text-align: center;
                padding: 10px;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.open_folder_button.clicked.connect(self.open_shortcut_folder)
        self.layout.addWidget(self.open_folder_button)

        # 添加新增快捷方式按钮
        self.add_shortcut_button = QPushButton("新增快捷方式到首文件夹")
        self.add_shortcut_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                text-align: center;
                padding: 10px;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.add_shortcut_button.clicked.connect(self.add_shortcut)
        self.layout.addWidget(self.add_shortcut_button)

        # 创建一个 QFrame 来容纳路径按钮
        self.paths_frame = QFrame(self)
        self.paths_frame.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 5px;
                border: 1px solid #444444;
            }
        """)
        self.paths_frame.setVisible(False)  # 初始时隐藏
        self.paths_layout = QVBoxLayout(self.paths_frame)
        self.layout.addWidget(self.paths_frame)

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
            path_button.setStyleSheet("""
                QPushButton {
                    background-color: #444444;
                    color: white;
                    text-align: center;
                    padding: 10px;
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
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
            button.setStyleSheet("""
                QPushButton {
                    background-color: red;
                    color: white;
                    text-align: center;
                    padding: 10px;
                    border: none;
                    font-size: 16px;
                }
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

    def restart_program(self):
        """重启程序"""
        QApplication.quit()
        # 只传递可执行文件的路径，不传递其他参数
        subprocess.Popen([sys.executable])

# 应用程序入口
if __name__ == "__main__":
    # 获取程序所在目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        program_directory = os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行
        program_directory = os.path.dirname(os.path.abspath(__file__))
    
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