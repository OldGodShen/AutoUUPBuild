import requests
import re
import time
import zipfile
import retail

def down(latest_id):
    if not latest_id:
        print("Failed to get the latest ID. Exiting.")
        return

    # 构造下载 URL
    download_url = f"https://uupdump.net/get.php?id={latest_id}&pack=zh-cn&edition=professional"

    # POST 请求的数据
    data = {
        'autodl': 2,
        'updates': 1,
        'cleanup': 1,
        'netfx': 1
    }

    max_retries=3
    retry_delay=5
    retries = 0
    
    while retries <= max_retries:
        try:
            # 发起 POST 请求
            response = requests.post(download_url, data=data, stream=True)

            # 检查响应状态
            if response.status_code == 200:
                # 从 Content-Disposition 获取文件名
                content_disposition = response.headers.get('Content-Disposition')
                if content_disposition:
                    file_name_match = re.search(r'filename="([^"]+)"', content_disposition)
                    if file_name_match:
                        file_name = file_name_match.group(1)
                    else:
                        file_name = f"uupdump_{latest_id}.zip"
                else:
                    file_name = f"uupdump_{latest_id}.zip"

                # 保存文件
                with open(file_name, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                print(f"Download completed. File saved as {file_name}")

                # 解压 ZIP 文件
                try:
                    with zipfile.ZipFile(file_name, 'r') as zip_ref:
                        # extract_path = os.path.splitext(file_name)[0]  # 解压到与文件名相同的文件夹
                        # zip_ref.extractall(extract_path)
                        # print(f"Unzipped {file_name} to {extract_path}")
                        zip_ref.extractall() # 解压到当前目录
                        print(f"Unzipped {file_name}")
                except zipfile.BadZipFile:
                    print(f"Error: {file_name} is not a valid zip file.")
                except Exception as e:
                    print(f"Error extracting zip file: {e}")

                break
            elif response.status_code == 429:
                print(f"Rate limited (429). Retrying in {retry_delay} seconds. Attempt {retries + 1}/{max_retries}")
                time.sleep(retry_delay)
                retries += 1
            else:
                print(f"Failed to download. Status code: {response.status_code}")
                break
        except requests.RequestException as e:
            print(f"Error downloading file: {e}")
            break

    if retries > max_retries:
        print("Max retries exceeded. Download failed.")

if __name__ == "__main__":
    down(retail.get_latest())