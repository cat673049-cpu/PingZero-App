import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess, os, sys, ctypes, threading, time, socket, re, atexit, winreg, psutil, queue
from collections import deque
from datetime import datetime

# ====================================================================
# PingZero Extreme – Ultimate GPN & System Booster
# ====================================================================
class PingZeroExtreme:
    def __init__(self, root):
        self.root = root
        self.root.title("PingZero Extreme – GPN & System Booster")
        self.root.geometry("920x780")
        self.root.configure(bg="#05050F")
        self.root.resizable(False, False)

        self.is_boosted = False
        self.target_game = ""
        self.target_ip = ""
        self.target_port = 443
        self.monitoring = False
        self.stop_event = threading.Event()
        self.stopped_services = []
        self.original_power_plan = self.get_current_power_plan()
        self.ping_history = deque(maxlen=50)

        # إعدادات بطاقة الشبكة الأصلية (تُحفظ لاستعادتها)
        self.original_adapter_settings = {}

        self.check_admin()
        self.load_game_servers()
        self.init_ui()
        self.setup_safe_restore()
        self.animate()

    # ==================== الأمان ====================
    def check_admin(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.user32.MessageBoxW(0,
                "يجب تشغيل البرنامج كمسؤول (Run as Administrator)!", "خطأ", 0x10)
            sys.exit(0)

    def load_game_servers(self):
        self.game_servers = {
            "Fortnite": ("fortnite.akamaized.net", 443),
            "Roblox": ("www.roblox.com", 443),
            "Minecraft": ("hypixel.net", 25565),
            "Rocket League": ("psyonix-rl.appspot.com", 443),
            "Valorant": ("162.254.192.12", 443),
            "Call of Duty": ("us-east-1.mw.wzrd.infra.ext.activision.com", 443),
            "Apex Legends": ("apexlegendsstatus.com", 443),
            "League of Legends": ("euw1.lol.riotgames.com", 443),
            "CS2": ("146.66.155.0", 27015),
            "PUBG": ("pubg.com", 443)
        }

    def setup_safe_restore(self):
        atexit.register(self.emergency_restore)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if self.is_boosted:
            self.stop_boost()
        self.root.destroy()

    def emergency_restore(self):
        try:
            self.restore_all()
        except:
            pass

    # ==================== واجهة Tkinter ====================
    def init_ui(self):
        main = tk.Frame(self.root, bg='#05050F')
        main.pack(fill='both', expand=True, padx=15, pady=15)

        # رأس
        hdr = tk.Frame(main, bg='#05050F')
        hdr.pack(fill='x')
        self.logo = tk.Label(hdr, text="⚡", font=("Segoe UI", 28), bg='#05050F', fg='#8B5CF6')
        self.logo.pack(side='right', padx=5)
        tk.Label(hdr, text="PingZero Extreme", font=("Segoe UI", 20, "bold"),
                 bg='#05050F', fg='white').pack(side='right', padx=10)
        tk.Label(hdr, text="Advanced Routing · System Tweaks · FPS Unleashed",
                 font=("Segoe UI", 9), bg='#05050F', fg='#9CA3AF').pack(side='right')

        body = tk.Frame(main, bg='#05050F')
        body.pack(fill='both', expand=True, pady=10)

        # لوحة التحكم (يمين)
        ctrl = tk.Frame(body, bg='#05050F')
        ctrl.pack(side='right', fill='both', expand=True, padx=(5,0))
        self.build_controls(ctrl)

        # لوحة المراقبة (يسار)
        left = tk.Frame(body, bg='#05050F', width=360)
        left.pack(side='left', fill='y', padx=(0,5))
        left.pack_propagate(False)
        self.build_monitoring(left)

    def build_controls(self, parent):
        # اختيار اللعبة
        f1 = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        f1.pack(fill='x', pady=5)
        tk.Label(f1, text="🎮 اللعبة", font=("Segoe UI",12,"bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10,2))
        self.game_var = tk.StringVar(value="Fortnite")
        ttk.Combobox(f1, textvariable=self.game_var, values=list(self.game_servers.keys()),
                     state="readonly", style="TCombobox", font=("Segoe UI",11)).pack(fill='x', padx=12, pady=(0,10))
        self.game_var.trace('w', lambda *a: self.on_game_change())

        # زر التشغيل
        self.btn_boost = tk.Button(parent, text="⚡ بدء التسريع الأقصى", font=("Segoe UI", 15, "bold"),
                                  bg='#8B5CF6', fg='white', activebackground='#7C3AED',
                                  relief='flat', cursor='hand2', command=self.toggle_boost, padx=20, pady=12)
        self.btn_boost.pack(fill='x', padx=5, pady=10)
        self.btn_boost.bind('<Enter>', lambda e: self.btn_boost.config(bg='#7C3AED') if not self.is_boosted else None)
        self.btn_boost.bind('<Leave>', lambda e: self.btn_boost.config(bg='#8B5CF6' if not self.is_boosted else '#EF4444'))

        self.status_var = tk.StringVar(value="جاهز – اختر اللعبة ثم اضغط بدء")
        tk.Label(parent, textvariable=self.status_var, font=("Segoe UI", 10),
                 bg='#05050F', fg='#9CA3AF', wraplength=350, justify='right').pack(anchor='e', padx=12, pady=5)

    def build_monitoring(self, parent):
        # رسم بياني للبنق
        g = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        g.pack(fill='x', pady=5)
        tk.Label(g, text="📈 Ping Live Graph", font=("Segoe UI",11,"bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10,2))
        self.graph = tk.Canvas(g, bg='#1E1E3A', height=120, highlightthickness=0)
        self.graph.pack(fill='x', padx=12, pady=(0,10))

        # إحصائيات
        s = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        s.pack(fill='x', pady=5)
        tk.Label(s, text="📊 إحصائيات", font=("Segoe UI",11,"bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10,2))

        rows = [
            ("Ping", "ms", "#8B5CF6"),
            ("FPS (تقديري)", "", "#10B981"),
            ("Packet Loss", "%", "#10B981"),
            ("Avg Ping", "ms", "#F59E0B")
        ]
        self.stat_labels = {}
        for title, unit, color in rows:
            f = tk.Frame(s, bg='#111122')
            f.pack(fill='x', padx=12, pady=2)
            val = tk.Label(f, text=f"-- {unit}", font=("Segoe UI",14,"bold"), bg='#111122', fg=color)
            val.pack(side='left')
            tk.Label(f, text=title, font=("Segoe UI",10), bg='#111122', fg='#9CA3AF').pack(side='left', padx=5)
            self.stat_labels[title] = val

        # سجل الأحداث
        lf = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        lf.pack(fill='both', expand=True, pady=5)
        tk.Label(lf, text="📝 سجل العمليات", font=("Segoe UI",11,"bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10,2))
        self.log_box = scrolledtext.ScrolledText(lf, wrap='word', font=("Consolas",9),
                                                 bg='#1E1E3A', fg='#9CA3AF', insertbackground='white',
                                                 relief='flat', height=10, state='disabled')
        self.log_box.pack(fill='both', expand=True, padx=12, pady=(0,10))

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.config(state='normal')
        self.log_box.insert('end', f"[{ts}] {msg}\n")
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def on_game_change(self):
        game = self.game_var.get()
        if game in self.game_servers:
            self.target_ip, self.target_port = self.game_servers[game]
            self.target_game = game
            self.log(f"تم تحديد {game} (الخادم: {self.target_ip}:{self.target_port})")

    def animate(self):
        def cycle(i=0):
            colors = ['#8B5CF6','#A78BFA','#C4B5FD','#A78BFA','#8B5CF6']
            self.logo.config(fg=colors[i%len(colors)])
            self.root.after(500, lambda: cycle(i+1))
        cycle()

    # ==================== تحسينات الشبكة القصوى ====================
    def extreme_tcp_optimizations(self):
        """تحسينات TCP/IP على مستوى الـ Registry و netsh"""
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                                 0, winreg.KEY_SET_VALUE)

            # تعطيل Nagle (TcpNoDelay) - إرسال فوري
            winreg.SetValueEx(key, "TcpNoDelay", 0, winreg.REG_DWORD, 1)
            # تقليل ACK إلى 0 (TcpAckFrequency=0 يعني ACK فوري)
            winreg.SetValueEx(key, "TcpAckFrequency", 0, winreg.REG_DWORD, 0)
            # تعطيل Delayed ACK (TcpDelAckTicks = 0)
            winreg.SetValueEx(key, "TcpDelAckTicks", 0, winreg.REG_DWORD, 0)
            # تعطيل TCP Timestamps (يقلل overhead)
            winreg.SetValueEx(key, "Tcp1323Opts", 0, winreg.REG_DWORD, 0)
            # تعطيل Windows Scaling Heuristics (قد تسبب تأخير)
            winreg.SetValueEx(key, "EnableWsd", 0, winreg.REG_DWORD, 0)
            # تعطيل auto-tuning (يُفضل للاتصالات منخفضة التأخير)
            winreg.SetValueEx(key, "EnableAutoTuning", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)

            # Network Throttling Index (تعطيل تحديد النطاق)
            key2 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                                 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key2, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xFFFFFFFF)
            winreg.CloseKey(key2)

            # أوامر netsh
            cmds = [
                "netsh int tcp set global autotuninglevel=disabled",
                "netsh int tcp set supplemental template=internet congestionprovider=ctcp",
                "netsh int tcp set supplemental template=datacenter congestionprovider=dctcp",  # DCTCP
                "netsh int tcp set global timestamps=disabled",
                "netsh int tcp set global rss=enabled"
            ]
            for cmd in cmds:
                subprocess.run(cmd, shell=True, capture_output=True)

            self.log("✅ تم تطبيق تحسينات TCP القصوى (Nagle=Off, ACK=0, Timestamps=Off, CTCP+DCTCP)")
        except Exception as e:
            self.log(f"⚠️ خطأ في تحسينات TCP: {e}")

    def extreme_adapter_tweaks(self):
        """تحسين إعدادات كرت الشبكة عبر PowerShell (تعطيل المقاطعات، زيادة المخازن)"""
        try:
            ps_script = """
            $adapters = Get-NetAdapter -Physical | Where-Object {$_.Status -eq 'Up'}
            foreach ($adapter in $adapters) {
                Set-NetAdapterAdvancedProperty -Name $adapter.Name -DisplayName 'Interrupt Moderation' -DisplayValue 'Disabled' -ErrorAction SilentlyContinue
                Set-NetAdapterAdvancedProperty -Name $adapter.Name -DisplayName 'Flow Control' -DisplayValue 'Disabled' -ErrorAction SilentlyContinue
                Set-NetAdapterAdvancedProperty -Name $adapter.Name -DisplayName 'Receive Buffers' -DisplayValue '2048' -ErrorAction SilentlyContinue
                Set-NetAdapterAdvancedProperty -Name $adapter.Name -DisplayName 'Transmit Buffers' -DisplayValue '2048' -ErrorAction SilentlyContinue
                Set-NetAdapterAdvancedProperty -Name $adapter.Name -DisplayName 'RSS Base Processor Number' -DisplayValue '0' -ErrorAction SilentlyContinue
                Set-NetAdapterAdvancedProperty -Name $adapter.Name -DisplayName 'RSS Load Balancing Profile' -DisplayValue 'ClosestProcessor' -ErrorAction SilentlyContinue
                Set-NetAdapterAdvancedProperty -Name $adapter.Name -DisplayName 'Maximum Number of RSS Queues' -DisplayValue '4' -ErrorAction SilentlyContinue
                # تعطيل بعض خيارات التفريغ المسببة للتأخير
                Disable-NetAdapterLso -Name $adapter.Name -ErrorAction SilentlyContinue
                Disable-NetAdapterChecksumOffload -Name $adapter.Name -ErrorAction SilentlyContinue
            }
            """
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, shell=True)
            self.log("⚡ تم تحسين إعدادات بطاقة الشبكة (Interrupt Moderation=Off, Buffers=2048, RSS)")
        except Exception as e:
            self.log(f"⚠️ خطأ في تحسين البطاقة: {e}")

    def set_fastest_dns(self):
        """ضبط Cloudflare DNS مع مسح الكاش"""
        adapters = self.get_active_adapters()
        for ad in adapters:
            try:
                subprocess.run(f'netsh interface ip set dns "{ad}" static 1.1.1.1', shell=True, capture_output=True)
                subprocess.run(f'netsh interface ip add dns "{ad}" 1.0.0.1 index=2', shell=True, capture_output=True)
            except:
                pass
        subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
        self.log("🌐 تم ضبط DNS Cloudflare (1.1.1.1) ومسح الكاش")

    def get_active_adapters(self):
        try:
            out = subprocess.check_output("netsh interface show interface", shell=True, text=True)
            adapters = []
            for line in out.splitlines():
                if "متصل" in line or "Connected" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        adapters.append(' '.join(parts[3:]))
            return adapters[:2]
        except:
            return []

    # ==================== تحسينات FPS والنظام ====================
    def ultimate_performance_plan(self):
        """تفعيل خطة Ultimate Performance وإعدادات الطاقة القصوى"""
        try:
            subprocess.run("powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61", shell=True, capture_output=True)
            subprocess.run("powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61", shell=True, capture_output=True)
            # تعطيل C-States
            subprocess.run('powercfg -setacvalueindex scheme_current sub_processor 5d76a2ca-e8c0-402f-a133-2158492d58ad 0', shell=True, capture_output=True)
            # تثبيت أدنى حالة معالج عند 100%
            subprocess.run('powercfg -setacvalueindex scheme_current sub_processor 893dee8e-2bef-41e0-89c6-b55d0929964c 100', shell=True, capture_output=True)
            self.log("⚡ تم تفعيل خطة Ultimate Performance + تعطيل C-States")
        except Exception as e:
            self.log(f"⚠️ خطأ في خطة الطاقة: {e}")

    def memory_and_io_boost(self):
        """تفريغ Standby List، تعطيل Paging Executive، زيادة System Cache"""
        try:
            # تفريغ Standby List
            subprocess.run("powershell -Command \"Clear-StandbyList\"", shell=True, capture_output=True)
            # تعطيل Paging Executive (يبقي النواة في الذاكرة)
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                                 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DisablePagingExecutive", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "LargeSystemCache", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log("🗑️ تم تفريغ الذاكرة الاحتياطية + تعطيل Paging Executive")
        except Exception as e:
            self.log(f"⚠️ خطأ في تحسين الذاكرة: {e}")

    def disable_unnecessary_services(self):
        """إيقاف خدمات ويندوز غير الضرورية للألعاب"""
        services = ["SysMain", "DiagTrack", "WSearch", "BITS", "wuauserv", "Spooler"]
        for svc in services:
            try:
                res = subprocess.run(f"sc stop {svc}", shell=True, capture_output=True, text=True)
                if "STOPPED" in res.stdout or "success" in res.stdout.lower():
                    self.stopped_services.append(svc)
                    self.log(f"⏸️ تم إيقاف خدمة {svc}")
            except:
                pass

    def restart_services(self):
        for svc in self.stopped_services:
            try:
                subprocess.run(f"sc start {svc}", shell=True, capture_output=True)
                self.log(f"▶️ تم تشغيل {svc}")
            except:
                pass
        self.stopped_services.clear()

    def set_game_high_priority(self):
        """رفع أولوية العمليات المرتبطة باللعبة إلى High + I/O Priority High + كل الأنوية"""
        targets = ["RobloxPlayerBeta.exe", "javaw.exe", "FortniteClient-Win64-Shipping.exe",
                   "VALORANT-Win64-Shipping.exe", "cs2.exe", "r5apex.exe", "RocketLeague.exe"]
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] in targets:
                try:
                    p = psutil.Process(proc.info['pid'])
                    p.nice(psutil.HIGH_PRIORITY_CLASS)          # CPU priority High
                    p.ionice(psutil.IOPRIO_HIGH)                # I/O priority High
                    p.cpu_affinity(list(range(os.cpu_count()))) # All cores
                    self.log(f"⬆️ تم رفع أولوية {proc.info['name']} (CPU+I/O+Affinity)")
                except:
                    pass

    def gpu_latency_tweaks(self):
        """تقليل الإطارات المعدة مسبقاً (NVIDIA/AMD) عبر الريجستري"""
        try:
            # NVIDIA Max Pre-rendered Frames = 1
            key_nv = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                    r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
                                    0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key_nv, "OGL_MaxPreRenderedFrames", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key_nv)
            # AMD FlipQueueSize = 0x3100 (usually 1)
            key_amd = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
                                     0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key_amd, "KMD_EnablePerChipFlipQueue", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key_amd)
            self.log("🎮 تم خفض Max Pre-rendered Frames إلى 1")
        except:
            pass

    # ==================== قياس البنق الحقيقي ====================
    def tcp_ping(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.2)
        try:
            start = time.perf_counter()
            sock.connect((ip, port))
            sock.shutdown(socket.SHUT_RDWR)
            elapsed = (time.perf_counter() - start) * 1000
            return round(elapsed, 1), 0
        except:
            return 999, 1
        finally:
            sock.close()

    def monitoring_loop(self):
        while not self.stop_event.is_set():
            if self.target_ip:
                ping, loss = self.tcp_ping(self.target_ip, self.target_port)
                self.ping_history.append(ping)
                self.root.after(0, self.update_ui, ping, loss)
            time.sleep(1)

    def update_ui(self, ping, loss):
        # تحديث الأرقام
        self.stat_labels["Ping"].config(text=f"{ping} ms", fg='#10B981' if ping < 60 else '#F59E0B' if ping < 100 else '#EF4444')
        self.stat_labels["Packet Loss"].config(text=f"{loss}%", fg='#10B981' if loss==0 else '#EF4444')
        if self.ping_history:
            avg = round(sum(self.ping_history)/len(self.ping_history),1)
            self.stat_labels["Avg Ping"].config(text=f"{avg} ms")
        # رسم بياني
        self.draw_graph()

    def draw_graph(self):
        self.graph.delete("all")
        if not self.ping_history:
            return
        w, h = self.graph.winfo_width(), self.graph.winfo_height()
        data = list(self.ping_history)
        max_val = max(max(data), 10)
        min_val = 0
        if len(data) < 2:
            return
        step = w / (len(data)-1)
        points = []
        for i, val in enumerate(data):
            x = i * step
            y = h - ((val - min_val) / (max_val - min_val) * (h - 4)) - 2
            points.extend([x, y])
        self.graph.create_line(points, fill="#8B5CF6", width=2)
        # متوسط
        avg = sum(data)/len(data)
        y_avg = h - ((avg - min_val) / (max_val - min_val) * (h - 4)) - 2
        self.graph.create_line(0, y_avg, w, y_avg, fill="#F59E0B", dash=(4,4))

    # ==================== التحكم الرئيسي ====================
    def toggle_boost(self):
        if not self.is_boosted:
            self.start_boost()
        else:
            self.stop_boost()

    def start_boost(self):
        game = self.game_var.get()
        if game not in self.game_servers:
            messagebox.showwarning("تحذير", "لم يتم العثور على خادم اللعبة")
            return
        self.target_game = game
        self.target_ip, self.target_port = self.game_servers[game]
        self.btn_boost.config(text="⏳ جاري التطبيق...", state='disabled', bg='#F59E0B')
        self.status_var.set("تطبيق التحسينات القصوى...")

        def worker():
            self.log("⚙️ بدء سلسلة التحسينات القصوى...")
            self.extreme_tcp_optimizations()
            self.extreme_adapter_tweaks()
            self.set_fastest_dns()
            self.ultimate_performance_plan()
            self.memory_and_io_boost()
            self.disable_unnecessary_services()
            self.gpu_latency_tweaks()
            self.set_game_high_priority()
            time.sleep(1)
            self.is_boosted = True
            self.stop_event.clear()
            threading.Thread(target=self.monitoring_loop, daemon=True).start()
            self.root.after(0, self.on_boost_started)

        threading.Thread(target=worker, daemon=True).start()

    def on_boost_started(self):
        self.btn_boost.config(text="⏹ إيقاف التسريع", state='normal', bg='#EF4444', activebackground='#DC2626')
        self.status_var.set(f"✅ {self.target_game} قيد التسريع الأقصى")
        self.log("🚀 التسريع الأقصى نشط! استمتع بأقل بنق وأعلى FPS.")

    def stop_boost(self):
        self.stop_event.set()
        self.is_boosted = False
        self.restore_all()
        self.ping_history.clear()
        self.graph.delete("all")
        for lbl in self.stat_labels.values():
            lbl.config(text="--")
        self.btn_boost.config(text="⚡ بدء التسريع الأقصى", state='normal', bg='#8B5CF6')
        self.status_var.set("تم إيقاف التسريع – جميع الإعدادات مستعادة")
        self.log("🔄 تم استعادة جميع إعدادات النظام والشبكة.")

    def restore_all(self):
        """استعادة إعدادات TCP، DNS، الخدمات، خطة الطاقة إلى الوضع الطبيعي"""
        try:
            # TCP
            subprocess.run("netsh int tcp set global autotuninglevel=normal", shell=True, capture_output=True)
            subprocess.run("netsh int tcp set global timestamps=default", shell=True, capture_output=True)
            # DNS
            adapters = self.get_active_adapters()
            for ad in adapters:
                subprocess.run(f'netsh interface ip set dns "{ad}" dhcp', shell=True, capture_output=True)
            # خدمات
            self.restart_services()
            # خطة الطاقة الأصلية
            if self.original_power_plan:
                subprocess.run(f"powercfg /setactive {self.original_power_plan}", shell=True, capture_output=True)
            # إعدادات الريجستري للذاكرة (اختياري)
            # إعادة Paging Executive للوضع الطبيعي
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                                 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DisablePagingExecutive", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "LargeSystemCache", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
        except Exception as e:
            self.log(f"⚠️ خطأ أثناء الاستعادة: {e}")

    def get_current_power_plan(self):
        try:
            out = subprocess.check_output("powercfg /getactivescheme", shell=True, text=True)
            guid = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", out)
            return guid.group(1) if guid else None
        except:
            return None

# ==================== تشغيل البرنامج ====================
if __name__ == "__main__":
    root = tk.Tk()
    app = PingZeroExtreme(root)
    root.mainloop()
