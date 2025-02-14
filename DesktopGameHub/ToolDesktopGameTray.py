import pystray
from PIL import Image
import subprocess
import win32process
import os,sys,multiprocessing
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
import win32gui,win32event,win32api
import time
from threading import Thread
import psutil
import pygame  # 添加pygame导入
from pystray import MenuItem as item

#PyInstaller --add-data "fav.ico;." ToolDesktopGameTray.py -i '.\fav.ico' --uac-admin --noconsole
#PyInstaller --add-data "fav.ico;." ToolDesktopGameTipsWindow.py -i '.\fav.ico' --noconsole
def has_active_window():
    # 获取当前活动窗口句柄
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        print("未找到活动窗口")
        return False  # 未找到活动窗口
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    process = psutil.Process(pid)
    exe_path = process.exe()
    exe_name = os.path.basename(exe_path)

    if exe_name == "explorer.exe":
        print("当前窗口为桌面")
        class_name = win32gui.GetClassName(hwnd)
        print("窗口类名:", class_name)
        if class_name == 'Shell_TrayWnd' or  class_name == 'WorkerW' or class_name == 'Progman':  #任务栏/桌面区域/桌面
            print(f"当前窗口已全屏{exe_name} 类名{class_name}")
            return True
        else:
            print(f"当前窗口非全屏 {exe_name} 类名{class_name}")
            return False


# 检查程序是否设置为开机自启
def is_startup_enabled():
    command = ['schtasks', '/query', '/tn', "ToolDesktopGameTray"]
    try:
        # 如果任务存在，将返回0
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


# 设置程序开机自启
def set_startup_enabled(enable):
    if enable:
        app_path = sys.executable
        command = [
            'schtasks', '/create', '/tn', "ToolDesktopGameTray", '/tr', f'"{app_path}"',
            '/sc', 'onlogon', '/rl', 'highest', '/f'
        ]
        subprocess.run(command, check=True)
    else:
        try:
            command = ['schtasks', '/delete', '/tn', "ToolDesktopGameTray", '/f']
            subprocess.run(command, check=True)
        except FileNotFoundError:
            pass


# 启动游戏并监听窗口
def run_game():
    def check_loop():
        while True:
            if has_active_window():
                for process in psutil.process_iter(['pid', 'name']):
                    if process.info['name'] == "DesktopGame.exe":
                        break
                else:
                    listen_gamepad()
            time.sleep(1)

    Thread(target=check_loop, daemon=True).start()

def create_window():
    parent_conn.send(True)
def close_window():
    parent_conn.send(False)

# 监听手柄的 A 键
def listen_gamepad():
    pygame.init()  # 初始化pygame
    pygame.joystick.init()  # 初始化手柄模块

    def detect_joysticks():
        joysticks = []
        joystick_count = pygame.joystick.get_count()
        for i in range(joystick_count):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            joysticks.append(joystick)
            print(f"Detected joystick {i}: {joystick.get_name()}")
        return joysticks

    joysticks = detect_joysticks()
    create_window()  # 创建窗口
    time.sleep(1)
    while has_active_window():
        for i in range(5):
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    joysticks = detect_joysticks()  # 更新手柄列表
                elif event.type == pygame.JOYBUTTONDOWN:  # 检测手柄按键按下事件
                    for joystick in joysticks:
                        if joystick.get_button(0):  # 假设 A 键是第一个按钮
                            print("A键被按下，进入游戏选择器")
                            game_path = "DesktopGame.exe"
                            if os.path.exists(game_path):
                                subprocess.Popen(game_path)
                                time.sleep(10)
                            close_window()  # 关闭窗口
                            return  # 退出 listen_gamepad
            time.sleep(0.1)
    print("退出桌面")
    close_window()  # 关闭窗口


# 退出程序
def on_exit(icon, item):
    icon.stop()
    #parent_conn.send(False)  # 关闭提示窗口
    p.terminate()  # 终止子进程
    p.join()  # 等待子进程结束
    os._exit(0)


# 切换开机自启
def on_toggle_startup(icon, item):
    enable = not item.checked
    set_startup_enabled(enable)
    item.checked = enable  # 更新复选框的状态

# 创建悬浮窗
def create_tray_icon():
    image = Image.open(os.path.join(os.path.dirname(__file__), "fav.ico"))

    # 创建复选框菜单项来控制开机自启
    menu = pystray.Menu(
        pystray.MenuItem('openDesktopGame', lambda:subprocess.Popen("DesktopGame.exe"), default=True ,visible=False),
        pystray.MenuItem('开机自启', on_toggle_startup, checked=lambda item: is_startup_enabled()),
        pystray.MenuItem('退出', on_exit)
    )

    # 创建并显示悬浮窗
    icon = pystray.Icon("game_launcher", image, "单击启动DesktopGame", menu)
    icon.run()
#子进程1：创建提示窗口
def tipswindow(conn):
    global click_count, text_label, window  # 添加window到全局变量
    print(f"Worker received: {conn.recv()}")
    click_count = 0
    
    def window_control_thread():
        while True:
            try:
                show_window = conn.recv()
                if show_window:
                    window.show()
                else:
                    window.hide()
            except EOFError:
                break
    
    def on_icon_label_clicked():
        subprocess.Popen(['start', 'DesktopGame.exe'], shell=True)
        
    def on_text_label_clicked():
        global click_count
        click_count += 1
        if click_count == 1:
            text_label.setText("再次点击退出提示窗口   ")
        elif click_count == 2:
            os._exit(0)
            
    def create_window():
        global text_label, window  # 修改这里
        try:
            # 创建窗口
            window = QWidget()
            window.setWindowTitle("Game Launcher")
            window.setStyleSheet("background-color: #1e1e1e;")  # 设置深灰背景色
            # 设置窗口无边框，设置窗口置顶, 设置鼠标穿透
            window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            # window.setAttribute(Qt.WA_TransparentForMouseEvents)
            # 设置窗口透明度
            window.setWindowOpacity(0.6)

            # 获取屏幕尺寸
            screen = QApplication.desktop().screenGeometry()
            window_width = 300  # 增加窗口宽度，便于查看
            window_height = 50  # 增加窗口高度，便于查看
            x = ((screen.width() - window_width) // 2)-50
            y = 0  # 顶部
            window.setGeometry(x, y, window_width, window_height)

            # 在窗口中显示图标和文字
            icon_label = QLabel()
            icon_path = os.path.join(os.path.dirname(__file__), "fav.ico")  # 获取图标路径
            if os.path.exists(icon_path):
                icon_pixmap = QPixmap(icon_path)
                icon_pixmap = icon_pixmap.scaled(50, 50, Qt.KeepAspectRatio)  # 缩放图标，保持宽高比
                icon_label.setPixmap(icon_pixmap)
                print(f"图标加载成功: {icon_path}")
            else:
                print(f"图标文件未找到: {icon_path}")

            icon_label.setAlignment(Qt.AlignLeft)  # 将图标左对齐

            # 文字
            frame = QWidget()
            frame.setStyleSheet("background-color: lightgray;")
            text_label = QLabel("点击手柄进入DesktopGame", frame)  # 这里定义 text_label
            text_label.setAlignment(Qt.AlignCenter)
            text_label.setStyleSheet("color: White;")  # 设置文字颜色

            # Set layout for the frame
            frame_layout = QHBoxLayout(frame)
            frame_layout.addWidget(text_label)
            frame.setLayout(frame_layout)

            # 放大文字
            font = QFont()
            font.setPointSize(18)  # 设置字体大小为 18
            text_label.setFont(font)

            # 水平布局，图标和文字并排
            layout = QHBoxLayout()
            layout.addWidget(icon_label)  # 添加图标
            layout.addWidget(text_label)  # 添加文字
            window.setLayout(layout)

            # 连接点击事件
            text_label.mousePressEvent = lambda event: on_text_label_clicked()
            icon_label.mousePressEvent = lambda event: on_icon_label_clicked()

            window.show() 
            return window
        except Exception as e:
            print(f"创建窗口时发生错误: {e}")
            return None

    try:
        app = QApplication(sys.argv)
        
        window = create_window()
        if window:
            # 创建并启动控制线程
            Thread(target=window_control_thread, daemon=True).start()
            
            sys.exit(app.exec_())
        else:
            print("窗口创建失败，程序退出。")
            sys.exit(1)
    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        sys.exit(1)
#线程：设置窗口置顶
def topmostset():
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

    # 获取窗口句柄
    def get_hwnd(title):
        hwnd = FindWindow(None, title)  # 根据窗口标题获取句柄
        return hwnd

    # 定时器回调函数
    def set_topmost_periodically(hwnd, interval):
        # 设置窗口为最上层
        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        time.sleep(0.3)
        screen_width, screen_height = pyautogui.size()
        pyautogui.FAILSAFE = False
        # 设置右下角坐标
        right_bottom_x = screen_width - 1  # 最右边
        right_bottom_y = screen_height - 1  # 最底部

        # 移动鼠标到屏幕右下角并进行右键点击
        pyautogui.rightClick(right_bottom_x, right_bottom_y)
        time.sleep(1)
        hwnda = win32gui.GetForegroundWindow()
        if win32gui.GetWindowText(hwnda) != "游戏选择器":
            print("游戏窗口未激活")
            set_topmost_periodically(hwnd, interval)
        else:
            while True:
                for process in psutil.process_iter(['pid', 'name']):
                    if process.info['name'] == "DesktopGame.exe":
                        break
                else:
                    main()
                time.sleep(1)
    def main():
        # 设置窗口标题
        window_title = "游戏选择器"  # 例如这里假设你要将记事本窗口置顶
        hwnd = get_hwnd(window_title)
        if hwnd != 0:
            print(f"找到窗口句柄：{hwnd}")
            interval = 0.5  # 每0.5秒更新一次
            set_topmost_periodically(hwnd, interval)
        time.sleep(1)
        main()
    main()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    # 检查程序是否已经运行
    mutex = win32event.CreateMutex(None, False, 'ToolDesktopGameTray')
    if win32api.GetLastError() > 0:
        os._exit(0)
    # 获取程序所在目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        program_directory = os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行
        program_directory = os.path.dirname(os.path.abspath(__file__))
    # 将工作目录更改为上一级目录
    os.chdir(program_directory)
    # 创建子进程
    multiprocessing.freeze_support()
    parent_conn, child_conn = multiprocessing.Pipe()
    p = multiprocessing.Process(target=tipswindow, args=(child_conn,))
    p.start()
    Thread(target=topmostset, daemon=True).start()
    run_game()
    create_tray_icon()
