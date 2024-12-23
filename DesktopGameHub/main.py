import sys
import json
import pygame
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QGridLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QFileDialog, QSlider, QTextEdit
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess
import time
import os

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
try:
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {
            "favorites": [],
            "last_played": [],
            "more_favorites": [],
            "more_last_used": [],
            "extra_paths": []
        }
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
except Exception as e:
    print(f"Error loading settings: {e}")
    settings = {
        "favorites": [],
        "last_played": [],
        "more_favorites": [],
        "more_last_used": [],
        "extra_paths": []
    }

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
        self.game_name_label = QLabel(sorted_games[self.current_index]["name"])
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
        sorted_games = self.sort_games()
        for index, game in enumerate(sorted_games):
            button = self.create_game_button(game, index)
            self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
            self.buttons.append(button)

        # 获取排序后的游戏列表
        sorted_games = self.sort_games()
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.top_layout)  # 添加顶部布局
        main_layout.addLayout(self.grid_layout)  # 添加游戏按钮网格
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
        sorted_games = self.sort_games()  # 获取排序后的游戏列表
        
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
        
        # 更新顶部游戏名称，使用排序后的游戏列表
        self.game_name_label.setText(sorted_games[self.current_index]["name"])

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
        self.buttons.append(select_folder_btn)
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
                padding: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        restart_button.clicked.connect(self.restart_program)
        self.layout.addWidget(restart_button)

        # 添加编辑 extra_paths 的选项
        self.extra_paths_button = QPushButton("编辑文件夹路径")
        self.extra_paths_button.setStyleSheet("""
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
        self.extra_paths_button.clicked.connect(self.edit_extra_paths)
        self.layout.addWidget(self.extra_paths_button)

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
        subprocess.Popen(sys.argv)

    def edit_extra_paths(self):
        """编辑 extra_paths"""
        extra_paths_text = "\n".join(settings["extra_paths"])
        self.extra_paths_textbox = QTextEdit(extra_paths_text)
        self.extra_paths_textbox.setStyleSheet("color: white; background-color: #2e2e2e;")
        self.layout.addWidget(self.extra_paths_textbox)

        save_button = QPushButton("保存")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                padding: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        save_button.clicked.connect(self.save_extra_paths)
        self.layout.addWidget(save_button)

    def save_extra_paths(self):
        """保存 extra_paths"""
        new_paths = self.extra_paths_textbox.toPlainText().split("\n")
        settings["extra_paths"] = [path.strip() for path in new_paths if path.strip()]

        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

        # 重新加载按钮
        self.parent().reload_interface()

    def update_highlight(self):
        """更新高亮状态（当前未实现）"""
        pass


# 应用程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    selector = GameSelector()
    selector.show()
    sys.exit(app.exec_())
