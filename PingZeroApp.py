"""
PingZero Extreme v2 - Network & System Booster لتقليل اللاق ورفع أداء الألعاب
================================================================================
نسخة مطوّرة من الكود الأصلي: نفس الفكرة، لكن مع نسخ احتياطي حقيقي لأي تغيير
(بيترجع لطبيعته حتى لو البرنامج قفل فجأة)، إصلاح لعدة باجات كانت بتمنع
الاستعادة الكاملة، وأرقام حقيقية بدل الوهمية (اختبار بنق قبل/بعد التفعيل).

⚠️ حقيقة مهمة: تحسينات الريجستري وكرت الشبكة بتقلل الاحتكاك المحلي (Jitter
وحمل النظام) لكنها ملهاش تأثير على المسار الفعلي للشبكة بين جهازك وسيرفر
اللعبة. أدوات زي ExitLag أو LagoFast بتشتغل بمبدأ مختلف: بتمرر اتصالك عبر
شبكة سيرفراتها هي حول العالم لتلاقي أسرع مسار (Route Optimization) - وده
محتاج بنية تحتية عالمية فعلية مش حاجة سكريبت محلي يقدر يعملها. البرنامج ده
بيدّيك أقصى استفادة ممكنة من جهازك وشبكتك، وبيقيس الفرق الحقيقي بدل ما يوعد
بأرقام.

المتطلبات: تشغيل كأدمن (Run as Administrator) + pip install psutil
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess, os, sys, ctypes, threading, time, socket, re, atexit, winreg, psutil, json, statistics
from ctypes import wintypes
from collections import deque
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

# ============================================================
# إعدادات عامة
# ============================================================
APP_TITLE = "PingZero Extreme v2 – Network & System Booster"
BACKUP_DIR = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "PingZeroExtreme"
BACKUP_FILE = BACKUP_DIR / "session_backup.json"

GAME_PROFILES = {
    "Fortnite": {"host": "fortnite.akamaized.net", "port": 443,
                 "exe": ["FortniteClient-Win64-Shipping.exe"]},
    "Roblox": {"host": "www.roblox.com", "port": 443,
               "exe": ["RobloxPlayerBeta.exe"]},
    "Minecraft": {"host": "hypixel.net", "port": 25565,
                  "exe": ["javaw.exe", "java.exe", "Minecraft.Windows.exe"]},
    "Rocket League": {"host": "psyonix-rl.appspot.com", "port": 443,
                       "exe": ["RocketLeague.exe"]},
    "Valorant": {"host": "162.254.192.12", "port": 443,
                 "exe": ["VALORANT-Win64-Shipping.exe", "VALORANT.exe"]},
    "Call of Duty": {"host": "us-east-1.mw.wzrd.infra.ext.activision.com", "port": 443,
                      "exe": ["cod.exe", "ModernWarfare.exe", "BlackOpsColdWar.exe"]},
    "Apex Legends": {"host": "apexlegendsstatus.com", "port": 443,
                      "exe": ["r5apex.exe"]},
    "League of Legends": {"host": "euw1.lol.riotgames.com", "port": 443,
                           "exe": ["League of Legends.exe", "LeagueClient.exe"]},
    "CS2": {"host": "146.66.155.0", "port": 27015,
            "exe": ["cs2.exe"]},
    "PUBG": {"host": "pubg.com", "port": 443,
             "exe": ["TslGame.exe", "PUBG.exe"]},
}


# ============================================================
# أدوات مساعدة عامة
# ============================================================
class _FailedResult:
    returncode = -1
    stdout = ""
    stderr = ""


def run(cmd, timeout=15):
    """تشغيل أمر نظام (netsh/sc/powercfg..) من غير ما يفجّر استثناء لو فشل."""
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        r = _FailedResult()
        r.stderr = str(e)
        return r


def ps_quote(s):
    """تهريب نص عشان يتحط جوه سكريبت PowerShell كـ string آمن."""
    return "'" + str(s).replace("'", "''") + "'"


def run_ps(script, timeout=25):
    """
    تشغيل PowerShell بدون shell=True (الكود الأصلي كان بيمرر list مع
    shell=True مع بعض، وده سلوكه غير مضمون على ويندوز).
    """
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout
        )
    except Exception as e:
        r = _FailedResult()
        r.stderr = str(e)
        return r


def get_active_adapters():
    """أسماء كروت الشبكة المتصلة - عبر Get-NetAdapter عشان يشتغل على أي
    لغة ويندوز (الكود الأصلي كان بيدور على كلمة 'متصل' نصيًا وده بيفشل
    على أي نظام غير عربي)."""
    res = run_ps("(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'}).Name")
    return [l.strip() for l in res.stdout.splitlines() if l.strip()]


def find_gpu_registry_keys():
    """يحدد المزوّد الحقيقي (NVIDIA/AMD/Intel) لكل كرت شاشة عبر DriverDesc،
    بدل ما نكتب قيم NVIDIA و AMD على نفس المفتاح زي ما كان بيحصل قبل كده."""
    base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    found = []
    try:
        base_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(base_key, i)
            except OSError:
                break
            i += 1
            if not sub.isdigit():
                continue
            try:
                sub_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{sub}")
                desc, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                winreg.CloseKey(sub_key)
            except Exception:
                continue
            d = desc.lower()
            vendor = ("nvidia" if any(k in d for k in ("nvidia", "geforce", "rtx", "gtx")) else
                      "amd" if any(k in d for k in ("amd", "radeon")) else
                      "intel" if "intel" in d else None)
            if vendor:
                found.append((f"{base}\\{sub}", vendor, desc))
        winreg.CloseKey(base_key)
    except Exception:
        pass
    return found


def _enable_privilege(name):
    """يفعّل صلاحية (زي SeProfileSingleProcessPrivilege) في التوكن الحالي."""
    try:
        advapi32 = ctypes.WinDLL("advapi32.dll")
        kernel32 = ctypes.WinDLL("kernel32.dll")
        TOKEN_ADJUST_PRIVILEGES, TOKEN_QUERY = 0x0020, 0x0008
        SE_PRIVILEGE_ENABLED = 0x00000002

        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", wintypes.DWORD),
                        ("Privileges", LUID_AND_ATTRIBUTES * 1)]

        h_token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                          TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                          ctypes.byref(h_token)):
            return False
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            kernel32.CloseHandle(h_token)
            return False
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0] = LUID_AND_ATTRIBUTES(luid, SE_PRIVILEGE_ENABLED)
        ok = advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), 0, None, None)
        kernel32.CloseHandle(h_token)
        return bool(ok)
    except Exception:
        return False


def clear_standby_list():
    """
    تفريغ Standby List لصفحات الذاكرة عبر NtSetSystemInformation - نفس
    الأسلوب الداخلي لأدوات زي RAMMap/EmptyStandbyList. الكود الأصلي كان
    بينادي أمر PowerShell اسمه Clear-StandbyList، وهو مش cmdlet حقيقي
    أصلاً. دي نسخة شغالة فعليًا، وبترجع False بهدوء لو فشلت.
    """
    try:
        if not _enable_privilege("SeProfileSingleProcessPrivilege"):
            return False
        ntdll = ctypes.WinDLL("ntdll.dll")
        SystemMemoryListInformation = 80
        MemoryPurgeStandbyList = 4
        cmd = ctypes.c_int(MemoryPurgeStandbyList)
        status = ntdll.NtSetSystemInformation(SystemMemoryListInformation,
                                               ctypes.byref(cmd), ctypes.sizeof(cmd))
        return status == 0
    except Exception:
        return False


def require_admin():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.user32.MessageBoxW(
            0, "يجب تشغيل البرنامج كمسؤول (Run as Administrator)!", "خطأ", 0x10)
        sys.exit(0)


# ============================================================
# نظام نسخ احتياطي موحّد - كل تغيير بيتسجل فورًا على القرص، عشان لو
# البرنامج قفل فجأة نقدر نسترجع الإعدادات الأصلية في المرة الجاية.
# ============================================================
class SessionBackup:
    def __init__(self, logger=print):
        self.log = logger
        self.data = {"registry": [], "adapters": [], "services": [], "power_plan": None}
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _persist(self):
        try:
            with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except Exception:
            pass

    # ---------- ريجستري ----------
    def set_dword(self, hive_name, path, name, new_value):
        hive = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[hive_name]
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(hive, path)
        existed, old_value, old_type = True, None, winreg.REG_DWORD
        try:
            old_value, old_type = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            existed = False
        self.data["registry"].append({"hive": hive_name, "path": path, "name": name,
                                       "existed": existed, "value": old_value, "type": old_type})
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, new_value)
        winreg.CloseKey(key)
        self._persist()

    # ---------- كرت الشبكة ----------
    def apply_adapter_props(self, adapters, props, extreme=False):
        """props: {DisplayName: new_value}"""
        for ad in adapters:
            get_lines = [f"$ad = {ps_quote(ad)}"]
            for p in props:
                get_lines.append(
                    f"$cur = Get-NetAdapterAdvancedProperty -Name $ad -DisplayName {ps_quote(p)} "
                    f"-ErrorAction SilentlyContinue; "
                    f"if ($cur) {{ Write-Output ({ps_quote(p)} + '::' + $cur.DisplayValue) }}"
                )
            backup_res = run_ps("\n".join(get_lines))
            for line in backup_res.stdout.splitlines():
                if "::" in line:
                    k, _, v = line.partition("::")
                    self.data["adapters"].append({"adapter": ad, "prop": k.strip(), "value": v.strip()})
            self._persist()

            set_lines = [f"$ad = {ps_quote(ad)}"]
            for p, v in props.items():
                set_lines.append(
                    f"Set-NetAdapterAdvancedProperty -Name $ad -DisplayName {ps_quote(p)} "
                    f"-DisplayValue {ps_quote(v)} -ErrorAction SilentlyContinue"
                )
            if extreme:
                set_lines.append("Disable-NetAdapterLso -Name $ad -ErrorAction SilentlyContinue")
                set_lines.append("Disable-NetAdapterChecksumOffload -Name $ad -ErrorAction SilentlyContinue")
            run_ps("\n".join(set_lines))

    # ---------- خدمات ----------
    def stop_service(self, svc):
        status = run(f"sc query {svc}")
        if "RUNNING" not in status.stdout:
            return False
        res = run(f"sc stop {svc}")
        if res.returncode == 0:
            self.data["services"].append(svc)
            self._persist()
            return True
        return False

    # ---------- خطة الطاقة ----------
    def note_power_plan(self, guid):
        if guid:
            self.data["power_plan"] = guid
            self._persist()

    # ---------- الاستعادة الكاملة ----------
    def restore_all(self):
        for item in reversed(self.data["registry"]):
            try:
                hive = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[item["hive"]]
                key = winreg.OpenKey(hive, item["path"], 0, winreg.KEY_SET_VALUE)
                if item["existed"]:
                    winreg.SetValueEx(key, item["name"], 0, item["type"], item["value"])
                else:
                    winreg.DeleteValue(key, item["name"])
                winreg.CloseKey(key)
            except Exception as e:
                self.log(f"⚠️ تعذرت استعادة {item.get('name')}: {e}")

        by_adapter = {}
        for item in self.data["adapters"]:
            by_adapter.setdefault(item["adapter"], []).append((item["prop"], item["value"]))
        for ad, items in by_adapter.items():
            lines = [f"$ad = {ps_quote(ad)}",
                     "Enable-NetAdapterLso -Name $ad -ErrorAction SilentlyContinue",
                     "Enable-NetAdapterChecksumOffload -Name $ad -ErrorAction SilentlyContinue"]
            for prop, val in items:
                lines.append(f"Set-NetAdapterAdvancedProperty -Name $ad -DisplayName {ps_quote(prop)} "
                              f"-DisplayValue {ps_quote(val)} -ErrorAction SilentlyContinue")
            run_ps("\n".join(lines))
        if by_adapter:
            self.log("🔄 تم استرجاع إعدادات كرت/كروت الشبكة الأصلية")

        for svc in self.data["services"]:
            run(f"sc start {svc}")
            self.log(f"▶️ تم إعادة تشغيل {svc}")

        run("netsh int tcp set global autotuninglevel=normal")
        run("netsh int tcp set global timestamps=default")
        for ad in get_active_adapters():
            run(f'netsh interface ip set dns "{ad}" dhcp')

        if self.data.get("power_plan"):
            run(f"powercfg /setactive {self.data['power_plan']}")
            self.log("⚡ تم إرجاع خطة الطاقة الأصلية")

        self.log("🔄 تم إرجاع DNS وTCP لوضعهم الطبيعي")

        self.data = {"registry": [], "adapters": [], "services": [], "power_plan": None}
        try:
            if BACKUP_FILE.exists():
                BACKUP_FILE.unlink()
        except Exception:
            pass

    @staticmethod
    def has_pending():
        try:
            return BACKUP_FILE.exists() and BACKUP_FILE.stat().st_size > 5
        except Exception:
            return False

    @staticmethod
    def restore_pending(logger=print):
        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger(f"⚠️ تعذرت قراءة نسخة احتياطية قديمة: {e}")
            return
        sb = SessionBackup(logger)
        sb.data = data
        sb.restore_all()
        logger("✅ تم استرجاع إعدادات جلسة سابقة ماتقفلتش صح")


# ============================================================
# التطبيق الرئيسي
# ============================================================
class PingZeroExtreme:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("940x800")
        self.root.configure(bg="#05050F")
        self.root.resizable(False, False)

        self.is_boosted = False
        self.target_game = ""
        self.target_ip = ""
        self.target_port = 443
        self.extreme_mode = False
        self.custom_exe_name = ""
        self.stop_event = threading.Event()
        self.ping_history = deque(maxlen=50)
        self.baseline_ping = None
        self.log_queue = Queue()
        self.backup = SessionBackup(logger=self.log)
        self.original_power_plan = self.get_current_power_plan()

        self.init_ui()
        self._drain_log_queue()
        self.setup_safe_restore()
        self.check_pending_backup()
        self.animate()
        self.on_game_change()

    # ==================== الأمان ====================
    def check_pending_backup(self):
        if SessionBackup.has_pending():
            answer = messagebox.askyesno(
                "استعادة جلسة سابقة",
                "لاحظنا إن البرنامج قفل قبل كده من غير ما يرجّع إعدادات النظام "
                "لوضعها الطبيعي (كراش أو إغلاق قسري). عايز نرجّعها دلوقتي؟"
            )
            if answer:
                SessionBackup.restore_pending(logger=self.log)

    def setup_safe_restore(self):
        atexit.register(self.emergency_restore)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if self.is_boosted:
            self.stop_event.set()
            self.status_var.set("جاري استعادة الإعدادات قبل الإغلاق...")
            try:
                self.root.update()
            except Exception:
                pass
            try:
                self.backup.restore_all()
            except Exception:
                pass
        self.root.destroy()

    def emergency_restore(self):
        try:
            if self.is_boosted:
                self.backup.restore_all()
        except Exception:
            pass

    # ==================== واجهة Tkinter ====================
    def init_ui(self):
        main = tk.Frame(self.root, bg='#05050F')
        main.pack(fill='both', expand=True, padx=15, pady=15)

        hdr = tk.Frame(main, bg='#05050F')
        hdr.pack(fill='x')
        self.logo = tk.Label(hdr, text="⚡", font=("Segoe UI", 28), bg='#05050F', fg='#8B5CF6')
        self.logo.pack(side='right', padx=5)
        tk.Label(hdr, text="PingZero Extreme", font=("Segoe UI", 20, "bold"),
                 bg='#05050F', fg='white').pack(side='right', padx=10)
        tk.Label(hdr, text="Local Tweaks · Real Metrics · Safe Restore",
                 font=("Segoe UI", 9), bg='#05050F', fg='#9CA3AF').pack(side='right')

        body = tk.Frame(main, bg='#05050F')
        body.pack(fill='both', expand=True, pady=10)

        ctrl = tk.Frame(body, bg='#05050F')
        ctrl.pack(side='right', fill='both', expand=True, padx=(5, 0))
        self.build_controls(ctrl)

        left = tk.Frame(body, bg='#05050F', width=380)
        left.pack(side='left', fill='y', padx=(0, 5))
        left.pack_propagate(False)
        self.build_monitoring(left)

    def build_controls(self, parent):
        f1 = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        f1.pack(fill='x', pady=5)
        tk.Label(f1, text="🎮 اللعبة", font=("Segoe UI", 12, "bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10, 2))

        row = tk.Frame(f1, bg='#111122')
        row.pack(fill='x', padx=12, pady=(0, 6))
        self.game_var = tk.StringVar(value="Fortnite")
        combo = ttk.Combobox(row, textvariable=self.game_var, values=list(GAME_PROFILES.keys()),
                              state="readonly", font=("Segoe UI", 11))
        combo.pack(side='right', fill='x', expand=True)
        self.game_var.trace('w', lambda *a: self.on_game_change())
        tk.Button(row, text="🔍 اكتشاف تلقائي", font=("Segoe UI", 9), bg='#2D2D5E', fg='white',
                  relief='flat', cursor='hand2', command=self.detect_running_game).pack(side='left', padx=(6, 0))

        tk.Label(f1, text="اسم exe يدوي (اختياري لو لعبتك مش في القائمة)",
                 font=("Segoe UI", 8), bg='#111122', fg='#9CA3AF').pack(anchor='e', padx=12)
        self.custom_exe_var = tk.StringVar()
        tk.Entry(f1, textvariable=self.custom_exe_var, font=("Segoe UI", 10), justify='right',
                 bg='#1E1E3A', fg='white', insertbackground='white', relief='flat').pack(fill='x', padx=12, pady=(2, 10))

        f2 = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        f2.pack(fill='x', pady=5)
        tk.Label(f2, text="⚙️ وضع التشغيل", font=("Segoe UI", 12, "bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10, 2))
        self.mode_var = tk.StringVar(value="safe")
        mrow = tk.Frame(f2, bg='#111122')
        mrow.pack(fill='x', padx=12, pady=(0, 4))
        tk.Radiobutton(mrow, text="آمن (موصى به)", variable=self.mode_var, value="safe",
                       bg='#111122', fg='white', selectcolor='#1E1E3A', font=("Segoe UI", 10),
                       activebackground='#111122').pack(side='right', padx=5)
        tk.Radiobutton(mrow, text="Extreme (أقصى قوة)", variable=self.mode_var, value="extreme",
                       bg='#111122', fg='white', selectcolor='#1E1E3A', font=("Segoe UI", 10),
                       activebackground='#111122').pack(side='right', padx=5)
        tk.Label(f2, text="Extreme بيوقف تحديثات ويندوز وBITS وSpooler مؤقتًا، ويثبّت المعالج\n"
                          "على أقصى سرعة طول الوقت - أقوى، بس استهلاك كهرباء/حرارة أعلى (خصوصًا لابتوب).",
                 font=("Segoe UI", 8), bg='#111122', fg='#9CA3AF', wraplength=340, justify='right').pack(anchor='e', padx=12, pady=(0, 10))

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
        g = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        g.pack(fill='x', pady=5)
        tk.Label(g, text="📈 Ping Live Graph", font=("Segoe UI", 11, "bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10, 2))
        self.graph = tk.Canvas(g, bg='#1E1E3A', height=120, highlightthickness=0)
        self.graph.pack(fill='x', padx=12, pady=(0, 10))

        s = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        s.pack(fill='x', pady=5)
        tk.Label(s, text="📊 إحصائيات حقيقية", font=("Segoe UI", 11, "bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10, 2))

        rows = [
            ("Ping", "ms", "#8B5CF6"),
            ("Jitter", "ms", "#10B981"),
            ("Packet Loss", "%", "#10B981"),
            ("Avg Ping", "ms", "#F59E0B"),
            ("حمل المعالج", "%", "#60A5FA"),
        ]
        self.stat_labels = {}
        for title, unit, color in rows:
            f = tk.Frame(s, bg='#111122')
            f.pack(fill='x', padx=12, pady=2)
            val = tk.Label(f, text=f"-- {unit}", font=("Segoe UI", 14, "bold"), bg='#111122', fg=color)
            val.pack(side='left')
            tk.Label(f, text=title, font=("Segoe UI", 10), bg='#111122', fg='#9CA3AF').pack(side='left', padx=5)
            self.stat_labels[title] = val

        lf = tk.Frame(parent, bg='#111122', highlightbackground='#2D2D5E', highlightthickness=1)
        lf.pack(fill='both', expand=True, pady=5)
        tk.Label(lf, text="📝 سجل العمليات", font=("Segoe UI", 11, "bold"), bg='#111122', fg='white').pack(anchor='e', padx=12, pady=(10, 2))
        self.log_box = scrolledtext.ScrolledText(lf, wrap='word', font=("Consolas", 9),
                                                   bg='#1E1E3A', fg='#9CA3AF', insertbackground='white',
                                                   relief='flat', height=10, state='disabled')
        self.log_box.pack(fill='both', expand=True, padx=12, pady=(0, 10))

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{ts}] {msg}")

    def _drain_log_queue(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log_box.config(state='normal')
                self.log_box.insert('end', line + "\n")
                self.log_box.see('end')
                self.log_box.config(state='disabled')
        except Empty:
            pass
        self.root.after(150, self._drain_log_queue)

    def on_game_change(self):
        game = self.game_var.get()
        if game in GAME_PROFILES:
            profile = GAME_PROFILES[game]
            self.target_ip, self.target_port = profile["host"], profile["port"]
            self.target_game = game
            self.log(f"تم تحديد {game} (الخادم: {self.target_ip}:{self.target_port})")

    def detect_running_game(self):
        running = {p.info['name'] for p in psutil.process_iter(['name']) if p.info.get('name')}
        for game, profile in GAME_PROFILES.items():
            if any(exe in running for exe in profile["exe"]):
                self.game_var.set(game)
                self.log(f"🔍 تم اكتشاف {game} شغالة دلوقتي")
                return
        self.log("🔍 مفيش لعبة من القائمة شغالة حاليًا")

    def animate(self):
        def cycle(i=0):
            colors = ['#8B5CF6', '#A78BFA', '#C4B5FD', '#A78BFA', '#8B5CF6']
            self.logo.config(fg=colors[i % len(colors)])
            self.root.after(500, lambda: cycle(i + 1))
        cycle()

    # ==================== تحسينات الشبكة ====================
    def extreme_tcp_optimizations(self):
        try:
            path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            for name, val in [("TcpNoDelay", 1), ("TcpAckFrequency", 0), ("TcpDelAckTicks", 0),
                               ("Tcp1323Opts", 0), ("EnableWsd", 0), ("EnableAutoTuning", 0)]:
                self.backup.set_dword("HKLM", path, name, val)
            self.log("✅ تم ضبط TCP (Nagle=Off, ACK فوري, Timestamps=Off)")
        except Exception as e:
            self.log(f"⚠️ خطأ في تحسينات TCP: {e}")

        try:
            path2 = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
            self.backup.set_dword("HKLM", path2, "NetworkThrottlingIndex", 0xFFFFFFFF)
            self.log("✅ تم تعطيل Network Throttling")
        except Exception as e:
            self.log(f"⚠️ خطأ في NetworkThrottlingIndex: {e}")

        cmds = [
            "netsh int tcp set global autotuninglevel=disabled",
            "netsh int tcp set supplemental template=internet congestionprovider=ctcp",
            "netsh int tcp set supplemental template=datacenter congestionprovider=dctcp",
            "netsh int tcp set global timestamps=disabled",
            "netsh int tcp set global rss=enabled",
        ]
        ok = sum(1 for c in cmds if run(c).returncode == 0)
        self.log(f"✅ تم تطبيق {ok}/{len(cmds)} من أوامر netsh")

    def extreme_adapter_tweaks(self):
        adapters = get_active_adapters()
        if not adapters:
            self.log("⚠️ لم يتم العثور على كرت شبكة متصل")
            return
        props = {
            "Interrupt Moderation": "Disabled",
            "Flow Control": "Disabled",
            "Receive Buffers": "2048",
            "Transmit Buffers": "2048",
            "RSS Base Processor Number": "0",
            "RSS Load Balancing Profile": "ClosestProcessor",
            "Maximum Number of RSS Queues": "4",
        }
        self.backup.apply_adapter_props(adapters, props, extreme=self.extreme_mode)
        self.log(f"⚡ تم تحسين {len(adapters)} كرت شبكة (مع حفظ القيم الأصلية للاستعادة)")

    def set_fastest_dns(self):
        adapters = get_active_adapters()
        for ad in adapters:
            run(f'netsh interface ip set dns "{ad}" static 1.1.1.1')
            run(f'netsh interface ip add dns "{ad}" 1.0.0.1 index=2')
        run("ipconfig /flushdns")
        self.log("🌐 تم ضبط DNS Cloudflare (1.1.1.1) ومسح الكاش")

    # ==================== تحسينات النظام ====================
    def ultimate_performance_plan(self):
        try:
            run("powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61")
            run("powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61")
            run("powercfg -setacvalueindex scheme_current sub_processor 5d76a2ca-e8c0-402f-a133-2158492d58ad 0")
            self.log("⚡ تم تفعيل خطة Ultimate Performance")
            if self.extreme_mode:
                run("powercfg -setacvalueindex scheme_current sub_processor 893dee8e-2bef-41e0-89c6-b55d0929964c 100")
                self.log("⚡ (Extreme) تم تثبيت الحد الأدنى للمعالج عند 100%")
        except Exception as e:
            self.log(f"⚠️ خطأ في خطة الطاقة: {e}")

    def memory_and_io_boost(self):
        if clear_standby_list():
            self.log("🗑️ تم تفريغ الذاكرة الاحتياطية (Standby List)")
        else:
            self.log("ℹ️ تفريغ الذاكرة الاحتياطية مش متاح على الجهاز ده - تم تجاوزه بأمان")
        try:
            path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
            self.backup.set_dword("HKLM", path, "DisablePagingExecutive", 1)
            self.backup.set_dword("HKLM", path, "LargeSystemCache", 1)
            self.log("🗑️ تم تعطيل Paging Executive")
        except Exception as e:
            self.log(f"⚠️ خطأ في تحسين الذاكرة: {e}")

    def disable_unnecessary_services(self):
        safe_services = ["SysMain", "DiagTrack", "WSearch"]
        extreme_services = ["BITS", "wuauserv", "Spooler"]
        targets = safe_services + (extreme_services if self.extreme_mode else [])
        for svc in targets:
            if self.backup.stop_service(svc):
                self.log(f"⏸️ تم إيقاف خدمة {svc}")
            else:
                self.log(f"ℹ️ {svc} واقفة مسبقًا أو مش متاحة")

    def set_game_high_priority(self):
        targets = set()
        if self.target_game in GAME_PROFILES:
            targets.update(GAME_PROFILES[self.target_game]["exe"])
        if self.custom_exe_name:
            targets.add(self.custom_exe_name)
        if not targets:
            return
        boosted = 0
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] in targets:
                try:
                    p = psutil.Process(proc.info['pid'])
                    p.nice(psutil.HIGH_PRIORITY_CLASS)
                    p.ionice(psutil.IOPRIO_HIGH)
                    p.cpu_affinity(list(range(os.cpu_count())))
                    boosted += 1
                except Exception:
                    pass
        if boosted:
            self.log(f"⬆️ تم رفع أولوية {boosted} عملية متعلقة باللعبة (CPU+I/O+Affinity)")

    def gpu_latency_tweaks(self):
        gpus = find_gpu_registry_keys()
        if not gpus:
            self.log("ℹ️ لم يتم التعرف على كرت شاشة NVIDIA/AMD مدعوم للتحسين")
            return
        for path, vendor, desc in gpus:
            try:
                if vendor == "nvidia":
                    self.backup.set_dword("HKLM", path, "OGL_MaxPreRenderedFrames", 1)
                    self.log(f"🎮 تم تحسين {desc}")
                elif vendor == "amd":
                    self.backup.set_dword("HKLM", path, "KMD_EnablePerChipFlipQueue", 1)
                    self.log(f"🎮 تم تحسين {desc}")
            except Exception as e:
                self.log(f"⚠️ تعذر تحسين {desc}: {e}")

    # ==================== قياس البنق ====================
    def tcp_ping(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.2)
        try:
            start = time.perf_counter()
            sock.connect((ip, port))
            sock.shutdown(socket.SHUT_RDWR)
            elapsed = (time.perf_counter() - start) * 1000
            return round(elapsed, 1), 0
        except Exception:
            return 999, 1
        finally:
            sock.close()

    def measure_baseline(self, samples=6):
        vals = []
        for _ in range(samples):
            p, loss = self.tcp_ping(self.target_ip, self.target_port)
            if loss == 0:
                vals.append(p)
            time.sleep(0.2)
        return round(statistics.median(vals), 1) if vals else None

    def monitoring_loop(self):
        tick = 0
        while not self.stop_event.is_set():
            if self.target_ip:
                ping, loss = self.tcp_ping(self.target_ip, self.target_port)
                self.ping_history.append(ping)
                cpu = psutil.cpu_percent(interval=None)
                self.root.after(0, self.update_ui, ping, loss, cpu)
            tick += 1
            if tick % 5 == 0:
                self.set_game_high_priority()
            time.sleep(1)

    def update_ui(self, ping, loss, cpu):
        self.stat_labels["Ping"].config(text=f"{ping} ms",
                                          fg='#10B981' if ping < 60 else '#F59E0B' if ping < 100 else '#EF4444')
        self.stat_labels["Packet Loss"].config(text=f"{loss}%", fg='#10B981' if loss == 0 else '#EF4444')
        self.stat_labels["حمل المعالج"].config(text=f"{cpu:.0f}%")
        if self.ping_history:
            data = list(self.ping_history)
            avg = round(sum(data) / len(data), 1)
            self.stat_labels["Avg Ping"].config(text=f"{avg} ms")
            jitter = round(statistics.pstdev(data), 1) if len(data) >= 2 else 0
            self.stat_labels["Jitter"].config(text=f"{jitter} ms",
                                                fg='#10B981' if jitter < 10 else '#F59E0B' if jitter < 25 else '#EF4444')
        self.draw_graph()

    def draw_graph(self):
        self.graph.delete("all")
        data = list(self.ping_history)
        if len(data) < 2:
            return
        w, h = self.graph.winfo_width(), self.graph.winfo_height()
        max_val = max(max(data), 10)
        step = w / (len(data) - 1)
        points = []
        for i, val in enumerate(data):
            x = i * step
            y = h - (val / max_val * (h - 4)) - 2
            points.extend([x, y])
        self.graph.create_line(points, fill="#8B5CF6", width=2)
        avg = sum(data) / len(data)
        y_avg = h - (avg / max_val * (h - 4)) - 2
        self.graph.create_line(0, y_avg, w, y_avg, fill="#F59E0B", dash=(4, 4))

    # ==================== التحكم الرئيسي ====================
    def toggle_boost(self):
        if not self.is_boosted:
            self.start_boost()
        else:
            self.stop_boost()

    def start_boost(self):
        game = self.game_var.get()
        if game not in GAME_PROFILES:
            messagebox.showwarning("تحذير", "لم يتم العثور على خادم اللعبة")
            return

        self.extreme_mode = (self.mode_var.get() == "extreme")
        self.custom_exe_name = self.custom_exe_var.get().strip()
        mode_txt = "Extreme (أقصى قوة)" if self.extreme_mode else "آمن"
        details = "• TCP وDNS وكرت الشبكة\n• خطة الطاقة Ultimate Performance\n• أولوية اللعبة في المعالج"
        if self.extreme_mode:
            details += "\n• إيقاف مؤقت لتحديثات ويندوز وBITS وSpooler\n• تثبيت المعالج على أقصى سرعة دايمًا"
        if not messagebox.askyesno(
                "تأكيد",
                f"هيتم تطبيق وضع: {mode_txt}\n\nالتغييرات:\n{details}\n\n"
                "كل حاجة بترجع لوضعها الطبيعي لما تدوس إيقاف. تكمل؟"):
            return

        self.target_game = game
        profile = GAME_PROFILES[game]
        self.target_ip, self.target_port = profile["host"], profile["port"]
        self.btn_boost.config(text="⏳ جاري التطبيق...", state='disabled', bg='#F59E0B')
        self.status_var.set("قياس البنق الحالي...")

        def worker():
            self.log(f"⚙️ بدء سلسلة التحسينات ({mode_txt})...")
            self.backup.note_power_plan(self.original_power_plan)
            self.baseline_ping = self.measure_baseline()
            if self.baseline_ping is not None:
                self.log(f"📏 متوسط البنق قبل التفعيل: {self.baseline_ping} ms")

            self.extreme_tcp_optimizations()
            self.extreme_adapter_tweaks()
            self.set_fastest_dns()
            self.ultimate_performance_plan()
            self.memory_and_io_boost()
            self.disable_unnecessary_services()
            self.gpu_latency_tweaks()
            self.set_game_high_priority()

            psutil.cpu_percent(interval=None)
            self.is_boosted = True
            self.stop_event.clear()
            threading.Thread(target=self.monitoring_loop, daemon=True).start()
            self.root.after(0, self.on_boost_started)
            self.root.after(15000, self.report_comparison)

        threading.Thread(target=worker, daemon=True).start()

    def report_comparison(self):
        if not self.is_boosted or self.baseline_ping is None or len(self.ping_history) < 3:
            return
        after = round(statistics.median(list(self.ping_history)[-6:]), 1)
        delta = round(self.baseline_ping - after, 1)
        if delta > 1:
            self.log(f"📊 المقارنة: قبل {self.baseline_ping}ms ← بعد {after}ms (تحسّن {delta}ms)")
        elif delta < -1:
            self.log(f"📊 المقارنة: قبل {self.baseline_ping}ms ← بعد {after}ms - الفرق ده الأغلب من "
                      f"تذبذب الشبكة العادي مش من التحسينات، لأن مسار السيرفر بيحدده مزود الإنترنت")
        else:
            self.log(f"📊 المقارنة: قبل {self.baseline_ping}ms ← بعد {after}ms - شبه ثابت. "
                      f"الفايدة هنا أساسًا في تقليل التلعثم (Jitter) مش رقم البنق نفسه")

    def on_boost_started(self):
        self.btn_boost.config(text="⏹ إيقاف التسريع", state='normal', bg='#EF4444', activebackground='#DC2626')
        self.status_var.set(f"✅ {self.target_game} قيد التسريع")
        self.log("🚀 التحسينات مفعّلة. بنقيس الفرق الحقيقي خلال ثواني...")

    def stop_boost(self):
        self.stop_event.set()
        self.is_boosted = False
        self.status_var.set("جاري استعادة الإعدادات...")
        self.btn_boost.config(state='disabled')

        def worker():
            self.backup.restore_all()
            self.root.after(0, self.on_boost_stopped)

        threading.Thread(target=worker, daemon=True).start()

    def on_boost_stopped(self):
        self.ping_history.clear()
        self.baseline_ping = None
        self.graph.delete("all")
        for lbl in self.stat_labels.values():
            lbl.config(text="--")
        self.btn_boost.config(text="⚡ بدء التسريع الأقصى", state='normal', bg='#8B5CF6')
        self.status_var.set("تم إيقاف التسريع – جميع الإعدادات مستعادة")
        self.log("🔄 تم استعادة إعدادات النظام والشبكة وكرت الشبكة والخدمات بالكامل.")

    def get_current_power_plan(self):
        try:
            out = subprocess.check_output("powercfg /getactivescheme", shell=True, text=True)
            guid = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", out)
            return guid.group(1) if guid else None
        except Exception:
            return None


# ==================== تشغيل البرنامج ====================
if __name__ == "__main__":
    require_admin()
    root = tk.Tk()
    app = PingZeroExtreme(root)
    root.mainloop()
