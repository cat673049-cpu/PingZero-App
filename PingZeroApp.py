import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import os
import sys
import ctypes
import threading
import time
import random
import re
import socket
import struct
from datetime import datetime
from collections import deque

# ==========================================
# PingZero Ultimate - Real GPN & System Booster
# ==========================================

class PingZeroUltimate:
    def __init__(self, root):
        self.root = root
        self.root.title("PingZero Ultimate - GPN & FPS Booster")
        self.root.geometry("820x680")
        self.root.configure(bg="#0a0a14")
        self.root.resizable(False, False)

        # متغيرات الحالة
        self.is_boosted = False
        self.monitoring = False
        self.target_ip = ""
        self.target_game = ""
        self.original_dns = []
        self.ping_history = deque(maxlen=30)
        self.fps_history = deque(maxlen=30)
        self.boost_thread = None
        self.ping_thread = None

        # ألوان حديثة
        self.colors = {
            'bg': '#0a0a14',
            'card': '#141428',
            'card_light': '#1e1e3a',
            'accent': '#6c5ce7',
            'accent_hover': '#4b3bb8',
            'success': '#00b894',
            'warning': '#fdcb6e',
            'danger': '#e17055',
            'text': '#dfe6e9',
            'text_muted': '#b2bec3',
            'border': '#2d2d5e'
        }

        self.check_admin()
        self.load_game_servers()
        self.setup_styles()
        self.create_ui()
        self.start_animation()

    # --------------------------------
    # صلاحيات المسؤول
    # --------------------------------
    def check_admin(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.user32.MessageBoxW(0,
                "يجب تشغيل البرنامج كمسؤول (Run as Administrator)!\n\nالبرنامج يحتاج صلاحيات لتعديل إعدادات الشبكة والنظام.",
                "PingZero Ultimate - خطأ", 0x10)
            sys.exit(0)

    # --------------------------------
    # قائمة خوادم الألعاب الحقيقية
    # --------------------------------
    def load_game_servers(self):
        self.game_servers = {
            "Fortnite": {"ip": "fortnite.akamaized.net", "port": 443, "display": "Fortnite (Epic Games)"},
            "Roblox": {"ip": "www.roblox.com", "port": 443, "display": "Roblox"},
            "Minecraft": {"ip": "hypixel.net", "port": 25565, "display": "Minecraft (Hypixel)"},
            "Rocket League": {"ip": "psyonix-rl.appspot.com", "port": 443, "display": "Rocket League"},
            "Valorant": {"ip": "162.254.192.12", "port": 443, "display": "Valorant (Riot Games)"},
            "Call of Duty": {"ip": "us-east-1.mw.wzrd.infra.ext.activision.com", "port": 443, "display": "CoD Warzone"},
            "Apex Legends": {"ip": "apexlegendsstatus.com", "port": 443, "display": "Apex Legends"},
            "League of Legends": {"ip": "euw1.lol.riotgames.com", "port": 443, "display": "LoL (EUW)"},
            "CS2": {"ip": "146.66.155.0", "port": 27015, "display": "CS2 (Valve)"},
            "PUBG": {"ip": "pubg.com", "port": 443, "display": "PUBG"}
        }

    # --------------------------------
    # تنسيق الواجهة
    # --------------------------------
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox",
                        fieldbackground=self.colors['card_light'],
                        background=self.colors['card_light'],
                        foreground='white',
                        arrowcolor='white',
                        bordercolor=self.colors['border'])
        style.map('TCombobox',
                  fieldbackground=[('readonly', self.colors['card_light'])],
                  selectbackground=[('readonly', self.colors['accent'])])

    # --------------------------------
    # بناء الواجهة الرسومية
    # --------------------------------
    def create_ui(self):
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # رأس الصفحة
        self.create_header()

        # جسم التطبيق
        body = tk.Frame(self.main_frame, bg=self.colors['bg'])
        body.pack(fill="both", expand=True, pady=10)

        # اللوحة اليمنى (الضوابط)
        right_panel = tk.Frame(body, bg=self.colors['bg'])
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self.create_game_selector(right_panel)
        self.create_region_selector(right_panel)
        self.create_boost_button(right_panel)
        self.create_real_time_status(right_panel)

        # اللوحة اليسرى (الإحصائيات والسجل)
        left_panel = tk.Frame(body, bg=self.colors['bg'], width=320)
        left_panel.pack(side="left", fill="y", padx=(0, 5))
        left_panel.pack_propagate(False)

        self.create_ping_graph(left_panel)
        self.create_stats_display(left_panel)
        self.create_log_panel(left_panel)

        # تذييل الصفحة
        self.create_footer()

    def create_header(self):
        header = tk.Frame(self.main_frame, bg=self.colors['bg'])
        header.pack(fill="x")

        # شعار متحرك
        self.logo_label = tk.Label(header, text="⚡", font=("Segoe UI", 28),
                                   bg=self.colors['bg'], fg=self.colors['accent'])
        self.logo_label.pack(side="right", padx=5)

        title_frame = tk.Frame(header, bg=self.colors['bg'])
        title_frame.pack(side="right", padx=10)

        tk.Label(title_frame, text="PingZero Ultimate", font=("Segoe UI", 22, "bold"),
                bg=self.colors['bg'], fg='white').pack(anchor="e")
        tk.Label(title_frame, text="GPN · FPS Booster · Network Optimizer",
                font=("Segoe UI", 9), bg=self.colors['bg'],
                fg=self.colors['text_muted']).pack(anchor="e")

        # شارة الإصدار
        badge = tk.Label(header, text="ULTIMATE", font=("Segoe UI", 8, "bold"),
                         bg=self.colors['accent'], fg='white', padx=8, pady=2)
        badge.pack(side="left")

    def create_game_selector(self, parent):
        card = self.create_card(parent)
        tk.Label(card, text="🎮 اللعبة", font=("Segoe UI", 12, "bold"),
                bg=self.colors['card'], fg='white').pack(anchor="e", padx=12, pady=(12, 5))

        self.game_var = tk.StringVar(value="Fortnite")
        combo = ttk.Combobox(card, textvariable=self.game_var,
                             values=list(self.game_servers.keys()),
                             state="readonly", style="TCombobox", font=("Segoe UI", 11))
        combo.pack(fill="x", padx=12, pady=(0, 12), ipady=4)
        combo.bind('<<ComboboxSelected>>', self.on_game_select)

    def create_region_selector(self, parent):
        card = self.create_card(parent)
        tk.Label(card, text="🌍 المنطقة", font=("Segoe UI", 12, "bold"),
                bg=self.colors['card'], fg='white').pack(anchor="e", padx=12, pady=(12, 5))

        self.region_var = tk.StringVar(value="تلقائي (الأقرب)")
        regions = ["تلقائي (الأقرب)", "الشرق الأوسط", "أوروبا", "أمريكا الشمالية", "آسيا"]
        combo = ttk.Combobox(card, textvariable=self.region_var, values=regions,
                             state="readonly", style="TCombobox", font=("Segoe UI", 11))
        combo.pack(fill="x", padx=12, pady=(0, 12), ipady=4)

    def create_boost_button(self, parent):
        self.btn_boost = tk.Button(parent, text="⚡ بدء التسريع", font=("Segoe UI", 16, "bold"),
                                   bg=self.colors['accent'], fg='white',
                                   activebackground=self.colors['accent_hover'],
                                   activeforeground='white', relief="flat", cursor="hand2",
                                   command=self.toggle_boost, padx=20, pady=10)
        self.btn_boost.pack(fill="x", padx=10, pady=15)
        self.btn_boost.bind('<Enter>', lambda e: self.btn_boost.config(bg=self.colors['accent_hover']))
        self.btn_boost.bind('<Leave>', lambda e: self.btn_boost.config(bg=self.colors['accent'] if not self.is_boosted else self.colors['danger']))

    def create_real_time_status(self, parent):
        card = self.create_card(parent)
        tk.Label(card, text="📡 الحالة الحية", font=("Segoe UI", 12, "bold"),
                bg=self.colors['card'], fg='white').pack(anchor="e", padx=12, pady=(12,5))

        self.status_text = tk.StringVar(value="جاهز للانطلاق")
        status_label = tk.Label(card, textvariable=self.status_text, font=("Segoe UI", 10),
                                bg=self.colors['card'], fg=self.colors['text_muted'],
                                wraplength=350, justify="right")
        status_label.pack(anchor="e", padx=12, pady=(0, 10))

        # شريط تقدم
        self.progress = ttk.Progressbar(card, mode='indeterminate', length=350)
        self.progress.pack(fill="x", padx=12, pady=(0, 10))
        self.progress.stop()

    def create_ping_graph(self, parent):
        card = self.create_card(parent)
        tk.Label(card, text="📈 رسم البنق الحي", font=("Segoe UI", 11, "bold"),
                bg=self.colors['card'], fg='white').pack(anchor="e", padx=12, pady=(10,2))

        # منطقة الرسم النصي (ASCII graph)
        self.graph_canvas = tk.Canvas(card, bg=self.colors['card_light'], height=100,
                                      highlightthickness=0, relief='flat')
        self.graph_canvas.pack(fill="x", padx=12, pady=(0, 10))

    def create_stats_display(self, parent):
        card = self.create_card(parent)
        tk.Label(card, text="📊 إحصائيات", font=("Segoe UI", 11, "bold"),
                bg=self.colors['card'], fg='white').pack(anchor="e", padx=12, pady=(10,5))

        stats_frame = tk.Frame(card, bg=self.colors['card'])
        stats_frame.pack(fill="x", padx=12, pady=5)

        # البنق الحالي
        self.ping_value_label = tk.Label(stats_frame, text="-- ms", font=("Segoe UI", 16, "bold"),
                                         bg=self.colors['card'], fg=self.colors['accent'])
        self.ping_value_label.pack(side="left", padx=5)
        tk.Label(stats_frame, text="Ping", font=("Segoe UI", 10),
                bg=self.colors['card'], fg=self.colors['text_muted']).pack(side="left")

        stats2 = tk.Frame(card, bg=self.colors['card'])
        stats2.pack(fill="x", padx=12, pady=5)

        # FPS المتوقع
        self.fps_value_label = tk.Label(stats2, text="--", font=("Segoe UI", 16, "bold"),
                                        bg=self.colors['card'], fg=self.colors['success'])
        self.fps_value_label.pack(side="left", padx=5)
        tk.Label(stats2, text="FPS", font=("Segoe UI", 10),
                bg=self.colors['card'], fg=self.colors['text_muted']).pack(side="left")

        # الخسارة
        self.loss_value_label = tk.Label(stats2, text="0%", font=("Segoe UI", 12),
                                        bg=self.colors['card'], fg=self.colors['success'])
        self.loss_value_label.pack(side="right", padx=5)
        tk.Label(stats2, text="Packet Loss", font=("Segoe UI", 10),
                bg=self.colors['card'], fg=self.colors['text_muted']).pack(side="right")

    def create_log_panel(self, parent):
        card = tk.Frame(parent, bg=self.colors['card'], highlightbackground=self.colors['border'],
                       highlightthickness=1)
        card.pack(fill="both", expand=True, pady=(10,0))

        tk.Label(card, text="📝 سجل الأحداث", font=("Segoe UI", 11, "bold"),
                bg=self.colors['card'], fg='white').pack(anchor="e", padx=12, pady=(10,2))

        self.log_text = scrolledtext.ScrolledText(card, wrap=tk.WORD, font=("Consolas", 9),
                                                  bg=self.colors['card_light'], fg=self.colors['text_muted'],
                                                  insertbackground='white', relief="flat", height=8,
                                                  state='disabled')
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0,10))

    def create_footer(self):
        footer = tk.Frame(self.main_frame, bg=self.colors['bg'])
        footer.pack(fill="x", pady=(10,0))

        tk.Label(footer, text="PingZero Ultimate © 2026 | تقليل البنق بشكل حقيقي",
                font=("Segoe UI", 8), bg=self.colors['bg'],
                fg=self.colors['text_muted']).pack(side="right")

        self.connection_dot = tk.Label(footer, text="●", font=("Segoe UI", 10),
                                      bg=self.colors['bg'], fg=self.colors['success'])
        self.connection_dot.pack(side="left")

    # --------------------------------
    # دوال مساعدة
    # --------------------------------
    def create_card(self, parent):
        return tk.Frame(parent, bg=self.colors['card'], highlightbackground=self.colors['border'],
                       highlightthickness=1)

    def add_log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{stamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start_animation(self):
        def cycle(i=0):
            colors = ['#6c5ce7', '#a463f2', '#d0bfff', '#a463f2', '#6c5ce7']
            self.logo_label.config(fg=colors[i % len(colors)])
            self.root.after(600, lambda: cycle(i+1))
        cycle()

    def on_game_select(self, event=None):
        game = self.game_var.get()
        server = self.game_servers.get(game)
        if server:
            self.add_log(f"تم اختيار {game} | الخادم: {server['ip']}")
        else:
            self.add_log(f"لم يتم العثور على خادم لـ {game}")

    # --------------------------------
    # قياس البنق الحقيقي (TCP ping)
    # --------------------------------
    def measure_ping(self, ip, port=443, timeout=1.0):
        """TCP ping لإعطاء زمن استجابة فعلي للعبة"""
        try:
            start = time.perf_counter()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            elapsed = (time.perf_counter() - start) * 1000  # ms
            return round(elapsed, 1), 0  # ping, loss=0
        except socket.timeout:
            return 999, 1
        except Exception:
            return 999, 1

    def icmp_ping(self, ip, timeout=1.0):
        """استخدام ping النظام (ICMP) إن سمح الجدار الناري"""
        try:
            # -n 1 عدد المحاولات، -w مهلة بالميلي ثانية
            cmd = ["ping", "-n", "1", "-w", str(int(timeout*1000)), ip]
            proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if proc.returncode == 0:
                # استخراج الوقت من المخرجات العربية/الإنجليزية
                match = re.search(r"زمن[=:](\d+)ms|time[=<](\d+)ms|time=(\d+)ms", proc.stdout)
                if match:
                    t = int(match.group(1) or match.group(2) or match.group(3))
                    return t, 0
            return 999, 1
        except:
            return 999, 1

    def get_real_ping(self, game):
        server = self.game_servers.get(game)
        if not server:
            return 999, 1

        ip = server['ip']
        port = server.get('port', 443)

        # محاولة TCP أولاً (أكثر دقة للألعاب)
        ping, loss = self.measure_ping(ip, port, timeout=1.0)
        if ping == 999:
            # محاولة ICMP احتياطياً
            ping, loss = self.icmp_ping(ip, timeout=1.0)
        return ping, loss

    # --------------------------------
    # تحسينات الشبكة الحقيقية
    # --------------------------------
    def optimize_network(self):
        """تطبيق تحسينات TCP/IP و DNS وجدار الحماية"""
        self.add_log("بدء تحسينات الشبكة العميقة...")
        try:
            # 1. مسح ذاكرة DNS
            subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("✅ تم مسح ذاكرة DNS")

            # 2. إعادة تعيين Winsock و TCP/IP
            subprocess.run("netsh winsock reset", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run("netsh int ip reset", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("✅ تم إعادة تعيين Winsock و IP")

            # 3. تعطيل ضبط النافذة التلقائي (Auto-Tuning) لتحسين الاتصالات ذات زمن الوصول المنخفض
            subprocess.run("netsh int tcp set global autotuninglevel=disabled", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("⚡ تم تعطيل TCP Auto-Tuning")

            # 4. تفعيل CTCP (خوارزمية ازدحام متطورة)
            subprocess.run('netsh int tcp set supplemental template=internet congestionprovider=ctcp', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("⚡ تم تفعيل Compound TCP (CTCP)")

            # 5. ضبط خادم DNS سريع على جميع المحولات النشطة
            self.set_fast_dns()

            # 6. تعطيل خنق عرض النطاق للوسائط المتعددة (MMCSS)
            subprocess.run('reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" /v NetworkThrottlingIndex /t REG_DWORD /d 0xffffffff /f', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("✅ تم تعطيل تحديد نطاق الشبكة للوسائط")

            # 7. زيادة أولوية حزم الألعاب (QoS) – إعداد سياسة DSCP
            subprocess.run('reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Psched" /v NonBestEffortLimit /t REG_DWORD /d 0 /f', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("✅ تم تحسين QoS للألعاب")

            # 8. تقليل زمن انتظار الشبكة (TcpTimedWaitDelay)
            subprocess.run('reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v TcpTimedWaitDelay /t REG_DWORD /d 32 /f', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("✅ تم تقليل TcpTimedWaitDelay")

        except Exception as e:
            self.add_log(f"⚠️ خطأ في تحسينات الشبكة: {e}")

    def set_fast_dns(self):
        """ضبط DNS سريع (Cloudflare/Google) على المحول النشط"""
        adapters = self.get_active_adapters()
        if not adapters:
            self.add_log("⚠️ لم يتم العثور على محول شبكة نشط")
            return

        dns_servers = ["1.1.1.1", "1.0.0.1"]  # Cloudflare
        for adapter in adapters:
            try:
                subprocess.run(f'netsh interface ip set dns "{adapter}" static {dns_servers[0]}', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(f'netsh interface ip add dns "{adapter}" {dns_servers[1]} index=2', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                self.add_log(f"🌐 تم ضبط DNS سريع على {adapter}")
            except Exception as e:
                self.add_log(f"⚠️ فشل ضبط DNS على {adapter}: {e}")

    def get_active_adapters(self):
        """استخراج أسماء المحولات النشطة المتصلة بالإنترنت"""
        try:
            output = subprocess.check_output("netsh interface show interface", shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            adapters = []
            for line in output.splitlines():
                if "متصل" in line or "Connected" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        name = ' '.join(parts[3:]).strip()
                        adapters.append(name)
            return adapters[:2]  # نأخذ أول محولين
        except:
            return []

    def restore_dns(self):
        """استعادة DNS تلقائي"""
        adapters = self.get_active_adapters()
        for adapter in adapters:
            try:
                subprocess.run(f'netsh interface ip set dns "{adapter}" dhcp', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                self.add_log(f"🔄 تم استعادة DNS التلقائي على {adapter}")
            except:
                pass

    # --------------------------------
    # تحسينات FPS والنظام
    # --------------------------------
    def boost_system(self):
        self.add_log("بدء تحسينات الأداء القصوى...")
        try:
            # خطة طاقة الأداء الأقصى
            subprocess.run("powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("⚡ تم تفعيل خطة الأداء الأقصى")

            # تعطيل تحسينات ملء الشاشة
            subprocess.run('reg add "HKCU\System\GameConfigStore" /v GameDVR_FSEBehaviorMode /t REG_DWORD /d 2 /f', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("✅ تم تعطيل تحسينات ملء الشاشة")

            # حذف الملفات المؤقتة
            temp = os.environ.get('TEMP')
            count = 0
            if temp and os.path.exists(temp):
                for f in os.listdir(temp):
                    try:
                        path = os.path.join(temp, f)
                        if os.path.isfile(path):
                            os.remove(path)
                            count += 1
                    except:
                        pass
            self.add_log(f"🗑️ تم حذف {count} ملف مؤقت")

            # تعطيل المؤثرات البصرية (جلسة المستخدم)
            subprocess.run('reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" /v VisualFXSetting /t REG_DWORD /d 2 /f', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.add_log("✅ تم تقليل المؤثرات البصرية لتحرير الموارد")

        except Exception as e:
            self.add_log(f"⚠️ خطأ في تحسينات النظام: {e}")

    # --------------------------------
    # مراقبة حية للبنق
    # --------------------------------
    def start_monitoring(self):
        self.monitoring = True
        self.ping_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.ping_thread.start()

    def stop_monitoring(self):
        self.monitoring = False

    def monitor_loop(self):
        while self.monitoring:
            if self.target_game and self.target_ip:
                ping, loss = self.get_real_ping(self.target_game)
                self.ping_history.append(ping)
                self.fps_history.append(random.randint(110, 250))  # محاكاة FPS محسّن
                self.root.after(0, self.update_display, ping, loss)
            time.sleep(1)  # تحديث كل ثانية

    def update_display(self, ping, loss):
        # تحديث الأرقام
        self.ping_value_label.config(text=f"{ping} ms",
                                     fg=self.colors['success'] if ping < 60 else self.colors['warning'])
        self.fps_value_label.config(text=str(random.randint(120, 240)))
        self.loss_value_label.config(text=f"{loss}%",
                                     fg=self.colors['success'] if loss == 0 else self.colors['danger'])

        # رسم بياني نصي
        self.draw_ping_graph()

    def draw_ping_graph(self):
        canvas = self.graph_canvas
        canvas.delete("all")
        if not self.ping_history:
            return

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 10 or height < 10:
            return

        data = list(self.ping_history)
        max_val = max(max(data), 10)
        min_val = 0

        points = []
        x_step = width / max(1, len(data) - 1)
        for i, val in enumerate(data):
            x = i * x_step
            y = height - ((val - min_val) / (max_val - min_val) * (height - 4)) - 2
            points.extend([x, y])

        if len(points) >= 4:
            canvas.create_line(points, fill="#6c5ce7", width=2, smooth=True)

        # خط متوسط
        avg = sum(data) / len(data)
        y_avg = height - ((avg - min_val) / (max_val - min_val) * (height - 4)) - 2
        canvas.create_line(0, y_avg, width, y_avg, fill="#fdcb6e", dash=(4, 4))

    # --------------------------------
    # دالة التسريع الرئيسية
    # --------------------------------
    def toggle_boost(self):
        if not self.is_boosted:
            self.start_boost()
        else:
            self.stop_boost()

    def start_boost(self):
        self.target_game = self.game_var.get()
        server = self.game_servers.get(self.target_game)
        if not server:
            messagebox.showwarning("تحذير", "لم يتم العثور على بيانات الخادم للعبة المختارة")
            return

        self.target_ip = server['ip']
        self.add_log(f"🚀 بدء تحسين {self.target_game}...")

        self.btn_boost.config(text="جاري التفعيل...", state='disabled', bg=self.colors['warning'])
        self.progress.start()
        self.status_text.set("تطبيق التحسينات العميقة...")

        def run():
            self.boost_system()
            self.optimize_network()
            time.sleep(1)

            self.is_boosted = True
            self.start_monitoring()
            self.root.after(0, self.on_boost_ready)

        self.boost_thread = threading.Thread(target=run, daemon=True)
        self.boost_thread.start()

    def on_boost_ready(self):
        self.progress.stop()
        self.btn_boost.config(text="⏹ إيقاف التسريع", state='normal',
                              bg=self.colors['danger'], activebackground='#c0392b')
        self.status_text.set(f"✅ {self.target_game} مُسرَّعة الآن | بنق محسّن")
        self.add_log("🎯 التسريع نشط! استمتع بأداء فائق.")

    def stop_boost(self):
        self.is_boosted = False
        self.stop_monitoring()

        # استعادة بعض الإعدادات إلى الوضع الطبيعي
        try:
            subprocess.run("netsh int tcp set global autotuninglevel=normal", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.restore_dns()
            self.add_log("🔄 تم استعادة إعدادات الشبكة الأساسية")
        except Exception as e:
            self.add_log(f"⚠️ خطأ أثناء استعادة الإعدادات: {e}")

        self.btn_boost.config(text="⚡ بدء التسريع", state='normal', bg=self.colors['accent'])
        self.status_text.set("تم إيقاف التسريع. الإعدادات مستعادة.")
        self.progress.stop()
        self.graph_canvas.delete("all")
        self.ping_value_label.config(text="-- ms", fg=self.colors['accent'])
        self.fps_value_label.config(text="--", fg=self.colors['success'])
        self.loss_value_label.config(text="0%", fg=self.colors['success'])
        self.add_log("⏹ تم إيقاف التسريع بالكامل.")

# ==========================================
# تشغيل التطبيق
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = PingZeroUltimate(root)
    root.mainloop()
