import os 
import time
import glob
import json
import winreg
import win32com.client  # 用于解析 .lnk 文件
from icoextract import IconExtractor, IconExtractorError
from PIL import Image, ImageDraw
from colorthief import ColorThief
from io import BytesIO
import requests
import tkinter as tk
from tkinter import filedialog
import sys, urllib3
import threading  # 导入 threading 模块
import configparser  # 导入 configparser 模块
import shutil  # 导入 shutil 模块
import re  # 导入正则表达式模块
import pythoncom
import win32api
import win32con
import win32security
import win32process
#PyInstaller main.py -i fav.ico --uac-admin --noconsole
#将两个程序使用PyInstaller打包后，将quick_add.exe和其文件夹粘贴到该main所生成的程序目录中（相同文件可跳过
#312 INFO: PyInstaller: 6.6.0, contrib hooks: 2024.4 Python: 3.8.5 Platform: Windows-10-10.0.22621-SP0
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) #禁用SSL警告
# 在文件开头添加全局变量
hidden_files = []
config = configparser.ConfigParser()
if getattr(sys, 'frozen', False):
    # 如果是打包后的应用程序
    config_file_path = os.path.join(os.path.dirname(sys.executable), 'config.ini')  # 存储在可执行文件同级目录
else:
    # 如果是开发环境
    config_file_path = 'config.ini'
onestart = True
skipped_entries = []
folder_selected = ''
close_after_completion = True  # 默认开启
pseudo_sorting_enabled = False  # 新增伪排序适应选项，默认关闭

# 重定向print函数，使输出显示在tkinter的文本框中
class RedirectPrint:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.yview(tk.END)  # 滚动到文本框底部
    def flush(self):
        pass
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
    return print(f"未检测到安装目录！")
APP_INSTALL_PATH=get_app_install_path()

def load_apps_json(json_path):
    # 加载已有的 apps.json
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 如果文件不存在，返回一个空的基础结构
        return {"env": "", "apps": []}
    
def save_apps_json(apps_json, file_path):
    # 将更新后的 apps.json 保存到文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(apps_json, f, ensure_ascii=False, indent=4)

def load_config():
    """加载配置文件"""
    global close_after_completion, pseudo_sorting_enabled, hidden_files ,folder
    config.read(config_file_path)
    folder = config.get('Settings', 'folder_selected', fallback='')
    hidden_files_str = config.get('Settings', 'hidden_files', fallback='')  # 获取隐藏的文件路径字符串
    hidden_files = hidden_files_str.split(',') if hidden_files_str else []  # 将字符串转换为列表
    close_after_completion = config.getboolean('Settings', 'close_after_completion', fallback=True)  # 获取关闭选项
    pseudo_sorting_enabled = config.getboolean('Settings', 'pseudo_sorting_enabled', fallback=False)  # 获取伪排序选项
    if os.path.exists(config_file_path)==False:
        save_config()  #没有配置文件保存下
    # 检查 folder 是否有效
    if not os.path.isdir(folder):
        print(f"无效的目录: {folder}，将使用默认目录。")
        folder = os.path.realpath(os.path.join(os.path.expanduser("~"), "Desktop")).replace("\\", "/")  # 设置为默认桌面目录
        save_config()
    return folder

def save_config():
    """保存选择的目录到配置文件"""
    try:
        global hidden_files, folder, close_after_completion, pseudo_sorting_enabled  # 添加全局变量声明
        config['Settings'] = {
            'folder_selected': folder,
            'close_after_completion': close_after_completion,
            'pseudo_sorting_enabled': pseudo_sorting_enabled,
            # 将 hidden_files 列表转换为逗号分隔的字符串
            'hidden_files': ','.join(hidden_files) if hidden_files else ''
        }
        with open(config_file_path, 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(f"保存配置文件时出错: {e}")

def delete_output_images():
    """删除 apps.json 中包含 "output_image" 的条目并重启服务"""
    apps_json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"  # 修改为你的 apps.json 文件路径
    apps_json = load_apps_json(apps_json_path)  # 加载现有的 apps.json 文件

    # 删除包含 "output_image" 的条目
    apps_json['apps'] = [entry for entry in apps_json['apps'] if "output_image" not in entry.get("image-path", "")]
    print("已删除包含 'output_image' 的条目")

    # 保存更新后的 apps.json 文件
    save_apps_json(apps_json, apps_json_path)

    # 删除 output_image 文件夹
    output_image_folder = f"{APP_INSTALL_PATH}\\assets\\output_image"
    if os.path.exists(output_image_folder):
        shutil.rmtree(output_image_folder)  # 删除文件夹及其内容
        print(f"已删除文件夹: {output_image_folder}")

    restart_service()  # 重启服务
def get_steam_base_dir():
    """
    获取Steam的安装目录
    返回: str - Steam安装路径，如果未找到则返回None
    """
    try:
        # 打开Steam的注册表键
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        
        # 获取SteamPath值
        steam_path = winreg.QueryValueEx(hkey, "SteamPath")[0]
        winreg.CloseKey(hkey)
        
        # 确保路径存在
        if os.path.exists(steam_path):
            return steam_path
            
    except WindowsError:
        return None
        
    return None
def generate_steamapp(app_id):
    # 检查图片文件是否存在
    steam_base_dir = get_steam_base_dir()
    image_path = f"{steam_base_dir}/appcache/librarycache/{app_id}_library_600x900.jpg"
    if not os.path.exists(image_path):
        image_path = f"{steam_base_dir}/appcache/librarycache/{app_id}_library_600x900_schinese.jpg"
        if not os.path.exists(image_path):
            return None  # 如果图片文件不存在，则返回None
    return image_path
# 创建Tkinter窗口
def create_gui():
    global folder_selected, close_after_completion, hidden_files
    folder_selected = load_config()  # 加载配置文件中的目录
    # 确保 folder_selected 是有效的目录
    if not os.path.isdir(folder_selected):
        folder_selected = os.path.realpath(os.path.join(os.path.expanduser("~"), "Desktop")).replace("\\", "/")  # 设置为默认桌面目录
    root = tk.Tk()
    root.title("QuickStreamAppAdd")
    root.geometry("700x400")

    # 创建一个框架用于放置文件夹选择文本框和按钮
    folder_frame = tk.Frame(root)
    folder_frame.pack(padx=10, pady=(10, 0), fill=tk.X)  # 上边距为10，下边距为0，填充X方向

    # 创建文本框显示选择的文件夹
    folder_entry = tk.Entry(folder_frame, width=50)
    folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)  # 左对齐，填充X方向并扩展
    folder_entry.insert(0, folder_selected)  # 显示加载的文件夹路径
    folder_entry.config(state=tk.DISABLED)

    def select_directory():
        global folder_selected, onestart , folder
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            print(f"选择的目录: {folder_selected}")
            text_box.delete('1.0', tk.END)
            folder_entry.config(state=tk.NORMAL)  # 允许编辑
            folder_entry.delete(0, tk.END)  # 清空文本框
            folder_entry.insert(0, folder_selected)  # 显示选择的文件夹路径
            folder = folder_selected
            save_config()  # 保存选择的目录
            onestart = True
            main()
            folder_entry.config(state=tk.DISABLED)  # 选择后再设置为不可编辑

    # 文件夹选择按钮
    folder_button = tk.Button(folder_frame, text="指定文件夹", command=select_directory)
    folder_button.pack(padx=(10, 0), side=tk.LEFT)  # 上边距为0，左对齐

    def open_folder():
        if os.path.exists(folder_selected):
            os.startfile(folder_selected)
        else:
            print(f"文件夹不存在: {folder_selected}")

    # 文件夹打开按钮
    folder_button = tk.Button(folder_frame, text="📂", command=open_folder)
    folder_button.pack(padx=(0, 0), side=tk.LEFT)  # 上边距为0，左对齐

    def open_sun_apps():
        import webbrowser
        webbrowser.open('https://localhost:47990/apps')

    # 打开sunapp管理按钮
    apps_button = tk.Button(folder_frame, text="应用管理",bg='#FFA500',command=open_sun_apps)
    apps_button.pack(padx=(0, 0), side=tk.LEFT)  # 上边距为0，左对齐

    # 创建文本框用来显示程序输出
    text_box = tk.Text(root, wrap=tk.WORD, height=15, bg='#333333', fg='white')
    text_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # 完成后关闭程序的选项
    def toggle_close_option():
        global close_after_completion
        close_after_completion = close_var.get()
        save_config()  # 保存选项状态
    def pseudo_sorting_option():
        global pseudo_sorting_enabled
        pseudo_sorting_enabled = pseudo_sorting_var.get()  # 获取伪排序选项状态
        apps_json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"  # 修改为你的 apps.json 文件路径
        apps_json = load_apps_json(apps_json_path)  # 加载现有的 apps.json 文件
        if not pseudo_sorting_enabled:
            for idx, entry in enumerate(apps_json["apps"]):
                entry["name"] = re.sub(r'^\d{2} ', '', entry["name"])
            save_apps_json(apps_json, apps_json_path)
            print("已清除伪排序标志")
        else:
            for idx, entry in enumerate(apps_json["apps"]):
                entry["name"] = re.sub(r'^\d{2} ', '', entry["name"])
                entry["name"] = f"{idx:02d} {entry['name']}"  # 在名称前加上排序数字，格式化为两位数
            save_apps_json(apps_json, apps_json_path)
            print("已添加伪排序标志")
        save_config()  # 保存选项状态

    # 创建一个框架来包含复选框
    checkbox_frame = tk.Frame(root)
    checkbox_frame.pack(side=tk.LEFT, padx=(10,0), pady=(0, 0))

    close_var = tk.BooleanVar(value=close_after_completion) # 设置复选框的初始值
    close_checkbox = tk.Checkbutton(checkbox_frame, text="完成后关闭程序", variable=close_var, command=toggle_close_option)
    close_checkbox.pack(side=tk.TOP, pady=(0, 0)) # 上边距为0

    # 在创建 GUI 时，添加伪排序选项
    pseudo_sorting_var = tk.BooleanVar(value=pseudo_sorting_enabled) # 设置复选框的初始值
    pseudo_sorting_checkbox = tk.Checkbutton(checkbox_frame, text="启用伪排序      ", variable=pseudo_sorting_var, command=pseudo_sorting_option)
    pseudo_sorting_checkbox.pack(side=tk.TOP, pady=(0, 0)) # 上边距为0
    
    def start_button_on():
        text_box.delete('1.0', tk.END)
        threading.Thread(target=main).start()
    # 开始程序按钮
    start_button = tk.Button(root, text="--点此开始程序--", command=start_button_on, width=25, height=2, bg='#333333', fg='white')  # 设置背景色为黑色，文字颜色为白色
    start_button.pack(side=tk.RIGHT, padx=(0,10), pady=3)  # 右侧对齐

    # 删除所有 output_image 条目的按钮
    delete_button = tk.Button(root, text="删除所有\n生成的sun应用", command=delete_output_images, width=15, height=2, bg='#aaaaaa', fg='white')  # 设置背景色为黑色，文字颜色为白色
    delete_button.pack(side=tk.RIGHT, padx=0, pady=(3, 3))  # 上边距为0，下边距为10

    # 在创建 GUI 时，添加转换 steam 封面按钮
    def open_steam_cover_window():
        """打开转换 steam 封面的新窗口"""
        steam_cover_window = tk.Toplevel()  # 创建一个新的顶级窗口
        steam_cover_window.title("转换 Steam 封面")
        steam_cover_window.geometry("360x250")  # 设置窗口大小

        # 在新窗口中添加内容，例如标签和按钮
        label = tk.Label(steam_cover_window, text="选择一个已导入的steam项目，使图标封面转变为游戏海报\n（转换后视作独立应用，QSAA不进行处理，删除请前往sunshine）")
        label.pack(pady=10)

        apps_json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"  # 修改为你的 apps.json 文件路径
        apps_json = load_apps_json(apps_json_path)  # 加载现有的 apps.json 文件
        apps_json_save = json.loads(json.dumps(apps_json)) # 序列化和反序列化解除嵌套
        # 只保留 detached 有效的条目
        apps_json['apps'] = [
            entry for entry in apps_json['apps'] 
            if entry.get("detached")  # 确保 detached 字段存在且有效
        ]

        # 汇集所有的 detached 字段到 items
        items = []
        for entry in apps_json['apps']:
            if isinstance(entry.get("detached"), list):  # 确保 detached 是一个列表
                items.extend(entry["detached"])  # 将所有的 detached 项添加到 items 列表中
        items = [item.strip('"') for item in items]
        # 检查每个文件是否包含 steam://rungameid/ 字段
        valid_items = []
        steam_urls = []  # 用于存储有效的 steam URL
        for item in items:
            try:
                # 检查文件扩展名
                if item.lower().endswith('.url'):
                    # 读取 .url 文件
                    with open(item, 'r', encoding='utf-8') as f:
                        content = f.readlines()
                        for line in content:
                            if line.startswith("URL="):  # 检查是否以 URL= 开头
                                url = line.split("=", 1)[1].strip()  # 获取 URL
                                if "steam://rungameid/" in url:  # 检查是否包含该字段
                                    valid_items.append(item)  # 如果包含，则保留该项
                                    steam_urls.append(re.findall(r'\d+', url))  # 存储有效的steamid
                                    break  # 找到后可以跳出循环
                else:
                    # 只读打开其他文件
                    with open(item, 'r', encoding='utf-8') as f:
                        content = f.read()  # 读取文件内容
                        if "steam://rungameid/" in content:  # 检查是否包含该字段
                            valid_items.append(item)  # 如果包含，则保留该项
            except Exception as e:
                print(f"无法读取文件 {item}: {e}")  # 处理文件读取异常

        items = valid_items  # 更新 items 列表为有效项

        # 创建 display_items 变量，将 items 中的项目转变为无后缀文件名形式
        display_items = [os.path.splitext(os.path.basename(item))[0] for item in items]  # 去掉文件后缀
        non_items = []
        for app in apps_json['apps']:
            # 如果'app'中包含'key'为'image-path'，并且该路径包含'_library_600x900'子字符串
            if 'image-path' in app and '_library_600x900' in app['image-path']:
                non_items.append(os.path.splitext(os.path.basename(app['detached'][0]))[0])
        for i in range(len(display_items)):
            # 判断当前项是否在 non_items 中
            if display_items[i] in non_items:
                # 如果存在，修改 display_items 中的该项
                display_items[i] += " -- 已转换过"
        # 创建 Listbox 组件
        listbox = tk.Listbox(steam_cover_window, height=4) 
        listbox.pack(pady=0, padx=15, fill=tk.BOTH, expand=True)

        # 将 display_items 中的内容添加到 Listbox
        for item in display_items:
            listbox.insert(tk.END, item)

        # 定义选择事件处理函数
        def on_select():
            selected_indices = listbox.curselection()  # 获取选中的索引
            if selected_indices:
                if " -- 已转换过" in display_items[selected_indices[0]]:
                    print("这个已经转换过了")
                    return  # 如果包含，直接返回
                selected_items = items[selected_indices[0]]  # 获取选中的项
                print(f"尝试转换: {selected_items} id：{int(steam_urls[selected_indices[0]][0])}") 
                steamimage = generate_steamapp(int(steam_urls[selected_indices[0]][0]))
                print(steamimage)
                for app in apps_json_save['apps']:
                    # 如果 'detached' 是一个列表，并且它有至少一个元素
                    if 'detached' in app and len(app['detached']) > 0 and app['detached'][0].strip('"') == selected_items:
                        app['image-path'] = steamimage
                        print("替换成功")
                        break
                save_apps_json(apps_json_save, apps_json_path)
                steam_cover_window.destroy()
            else:
                print("请选中一项再转换")

        # 创建一个框架用于放置按钮
        fold_frame = tk.Frame(steam_cover_window)
        fold_frame.pack(padx=10, pady=(10, 0))

        # 创建两个按钮并放置在同一行
        c_button = tk.Button(fold_frame, text="--转换--", width=25, bg='#aaaaaa', command=on_select)
        c_button.pack(side=tk.LEFT, padx=5)  # 使用 side=tk.LEFT 使按钮在同一行

        close_button = tk.Button(fold_frame, text="关闭转换窗口", width=20, bg='#aaaaaa', command=steam_cover_window.destroy)
        close_button.pack(side=tk.LEFT)  # 使用 side=tk.LEFT 使按钮在同一行

        # 添加开源地址标签
        label = tk.Label(steam_cover_window, text="开源地址：https://github.com/gmaox/QuickStreamAppAdd")
        label.pack(pady=5)  # 确保调用 pack() 方法将标签添加到窗口中

    steam_cover_button = tk.Button(root, text="转换已生成\nsteam快捷方式封面", command=open_steam_cover_window, width=15, height=2, bg='#aaaaaa', fg='white')  # 设置背景色为黑色，文字颜色为白色
    steam_cover_button.pack(side=tk.RIGHT, padx=0, pady=(3, 3))  # 上边距为0，下边距为10

    # 添加两个新按钮
    def edit_excluded_shortcuts_window():
        """打开编辑排除快捷方式的新窗口"""
        excluded_window = tk.Toplevel()
        excluded_window.title("编辑排除的快捷方式项目")
        excluded_window.geometry("360x250")
        print("--------------------------分隔线---------------------------")
        # 在新窗口中添加内容，例如标签和按钮
        label = tk.Label(excluded_window, text="选择一个列表中的项目，选中隐藏后的项目将不会添加\n（可多选，可以把办公软件和系统软件隐藏）")
        label.pack(pady=10)

        # 创建支持多选的Listbox
        listbox = tk.Listbox(excluded_window, height=4, selectmode=tk.MULTIPLE)
        listbox.pack(pady=0, padx=15, fill=tk.BOTH, expand=True)

        # 获取包含已隐藏文件的完整列表
        os.chdir(folder_selected)
        current_lnk = get_lnk_files(include_hidden=True)  # 包含已隐藏
        current_url = get_url_files(include_hidden=True)  # 包含已隐藏（正确调用方式）
        current_files = current_lnk + [url[0] for url in current_url]
        print("--------------------------分隔线---------------------------")

        # 将内容添加到Listbox并添加已隐藏标记
        for file in current_files:
            # 统一格式化显示名称（使用固定宽度字体对齐）
            max_name_len = 34
            status_suffix = " --已隐藏" if file in hidden_files else ""
            
            # 移除路径只显示文件名
            display_name = os.path.basename(file)
            
            if len(display_name) > max_name_len:
                trimmed = display_name[:max_name_len-3] + '...'
            else:
                trimmed = display_name.ljust(max_name_len)
            
            listbox.insert(tk.END, f"{trimmed}{status_suffix}")

        # 创建一个框架用于放置按钮
        fold_frame = tk.Frame(excluded_window)
        fold_frame.pack(padx=10, pady=(10, 0))

        # 创建两个按钮并放置在同一行
        def toggle_hidden():
            selected_indices = listbox.curselection()
            
            # 获取包含隐藏文件的完整列表
            current_lnk = get_lnk_files(include_hidden=True)
            current_url = [url[0] for url in get_url_files(include_hidden=True)]
            current_files = current_lnk + current_url
            
            # 更新选中项状态
            for idx in selected_indices:
                original_item = current_files[idx]  # 从最新文件列表获取
                if original_item in hidden_files:
                    hidden_files.remove(original_item)
                    print(f"已显示: {original_item}")
                else:
                    hidden_files.append(original_item)
                    print(f"已隐藏: {original_item}")
            save_config()
            
            # 完全刷新Listbox
            listbox.delete(0, tk.END)
            for file in current_files:
                # 统一格式化显示名称（使用固定宽度字体对齐）
                max_name_len = 34
                status_suffix = " --已隐藏" if file in hidden_files else ""
                
                # 移除路径只显示文件名
                display_name = os.path.basename(file)
                
                if len(display_name) > max_name_len:
                    trimmed = display_name[:max_name_len-3] + '...'
                else:
                    trimmed = display_name.ljust(max_name_len)
                
                listbox.insert(tk.END, f"{trimmed}{status_suffix}")
            # 清空文本框并运行main()
            text_box.delete('1.0', tk.END)
            global onestart
            onestart = True
            main()

        c_button = tk.Button(fold_frame, text="--显示/隐藏--", width=25, bg='#aaaaaa', command=toggle_hidden)
        c_button.pack(side=tk.LEFT, padx=5)  # 使用 side=tk.LEFT 使按钮在同一行

        close_button = tk.Button(fold_frame, text="关闭窗口", width=20, bg='#aaaaaa', command=excluded_window.destroy)
        close_button.pack(side=tk.LEFT)  # 使用 side=tk.LEFT 使按钮在同一行


    button1 = tk.Button(root, text="编辑排除\n快捷方式项目", width=11, height=2, bg='#aaaaaa', fg='white', command=edit_excluded_shortcuts_window)
    button1.pack(side=tk.RIGHT, padx=0, pady=(3, 3))

    def edit_excluded_shortcuts(): 
        global folder
        if not folder:
            print("没有可用的目标文件夹")
            return

        try:
            if getattr(sys, 'frozen', False):
                current_dir = os.path.dirname(sys.executable)
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))

            quick_add_path = os.path.join(current_dir, "quick_add.exe")
            
            if not os.path.exists(quick_add_path):
                print(f"错误：未找到quick_add.exe，请确保它与主程序在同一目录下")
                return

            # 获取当前用户的令牌
            token = win32security.OpenProcessToken(
                win32api.GetCurrentProcess(),
                win32con.TOKEN_QUERY | win32con.TOKEN_DUPLICATE | win32con.TOKEN_ASSIGN_PRIMARY
            )
            
            # 创建新的令牌
            new_token = win32security.DuplicateTokenEx(
                token,
                win32security.SecurityImpersonation,
                win32con.TOKEN_ALL_ACCESS,
                win32security.TokenPrimary
            )
            
            # 创建中等完整性级别的SID
            medium_sid = win32security.CreateWellKnownSid(win32security.WinMediumLabelSid, None)
            
            # 设置令牌的权限级别
            win32security.SetTokenInformation(
                new_token,
                win32security.TokenIntegrityLevel,
                (medium_sid, 0)  # 使用正确的SID格式
            )
            
            # 创建进程
            startup_info = win32process.STARTUPINFO()
            startup_info.dwFlags = win32con.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = win32con.SW_NORMAL
            
            process_info = win32process.CreateProcessAsUser(
                new_token,
                None,  # 应用程序名
                f'"{quick_add_path}" "{folder}"',  # 命令行
                None,  # 进程安全属性
                None,  # 线程安全属性
                False,  # 不继承句柄
                win32con.NORMAL_PRIORITY_CLASS,  # 创建标志
                None,  # 新环境
                None,  # 当前目录
                startup_info
            )
            
            # 获取进程ID
            pid = process_info[2]
            
            # 关闭不需要的句柄
            win32api.CloseHandle(process_info[1])  # 线程句柄
            win32api.CloseHandle(new_token)
            win32api.CloseHandle(token)
            
            # 等待进程结束
            while True:
                try:
                    # 尝试打开进程
                    process_handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
                    if process_handle:
                        # 获取退出码
                        exit_code = win32process.GetExitCodeProcess(process_handle)
                        if exit_code != win32con.STILL_ACTIVE:
                            # 进程已结束
                            win32api.CloseHandle(process_handle)
                            break
                        win32api.CloseHandle(process_handle)
                except:
                    # 进程已结束
                    break
                time.sleep(0.1)  # 避免CPU占用过高
            
            # 关闭进程句柄
            win32api.CloseHandle(process_info[0])
            
            text_box.delete('1.0', tk.END)
            # 运行main()
            global onestart
            onestart = True
            main()
            
        except Exception as e:
            print(f"运行quick_add.exe时出错: {e}")

    button2 = tk.Button(root, text="快速\n添加", width=6, height=2, bg='#aaaaaa', fg='white') 
    button2.pack(side=tk.RIGHT, padx=1, pady=(3, 3))
    button2.config(command=edit_excluded_shortcuts)

    # 重定向 stdout 和 stderr 到文本框
    redirector = RedirectPrint(text_box)
    sys.stdout = redirector  # 重定向标准输出
    sys.stderr = redirector  # 重定向错误输出
    main()
    root.mainloop()

def get_lnk_files(include_hidden=False):
    # 获取当前工作目录下的所有 .lnk 文件
    lnk_files = glob.glob("*.lnk")
    valid_lnk_files = []
    
    # 过滤掉指向文件夹的快捷方式和已隐藏文件
    for lnk in lnk_files:
        try:
            # 检查是否在隐藏列表中（当不需要包含隐藏文件时）
            if not include_hidden and lnk in hidden_files:
                continue
                
            target_path = get_target_path_from_lnk(lnk)
            if os.path.isdir(target_path):
                print(f"跳过文件夹快捷方式: {lnk} -> {target_path}")
            else:
                valid_lnk_files.append(lnk)
        except Exception as e:
            print(f"无法获取 {lnk} 的目标路径: {e}")
    
    if include_hidden:
        print("找到所有.lnk文件（包含已隐藏）:")
    else:
        print("找到的可见.lnk文件:")
        
    for idx, lnk in enumerate(valid_lnk_files):
        print(f"{idx+1}. {lnk}")
    return valid_lnk_files

def get_target_path_from_lnk(lnk_file):
    pythoncom.CoInitialize()
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

def create_image_with_icon(exe_path, output_path ,idx):
    global skipped_entries  # 声明使用全局变量
    try:
        # 检查是否为 .ico 文件
        if exe_path.lower().endswith('.ico'):
            icon_path = exe_path  # 直接使用 .ico 文件
        else:
            icon_path = extract_icon(exe_path)
            if icon_path is None:
                print(f"无法提取图标: {exe_path}")
                return

        with Image.open(icon_path) as icon_img:
            # 确保图标是RGBA模式
            if icon_img.mode != 'RGBA':
                icon_img = icon_img.convert('RGBA')

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
            img.paste(icon_img, (icon_x, icon_y), icon_img.convert('RGBA'))

            img.save(output_path, format="PNG")
            print(f"图像已保存至 {output_path}")

        try:
            if not exe_path.lower().endswith('.ico'):
                os.remove(icon_path)  # 仅在提取图标时删除临时文件
            print(f"\n {exe_path}\n")
        except PermissionError:
            print(f"无法删除临时图标文件: {icon_path}. 稍后再试.")
            time.sleep(1)
            os.remove(icon_path)

    except Exception as e:
        print(f"创建图像时发生异常，跳过此文件: {exe_path}\n异常信息: {e}")
        skipped_entries.append(idx)  # 记录异常条目


def generate_app_entry(lnk_file, index):
    # 跳过已记录的异常条目
    if index in skipped_entries:
        print(f"跳过已记录的异常条目: {lnk_file}")
        return None  # 返回 None 以表示跳过该条目

    # 判断 lnk_file 是否为 .url 文件
    if lnk_file.lower().endswith('.url'):
        entry = {
            "name": os.path.splitext(lnk_file)[0],  # 使用快捷方式文件名作为名称
            "output": "",
            "cmd": "",
            "exclude-global-prep-cmd": "false",
            "elevated": "false",
            "auto-detach": "true",
            "wait-all": "true",
            "exit-timeout": "5",
            "menu-cmd": "",
            "image-path": f"{APP_INSTALL_PATH}\\assets\\output_image\\output_image{index}.png",
            "detached": [
                f"\"{os.path.abspath(lnk_file)}\""
            ]
        }
    else:
        # 为每个快捷方式生成对应的 app 条目
        entry = {
            "name": os.path.splitext(lnk_file)[0],  # 使用快捷方式文件名作为名称
            "output": "",
            "cmd": f"\"{os.path.abspath(lnk_file)}\"",
            "exclude-global-prep-cmd": "false",
            "elevated": "false",
            "auto-detach": "true",
            "wait-all": "true",
            "exit-timeout": "5",
            "menu-cmd": "",
            "image-path": f"{APP_INSTALL_PATH}\\assets\\output_image\\output_image{index}.png",
        }
    return entry

def add_entries_to_apps_json(valid_lnk_files, apps_json, modified_target_paths,image_target_paths):
    
    # 为每个有效的快捷方式生成新的条目并添加到 apps 中
    for index, lnk_file in enumerate(valid_lnk_files):
        # 检查是否在 modified_target_paths 中标记为存在
        if any(target_path == lnk_file and is_existing for target_path, is_existing in modified_target_paths):
            print(f"跳过已存在的条目: {lnk_file}")
            continue  # 跳过已有条目的处理
        matching_image_entry = next((item for item in image_target_paths if item[0] == lnk_file), None)
        app_entry = generate_app_entry(lnk_file, matching_image_entry[1])
        if app_entry:  # 仅在 app_entry 不为 None 时添加
            apps_json["apps"].append(app_entry)
            print(f"新加入: {lnk_file}")

def remove_entries_with_output_image(apps_json, base_names):
    # 删除 apps.json 中包含 "output_image" 的条目，且 cmd 和 detached 字段不在 base_names 中
    apps_json['apps'] = [
        entry for entry in apps_json['apps'] 
        if "output_image" not in entry.get("image-path", "") or 
           (entry.get("cmd") and os.path.basename(entry["cmd"].strip('"')) in base_names) or 
           (entry.get("detached") and any(os.path.basename(detached_item.strip('"')) in base_names for detached_item in entry["detached"]))
    ]
    print("已删除不符合条件的条目")


def get_url_files(include_hidden=False):
    # 获取当前工作目录下的所有 .url 文件
    url_files = glob.glob("*.url")
    valid_url_files = []
    
    for url in url_files:
        try:
            # 检查是否在隐藏列表中（当不需要包含隐藏文件时）
            if not include_hidden and url in hidden_files:
                continue
                
            target_path = get_url_target_path(url)
            valid_url_files.append((url, target_path))
        except Exception as e:
            print(f"无法获取 {url} 的目标路径: {e}")
    
    print("找到的 .url 文件:")
    for idx, (url, target) in enumerate(valid_url_files):
        print(f"{idx+1}. {url}")
    return valid_url_files

def get_url_target_path(url_file):
    # 读取 .url 文件并获取目标路径
    with open(url_file, 'r', encoding='utf-8') as f:
        content = f.readlines()
    
    for line in content:
        if line.startswith("IconFile="):
            icon_file = line.split("=", 1)[1].strip()
            return icon_file  # 返回图标文件路径或可执行文件路径
    raise ValueError("未找到 IconFile 路径")

def restart_service():
    """
    发送POST请求以重启服务
    """
    try:
        response = requests.post('https://localhost:47990/api/restart', verify=False)
        if response.status_code == 200:
            print("sunshine服务重启")
        else:
            print(f"sunshine服务重启")
    except requests.exceptions.RequestException as e:
        print(f"sunshine服务已重启")

def find_unused_index(apps_json, image_target_paths):
    existing_indices = {int(entry["image-path"].split("output_image")[-1].split(".png")[0]) for entry in apps_json['apps'] if "output_image" in entry.get("image-path", "")}
    existing_indices = existing_indices.union({ima[1] for ima in image_target_paths})  # 使用 union 合并集合
    index = 0
    while index in existing_indices:
        index += 1
    return index

def main():
    global folder_selected, onestart, close_after_completion, pseudo_sorting_enabled, lnkandurl_files
    # 获取当前目录下所有有效的 .lnk 和 .url 文件
    os.chdir(folder_selected)  # 设置为用户选择的目录
    lnk_files = get_lnk_files()
    url_files = get_url_files()
    
    target_paths = [get_target_path_from_lnk(lnk) for lnk in lnk_files]
    target_paths += [url[1] for url in url_files]  # 添加 .url 文件的目标路径
    lnkandurl_files = lnk_files + [url[0] for url in url_files]

    # 确保目标文件夹存在
    output_folder = f"{APP_INSTALL_PATH}\\assets\\output_image"  # 更改为适当的文件夹

    # 加载现有的 apps.json 文件
    apps_json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"  # 修改为你的 apps.json 文件路径
    print(f"该应用会创建《{output_folder}》文件夹来存放输出的图像\n修改以下文件《{apps_json_path}》来添加sunshine应用程序")
    if onestart:
        onestart = False
        return
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    apps_json = load_apps_json(apps_json_path)

    # 检查 target_paths 是否与 apps.json 中的条目名称相同
    existing_names1 = {os.path.splitext(os.path.basename(entry.get('cmd', '')))[0] for entry in apps_json['apps']}  # 处理 cmd 字段
    existing_names2 = {os.path.splitext(os.path.basename(detached_item))[0] for entry in apps_json['apps'] if 'detached' in entry for detached_item in entry['detached']}  # 处理 detached 字段
    modified_target_paths = []  # 确保在这里初始化

    for idx, target_path in enumerate(target_paths):
        name = lnkandurl_files[idx]  # 获取文件名作为名称
        base_name = name.rsplit('.', 1)[0]
        # 修正条件判断，确保正确识别 .lnk 和 .url 文件
        if base_name in existing_names1 or base_name in existing_names2:
            modified_target_paths.append((target_path, True))  # 添加特殊标识符
        else:
            modified_target_paths.append((target_path, False))  # 不存在则标记为 False

    # 删除不存在的条目
    remove_entries_with_output_image(apps_json, lnkandurl_files)
    image_target_paths = []
    print("--------------------生成封面--------------------")
    # 创建并处理图像
    for idx, (target_path, is_existing) in enumerate(modified_target_paths):
        if is_existing:
            print(f"跳过已存在的条目: {target_path}")
            continue  # 跳过已有条目的处理
        output_index = find_unused_index(apps_json, image_target_paths)  # 获取未使用的索引
        image_target_paths.append((lnkandurl_files[idx], output_index))
        output_path = os.path.join(output_folder, f"output_image{output_index}.png")
        create_image_with_icon(target_path, output_path, idx)

    # 转换 modified_target_paths
    modified_target_paths1 = modified_target_paths
    modified_target_paths = []
    for idx, (target_path, is_existing) in enumerate(modified_target_paths1):
        modified_target_paths.append((lnkandurl_files[idx], is_existing))
    
    print("--------------------更新配置--------------------")
    # 添加新的快捷方式条目
    add_entries_to_apps_json(lnk_files, apps_json, modified_target_paths, image_target_paths)

    # 处理 .url 文件的条目
    for index, (url_file, target_path) in enumerate(url_files, start=len(lnk_files)):
        if any(target_path == url_file and is_existing for target_path, is_existing in modified_target_paths):
            print(f"跳过已存在的条目: {url_file}")
            continue  # 跳过已有条目的处理
        matching_image_entry = next((item for item in image_target_paths if item[0] == url_file), None)
        app_entry = generate_app_entry(url_file, matching_image_entry[1])
        if app_entry:  # 仅在 app_entry 不为 None 时添加
            apps_json["apps"].append(app_entry)
            print(f"新加入: {url_file}")

    # 如果启用了伪排序，更新条目的名称
    if pseudo_sorting_enabled:
        for idx, entry in enumerate(apps_json["apps"]):
            # 去掉之前的序号
            entry["name"] = re.sub(r'^\d{2} ', '', entry["name"])  # 去掉开头的两位数字和空格
            entry["name"] = f"{idx:02d} {entry['name']}"  # 在名称前加上排序数字，格式化为两位数
        print("已添加伪排序标志")

    # 保存更新后的 apps.json 文件
    save_apps_json(apps_json, apps_json_path)
    restart_service()
    if close_after_completion:
        os._exit(0)  # 正常退出

if __name__ == "__main__":
    create_gui()  # 启动Tkinter界面
