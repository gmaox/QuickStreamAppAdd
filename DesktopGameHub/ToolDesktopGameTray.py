import sys
import pystray
from PIL import Image
import subprocess
import win32process
import os
import winreg
import win32gui,win32event,win32api
import time
from threading import Thread
import psutil
import pygame  # 添加pygame导入
from pystray import MenuItem as item

#PyInstaller --add-data "fav.ico;." ToolDesktopGameTray.py -i '.\fav.ico' --uac-admin --noconsole
#PyInstaller --add-data "fav.ico;." ToolDesktopGameTipsWindow.py -i '.\fav.ico' --noconsole
#确保只有一个程序运行
if __name__ == '__main__':
    mutex = win32event.CreateMutex(None, False, 'ToolDesktopGameTray')
    if win32api.GetLastError() > 0:
        os._exit(0)
# 获取当前前台窗口
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
        return True  # 桌面


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
        with open("ToolDesktopGameTray.bat", "w", encoding="utf-8") as file:
            file.write(f'@echo off\nif "%1"=="hide" goto Begin\nstart mshta vbscript:createobject("wscript.shell").run("""%~0"" hide",0)(window.close)&&exit\n:Begin\ncd /d "{os.path.dirname(psutil.Process(os.getpid()).exe())}"\nstart {os.path.basename(psutil.Process(os.getpid()).exe())}')
        app_path = os.path.dirname(psutil.Process(os.getpid()).exe())+"\\ToolDesktopGameTray.bat"
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
                listen_gamepad()
            time.sleep(1)

    Thread(target=check_loop, daemon=True).start()

def create_window():
    subprocess.Popen(["ToolDesktopGameTipsWindow.exe"]) 
def close_window():
    try:
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == "ToolDesktopGameTipsWindow.exe":
                # 遍历所有子进程并终止它们
                for child in process.children(recursive=True):
                    child.kill()
                    print(f"已结束子进程 PID: {child.pid}")
                # 最后结束父进程
                process.kill()
                print(f"已关闭 PID {process.info['pid']} 的程序。")
                return
    except psutil.NoSuchProcess:
        print(f"未找到 ToolDesktopGameTipsWindow.exe 程序。")
    except Exception as e:
        print(f"关闭程序时发生错误: {e}")

# 监听手柄的 A 键
def listen_gamepad():
    pygame.init()  # 初始化pygame
    pygame.joystick.init()  # 初始化手柄模块

    joystick_count = pygame.joystick.get_count()
    joysticks = []
    for i in range(joystick_count):
        joystick = pygame.joystick.Joystick(i)
        joystick.init()
        joysticks.append(joystick)
        print(f"Detected joystick {i}: {joystick.get_name()}")

    create_window() # 创建窗口
    time.sleep(1)
    while has_active_window():
        for i in range(10):
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:  # 检测手柄按键按下事件
                    for joystick in joysticks:
                        if joystick.get_button(0):  # 假设 A 键是第一个按钮
                            print("A键被按下，进入游戏选择器")
                            game_path = "DesktopGame.exe"
                            if os.path.exists(game_path):
                                subprocess.Popen(game_path)
                                time.sleep(10)
                            close_window() # 关闭窗口
                            return # 退出 listen_gamepad
            time.sleep(0.1)
    print("退出桌面")
    close_window() # 退出桌面时关闭窗口


# 退出程序
def on_exit(icon, item):
    close_window()
    icon.stop()


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
    icon.run_detached()


if __name__ == "__main__":
    run_game()
    create_tray_icon()
