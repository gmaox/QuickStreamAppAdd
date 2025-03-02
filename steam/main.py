import winreg
import os
import re
import json
import urllib3
import requests  # 添加requests库
# PyInstaller -F main.py -i fav.ico --uac-admin
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) #禁用SSL警告
print("v25.03.02")
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

def parse_library_folders(file_path):
    """
    解析libraryfolders.vdf文件以获取所有的应用ID
    返回: dict - 包含库路径和应用ID的字典
    """
    library_data = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        # 使用正则表达式匹配库路径和应用ID
        matches = re.findall(r'"\d+"\s*{\s*"path"\s*"([^"]+)"[^}]*"apps"\s*{([^}]*)}', content, re.DOTALL)
        for path, apps in matches:
            app_ids = re.findall(r'"(\d+)"', apps)
            # 只保留奇数位置的应用ID
            library_data[path] = [app_ids[i] for i in range(len(app_ids)) if i % 2 == 0]
    return library_data

def generate_app_entry(app_id, steam_base_dir):
    # 检查图片文件是否存在
    image_path = f"{steam_base_dir}/appcache/librarycache/{app_id}_library_600x900.jpg"
    if not os.path.exists(image_path):
        image_path = f"{steam_base_dir}/appcache/librarycache/{app_id}_library_600x900_schinese.jpg"
        if not os.path.exists(image_path):
            return None  # 如果图片文件不存在，则返回None

    # 为每个应用ID生成对应的 app 条目
    entry = {
        "name": f"steamgame {app_id}", 
        "output": "",
        "cmd": f"steam://rungameid/{app_id}",
        "exclude-global-prep-cmd": "false",
        "elevated": "false",
        "auto-detach": "true",
        "wait-all": "true",
        "exit-timeout": "5",
        "menu-cmd": "",
        "image-path": image_path,
        "working-dir": f"steam steam://rungameid/{app_id}"
    }
    return entry

def update_apps_json(apps_json_path, steam_base_dir, all_app_ids):
    """
    更新apps.json文件，添加新的应用条目
    """
    with open(apps_json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    data['apps'] = [app for app in data['apps'] if "steamgame" not in app['name']]
    
    # 提示用户确认
    user_input = input("按回车键确认更新，或输入'd'删除包含'steamgame'的条目后更新: ").strip().lower()
    if user_input == 'd':
        # 删除name中包含"steamgame"的条目
        with open(apps_json_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print("已删除包含'steamgame'的条目")
        return 

    # 为每个应用ID生成条目并添加到apps列表中
    for app_id in all_app_ids:
        entry = generate_app_entry(app_id, steam_base_dir)
        if entry:  # 只有在entry不为None时才添加
            data['apps'].append(entry)
    
    # 将更新后的数据写回到apps.json文件
    with open(apps_json_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

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

if __name__ == "__main__":
    steam_base_dir = get_steam_base_dir()
    if steam_base_dir:
        print(f"Steam安装路径: {steam_base_dir}")
        library_file_path = os.path.join(steam_base_dir, 'steamapps', 'libraryfolders.vdf')
        if os.path.exists(library_file_path):
            libraries = parse_library_folders(library_file_path)
            all_app_ids = []
            for path, app_ids in libraries.items():
                print(f"库路径: {path}")
                print("应用ID:")
                for app_id in app_ids:
                    print(f"  - {app_id}")
                all_app_ids.extend(app_ids)
            # 更新apps.json文件
            update_apps_json(f"{APP_INSTALL_PATH}\\config\\apps.json", steam_base_dir, all_app_ids)
            # 更新完成后重启服务
            restart_service()
        else:
            print("未找到libraryfolders.vdf文件")
    else:
        print("未找到Steam安装路径")
input("按回车键退出")
