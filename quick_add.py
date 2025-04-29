import os
import sys
import tkinter
from tkinterdnd2 import *
from tkinter import filedialog
import win32com.client
import shutil
import json
#PyInstaller -F quick_add.py --noconsole --additional-hooks-dir=.
class RedirectPrint:
    def __init__(self, label):
        self.label = label
        self.buffer = ""

    def write(self, text):
        self.buffer += text
        self.label.config(text=self.buffer)
        self.label.update()

    def flush(self):
        pass

def main():
    # 从命令行参数获取目标文件夹
    if len(sys.argv) < 2:
        print("错误：未提供目标文件夹路径")
        return
        
    target_folder = sys.argv[1]
    if not os.path.exists(target_folder):
        print(f"错误：目标文件夹不存在: {target_folder}")
        return

    # 创建新窗口
    add_window = TkinterDnD.Tk()
    add_window.title("快速添加")
    add_window.geometry("360x250")
    add_window.attributes("-topmost", True)  # 窗口始终显示于最前端
    # 创建标签用于显示拖放区域
    drop_label = tkinter.Label(add_window, text="拖放文件到这里\n或点击下方按钮选择文件", 
                         relief="solid", borderwidth=2, width=45, height=9)
    drop_label.pack(pady=20)

    # 重定向输出到drop_label
    redirector = RedirectPrint(drop_label)
    sys.stdout = redirector
    sys.stderr = redirector

    # 处理文件的函数
    def process_file(file_path):
        if not file_path:
            return

        # 检查文件扩展名
        if not file_path.lower().endswith('.exe'):
            print("请选择.exe文件")
            return

        shortcut_name = os.path.splitext(os.path.basename(file_path))[0] + ".lnk"
        shortcut_path = os.path.join(target_folder, shortcut_name)

        # 如果是lnk文件，直接复制
        if file_path.endswith('.lnk'):
            shutil.copy(file_path, shortcut_path)
        else:
            # 创建新的快捷方式
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = file_path
            shortcut.WorkingDirectory = os.path.dirname(file_path)
            shortcut.save()
        
        print(f"快捷方式已创建: {shortcut_path}")
        add_window.destroy()

    # 创建按钮用于选择文件
    def select_file():
        selected_file = filedialog.askopenfilename(
            title="选择一个exe可执行文件，生成快捷方式到目录文件夹",
            filetypes=[("Executable Files", "*.exe")]
        )
        if selected_file:
            process_file(selected_file)

    select_button = tkinter.Button(add_window, text="选择文件", width=25, bg='#aaaaaa', command=select_file)
    select_button.pack(side=tkinter.LEFT, padx=5)

    # 创建关闭按钮
    close_button = tkinter.Button(add_window, text="关闭", width=20, bg='#aaaaaa', command=add_window.destroy)
    close_button.pack(side=tkinter.LEFT)

    # 实现拖放功能
    def on_drop(event):
        try:
            # 获取拖放的文件路径
            file_path = event.data.strip('{}')  # 移除可能的大括号
            if not file_path:
                return
                
            # 处理多个文件的情况（只取第一个）
            if isinstance(file_path, tuple):
                file_path = file_path[0]
                
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                return
                
            if file_path.lower().endswith('.exe') or file_path.lower().endswith('.lnk'):
                process_file(file_path)
            else:
                print("只能处理 .exe 或 .lnk 文件")
        except Exception as e:
            print(f"处理拖放文件时出错: {e}")

    # 设置拖放目标
    try:
        add_window.drop_target_register(DND_FILES)
        add_window.dnd_bind('<<Drop>>', on_drop)
    except Exception as e:
        print(f"初始化拖放功能时出错: {e}")
        # 如果拖放功能初始化失败，禁用拖放功能
        drop_label.config(text="拖放功能不可用\n请使用选择文件按钮")

    add_window.mainloop()

if __name__ == "__main__":
    main() 