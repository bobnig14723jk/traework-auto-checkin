# -*- coding: utf-8 -*-
import sys
import os
import time
import json
import ctypes
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, "checkin_config.json")
TASK_NAME = "TraeWorkDailyCheckin"

SW_MAXIMIZE = 3
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

user32 = ctypes.windll.user32

DEFAULT_CONFIG = {
    "avatar_rel_x": -1,
    "avatar_rel_y": -1,
    "checkin_rel_x": -1,
    "checkin_rel_y": -1,
    "trae_path": "",
    "calibrated": False,
    "auto_time": "09:00"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except:
        pass

def find_trae_path():
    paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\TRAE SOLO CN\TRAE SOLO CN.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\TraeWork CN\TraeWork CN.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\TRAE SOLO CN\TRAE SOLO CN.exe"),
    ]
    for p in paths:
        try:
            if os.path.exists(p):
                return p
        except:
            pass
    return None

def find_trae_window():
    for title in ["TraeWork CN", "TRAE SOLO CN", "Trae CN", "TraeWork"]:
        try:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                return hwnd, title
        except:
            pass
    return None, None

def get_cursor_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def click_at(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.03)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.08)

def task_exists():
    try:
        r = subprocess.run(['schtasks', '/query', '/tn', TASK_NAME],
                          capture_output=True, creationflags=0x08000000)
        return r.returncode == 0
    except:
        return False

def create_task(exe_path, run_time="09:00"):
    try:
        if not os.path.exists(exe_path):
            return False, "找不到程序"
        subprocess.run(['schtasks', '/delete', '/tn', TASK_NAME, '/f'],
                      capture_output=True, creationflags=0x08000000)
        r = subprocess.run(
            ['schtasks', '/create', '/tn', TASK_NAME, '/tr', '"%s"' % exe_path,
             '/sc', 'daily', '/st', run_time, '/f', '/rl', 'highest'],
            capture_output=True, text=True, creationflags=0x08000000)
        if r.returncode == 0:
            return True, "已设置每天 %s 自动签到" % run_time
        return False, "创建失败"
    except Exception as e:
        return False, str(e)

def delete_task():
    try:
        r = subprocess.run(['schtasks', '/delete', '/tn', TASK_NAME, '/f'],
                          capture_output=True, creationflags=0x08000000)
        return r.returncode == 0
    except:
        return False

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("橙子签到 - TraeWork自动签到")
        self.root.geometry("500x550")
        self.root.resizable(False, False)
        
        try:
            icon_path = os.path.join(APP_DIR, "orange.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        self.config = load_config()
        self.trae_path = self.config.get("trae_path", "") or find_trae_path() or ""
        self.is_calibrating = False
        
        self.ax_var = tk.StringVar(value=str(self.config.get("avatar_rel_x", -1)))
        self.ay_var = tk.StringVar(value=str(self.config.get("avatar_rel_y", -1)))
        self.cx_var = tk.StringVar(value=str(self.config.get("checkin_rel_x", -1)))
        self.cy_var = tk.StringVar(value=str(self.config.get("checkin_rel_y", -1)))
        self.hour_var = tk.StringVar(value=self.config.get("auto_time", "09:00").split(":")[0])
        self.min_var = tk.StringVar(value=self.config.get("auto_time", "09:00").split(":")[1])
        self.task_status_var = tk.StringVar(value="检查中...")
        
        self._build_ui()
        self._log("橙子签到已启动")
        if self.trae_path:
            self._log("找到TraeWork: " + os.path.basename(self.trae_path))
        else:
            self._log("未找到TraeWork，请先校准")
        
        self._update_task_status()
        
        if self.config.get("avatar_rel_x", -1) < 0:
            self.checkin_btn.config(state=tk.DISABLED)
            self.warn_label.pack(fill=tk.X, padx=20, pady=(0,5), after=self.sep1)
            self._log("首次使用，请先完成坐标校准")
    
    def _build_ui(self):
        title_frame = tk.Frame(self.root, pady=10)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text="橙子签到", font=("微软雅黑", 20, "bold"), fg="#e67e22").pack()
        tk.Label(title_frame, text="TraeWork CN 自动领积分", font=("微软雅黑", 9), fg="#666").pack()
        
        self.sep1 = tk.Frame(self.root, height=2, bg="#ddd")
        self.sep1.pack(fill=tk.X, padx=20, pady=5)
        
        self.warn_label = tk.Label(self.root, 
            text="【注意】第一次使用必须先校准坐标！请点击下方「开始校准坐标」按钮",
            font=("微软雅黑", 9, "bold"), fg="#d35400", bg="#fef9e7", pady=6)
        
        bf = tk.Frame(self.root, padx=20)
        bf.pack(fill=tk.X, pady=5)
        self.checkin_btn = tk.Button(bf, text="立即签到", font=("微软雅黑", 14, "bold"),
                                    bg="#27ae60", fg="white", command=self._checkin_thread, pady=8)
        self.checkin_btn.pack(fill=tk.X)
        
        self.calib_btn = tk.Button(bf, text="开始校准坐标", font=("微软雅黑", 11),
                                  bg="#3498db", fg="white", command=self._calib_thread, pady=5)
        self.calib_btn.pack(fill=tk.X, pady=(5,0))
        
        tk.Frame(self.root, height=2, bg="#ddd").pack(fill=tk.X, padx=20, pady=5)
        
        cf = tk.LabelFrame(self.root, text=" 当前坐标 ", font=("微软雅黑", 9), padx=10, pady=8)
        cf.pack(fill=tk.X, padx=20)
        
        r1 = tk.Frame(cf)
        r1.pack(fill=tk.X)
        tk.Label(r1, text="头像位置：", width=10, anchor=tk.W, font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Label(r1, text="X:", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Entry(r1, textvariable=self.ax_var, width=6, state="readonly").pack(side=tk.LEFT, padx=2)
        tk.Label(r1, text=" Y:", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(8,0))
        tk.Entry(r1, textvariable=self.ay_var, width=6, state="readonly").pack(side=tk.LEFT, padx=2)
        
        r2 = tk.Frame(cf)
        r2.pack(fill=tk.X, pady=(3,0))
        tk.Label(r2, text="签到按钮：", width=10, anchor=tk.W, font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Label(r2, text="X:", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Entry(r2, textvariable=self.cx_var, width=6, state="readonly").pack(side=tk.LEFT, padx=2)
        tk.Label(r2, text=" Y:", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(8,0))
        tk.Entry(r2, textvariable=self.cy_var, width=6, state="readonly").pack(side=tk.LEFT, padx=2)
        
        lf = tk.LabelFrame(self.root, text=" 每日自动签到 ", font=("微软雅黑", 9), padx=10, pady=8)
        lf.pack(fill=tk.X, padx=20, pady=8)
        
        tk.Label(lf, textvariable=self.task_status_var, font=("微软雅黑", 9, "bold"), fg="#e74c3c").pack(anchor=tk.W)
        
        tr = tk.Frame(lf)
        tr.pack(fill=tk.X, pady=5)
        tk.Label(tr, text="时间：", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        
        hours = ["%02d" % h for h in range(24)]
        mins = ["%02d" % m for m in range(0, 60, 5)]
        
        h_menu = tk.OptionMenu(tr, self.hour_var, *hours)
        h_menu.config(width=3, font=("微软雅黑", 9))
        h_menu.pack(side=tk.LEFT, padx=3)
        tk.Label(tr, text=":", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        m_menu = tk.OptionMenu(tr, self.min_var, *mins)
        m_menu.config(width=3, font=("微软雅黑", 9))
        m_menu.pack(side=tk.LEFT, padx=3)
        
        br = tk.Frame(lf)
        br.pack(fill=tk.X, pady=(5,0))
        tk.Button(br, text="启用自动签到", font=("微软雅黑", 9),
                 bg="#3498db", fg="white", command=self._enable_task, pady=2).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,3))
        tk.Button(br, text="取消自动", font=("微软雅黑", 9),
                 command=self._disable_task, pady=2).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(3,0))
        
        logf = tk.LabelFrame(self.root, text=" 运行日志 ", font=("微软雅黑", 9), padx=3, pady=3)
        logf.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,10))
        
        self.log_list = tk.Listbox(logf, height=6, font=("Consolas", 8), bg="#fafafa")
        log_scroll = tk.Scrollbar(logf, command=self.log_list.yview)
        self.log_list.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _log(self, msg):
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = "[%s] %s" % (ts, msg)
            self.log_list.insert(tk.END, line)
            self.log_list.see(tk.END)
            if self.log_list.size() > 200:
                self.log_list.delete(0, self.log_list.size()-200)
        except:
            pass
    
    def _update_task_status(self):
        def _check():
            exists = task_exists()
            def _update():
                try:
                    if exists:
                        self.task_status_var.set("自动签到：已启用")
                    else:
                        self.task_status_var.set("自动签到：未启用")
                except:
                    pass
            try:
                self.root.after(100, _update)
            except:
                pass
        threading.Thread(target=_check, daemon=True).start()
    
    def _checkin_thread(self):
        if self.config.get("avatar_rel_x", -1) < 0:
            messagebox.showwarning("提示", "请先完成坐标校准！")
            return
        self.checkin_btn.config(state=tk.DISABLED, text="签到中...")
        threading.Thread(target=self._do_checkin, daemon=True).start()
    
    def _do_checkin(self):
        self._log("===== 开始签到 =====")
        try:
            ax = int(self.ax_var.get())
            ay = int(self.ay_var.get())
            cx = int(self.cx_var.get())
            cy = int(self.cy_var.get())
        except:
            self._log("坐标错误，请重新校准")
            self.root.after(0, lambda: self.checkin_btn.config(state=tk.NORMAL, text="立即签到"))
            return
        
        if ax < 0:
            self._log("坐标未设置，请先校准")
            self.root.after(0, lambda: messagebox.showwarning("提示", "请先完成坐标校准！"))
            self.root.after(0, lambda: self.checkin_btn.config(state=tk.NORMAL, text="立即签到"))
            return
        
        tp = self.trae_path or find_trae_path()
        if not tp or not os.path.exists(tp):
            self._log("找不到TraeWork")
            self.root.after(0, lambda: messagebox.showerror("错误", "找不到TraeWork，请先校准！"))
            self.root.after(0, lambda: self.checkin_btn.config(state=tk.NORMAL, text="立即签到"))
            return
        
        orig_x, orig_y = get_cursor_pos()
        try:
            hwnd, title = find_trae_window()
            if not hwnd:
                self._log("正在启动TraeWork...")
                subprocess.Popen(tp)
                time.sleep(6)
                hwnd, title = find_trae_window()
            else:
                self._log("TraeWork已运行: " + str(title))
                time.sleep(0.15)
            
            if not hwnd:
                raise Exception("找不到TraeWork窗口，请手动打开后再试")
            
            self._log("最大化窗口...")
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
            time.sleep(0.3)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            ww = rect.right - rect.left
            wh = rect.bottom - rect.top
            
            click_at(rect.left + ww//2, rect.top + wh//2)
            time.sleep(0.1)
            
            self._log("点击头像...")
            click_at(rect.left + ax, rect.top + ay)
            time.sleep(0.4)
            
            self._log("点击签到按钮...")
            click_at(rect.left + cx, rect.top + cy)
            time.sleep(0.2)
            
            user32.SetCursorPos(orig_x, orig_y)
            self._log("===== 签到成功！200积分到手 =====")
            self.root.after(0, lambda: messagebox.showinfo("成功", "签到完成！\n200积分已领取~"))
        except Exception as e:
            self._log("签到失败: " + str(e))
            self.root.after(0, lambda: messagebox.showerror("失败", "签到出错：\n" + str(e)))
            try:
                user32.SetCursorPos(orig_x, orig_y)
            except:
                pass
        finally:
            self._log("")
            try:
                self.root.after(0, lambda: self.checkin_btn.config(state=tk.NORMAL, text="立即签到"))
            except:
                pass
    
    def _calib_thread(self):
        if self.is_calibrating:
            return
        ok = messagebox.askokcancel("开始校准",
            "校准流程说明：\n\n"
            "1. 程序会自动打开TraeWork并最大化\n"
            "2. 右下角会出现一个小提示窗口\n"
            "3. 你只需要【移动鼠标】到指定位置\n"
            "   （不需要点击TraeWork窗口）\n"
            "4. 鼠标放好位置后，点击提示窗口上的\n"
            "   【确认位置】按钮\n\n"
            "准备好了吗？")
        if not ok:
            return
        
        self.is_calibrating = True
        self.calib_btn.config(state=tk.DISABLED, text="校准中...")
        threading.Thread(target=self._do_calibration, daemon=True).start()
    
    def _do_calibration(self):
        self._log("===== 开始坐标校准 =====")
        tp = self.trae_path or find_trae_path()
        if not tp:
            self._log("未找到TraeWork")
            self.root.after(0, lambda: messagebox.showerror("错误", "未找到TraeWork CN！\n请先确认已安装。"))
            self._finish_calib()
            return
        
        ax = ay = cx = cy = 0
        
        try:
            self._log("准备TraeWork窗口...")
            hwnd, title = find_trae_window()
            if not hwnd:
                self._log("正在启动TraeWork...")
                subprocess.Popen(tp)
                time.sleep(7)
                hwnd, title = find_trae_window()
            
            if not hwnd:
                raise Exception("找不到TraeWork窗口，请手动打开后再试")
            
            self._log("找到窗口: " + str(title))
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
            time.sleep(0.4)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.4)
            
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            ww = rect.right - rect.left
            wh = rect.bottom - rect.top
            
            click_at(rect.left + ww//2, rect.top + wh//2)
            time.sleep(0.2)
            
            # ========== 第一步 ==========
            self._log("第1步：请将鼠标移到左下角头像上，然后点确认...")
            s1 = threading.Event()
            r1 = {"cancel": True, "x": 0, "y": 0}
            
            def show_step1():
                win = tk.Toplevel(self.root)
                win.title("校准 - 第1步")
                win.attributes("-topmost", True)
                win.resizable(False, False)
                
                win_w = 320
                win_h = 140
                sx = win.winfo_screenwidth()
                sy = win.winfo_screenheight()
                x_pos = sx - win_w - 20
                y_pos = sy - win_h - 60
                win.geometry("%dx%d+%d+%d" % (win_w, win_h, x_pos, y_pos))
                
                f = tk.Frame(win, padx=15, pady=12, bg="#fff3cd")
                f.pack(fill=tk.BOTH, expand=True)
                
                tk.Label(f, text="第 1 步 / 共 2 步", font=("微软雅黑", 12, "bold"), 
                        fg="#d35400", bg="#fff3cd").pack(pady=(0,5))
                tk.Label(f, text="请把鼠标移动到 TraeWork 左下角的头像上\n（不需要点击，只需要移动鼠标过去）", 
                        font=("微软雅黑",9), justify=tk.CENTER, bg="#fff3cd").pack(pady=(0,10))
                
                bf = tk.Frame(f, bg="#fff3cd")
                bf.pack(fill=tk.X)
                
                def ok1():
                    r1["x"], r1["y"] = get_cursor_pos()
                    r1["cancel"] = False
                    try:
                        win.destroy()
                    except:
                        pass
                    s1.set()
                
                def cancel1():
                    r1["cancel"] = True
                    try:
                        win.destroy()
                    except:
                        pass
                    s1.set()
                
                ok_btn = tk.Button(bf, text="✓ 确认位置", font=("微软雅黑",11,"bold"), 
                                  bg="#27ae60", fg="white", command=ok1, width=14, pady=3)
                ok_btn.pack(side=tk.LEFT, padx=5)
                ok_btn.focus_set()
                
                tk.Button(bf, text="取消", font=("微软雅黑",10), command=cancel1, width=8, pady=3).pack(side=tk.RIGHT, padx=5)
                
                win.bind('<Return>', lambda e: ok1())
                win.protocol("WM_DELETE_WINDOW", cancel1)
            
            self.root.after(300, show_step1)
            s1.wait()
            
            if r1["cancel"]:
                self._log("校准已取消")
                self._finish_calib()
                return
            
            ax, ay = r1["x"], r1["y"]
            avx = ax - rect.left
            avy = ay - rect.top
            self._log("头像位置: (%d, %d)" % (avx, avy))
            
            self._log("点击头像打开侧边栏...")
            click_at(ax, ay)
            time.sleep(0.6)
            
            # ========== 第二步 ==========
            self._log("第2步：请将鼠标移到「每日签到」按钮上，然后点确认...")
            s2 = threading.Event()
            r2 = {"cancel": True, "x": 0, "y": 0}
            
            def show_step2():
                win = tk.Toplevel(self.root)
                win.title("校准 - 第2步")
                win.attributes("-topmost", True)
                win.resizable(False, False)
                
                win_w = 340
                win_h = 140
                sx = win.winfo_screenwidth()
                sy = win.winfo_screenheight()
                x_pos = sx - win_w - 20
                y_pos = sy - win_h - 60
                win.geometry("%dx%d+%d+%d" % (win_w, win_h, x_pos, y_pos))
                
                f = tk.Frame(win, padx=15, pady=12, bg="#d1ecf1")
                f.pack(fill=tk.BOTH, expand=True)
                
                tk.Label(f, text="第 2 步 / 共 2 步", font=("微软雅黑", 12, "bold"), 
                        fg="#0c5460", bg="#d1ecf1").pack(pady=(0,5))
                tk.Label(f, text="请把鼠标移动到「每日签到领200积分」按钮上\n（不需要点击，只需要移动鼠标过去）", 
                        font=("微软雅黑",9), justify=tk.CENTER, bg="#d1ecf1").pack(pady=(0,10))
                
                bf = tk.Frame(f, bg="#d1ecf1")
                bf.pack(fill=tk.X)
                
                def ok2():
                    r2["x"], r2["y"] = get_cursor_pos()
                    r2["cancel"] = False
                    try:
                        win.destroy()
                    except:
                        pass
                    s2.set()
                
                def cancel2():
                    r2["cancel"] = True
                    try:
                        win.destroy()
                    except:
                        pass
                    s2.set()
                
                ok_btn = tk.Button(bf, text="✓ 确认位置", font=("微软雅黑",11,"bold"), 
                                  bg="#27ae60", fg="white", command=ok2, width=14, pady=3)
                ok_btn.pack(side=tk.LEFT, padx=5)
                ok_btn.focus_set()
                
                tk.Button(bf, text="取消", font=("微软雅黑",10), command=cancel2, width=8, pady=3).pack(side=tk.RIGHT, padx=5)
                
                win.bind('<Return>', lambda e: ok2())
                win.protocol("WM_DELETE_WINDOW", cancel2)
            
            self.root.after(300, show_step2)
            s2.wait()
            
            if r2["cancel"]:
                self._log("校准已取消")
                self._finish_calib()
                return
            
            cx, cy = r2["x"], r2["y"]
            ckx = cx - rect.left
            cky = cy - rect.top
            self._log("签到按钮: (%d, %d)" % (ckx, cky))
            
            self.config["avatar_rel_x"] = avx
            self.config["avatar_rel_y"] = avy
            self.config["checkin_rel_x"] = ckx
            self.config["checkin_rel_y"] = cky
            self.config["trae_path"] = tp
            self.config["calibrated"] = True
            save_config(self.config)
            self.trae_path = tp
            
            def upd():
                try:
                    self.ax_var.set(str(avx))
                    self.ay_var.set(str(avy))
                    self.cx_var.set(str(ckx))
                    self.cy_var.set(str(cky))
                    self.checkin_btn.config(state=tk.NORMAL)
                    try:
                        self.warn_label.pack_forget()
                    except:
                        pass
                except:
                    pass
            self.root.after(0, upd)
            
            self._log("测试点击...")
            click_at(rect.left + ww//2, rect.top + wh//2)
            time.sleep(0.2)
            click_at(ax, ay)
            time.sleep(0.4)
            click_at(cx, cy)
            time.sleep(0.15)
            
            ox, oy = get_cursor_pos()
            user32.SetCursorPos(ox, oy)
            
            self._log("===== 校准完成并保存！=====")
            self.root.after(0, lambda: messagebox.showinfo("成功",
                "坐标校准成功！\n\n"
                "头像位置: (%d, %d)\n"
                "签到按钮: (%d, %d)\n\n"
                "现在可以点击「立即签到」了！" % (avx, avy, ckx, cky)))
        except Exception as e:
            self._log("校准失败: " + str(e))
            self.root.after(0, lambda: messagebox.showerror("失败", "校准出错：\n" + str(e)))
        finally:
            self._finish_calib()
    
    def _finish_calib(self):
        self.is_calibrating = False
        try:
            self.root.after(0, lambda: self.calib_btn.config(state=tk.NORMAL, text="开始校准坐标"))
        except:
            pass
    
    def _enable_task(self):
        if self.config.get("avatar_rel_x", -1) < 0:
            messagebox.showwarning("提示", "请先完成坐标校准！")
            return
        
        h = self.hour_var.get().zfill(2)
        m = self.min_var.get().zfill(2)
        rt = "%s:%s" % (h, m)
        
        exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.join(APP_DIR, "dist", "橙子签到.exe")
        if not os.path.exists(exe_path):
            exe_path = os.path.join(APP_DIR, "橙子签到.exe")
        if not os.path.exists(exe_path):
            messagebox.showwarning("提示", "请使用打包后的exe设置自动签到")
            return
        
        self.config["auto_time"] = rt
        save_config(self.config)
        
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "schtasks",
                    '/create /tn "%s" /tr "\"%s\"" /sc daily /st %s /f /rl highest' % (TASK_NAME, exe_path, rt),
                    None, 1)
                time.sleep(1)
                self._update_task_status()
                messagebox.showinfo("提示", "已请求管理员权限，\n请在弹出的对话框点「是」")
                return
            except:
                pass
        
        ok, msg = create_task(exe_path, rt)
        if ok:
            self._log(msg)
            messagebox.showinfo("成功", msg)
        else:
            self._log("设置失败: " + msg)
            messagebox.showerror("失败", msg)
        self._update_task_status()
    
    def _disable_task(self):
        if messagebox.askyesno("确认", "确定要取消每日自动签到吗？"):
            if delete_task():
                self.config["auto_checkin"] = False
                save_config(self.config)
                self._log("已取消自动签到")
                messagebox.showinfo("成功", "已取消每日自动签到！")
            else:
                messagebox.showerror("失败", "取消失败")
            self._update_task_status()

def main():
    try:
        root = tk.Tk()
        app = App(root)
        root.mainloop()
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        try:
            log_path = os.path.join(APP_DIR, "error_log.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(err)
        except:
            pass
        try:
            ctypes.windll.user32.MessageBoxW(0, 
                "程序出错：\n" + str(e) + "\n\n详细信息已保存到 error_log.txt", 
                "橙子签到错误", 0x10)
        except:
            pass

if __name__ == "__main__":
    main()
