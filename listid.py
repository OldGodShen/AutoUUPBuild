import requests

def get_latest():
    url = "https://api.uupdump.net/listid.php?search=26100&sortByDate=1"
    
    try:
        # 发起 GET 请求获取 JSON 数据
        response = requests.get(url)
        response.raise_for_status()  # 如果请求失败，会抛出异常
        
        # 解析返回的 JSON 数据
        data = response.json()
        
        # 获取第一个最新的 build 信息
        builds = data.get("response", {}).get("builds", {})
        
        if builds:
            # 获取最新的 uuid,version
            latest_uuid = next(iter(builds.values())).get("uuid")
            latest_version = next(iter(builds.values())).get("build")
            return latest_uuid, latest_version
        else:
            print("No builds found.")
            return None
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def save_to_file(context,file):
    # 将 uuid 写入临时文件
    with open(file, "w") as file:
        file.write(context)
    print(file.name + ",version saved.")

if __name__ == "__main__":
    uuid, version = get_latest()
    if uuid:
        print(f"The latest UUID is: {uuid}")
        print(f"The latest version is: {version}")
        save_to_file(uuid,"uuid.txt")
        save_to_file(version,"version.txt")
    else:
        print("Failed to retrieve the UUID.")
