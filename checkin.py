"""
TraeWork CN 自动签到脚本 - 自动查找安装路径，支持DPI缩放
"""
import ctypes
import ctypes.wintypes
import time
import subprocess
import os
import sys
import json
from pathlib import Path

# 启用DPI感知 - 必须在最前面！解决高DPI屏幕坐标偏移问题
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# 判断运行目录
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(app_dir)

user32 = ctypes.windll.user32

SW_MAXIMIZE = 3
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

CONFIG_FILE = "checkin_config.json"

# 默认坐标（1920x1080屏幕下校准值）
DEFAULT_CONFIG = {
    "avatar_rel_x": 64,
    "avatar_rel_y": 1006,
    "checkin_rel_x": 242,
    "checkin_rel_y": 653,
    "trae_path": ""
}

def find_trae_path():
    """自动查找TraeWork CN安装路径"""
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\TraeWork CN\TraeWork CN.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\TRAE SOLO CN\TRAE SOLO CN.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\TRAE SOLO CN\TRAE SOLO CN.exe"),
        r"C:\Program Files\TRAE SOLO CN\TRAE SOLO CN.exe",
        r"D:\Program Files\TRAE SOLO CN\TRAE SOLO CN.exe",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    
    # 尝试从注册表查找
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
                try:
                    name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    if "trae" in name.lower() and "solo" in name.lower() or "traework" in name.lower():
                        exe = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                        if os.path.exists(exe):
                            return exe
                except:
                    pass
                winreg.CloseKey(subkey)
            except:
                pass
        winreg.CloseKey(key)
    except:
        pass
    
    return None

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # 合并默认值
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except:
            pass
    return DEFAULT_CONFIG.copy()

def find_trae_window():
    for title in ["TraeWork CN", "TRAE SOLO CN", "Trae CN", "TraeWork"]:
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd, title
    return None, None

def get_window_rect(hwnd):
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect

def get_cursor_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def click_at(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.01)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.01)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.02)

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        log_path = os.path.join(app_dir, "traework-checkin.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

def show_message(title, message):
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)

def main():
    log("=== TraeWork 自动签到开始 ===")
    
    cfg = load_config()
    trae_path = cfg.get("trae_path", "") or find_trae_path()
    
    if not trae_path or not os.path.exists(trae_path):
        log("错误: 找不到TraeWork安装路径!")
        show_message("签到失败", "找不到 TraeWork CN 安装路径。\n请运行 CalibrateCoords.exe 进行校准，或在checkin_config.json中手动指定trae_path。")
        return
    
    orig_x, orig_y = get_cursor_pos()
    
    try:
        hwnd, title = find_trae_window()
        
        if not hwnd:
            log(f"正在启动 TraeWork: {trae_path}")
            subprocess.Popen(trae_path)
            log("等待 TraeWork 加载...")
            time.sleep(10)
            hwnd, title = find_trae_window()
        else:
            log(f"TraeWork 已运行: {title}")
            time.sleep(0.2)
        
        if not hwnd:
            log("错误: 找不到 TraeWork 窗口!")
            show_message("签到失败", "找不到 TraeWork CN 窗口，请确认应用已正确安装。")
            return
        
        log("最大化窗口...")
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
        time.sleep(0.3)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        
        rect = get_window_rect(hwnd)
        win_w = rect.right - rect.left
        win_h = rect.bottom - rect.top
        
        # 点击窗口中间关闭可能打开的侧边栏
        click_at(rect.left + win_w // 2, rect.top + win_h // 2)
        time.sleep(0.2)
        
        # 点击头像
        avatar_x = rect.left + cfg["avatar_rel_x"]
        avatar_y = rect.top + cfg["avatar_rel_y"]
        click_at(avatar_x, avatar_y)
        time.sleep(0.6)
        
        # 点击签到按钮
        checkin_x = rect.left + cfg["checkin_rel_x"]
        checkin_y = rect.top + cfg["checkin_rel_y"]
        click_at(checkin_x, checkin_y)
        time.sleep(0.2)
        
        # 立即把鼠标放回原位！
        user32.SetCursorPos(orig_x, orig_y)
        log("鼠标已恢复原位")
        
        log("签到完成!")
        show_message("签到成功", "TraeWork CN 签到已完成!\n200积分已领取~ 🍊")
        
    except Exception as e:
        log(f"出错: {e}")
        import traceback
        log(traceback.format_exc())
        show_message("签到出错", f"签到过程中出现错误:\n{e}")
    finally:
        user32.SetCursorPos(orig_x, orig_y)
        log("=== 结束 ===")
        log("")

if __name__ == "__main__":
    main()
