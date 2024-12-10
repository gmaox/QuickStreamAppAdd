import os 
import time
import glob
import json
import win32com.client  # 用于解析 .lnk 文件
from icoextract import IconExtractor, IconExtractorError
from PIL import Image, ImageDraw
from colorthief import ColorThief
from io import BytesIO

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

def main():
    # 获取当前目录下所有有效的 .lnk 文件
    lnk_files = get_lnk_files()
    target_paths = [get_target_path_from_lnk(lnk) for lnk in lnk_files]

    # 确保目标文件夹存在
    output_folder = r"C:\Program Files\Sunshine\assets\output_image"  # 更改为适当的文件夹

    # 加载现有的 apps.json 文件
    apps_json_path = r"C:\Program Files\Sunshine\config\apps.json"  # 修改为你的 apps.json 文件路径
    input(f"该应用会创建《{output_folder}》文件夹来存放输出的图像\n修改以下文件《{apps_json_path}》来添加sunshine应用程序\n这个ex版本会将应用放置在独立命令处。效果为退出串流不退出游戏，退出游戏不退出串流\n若不需要这种效果请选择普通版本\n按回车继续...")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    apps_json = load_apps_json(apps_json_path)

    # 删除包含 "output_image" 的条目
    remove_entries_with_output_image(apps_json)

    # 创建并处理图像
    for idx, target_path in enumerate(target_paths):
        output_path = os.path.join(output_folder, f"output_image{idx}.png")
        create_image_with_icon(target_path, output_path)

    # 添加新的快捷方式条目
    add_entries_to_apps_json(lnk_files, apps_json)

    # 保存更新后的 apps.json 文件
    save_apps_json(apps_json, apps_json_path)
    input(f"apps.json 文件已更新并保存至 {apps_json_path}")

if __name__ == "__main__":
    main()
