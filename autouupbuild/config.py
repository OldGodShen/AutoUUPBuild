import configparser
from pathlib import Path


APP_PACKAGES_TO_ENABLE = {
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
    "Microsoft.AV1VideoExtension_8wekyb3d8bbwe",
}

ARTIFACT_PRESETS = {
    "iso": {
        "convert-UUP": {
            "AutoStart": "1",
            "ResetBase": "1",
            "SkipISO": "0",
            "SkipWinRE": "1",
            "AutoExit": "1",
        },
        "Store_Apps": {
            "StubAppsFull": "1",
            "CustomList": "1",
        },
        "create_virtual_editions": {
            "vAutoStart": "0",
        },
    },
    "wim": {
        "convert-UUP": {
            "AutoStart": "3",
            "ResetBase": "1",
            "SkipISO": "1",
            "SkipWinRE": "1",
            "AutoExit": "1",
        },
        "Store_Apps": {
            "StubAppsFull": "1",
            "CustomList": "1",
        },
        "create_virtual_editions": {
            "vAutoStart": "0",
        },
    },
}


def configure_convert_config(config_path, artifact):
    config_path = Path(config_path)
    if artifact not in ARTIFACT_PRESETS:
        raise ValueError(f"Unsupported artifact type: {artifact}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(config_path, encoding="utf-8")

    for section, values in ARTIFACT_PRESETS[artifact].items():
        if not parser.has_section(section):
            raise KeyError(f"Missing section [{section}] in {config_path}")
        for key, value in values.items():
            parser.set(section, key, value)

    with config_path.open("w", encoding="utf-8") as file:
        parser.write(file)


def uncomment_custom_apps(apps_list_path, packages=APP_PACKAGES_TO_ENABLE):
    apps_list_path = Path(apps_list_path)
    if not apps_list_path.exists():
        raise FileNotFoundError(f"Custom apps list not found: {apps_list_path}")

    changed = 0
    lines = apps_list_path.read_text(encoding="utf-8").splitlines()
    output = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and stripped[1:].strip() in packages:
            output.append(stripped[1:].strip())
            changed += 1
        else:
            output.append(line)

    text = "\n".join(output)
    if text:
        text += "\n"
    apps_list_path.write_text(text, encoding="utf-8")
    return changed
