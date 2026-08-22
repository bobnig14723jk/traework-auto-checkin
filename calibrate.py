"""
TraeWork 坐标校准工具 - 通用版
"""
import ctypes
import time
import subprocess
import os
import sys
import json

# 启用DPI感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(app_dir)

user32 = ctypes.windll.user32
SW_MAXIMIZE = 3

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def find_trae_path():
    """自动查找TraeWork CN安装路径"""
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\TraeWork CN\TraeWork CN.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\TRAE SOLO CN\TRAE SOLO CN.exe"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return None

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
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.1)

def msg_box(text, title="TraeWork 坐标校准"):
    user32.MessageBoxW(0, text, title, 0x40)

def main():
    print("=" * 50)
    print("  TraeWork CN 坐标校准工具")
    print("=" * 50)
    print()
    
    trae_path = find_trae_path()
    if not trae_path:
        print("未自动找到TraeWork路径，请手动启动TraeWork后再运行此工具。")
        msg_box("未找到TraeWork安装路径！\n请先手动启动TraeWork，然后再运行校准工具。", "错误")
        return
    
    msg_box("即将开始坐标校准，请确保TraeWork已打开并处于主界面。\n\n点击确定开始...", "坐标校准")
    
    hwnd, title = find_trae_window()
    if not hwnd:
        print("正在启动 TraeWork...")
        subprocess.Popen(trae_path)
        time.sleep(12)
        hwnd, title = find_trae_window()
    
    if not hwnd:
        msg_box("找不到TraeWork窗口，请手动打开后再试！", "错误")
        return
    
    print(f"找到窗口: {title}")
    print("正在最大化窗口...")
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    time.sleep(1)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1)
    
    rect = get_window_rect(hwnd)
    win_w = rect.right - rect.left
    win_h = rect.bottom - rect.top
    print(f"窗口大小: {win_w}x{win_h}")
    print(f"屏幕分辨率: {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}")
    print()
    
    # 点击中间重置状态
    click_at(rect.left + win_w // 2, rect.top + win_h // 2)
    time.sleep(0.5)
    
    # 第一步：记录头像位置
    msg_box("【第1步/共2步】\n\n请将鼠标指针移动到左下角的【头像】上（悬停即可，不要点击），\n然后按Alt+Tab切回这个黑色窗口，按回车键继续。", "坐标校准")
    
    ax, ay = get_cursor_pos()
    avatar_rel_x = ax - rect.left
    avatar_rel_y = ay - rect.top
    print(f"头像绝对坐标: ({ax}, {ay})")
    print(f"头像相对坐标: x={avatar_rel_x}, y={avatar_rel_y}")
    print()
    
    # 点击头像打开侧边栏
    click_at(ax, ay)
    time.sleep(1.5)
    
    # 第二步：记录签到按钮位置
    msg_box("【第2步/共2步】\n\n侧边栏应该已经打开了。\n请将鼠标指针移动到【每日签到领200积分】按钮上（悬停即可，不要点击），\n然后按Alt+Tab切回这个黑色窗口，按回车键继续。", "坐标校准")
    
    cx, cy = get_cursor_pos()
    checkin_rel_x = cx - rect.left
    checkin_rel_y = cy - rect.top
    print(f"签到按钮绝对坐标: ({cx}, {cy})")
    print(f"签到按钮相对坐标: x={checkin_rel_x}, y={checkin_rel_y}")
    print()
    
    # 保存配置
    cfg = {
        "avatar_rel_x": avatar_rel_x,
        "avatar_rel_y": avatar_rel_y,
        "checkin_rel_x": checkin_rel_x,
        "checkin_rel_y": checkin_rel_y,
        "trae_path": trae_path
    }
    
    config_path = os.path.join(app_dir, "checkin_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    
    print(f"配置已保存到: {config_path}")
    print()
    
    # 测试点击
    print("正在测试新坐标...")
    click_at(rect.left + win_w // 2, rect.top + win_h // 2)
    time.sleep(0.5)
    click_at(ax, ay)
    time.sleep(1)
    click_at(cx, cy)
    time.sleep(0.5)
    print("测试完成！")
    
    msg_box(
        f"坐标校准完成！🍊\n\n"
        f"头像相对坐标: ({avatar_rel_x}, {avatar_rel_y})\n"
        f"签到按钮相对坐标: ({checkin_rel_x}, {checkin_rel_y})\n\n"
        f"配置已自动保存。现在可以运行 OrangeCheckin.exe 进行签到了！\n\n"
        f"提示：如果想设置每天自动签到，请运行 setup_task.bat",
        "校准完成"
    )
    print("\n校准完成！可以关闭此窗口了。")

if __name__ == "__main__":
    main()
