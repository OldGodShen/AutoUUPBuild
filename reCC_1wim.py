import configparser

# 定义文件路径
ini_file = "ConvertConfig.ini"

# 创建 ConfigParser 对象
config = configparser.ConfigParser()

# 保留原始大小写
config.optionxform = str

# 读取 INI 文件
config.read(ini_file)

# 修改 [convert-UUP] 部分中的参数
config.set("convert-UUP", "AutoStart", "1")
config.set("convert-UUP", "ResetBase", "1")
config.set("convert-UUP", "SkipISO", "1")
config.set("convert-UUP", "SkipWinRE", "1")
config.set("convert-UUP", "AutoExit", "1")

# 修改 [Store_Apps] 部分中的参数
config.set("Store_Apps", "StubAppsFull", "1")
config.set("Store_Apps", "CustomList", "1")

# 修改 [create_virtual_editions] 部分中的参数
config.set("create_virtual_editions", "vAutoStart", "0")

# 保存修改后的 INI 文件
with open(ini_file, 'w') as configfile:
    config.write(configfile)

print(f"Modified {ini_file} successfully.")