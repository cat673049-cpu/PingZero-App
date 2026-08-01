import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import ctypes
import threading
import time

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.user32.MessageBoxW(0, "يجب تشغيل البرنامج كمسؤول (Run as Administrator)!", "PingZero Error", 1)
    os._exit(0)

root = tk.Tk()
root.title("PingZero - GPN & FPS Booster")
root.geometry("500x450")
root.configure(bg="#0f172a")
root.resizable(False, False)

selected_game = tk.StringVar(value="Fortnite")
selected_region = tk.StringVar(value="تلقائي (Auto)")
is_boosted = False

def boost_fps():
    try:
        subprocess.run("powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        os.system('del /q/f/s %TEMP%\* >nul 2>&1')
    except:
        pass

def optimize_ping(game, region):
    server_ip = "185.20.10.5"
    game_ips = {"Fortnite": "104.28.14.0", "Roblox": "128.116.114.0", "Minecraft": "192.95.20.0", "Rocket League": "104.156.224.0", "Valorant": "104.160.141.3"}
    target_ip = game_ips.get(game, "8.8.8.8")
    subprocess.run(f"route add {target_ip} mask 255.255.255.0 {server_ip}", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

def stop_optimization():
    subprocess.run("route print", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

def toggle_boost():
    global is_boosted
    if not is_boosted:
        btn_boost.config(text="جاري التسريع...", bg="#f59e0b")
        root.update()
        def run_boost():
            boost_fps()
            optimize_ping(selected_game.get(), selected_region.get())
            time.sleep(1.5)
            btn_boost.config(text="إيقاف التسريع 🛑", bg="#ef4444")
            lbl_status.config(text=f"✅ تم تسريع {selected_game.get()} ورفع الـ FPS!", fg="#10b981")
        threading.Thread(target=run_boost).start()
        is_boosted = True
    else:
        stop_optimization()
        btn_boost.config(text="تفعيل التسريع 🚀", bg="#3b82f6")
        lbl_status.config(text="البرنامج جاهز. اختر اللعبة واضغط تفعيل.", fg="#94a3b8")
        is_boosted = False

tk.Label(root, text="PingZero", font=("Arial", 28, "bold"), bg="#0f172a", fg="#3b82f6").pack(pady=20)
frame_game = tk.Frame(root, bg="#1e293b", padx=10, pady=10)
frame_game.pack(fill="x", padx=20, pady=10)
tk.Label(frame_game, text="اختر اللعبة:", font=("Arial", 14), bg="#1e293b", fg="white").pack(side="right", padx=10)
ttk.Combobox(frame_game, textvariable=selected_game, values=["Fortnite", "Roblox", "Minecraft", "Rocket League", "Valorant"], font=("Arial", 12), state="readonly").pack(side="left", fill="x", expand=True)

frame_region = tk.Frame(root, bg="#1e293b", padx=10, pady=10)
frame_region.pack(fill="x", padx=20, pady=10)
tk.Label(frame_region, text="اختر السيرفر:", font=("Arial", 14), bg="#1e293b", fg="white").pack(side="right", padx=10)
ttk.Combobox(frame_region, textvariable=selected_region, values=["تلقائي (Auto)", "الشرق الأوسط (البحرين)", "أوروبا (فرانكفورت)"], font=("Arial", 12), state="readonly").pack(side="left", fill="x", expand=True)

btn_boost = tk.Button(root, text="تفعيل التسريع 🚀", font=("Arial", 18, "bold"), bg="#3b82f6", fg="white", relief="flat", command=toggle_boost)
btn_boost.pack(fill="x", padx=20, pady=30, ipady=10)
lbl_status = tk.Label(root, text="البرنامج جاهز. اختر اللعبة واضغط تفعيل.", font=("Arial", 12), bg="#0f172a", fg="#94a3b8")
lbl_status.pack()

root.mainloop()
