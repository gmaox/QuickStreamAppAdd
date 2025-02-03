import subprocess
import sys
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
import os,win32api,win32event
#确保只有一个程序运行
if __name__ == '__main__':
    mutex = win32event.CreateMutex(None, False, 'ToolDesktopGameTipsWindow')
    if win32api.GetLastError() > 0:
        os._exit(0)
# 创建一个全局变量来跟踪点击次数
click_count = 0

# 在文件开头添加全局变量声明
global text_label
def on_icon_label_clicked():
    subprocess.Popen("DesktopGame.exe")
# 添加点击事件处理函数
def on_text_label_clicked():
    global click_count
    click_count += 1
    if click_count == 1:
        text_label.setText("再次点击退出提示窗口   ")  # 更改文字
    elif click_count == 2:
        os._exit(0)  # 第二次点击时退出程序

# 生成窗口函数
def create_window():
    global text_label  # 声明为全局变量
    try:
        # 创建窗口
        window = QWidget()
        window.setWindowTitle("Game Launcher")

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
        text_label = QLabel("点击手柄A键进入DesktopGame", frame)  # 这里定义 text_label
        text_label.setAlignment(Qt.AlignCenter)
        
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

        window.show()  # 显示窗口
        return window  # 返回创建的窗口实例
    except Exception as e:
        print(f"创建窗口时发生错误: {e}")
        return None  # 如果发生错误，返回 None

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)  # 初始化QApplication，传入sys.argv确保兼容命令行参数

        window = create_window()  # 创建窗口
        if window:
            sys.exit(app.exec_())  # 启动事件循环，确保程序运行，退出时正确退出
        else:
            print("窗口创建失败，程序退出。")
            sys.exit(1)  # 如果窗口创建失败，退出程序
    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        sys.exit(1)  # 发生严重错误时退出程序
