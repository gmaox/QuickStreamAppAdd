import os 
import time
import glob
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
            print(f"图像已保存至该目录的 {output_path}")

        try:
            os.remove(icon_path)
            print(f"\n {exe_path}\n")
        except PermissionError:
            print(f"无法删除临时图标文件: {icon_path}. 稍后再试.")
            time.sleep(1)
            os.remove(icon_path)

    except Exception as e:
        print(f"创建图像时发生异常，跳过此文件: {exe_path}\n异常信息: {e}")


def main():
    # 获取当前目录下所有有效的 .lnk 文件
    lnk_files = get_lnk_files()
    target_paths = [get_target_path_from_lnk(lnk) for lnk in lnk_files]

    # 确保目标文件夹存在
    output_folder = r"output_image"  # 更改为适当的文件夹


    input(f"该应用会在快捷方式同目录下创建《{output_folder}》文件夹来存放输出的图像\n按回车继续...")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 创建并处理图像
    for idx, target_path in enumerate(target_paths):
        output_path = os.path.join(output_folder, f"output_image{idx}.png")
        create_image_with_icon(target_path, output_path)

    input(f"完成 !\n按回车退出...")

if __name__ == "__main__":
    main()
