# 定义文件路径
file_path = "CustomAppsList.txt"

# 定义需要取消注释的行内容（精确匹配）
lines_to_uncomment = [
    "Microsoft.WindowsStore_8wekyb3d8bbwe",
    "Microsoft.StorePurchaseApp_8wekyb3d8bbwe",
    "Microsoft.SecHealthUI_8wekyb3d8bbwe",
    "Microsoft.DesktopAppInstaller_8wekyb3d8bbwe",
    "Microsoft.Windows.Photos_8wekyb3d8bbwe",
    "Microsoft.WindowsCamera_8wekyb3d8bbwe",
    "Microsoft.WindowsNotepad_8wekyb3d8bbwe",
    "Microsoft.Paint_8wekyb3d8bbwe",
    "Microsoft.WindowsTerminal_8wekyb3d8bbwe",
    "MicrosoftWindows.Client.WebExperience_cw5n1h2txyewy",
    "Microsoft.WindowsAlarms_8wekyb3d8bbwe",
    "Microsoft.WindowsCalculator_8wekyb3d8bbwe",
    "Microsoft.WindowsMaps_8wekyb3d8bbwe",
    "Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe",
    "Microsoft.ScreenSketch_8wekyb3d8bbwe",
    "Microsoft.WindowsFeedbackHub_8wekyb3d8bbwe",
    "Microsoft.XboxSpeechToTextOverlay_8wekyb3d8bbwe",
    "Microsoft.XboxGameOverlay_8wekyb3d8bbwe",
    "Microsoft.XboxIdentityProvider_8wekyb3d8bbwe",
    "Microsoft.Windows.DevHome_8wekyb3d8bbwe",
    "Microsoft.ApplicationCompatibilityEnhancements_8wekyb3d8bbwe",
    "MicrosoftWindows.CrossDevice_cw5n1h2txyewy",
    "Microsoft.StartExperiencesApp_8wekyb3d8bbwe",
    "Microsoft.WindowsTerminal_8wekyb3d8bbwe",
    "Microsoft.ZuneMusic_8wekyb3d8bbwe",
    "Microsoft.ZuneVideo_8wekyb3d8bbwe",
    "Microsoft.YourPhone_8wekyb3d8bbwe",
    "Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe",
    "Microsoft.GamingApp_8wekyb3d8bbwe",
    "Microsoft.XboxGamingOverlay_8wekyb3d8bbwe",
    "Microsoft.Xbox.TCUI_8wekyb3d8bbwe",
    "Microsoft.WebMediaExtensions_8wekyb3d8bbwe",
    "Microsoft.RawImageExtension_8wekyb3d8bbwe",
    "Microsoft.HEIFImageExtension_8wekyb3d8bbwe",
    "Microsoft.HEVCVideoExtension_8wekyb3d8bbwe",
    "Microsoft.VP9VideoExtensions_8wekyb3d8bbwe",
    "Microsoft.WebpImageExtension_8wekyb3d8bbwe",
    "Microsoft.DolbyAudioExtensions_8wekyb3d8bbwe",
    "Microsoft.AVCEncoderVideoExtension_8wekyb3d8bbwe",
    "Microsoft.MPEG2VideoExtension_8wekyb3d8bbwe",
    "Microsoft.AV1VideoExtension_8wekyb3d8bbwe"
]

# 读取文件内容
with open(file_path, 'r') as file:
    lines = file.readlines()

# 修改内容：取消指定行的注释
new_lines = []
for line in lines:
    stripped_line = line.strip()
    if stripped_line.startswith("#") and stripped_line[1:].strip() in lines_to_uncomment:
        new_lines.append(stripped_line[1:].strip() + "\n")  # 去掉 # 并添加回换行符
    else:
        new_lines.append(line)

# 将修改后的内容写回文件
with open(file_path, 'w') as file:
    file.writelines(new_lines)

print(f"Uncommented specified lines in {file_path} successfully.")