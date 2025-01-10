import os 
import time
import glob
import json
import win32com.client  # 用于解析 .lnk 文件
from icoextract import IconExtractor, IconExtractorError
from PIL import Image, ImageDraw
from colorthief import ColorThief
from io import BytesIO
import requests
import tkinter as tk
from tkinter import filedialog
import sys
import threading  # 导入 threading 模块
import configparser  # 导入 configparser 模块
import shutil  # 导入 shutil 模块

# 在文件开头添加全局变量

config = configparser.ConfigParser()
config_file_path = 'config.ini'  # 配置文件路径
onestart = True
skipped_entries = []
#folder_selected = os.path.join(os.path.expanduser("~"), "Desktop")
folder_selected = ""
close_after_completion = True  # 默认开启

# 重定向print函数，使输出显示在tkinter的文本框中
class RedirectPrint:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.original_stdout = sys.stdout
    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.yview(tk.END)  # 滚动到文本框底部
    def flush(self):
        pass

def load_config():
    """加载配置文件"""
    if os.path.exists(config_file_path):
        config.read(config_file_path)
        folder = config.get('Settings', 'folder_selected', fallback='')
        global close_after_completion
        close_after_completion = config.getboolean('Settings', 'close_after_completion', fallback=True)  # 获取关闭选项
        return folder
    return ''

def save_config(folder):
    """保存选择的目录到配置文件"""
    config['Settings'] = {
        'folder_selected': folder,
        'close_after_completion': close_after_completion  # 保存关闭选项
    }
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

def delete_output_images():
    """删除 apps.json 中包含 "output_image" 的条目并重启服务"""
    apps_json_path = r"C:\Program Files\Sunshine\config\apps.json"  # 修改为你的 apps.json 文件路径
    apps_json = load_apps_json(apps_json_path)  # 加载现有的 apps.json 文件

    # 删除包含 "output_image" 的条目
    apps_json['apps'] = [entry for entry in apps_json['apps'] if "output_image" not in entry.get("image-path", "")]
    print("已删除包含 'output_image' 的条目")

    # 保存更新后的 apps.json 文件
    save_apps_json(apps_json, apps_json_path)

    # 删除 output_image 文件夹
    output_image_folder = r"C:\Program Files\Sunshine\assets\output_image"
    if os.path.exists(output_image_folder):
        shutil.rmtree(output_image_folder)  # 删除文件夹及其内容
        print(f"已删除文件夹: {output_image_folder}")

    restart_service()  # 重启服务

# 创建Tkinter窗口
def create_gui():
    global folder_selected, close_after_completion
    folder_selected = load_config()  # 加载配置文件中的目录
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
        global folder_selected, onestart
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            print(f"选择的目录: {folder_selected}")
            text_box.delete('1.0', tk.END)
            folder_entry.config(state=tk.NORMAL)  # 允许编辑
            folder_entry.delete(0, tk.END)  # 清空文本框
            folder_entry.insert(0, folder_selected)  # 显示选择的文件夹路径
            save_config(folder_selected)  # 保存选择的目录
            onestart = True
            main()
            folder_entry.config(state=tk.DISABLED)  # 选择后再设置为不可编辑

    # 文件夹选择按钮
    folder_button = tk.Button(folder_frame, text="选择文件夹", command=select_directory)
    folder_button.pack(padx=(10, 0), side=tk.LEFT)  # 上边距为0，左对齐

    # 创建文本框用来显示程序输出
    text_box = tk.Text(root, wrap=tk.WORD, height=15, bg='#333333', fg='white')
    text_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # 完成后关闭程序的选项
    def toggle_close_option():
        global close_after_completion
        close_after_completion = close_var.get()
        save_config(folder_selected)  # 保存选项状态

    close_var = tk.BooleanVar(value=close_after_completion)  # 设置复选框的初始值
    close_checkbox = tk.Checkbutton(root, text="完成后关闭程序", variable=close_var, command=toggle_close_option)
    close_checkbox.pack(side=tk.LEFT,pady=(0, 10))  # 上边距为0，下边距为10
    def start_button_on():
        text_box.delete('1.0', tk.END)
        threading.Thread(target=main).start()
    # 开始程序按钮
    start_button = tk.Button(root, text="--开始程序--", command=start_button_on, width=25, height=2, bg='#333333', fg='white')  # 设置背景色为黑色，文字颜色为白色
    start_button.pack(side=tk.RIGHT, padx=3, pady=3)  # 右侧对齐

    # 删除所有 output_image 条目的按钮
    delete_button = tk.Button(root, text="删除所有\n生成的sun应用", command=delete_output_images, width=15, height=2, bg='#aaaaaa', fg='white')  # 设置背景色为黑色，文字颜色为白色
    delete_button.pack(side=tk.RIGHT, pady=(3, 3))  # 上边距为0，下边距为10

    # 在GUI启动时重定向print
    sys.stdout = RedirectPrint(text_box)
    main()
    root.mainloop()

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

def load_apps_json(json_path):
    # 加载已有的 apps.json
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 如果文件不存在，返回一个空的基础结构
        return {"env": "", "apps": []}

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
            "image-path": f"C:\\Program Files\\Sunshine\\assets\\output_image\\output_image{index}.png",
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
            "image-path": f"C:\\Program Files\\Sunshine\\assets\\output_image\\output_image{index}.png",
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

def save_apps_json(apps_json, file_path):
    # 将更新后的 apps.json 保存到文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(apps_json, f, ensure_ascii=False, indent=4)

def get_url_files():
    # 获取当前工作目录下的所有 .url 文件
    url_files = glob.glob("*.url")
    valid_url_files = []
    
    for url in url_files:
        try:
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
    global folder_selected, onestart, close_after_completion
    # 获取当前目录下所有有效的 .lnk 和 .url 文件
    os.chdir(folder_selected)  # 设置为用户选择的目录
    lnk_files = get_lnk_files()
    url_files = get_url_files()
    
    target_paths = [get_target_path_from_lnk(lnk) for lnk in lnk_files]
    target_paths += [url[1] for url in url_files]  # 添加 .url 文件的目标路径
    lnkandurl_files = lnk_files + [url[0] for url in url_files]

    # 确保目标文件夹存在
    output_folder = r"C:\Program Files\Sunshine\assets\output_image"  # 更改为适当的文件夹

    # 加载现有的 apps.json 文件
    apps_json_path = r"C:\Program Files\Sunshine\config\apps.json"  # 修改为你的 apps.json 文件路径
    print(f"该应用会创建《{output_folder}》文件夹来存放输出的图像\n修改以下文件《{apps_json_path}》来添加sunshine应用程序")
    if onestart:
        onestart=False
        return
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    apps_json = load_apps_json(apps_json_path)

    # 检查 target_paths 是否与 apps.json 中的条目名称相同
    existing_names1 = {os.path.splitext(os.path.basename(entry['cmd']))[0] for entry in apps_json['apps']}  # 处理 cmd 字段
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
    remove_entries_with_output_image(apps_json,lnkandurl_files)
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
    #转换modified_target_paths
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

    # 保存更新后的 apps.json 文件
    save_apps_json(apps_json, apps_json_path)
    restart_service()
    if close_after_completion:
        os._exit(0)  # 正常退出

if __name__ == "__main__":
    create_gui()  # 启动Tkinter界面
