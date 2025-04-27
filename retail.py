import requests
from bs4 import BeautifulSoup
import re
import time


def get_latest():
    url = "https://uupdump.net/fetchupd.php?arch=amd64&ring=retail"
    
    max_retries=3
    retry_delay=5
    retries = 0
    while retries <= max_retries:
        try:
            # 发起 GET 请求获取 XML 数据
            response = requests.get(url)

            if response.status_code == 200:
                # 解析返回的 XML 数据
                soup = BeautifulSoup(response.content, 'html.parser')

                # 提取 Build number
                extract_build_number(response.text)

                a_tags = soup.find_all('a')

                # 遍历所有<a>标签，寻找包含特定URL的标签
                for a_tag in a_tags:
                    href = a_tag.get('href')
                    if href and 'selectlang.php?id=' in href:
                        # 使用正则表达式提取id参数
                        match = re.search(r'selectlang\.php\?id=([a-f0-9-]+)', href)
                        if match:
                            id_value = match.group(1)
                            print(f"Extracted ID: {id_value}")
                            return id_value
                else:
                    print("No matching ID found in the links.")
                    return None
            
            elif response.status_code == 429:
                print(f"Rate limited (429). Retrying in {retry_delay} seconds. Attempt {retries + 1}/{max_retries}")
                time.sleep(retry_delay)
                retries += 1
            else:
                print(f"Failed to get. Status code: {response.status_code}")
                break
            
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return None
    if retries > max_retries:
        print("Max retries exceeded. Download failed.")

def extract_build_number(html_content):
    # 使用正则表达式提取 Build number
    match = re.search(r'Build number: (\d+\.\d+)', html_content)
    if match:
        build_number = match.group(1)
        print(f"Extracted Build Number: {build_number}")
        
        # 将构建号写入 version 文件
        with open("version", "w") as version_file:
            version_file.write(build_number)
        print("Build number written to 'version' file.")
        return build_number
    else:
        print("Build number not found.")
        return None

if __name__ == "__main__":
    get_latest()