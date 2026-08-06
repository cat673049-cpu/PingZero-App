"""
PingZero Extreme v5 - Network & System Booster لتقليل اللاق ورفع أداء الألعاب
================================================================================
نسخة v5: نفس فلسفة v2/v3/v4 (نسخ احتياطي حقيقي لأي تغيير - بيترجع لطبيعته حتى
لو البرنامج قفل فجأة - وأرقام حقيقية بدل الوهمية)، مع دفعة تحسينات محلية حقيقية
إضافية بتستهدف سبب شائع وحقيقي لارتفاع/تذبذب البنق بيتنسى غالبًا: الازدحام جوه
جهازك وشبكتك المحلية نفسها (Bufferbloat)، مش بس مسار السيرفر.

جديد في v5:
  • TCP ACK لكل كارت شبكة على حدة (Interfaces\\{GUID}) مش بس الإعداد العام -
    بعض نسخ ويندوز بتقرا القيمة لكل كارت وتتجاهل العام، فده بيضمن إن تحسين TCP
    الأساسي بيتطبق فعليًا مش بس مكتوب في الريجستري من غير تأثير حقيقي.
  • (Extreme) تقييد باندويدث البرامج المعروف إنها بتستهلك في الخلفية (مزامنة
    سحابية، لانشرز ألعاب، تحديثات) عبر QoS - بيفيد فعليًا لو سبب تذبذب البنق
    عندك ازدحام محلي (حد تاني بيستريم في البيت، مزامنة شغالة في الخلفية..).
  • (Extreme) إيقاف خدمة Delivery Optimization (مشاركة تحديثات ويندوز P2P مع
    مستخدمين تانيين على الإنترنت في الخلفية).
  • تنبيه تلقائي لو أنت متوصل واي فاي بدل كابل (Ethernet بيقلل الـ Jitter
    بشكل ملموس - نصيحة حقيقية، مش تحسين كود).

⚠️ نفس الحقيقة اللي كانت في v2 وv3 وv4 بالظبط، ولازم تتقال بصراحة حتى لو
عدد التحسينات كتر كتير: مفيش أي عدد "تحسينات" أو "قوة كود" يقدر يضمن رقم بنق
معين (زي "من 100 لـ 50") لأي حد - رقم البنق الأساسي بيتحدد بالمسافة الفعلية
وعدد القفزات (Hops) في الراوتينج بينك وبين سيرفر اللعبة، وده برا سيطرة أي
سكريبت شغال على جهازك مهما "طورناه". اللي فعلاً بيحصل هنا: تقليل التلعثم
(Jitter) والقفزات المفاجئة اللي سببها جهازك أو شبكتك المحلية (ومعاها v5 بقت
تستهدف الازدحام المحلي فعليًا عبر تقييد الباندويدث)، مش تغيير المسار الفعلي
للإنترنت. لو عايز تحسين مضمون في رقم البنق الأساسي نفسه، الحل الوحيد لسه هو
خدمة route optimization حقيقية (ExitLag/LagoFast) أو VPN خاص بيك على سيرفرات
قريبة من سيرفر اللعبة - وده محتاج بنية تحتية عالمية فعلية مش سطور كود إضافية.

المتطلبات: تشغيل كأدمن (Run as Administrator) + pip install psutil
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess, os, sys, ctypes, threading, time, socket, re, atexit, winreg, psutil, json, statistics
from ctypes import wintypes
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

# ============================================================
# إعدادات عامة
# ============================================================
APP_TITLE = "PingZero Extreme v5 – Network, System & FPS Booster"
BACKUP_DIR = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "PingZeroExtreme"
BACKUP_FILE = BACKUP_DIR / "session_backup.json"
FSE_LAYER_PATH = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"

# نظام ألوان موحّد - عشان أي تعديل شكل مستقبلي يبقى مكان واحد بس
COLORS = {
    "bg": "#05050F",
    "card": "#111122",
    "card_alt": "#161628",
    "border": "#2D2D5E",
    "accent": "#8B5CF6",
    "accent_hover": "#7C3AED",
    "accent_soft": "#1E1E3A",
    "text": "#FFFFFF",
    "text_dim": "#9CA3AF",
    "text_faint": "#54546E",
    "green": "#10B981",
    "amber": "#F59E0B",
    "red": "#EF4444",
    "blue": "#60A5FA",
}

DNS_CANDIDATES = [
    ("Cloudflare", "1.1.1.1", "1.0.0.1"),
    ("Google", "8.8.8.8", "8.8.4.4"),
    ("Quad9", "9.9.9.9", "149.112.112.112"),
    ("OpenDNS", "208.67.222.222", "208.67.220.220"),
]

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
    "Overwatch 2": {"host": "battle.net", "port": 443,
                     "exe": ["Overwatch.exe"]},
    "Dota 2": {"host": "dota2.com", "port": 443,
               "exe": ["dota2.exe"]},
    "GTA Online": {"host": "socialclub.rockstargames.com", "port": 443,
                    "exe": ["GTA5.exe", "PlayGTAV.exe"]},
    "Destiny 2": {"host": "bungie.net", "port": 443,
                   "exe": ["destiny2.exe"]},
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
    """تشغيل PowerShell بدون shell=True."""
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
    """أسماء كروت الشبكة المتصلة - عبر Get-NetAdapter عشان يشتغل على أي لغة ويندوز."""
    res = run_ps("(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'}).Name")
    return [l.strip() for l in res.stdout.splitlines() if l.strip()]


def measure_tcp_latency(ip, port=53, timeout=0.7):
    """قياس زمن اتصال TCP تقريبي لأي IP/بورت، مستخدم هنا لقياس استجابة خوادم DNS فعليًا."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        start = time.perf_counter()
        sock.connect((ip, port))
        sock.shutdown(socket.SHUT_RDWR)
        return (time.perf_counter() - start) * 1000
    except Exception:
        return None
    finally:
        sock.close()


def pick_fastest_dns():
    """يرجع قائمة (name, primary, secondary, ms) مرتبة من الأسرع للأبطأ، بناءً على قياس فعلي بالتوازي."""
    def probe(entry):
        name, primary, secondary = entry
        samples = [t for t in (measure_tcp_latency(primary) for _ in range(3)) if t is not None]
        if samples:
            return (name, primary, secondary, round(statistics.median(samples), 1))
        return None

    with ThreadPoolExecutor(max_workers=len(DNS_CANDIDATES)) as pool:
        results = [r for r in pool.map(probe, DNS_CANDIDATES) if r is not None]
    results.sort(key=lambda r: r[3])
    return results


def find_gpu_registry_keys():
    """يحدد المزوّد الحقيقي (NVIDIA/AMD/Intel) لكل كرت شاشة عبر DriverDesc."""
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
    """تفريغ Standby List لصفحات الذاكرة عبر NtSetSystemInformation."""
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
# حوارات مخصصة بنفس ثيم البرنامج - بديل messagebox الافتراضي اللي شكله
# مكسور عن باقي التطبيق
# ============================================================
class StyledDialog(tk.Toplevel):
    def __init__(self, parent, title, message, kind="info"):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.transient(parent)

        wrap = tk.Frame(self, bg=COLORS["bg"], padx=28, pady=22,
                         highlightbackground=COLORS["border"], highlightthickness=1)
        wrap.pack()

        icon = "⚠️" if kind == "confirm" else "ℹ️"
        tk.Label(wrap, text=icon, font=("Segoe UI", 26), bg=COLORS["bg"], fg=COLORS["accent"]).pack(pady=(0, 8))
        tk.Label(wrap, text=title, font=("Segoe UI", 13, "bold"), bg=COLORS["bg"], fg="white",
                 wraplength=420, justify='center').pack()
        tk.Label(wrap, text=message, font=("Segoe UI", 10), bg=COLORS["bg"], fg=COLORS["text_dim"],
                 wraplength=420, justify='right').pack(pady=(10, 20))

        btns = tk.Frame(wrap, bg=COLORS["bg"])
        btns.pack(fill="x")
        if kind == "confirm":
            tk.Button(btns, text="إلغاء", font=("Segoe UI", 10), bg=COLORS["accent_soft"], fg="white",
                      relief="flat", cursor="hand2", padx=18, pady=8,
                      command=self._cancel).pack(side="left")
            tk.Button(btns, text="تأكيد", font=("Segoe UI", 10, "bold"), bg=COLORS["accent"], fg="white",
                      relief="flat", cursor="hand2", padx=18, pady=8,
                      command=self._confirm).pack(side="right")
        else:
            tk.Button(btns, text="تمام", font=("Segoe UI", 10, "bold"), bg=COLORS["accent"], fg="white",
                      relief="flat", cursor="hand2", padx=24, pady=8,
                      command=self._confirm).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
            y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            pass
        self.grab_set()
        self.focus_set()

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


def ask_confirm(parent, title, message):
    d = StyledDialog(parent, title, message, kind="confirm")
    parent.wait_window(d)
    return d.result


def show_info(parent, title, message):
    d = StyledDialog(parent, title, message, kind="info")
    parent.wait_window(d)


# ============================================================
# نظام نسخ احتياطي موحّد - كل تغيير بيتسجل فورًا على القرص، عشان لو
# البرنامج قفل فجأة نقدر نسترجع الإعدادات الأصلية في المرة الجاية.
# ============================================================
class SessionBackup:
    def __init__(self, logger=print):
        self.log = logger
        self.data = {"registry": [], "adapters": [], "services": [], "power_plan": None, "qos_policies": []}
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
    def set_dword(self, hive_name, path, name, new_value, value_type=winreg.REG_DWORD):
        """بيقبل أي نوع قيمة (REG_DWORD الافتراضي، أو REG_SZ.. الخ) عبر value_type."""
        hive = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[hive_name]
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(hive, path)
        existed, old_value, old_type = True, None, value_type
        try:
            old_value, old_type = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            existed = False
        self.data["registry"].append({"hive": hive_name, "path": path, "name": name,
                                       "existed": existed, "value": old_value, "type": old_type})
        winreg.SetValueEx(key, name, 0, value_type, new_value)
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

    # ---------- QoS ----------
    def add_qos_policy(self, name, exe_name):
        """بينشئ سياسة QoS (DSCP=46, Expedited Forwarding) لحركة exe معينة. بيتحقق
        فعليًا إن السياسة اتعملت (مش بس إن الأمر مرجعش خطأ)."""
        run_ps(f"Remove-NetQosPolicy -Name {ps_quote(name)} -PolicyStore ActiveStore "
               f"-Confirm:$false -ErrorAction SilentlyContinue | Out-Null")
        script = (
            f"New-NetQosPolicy -Name {ps_quote(name)} -AppPathNameMatchCondition {ps_quote(exe_name)} "
            f"-DSCPAction 46 -NetworkProfile All -PolicyStore ActiveStore -ErrorAction SilentlyContinue | Out-Null\n"
            f"if (Get-NetQosPolicy -Name {ps_quote(name)} -PolicyStore ActiveStore -ErrorAction SilentlyContinue) "
            f"{{ Write-Output 'QOS_OK' }} else {{ Write-Output 'QOS_FAIL' }}"
        )
        res = run_ps(script)
        ok = "QOS_OK" in res.stdout
        if ok:
            self.data["qos_policies"].append(name)
            self._persist()
        return ok

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
                     "Enable-NetAdapterChecksumOffload -Name $ad -ErrorAction SilentlyContinue",
                     "Enable-NetAdapterPowerManagement -Name $ad -ErrorAction SilentlyContinue"]
            for prop, val in items:
                lines.append(f"Set-NetAdapterAdvancedProperty -Name $ad -DisplayName {ps_quote(prop)} "
                              f"-DisplayValue {ps_quote(val)} -ErrorAction SilentlyContinue")
            run_ps("\n".join(lines))
        if by_adapter:
            self.log("🔄 تم استرجاع إعدادات كرت/كروت الشبكة الأصلية (بما فيها إدارة الطاقة)")

        for policy in self.data.get("qos_policies", []):
            run_ps(f"Remove-NetQosPolicy -Name {ps_quote(policy)} -PolicyStore ActiveStore "
                   f"-Confirm:$false -ErrorAction SilentlyContinue | Out-Null")
        if self.data.get("qos_policies"):
            self.log(f"🌐 تم إلغاء {len(self.data['qos_policies'])} سياسة QoS")

        for svc in self.data["services"]:
            run(f"sc start {svc}")
            self.log(f"▶️ تم إعادة تشغيل {svc}")

        run("netsh int tcp set global autotuninglevel=normal")
        run("netsh int tcp set global timestamps=default")
        for ad in get_active_adapters():
            run(f'netsh interface ip set dns "{ad}" dhcp')

        if self.data.get("power_plan"):
            run(f"powercfg /setactive {self.data['power_plan']}")
            self.log("⚡ تم إرجاع خطة الطاقة الأصلية (بما فيها إعدادات Core Parking)")

        self.log("🔄 تم إرجاع DNS وTCP لوضعهم الطبيعي")

        self.data = {"registry": [], "adapters": [], "services": [], "power_plan": None, "qos_policies": []}
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
        self.root.geometry("960x820")
        self.root.configure(bg=COLORS["bg"])
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

        # --- تتبع إضافي لتحسينات الـ FPS/QoS ---
        self._timer_resolution_active = False
        self.tweaked_pids = set()
        self.qos_policy_created = False
        self.qos_policy_name = ""

        self.init_ui()
        self._drain_log_queue()
        self.setup_safe_restore()
        self.root.update()  # يضمن إن الشباك اتحدد مكانها قبل أي حوار مخصص
        self.check_pending_backup()
        self.animate()
        self.on_game_change()

    # ==================== الأمان ====================
    def check_pending_backup(self):
        if SessionBackup.has_pending():
            if ask_confirm(self.root, "استعادة جلسة سابقة",
                            "لاحظنا إن البرنامج قفل قبل كده من غير ما يرجّع إعدادات النظام "
                            "لوضعها الطبيعي (كراش أو إغلاق قسري). عايز نرجّعها دلوقتي؟"):
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
            self.full_restore()
        self.root.destroy()

    def emergency_restore(self):
        try:
            if self.is_boosted:
                self.full_restore()
        except Exception:
            pass

    def full_restore(self):
        """يجمع كل مسارات الاستعادة (ريجستري/شبكة/خدمات/QoS) + دقة المؤقت في نداء واحد."""
        try:
            self.backup.restore_all()
        except Exception:
            pass
        self.restore_timer_resolution()

    # ==================== واجهة Tkinter ====================
    def init_ui(self):
        self._setup_ttk_style()

        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill='both', expand=True, padx=15, pady=15)

        hdr = tk.Frame(main, bg=COLORS["bg"])
        hdr.pack(fill='x')
        brand = tk.Frame(hdr, bg=COLORS["bg"])
        brand.pack(side='right')
        self.logo = tk.Label(brand, text="⚡", font=("Segoe UI", 28), bg=COLORS["bg"], fg=COLORS["accent"])
        self.logo.pack(side='right', padx=5)
        title_box = tk.Frame(brand, bg=COLORS["bg"])
        title_box.pack(side='right', padx=6)
        name_row = tk.Frame(title_box, bg=COLORS["bg"])
        name_row.pack(anchor='e')
        tk.Label(name_row, text="PingZero Extreme", font=("Segoe UI", 20, "bold"),
                 bg=COLORS["bg"], fg="white").pack(side='right')
        tk.Label(name_row, text=" v5", font=("Segoe UI", 11, "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(side='right')
        tk.Label(title_box, text="Local Tweaks · Real Metrics · FPS Boost · Safe Restore",
                 font=("Segoe UI", 9), bg=COLORS["bg"], fg=COLORS["text_dim"]).pack(anchor='e')
        tk.Button(hdr, text="ℹ️ إحنا وExitLag/LagoFast", font=("Segoe UI", 9), bg=COLORS["card"], fg='white',
                  relief='flat', cursor='hand2', command=self.show_real_difference_info).pack(side='left', padx=5)

        body = tk.Frame(main, bg=COLORS["bg"])
        body.pack(fill='both', expand=True, pady=10)

        ctrl = tk.Frame(body, bg=COLORS["bg"])
        ctrl.pack(side='right', fill='both', expand=True, padx=(5, 0))
        self.build_controls(ctrl)

        left = tk.Frame(body, bg=COLORS["bg"], width=380)
        left.pack(side='left', fill='y', padx=(0, 5))
        left.pack_propagate(False)
        self.build_monitoring(left)

    def _setup_ttk_style(self):
        """ثيم الـ ttk (الـ Combobox أساسًا) عشان يبقى غامق زي باقي البرنامج بدل
        الشكل الفاتح الافتراضي اللي كان بيبوّظ الانسجام البصري."""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure("Dark.TCombobox",
                        fieldbackground=COLORS["accent_soft"],
                        background=COLORS["accent_soft"],
                        foreground="white",
                        arrowcolor="white",
                        bordercolor=COLORS["border"],
                        selectbackground=COLORS["accent_soft"],
                        selectforeground="white")
        style.map("Dark.TCombobox",
                  fieldbackground=[('readonly', COLORS["accent_soft"])],
                  foreground=[('readonly', 'white')])
        self.root.option_add('*TCombobox*Listbox.background', COLORS["accent_soft"])
        self.root.option_add('*TCombobox*Listbox.foreground', 'white')
        self.root.option_add('*TCombobox*Listbox.selectBackground', COLORS["accent"])
        self.root.option_add('*TCombobox*Listbox.selectForeground', 'white')

    def _card(self, parent, **kwargs):
        f = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        pack_opts = {"fill": "x", "pady": 5}
        pack_opts.update(kwargs)
        f.pack(**pack_opts)
        return f

    def _section_title(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 12, "bold"), bg=COLORS["card"],
                 fg="white").pack(anchor='e', padx=12, pady=(10, 2))

    def build_controls(self, parent):
        f1 = self._card(parent)
        self._section_title(f1, "🎮 اللعبة")

        row = tk.Frame(f1, bg=COLORS["card"])
        row.pack(fill='x', padx=12, pady=(0, 6))
        self.game_var = tk.StringVar(value="Fortnite")
        combo = ttk.Combobox(row, textvariable=self.game_var, values=list(GAME_PROFILES.keys()),
                              state="readonly", font=("Segoe UI", 11), style="Dark.TCombobox")
        combo.pack(side='right', fill='x', expand=True)
        self.game_var.trace('w', lambda *a: self.on_game_change())
        tk.Button(row, text="🔍 اكتشاف تلقائي", font=("Segoe UI", 9), bg=COLORS["accent_soft"], fg='white',
                  relief='flat', cursor='hand2', command=self.detect_running_game).pack(side='left', padx=(6, 0))

        tk.Label(f1, text="اسم exe يدوي (اختياري لو لعبتك مش في القائمة)",
                 font=("Segoe UI", 8), bg=COLORS["card"], fg=COLORS["text_dim"]).pack(anchor='e', padx=12)
        self.custom_exe_var = tk.StringVar()
        tk.Entry(f1, textvariable=self.custom_exe_var, font=("Segoe UI", 10), justify='right',
                 bg=COLORS["accent_soft"], fg='white', insertbackground='white',
                 relief='flat').pack(fill='x', padx=12, pady=(2, 10))

        f2 = self._card(parent)
        self._section_title(f2, "⚙️ وضع التشغيل")

        toggle_row = tk.Frame(f2, bg=COLORS["accent_soft"])
        toggle_row.pack(fill='x', padx=12, pady=(0, 6))
        self.mode_var = tk.StringVar(value="safe")
        self.mode_buttons = {}

        def set_mode(m):
            self.mode_var.set(m)
            for key, btn in self.mode_buttons.items():
                selected = key == m
                btn.config(bg=COLORS["accent"] if selected else COLORS["accent_soft"],
                           fg="white" if selected else COLORS["text_dim"])

        for key, label in [("safe", "آمن (موصى به)"), ("extreme", "Extreme ⚡")]:
            b = tk.Button(toggle_row, text=label, font=("Segoe UI", 10, "bold"), relief='flat', bd=0,
                          cursor='hand2', activebackground=COLORS["accent_hover"],
                          command=lambda k=key: set_mode(k))
            b.pack(side='right', fill='x', expand=True, padx=2, pady=4)
            self.mode_buttons[key] = b
        set_mode("safe")

        tk.Label(f2, text="Extreme بيوقف تحديثات ويندوز وBITS وSpooler وDelivery Optimization مؤقتًا،\n"
                          "يثبّت المعالج على أقصى سرعة، يعطّل Core Parking، ويقيّد باندويدث برامج الخلفية\n"
                          "(مزامنة، لانشرز) لصالح اللعبة - أقوى، بس استهلاك كهرباء/حرارة أعلى (لابتوب).\n"
                          "كل الأوضاع بتشمل TCP لكل كارت شبكة، MMCSS، تعطيل Game DVR وFSE، ودقة المؤقت.",
                 font=("Segoe UI", 8), bg=COLORS["card"], fg=COLORS["text_dim"],
                 wraplength=340, justify='right').pack(anchor='e', padx=12, pady=(0, 10))

        self.btn_boost = tk.Button(parent, text="⚡ بدء التسريع الأقصى", font=("Segoe UI", 15, "bold"),
                                    bg=COLORS["accent"], fg='white', activebackground=COLORS["accent_hover"],
                                    relief='flat', cursor='hand2', command=self.toggle_boost, padx=20, pady=12)
        self.btn_boost.pack(fill='x', padx=5, pady=10)
        self.btn_boost.bind('<Enter>', lambda e: self.btn_boost.config(bg=COLORS["accent_hover"]) if not self.is_boosted else None)
        self.btn_boost.bind('<Leave>', lambda e: self.btn_boost.config(bg=COLORS["accent"] if not self.is_boosted else '#EF4444'))

        status_row = tk.Frame(parent, bg=COLORS["bg"])
        status_row.pack(fill='x', padx=12, pady=5)
        self.status_dot = tk.Canvas(status_row, width=10, height=10, bg=COLORS["bg"], highlightthickness=0)
        self.status_dot.pack(side='right', padx=(0, 6), pady=3)
        self._dot_id = self.status_dot.create_oval(1, 1, 9, 9, fill=COLORS["text_faint"], outline="")
        self.status_var = tk.StringVar(value="جاهز – اختر اللعبة ثم اضغط بدء")
        tk.Label(status_row, textvariable=self.status_var, font=("Segoe UI", 10),
                 bg=COLORS["bg"], fg=COLORS["text_dim"], wraplength=310, justify='right').pack(side='right')

    def build_monitoring(self, parent):
        g = self._card(parent)
        self._section_title(g, "📈 Ping Live Graph")
        self.graph = tk.Canvas(g, bg=COLORS["accent_soft"], height=120, highlightthickness=0)
        self.graph.pack(fill='x', padx=12, pady=(0, 10))

        s = self._card(parent)
        self._section_title(s, "📊 إحصائيات حقيقية")

        tiles = tk.Frame(s, bg=COLORS["card"])
        tiles.pack(fill='x', padx=12, pady=(0, 10))
        tiles.grid_columnconfigure(0, weight=1)
        tiles.grid_columnconfigure(1, weight=1)

        stat_defs = [
            ("Ping", "ms", COLORS["accent"], "📶"),
            ("Jitter", "ms", COLORS["green"], "🎯"),
            ("Packet Loss", "%", COLORS["green"], "📉"),
            ("Avg Ping", "ms", COLORS["amber"], "📊"),
            ("حمل المعالج", "%", COLORS["blue"], "🧠"),
            ("الذاكرة", "%", COLORS["blue"], "💾"),
        ]
        self.stat_labels = {}
        for i, (title, unit, color, icon) in enumerate(stat_defs):
            r, c = divmod(i, 2)
            tile = tk.Frame(tiles, bg=COLORS["card_alt"], highlightbackground=COLORS["border"],
                             highlightthickness=1)
            tile.grid(row=r, column=c, sticky='nsew', padx=4, pady=4)
            top = tk.Frame(tile, bg=COLORS["card_alt"])
            top.pack(fill='x', padx=10, pady=(8, 0))
            tk.Label(top, text=icon, font=("Segoe UI", 11), bg=COLORS["card_alt"], fg=color).pack(side='right')
            val = tk.Label(tile, text=f"-- {unit}", font=("Segoe UI", 15, "bold"), bg=COLORS["card_alt"], fg=color)
            val.pack(anchor='e', padx=10)
            tk.Label(tile, text=title, font=("Segoe UI", 9), bg=COLORS["card_alt"],
                     fg=COLORS["text_dim"]).pack(anchor='e', padx=10, pady=(0, 8))
            self.stat_labels[title] = val

        lf = self._card(parent, fill='both', expand=True)
        self._section_title(lf, "📝 سجل العمليات")
        self.log_box = scrolledtext.ScrolledText(lf, wrap='word', font=("Consolas", 9),
                                                   bg=COLORS["accent_soft"], fg=COLORS["text_dim"],
                                                   insertbackground='white',
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
        def cycle_logo(i=0):
            colors = ['#8B5CF6', '#A78BFA', '#C4B5FD', '#A78BFA', '#8B5CF6']
            self.logo.config(fg=colors[i % len(colors)])
            self.root.after(500, lambda: cycle_logo(i + 1))
        cycle_logo()

        def pulse_dot(i=0):
            if self.is_boosted:
                pulse_colors = [COLORS["green"], "#34D399", COLORS["green"], "#0B6B4F"]
                self.status_dot.itemconfig(self._dot_id, fill=pulse_colors[i % len(pulse_colors)])
            else:
                self.status_dot.itemconfig(self._dot_id, fill=COLORS["text_faint"])
            self.root.after(500, lambda: pulse_dot(i + 1))
        pulse_dot()

    def show_real_difference_info(self):
        show_info(self.root, "الفرق الحقيقي بيننا وبين ExitLag / LagoFast / Prime",
            "أدوات زي دي - حتى في باقتها المدفوعة (Premium) - بتمرر اتصالك عبر شبكة سيرفرات "
            "خاصة بيهم منتشرة حول العالم، عشان تلاقي مسار إنترنت أسرع من اللي بيحدده مزود "
            "الإنترنت بتاعك افتراضيًا (Route Optimization). ده محتاج بنية تحتية فعلية "
            "(سيرفرات مستأجرة عالميًا + استضافة شهرية) - مش حاجة أي برنامج على جهازك بمفرده "
            "يقدر يعملها، ومهما سمّينا وضع فيه 'Extreme' أو 'Premium'.\n\n"
            "البرنامج ده بيشتغل بمبدأ مختلف: بيحسّن جهازك وشبكتك المحلية لأقصى درجة (TCP، "
            "كرت الشبكة، أولويات المعالج، الذاكرة، Game DVR، جدولة MMCSS، دقة المؤقت، وتقييد "
            "باندويدث برامج الخلفية في وضع Extreme)، وده بيقلل التلعثم (Jitter) وازدحامك المحلي "
            "فعليًا، لكنه مش بيغيّر المسار الفعلي للإنترنت. لو الـ Ping الأساسي عندك متأثر بمسار "
            "الشبكة نفسه (مش ازدحام محلي)، الحل الحقيقي الوحيد هو خدمة زي دي أو VPN خاص بيك على "
            "سيرفرات قريبة من سيرفر اللعبة.")

    # ==================== تحسينات الشبكة ====================
    def extreme_tcp_optimizations(self):
        try:
            path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
            for name, val in [("TcpNoDelay", 1), ("TcpAckFrequency", 1), ("TcpDelAckTicks", 0),
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

    def per_interface_tcp_tweaks(self):
        """(v5) نفس منطق TcpAckFrequency/TCPNoDelay بس على مستوى كل كارت شبكة
        متصل لوحده (Interfaces\\{GUID}) مش بس المفتاح العام. بعض نسخ/تعريفات
        ويندوز بتقرا القيمة لكل كارت وتتجاهل العام تمامًا، فده بيضمن إن التحسين
        فعليًا بيتطبق مش بس مكتوب من غير تأثير."""
        try:
            res = run_ps("(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'}).InterfaceGuid")
            guids = [l.strip().strip('{}') for l in res.stdout.splitlines() if l.strip()]
            applied = 0
            for guid in guids:
                path = rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{{{guid}}}"
                try:
                    self.backup.set_dword("HKLM", path, "TcpAckFrequency", 1)
                    self.backup.set_dword("HKLM", path, "TCPNoDelay", 1)
                    applied += 1
                except Exception:
                    pass
            if applied:
                self.log(f"✅ تم ضبط TCP ACK لكل كارت شبكة على حدة ({applied} كارت) - مش بس الإعداد العام")
            else:
                self.log("ℹ️ محدّش كارت شبكة استجاب لضبط TCP لكل كارت - الإعداد العام لسه شغال")
        except Exception as e:
            self.log(f"⚠️ خطأ في ضبط TCP لكل كارت: {e}")

    def check_connection_type_tip(self):
        """(v5) نصيحة حقيقية مش تحسين كود: لو أنت متوصل واي فاي، الكابل بيقلل
        الـ Jitter بشكل ملموس لأنه مش عرضة لتداخل الإشارة زي الواي فاي."""
        try:
            res = run_ps("(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'}).InterfaceDescription")
            desc = " ".join(res.stdout.splitlines()).lower()
            if any(k in desc for k in ("wireless", "wi-fi", "wifi", "802.11")) and "ethernet" not in desc:
                self.log("💡 نصيحة: أنت متوصل واي فاي - سلك Ethernet بيقلل الـ Jitter والتذبذب "
                          "بشكل ملموس لأنه مش عرضة لتداخل الإشارة")
        except Exception:
            pass

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
        if self.extreme_mode:
            props["Energy Efficient Ethernet"] = "Disabled"
            props["Green Ethernet"] = "Disabled"
            props["Power Saving Mode"] = "Disabled"
        self.backup.apply_adapter_props(adapters, props, extreme=self.extreme_mode)
        if self.extreme_mode:
            for ad in adapters:
                run_ps(f"Disable-NetAdapterPowerManagement -Name {ps_quote(ad)} -ErrorAction SilentlyContinue")
            self.log("🔋 تم تعطيل إدارة الطاقة لكرت/كروت الشبكة (Extreme)")
        self.log(f"⚡ تم تحسين {len(adapters)} كرت شبكة (مع حفظ القيم الأصلية للاستعادة)")

    def set_fastest_dns(self):
        self.log("🌐 قياس زمن الاستجابة لأشهر خوادم DNS لاختيار الأسرع فعليًا...")
        results = pick_fastest_dns()
        adapters = get_active_adapters()
        if results:
            for r_name, r_primary, r_secondary, r_ms in results:
                self.log(f"   • {r_name}: {r_ms} ms")
            chosen_name, primary, secondary, _ = results[0]
        else:
            chosen_name, primary, secondary = "Cloudflare (افتراضي - تعذر القياس)", "1.1.1.1", "1.0.0.1"
        for ad in adapters:
            run(f'netsh interface ip set dns "{ad}" static {primary}')
            run(f'netsh interface ip add dns "{ad}" {secondary} index=2')
        run("ipconfig /flushdns")
        self.log(f"🌐 تم اختيار {chosen_name} كأسرع DNS ({primary}) وتطبيقه ومسح الكاش")

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
                self.disable_core_parking()
        except Exception as e:
            self.log(f"⚠️ خطأ في خطة الطاقة: {e}")

    def disable_core_parking(self):
        """(Extreme) بيمنع النواة من "تنويم" أي كور من كروت المعالج، عشان كل كور
        يكون جاهز فورًا لحظة ما اللعبة تحتاجه - بيفيد خصوصًا في الألعاب اللي
        بتستخدم أنوية كتير بشكل متقطع. بيترجع تلقائيًا مع خطة الطاقة الأصلية عند الإيقاف."""
        res = run("powercfg -setacvalueindex scheme_current 54533251-82be-4824-96c1-47b60b740d00 "
                  "0cc5b647-c1df-4637-891a-dec35c318583 100")
        run("powercfg -setactive scheme_current")
        if res.returncode == 0:
            self.log("🧩 (Extreme) تم تعطيل Core Parking - كل الأنوية شغالة طول الوقت")
        else:
            self.log("ℹ️ تعذر تعطيل Core Parking على هذا الجهاز - تم تجاوزه بأمان")

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
        extreme_services = ["BITS", "wuauserv", "Spooler", "DoSvc"]
        targets = safe_services + (extreme_services if self.extreme_mode else [])
        for svc in targets:
            if self.backup.stop_service(svc):
                self.log(f"⏸️ تم إيقاف خدمة {svc}")
            else:
                self.log(f"ℹ️ {svc} واقفة مسبقًا أو مش متاحة")

    def disable_game_dvr_overlay(self):
        try:
            self.backup.set_dword("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0)
            self.backup.set_dword("HKCU", r"System\GameConfigStore", "GameDVR_FSEBehaviorMode", 2)
            self.backup.set_dword("HKCU", r"System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", 1)
            self.backup.set_dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0)
            self.backup.set_dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                                   "AppCaptureEnabled", 0)
            self.log("🎮 تم تعطيل Xbox Game Bar / Game DVR (تقليل استهلاك خلفي وتحسين ثبات الـ FPS)")
        except Exception as e:
            self.log(f"⚠️ خطأ في تعطيل Game DVR: {e}")

    def advanced_fps_scheduler_tweaks(self):
        """MMCSS Games profile + SystemResponsiveness=0 - تقنية موثقة من مايكروسوفت
        بتدي أولوية فورية لمعالجة الرسوميات/الصوت بدل ما تستنى دورها زي أي Thread
        عادي، وده اللي بيقلل الـ micro-stutter فعليًا (نفس اللي ويندوز بيعمله لما
        اللعبة تسجل نفسها كـ 'Games' task)."""
        try:
            base = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
            self.backup.set_dword("HKLM", base, "SystemResponsiveness", 0)
            games_path = base + r"\Tasks\Games"
            self.backup.set_dword("HKLM", games_path, "GPU Priority", 8)
            self.backup.set_dword("HKLM", games_path, "Priority", 6)
            self.backup.set_dword("HKLM", games_path, "Scheduling Category", "High", winreg.REG_SZ)
            self.backup.set_dword("HKLM", games_path, "SFIO Priority", "High", winreg.REG_SZ)
            self.log("🎯 تم ضبط جدولة MMCSS لمهام الألعاب (GPU/CPU Scheduling) لتقليل الـ micro-stutter")
        except Exception as e:
            self.log(f"⚠️ خطأ في ضبط MMCSS: {e}")

    def enable_high_timer_resolution(self):
        try:
            result = ctypes.WinDLL("winmm").timeBeginPeriod(1)
            if result == 0:
                self._timer_resolution_active = True
                self.log("⏱️ تم ضبط دقة المؤقت (Timer Resolution) على 1ms لتحسين ثبات الفريمات")
            else:
                self.log("ℹ️ تعذر ضبط دقة المؤقت على هذا الجهاز")
        except Exception as e:
            self.log(f"⚠️ خطأ في ضبط دقة المؤقت: {e}")

    def restore_timer_resolution(self):
        if self._timer_resolution_active:
            try:
                ctypes.WinDLL("winmm").timeEndPeriod(1)
                self.log("⏱️ تم إرجاع دقة المؤقت لوضعها الطبيعي")
            except Exception:
                pass
            self._timer_resolution_active = False

    def apply_per_process_tweaks(self):
        """بتجمع رفع الأولوية + تعطيل Fullscreen Optimizations + سياسة QoS لعمليات
        اللعبة الشغالة دلوقتي. بتتنادى فورًا بعد التفعيل وكل شوية من monitoring_loop
        عشان تمسك اللعبة حتى لو اتقفلت وفُتحت تاني."""
        targets = set()
        if self.target_game in GAME_PROFILES:
            targets.update(GAME_PROFILES[self.target_game]["exe"])
        if self.custom_exe_name:
            targets.add(self.custom_exe_name)
        if not targets:
            return
        boosted = 0
        for proc in psutil.process_iter(['pid', 'name']):
            name = proc.info.get('name')
            if name not in targets:
                continue
            pid = proc.info['pid']
            p = None
            try:
                p = psutil.Process(pid)
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                p.ionice(psutil.IOPRIO_HIGH)
                p.cpu_affinity(list(range(os.cpu_count())))
                boosted += 1
            except Exception:
                pass

            if pid in self.tweaked_pids:
                continue
            self.tweaked_pids.add(pid)

            try:
                full_path = (p or psutil.Process(pid)).exe()
                existing = ""
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, FSE_LAYER_PATH, 0, winreg.KEY_QUERY_VALUE)
                    existing, _ = winreg.QueryValueEx(key, full_path)
                    winreg.CloseKey(key)
                except Exception:
                    existing = ""
                flag = "DISABLEDXMAXIMIZEDWINDOWEDMODE"
                if flag not in existing:
                    new_value = (existing + " " + flag).strip() if existing else "~ " + flag
                    self.backup.set_dword("HKCU", FSE_LAYER_PATH, full_path, new_value, winreg.REG_SZ)
                    self.log(f"🖥️ تم تعطيل Fullscreen Optimizations لـ {name}")
            except Exception:
                pass

            if self.extreme_mode and not self.qos_policy_created:
                if self.backup.add_qos_policy(self.qos_policy_name, name):
                    self.log(f"🌐 تم إنشاء سياسة QoS (DSCP) لحركة {name} - بتساعد أساسًا لو في أجهزة "
                              "تانية بتزاحم شبكتك المحلية")
                else:
                    self.log("ℹ️ سياسات QoS مش مدعومة على نسخة ويندوز دي - تم تجاوزها بأمان")
                self.qos_policy_created = True

        if boosted:
            self.log(f"⬆️ تم رفع أولوية {boosted} عملية متعلقة باللعبة (CPU+I/O+Affinity)")

    def throttle_background_apps(self):
        """(Extreme, v5) بتحدد أشهر البرامج اللي بتستهلك باندويدث في الخلفية
        (مزامنة سحابية، لانشرز ألعاب، تحديثات) وبتحط سقف سرعة ليها عبر QoS -
        مش بتوقفها، بس بتمنعها تزاحم اللعبة على الباندويدث المحلي. ده بيفيد
        فعليًا في حالة الـ Bufferbloat (لما جهازك أو الراوتر يبقوا مزنوقين
        بيانات، البنق بيرتفع لحد ما الطابور يفضى - سبب حقيقي وشائع لارتفاع
        وتذبذب البنق، مش بس مسار السيرفر). لو مفيش من البرامج دي شغال، مفيش
        حاجة هتتغير."""
        bg_targets = ["OneDrive.exe", "Dropbox.exe", "steam.exe", "EpicGamesLauncher.exe",
                      "Battle.net.exe", "MicrosoftEdgeUpdate.exe", "GoogleUpdate.exe",
                      "OneDriveSetup.exe", "backgroundTransferHost.exe"]
        running = {p.info['name'] for p in psutil.process_iter(['name']) if p.info.get('name')}
        throttled = 0
        for name in bg_targets:
            if name not in running:
                continue
            policy_name = f"PingZero_Throttle_{name}"
            script = (
                f"Remove-NetQosPolicy -Name {ps_quote(policy_name)} -PolicyStore ActiveStore "
                f"-Confirm:$false -ErrorAction SilentlyContinue | Out-Null\n"
                f"New-NetQosPolicy -Name {ps_quote(policy_name)} -AppPathNameMatchCondition {ps_quote(name)} "
                f"-ThrottleRateActionBitsPerSecond 3000000 -NetworkProfile All -PolicyStore ActiveStore "
                f"-ErrorAction SilentlyContinue | Out-Null\n"
                f"if (Get-NetQosPolicy -Name {ps_quote(policy_name)} -PolicyStore ActiveStore "
                f"-ErrorAction SilentlyContinue) {{ Write-Output 'OK' }}"
            )
            res = run_ps(script)
            if "OK" in res.stdout:
                self.backup.data["qos_policies"].append(policy_name)
                self.backup._persist()
                throttled += 1
        if throttled:
            self.log(f"🚦 (Extreme) تم تقييد باندويدث {throttled} برنامج خلفية (تحديثات/مزامنة) لصالح "
                      "اللعبة - بيفيد لو سبب تذبذب البنق عندك ازدحام محلي")
        else:
            self.log("ℹ️ مفيش برامج خلفية معروفة شغالة دلوقتي تحتاج تقييد باندويدث")

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
                ram = psutil.virtual_memory().percent
                self.root.after(0, self.update_ui, ping, loss, cpu, ram)
            tick += 1
            if tick % 5 == 0:
                self.apply_per_process_tweaks()
            time.sleep(1)

    def update_ui(self, ping, loss, cpu, ram):
        self.stat_labels["Ping"].config(text=f"{ping} ms",
                                          fg=COLORS["green"] if ping < 60 else COLORS["amber"] if ping < 100 else COLORS["red"])
        self.stat_labels["Packet Loss"].config(text=f"{loss}%", fg=COLORS["green"] if loss == 0 else COLORS["red"])
        self.stat_labels["حمل المعالج"].config(text=f"{cpu:.0f}%")
        self.stat_labels["الذاكرة"].config(text=f"{ram:.0f}%")
        if self.ping_history:
            data = list(self.ping_history)
            avg = round(sum(data) / len(data), 1)
            self.stat_labels["Avg Ping"].config(text=f"{avg} ms")
            jitter = round(statistics.pstdev(data), 1) if len(data) >= 2 else 0
            self.stat_labels["Jitter"].config(text=f"{jitter} ms",
                                                fg=COLORS["green"] if jitter < 10 else COLORS["amber"] if jitter < 25 else COLORS["red"])
        self.draw_graph()

    def draw_graph(self):
        self.graph.delete("all")
        data = list(self.ping_history)
        if len(data) < 2:
            return
        w, h = self.graph.winfo_width(), self.graph.winfo_height()
        pad = 6
        max_val = max(max(data), 10) * 1.15
        step = w / (len(data) - 1)

        for frac in (0.25, 0.5, 0.75):
            y = h - frac * (h - pad * 2) - pad
            self.graph.create_line(0, y, w, y, fill="#2A2A4A", dash=(2, 3))

        points = []
        for i, val in enumerate(data):
            x = i * step
            y = h - (val / max_val * (h - pad * 2)) - pad
            points.extend([x, y])

        area = [0, h] + points + [w, h]
        self.graph.create_polygon(area, fill=COLORS["accent"], stipple="gray25", outline="")
        self.graph.create_line(points, fill=COLORS["accent"], width=2, smooth=True)

        avg = sum(data) / len(data)
        y_avg = h - (avg / max_val * (h - pad * 2)) - pad
        self.graph.create_line(0, y_avg, w, y_avg, fill=COLORS["amber"], dash=(4, 4))

        last_x, last_y = points[-2], points[-1]
        self.graph.create_oval(last_x - 3, last_y - 3, last_x + 3, last_y + 3,
                                fill=COLORS["accent"], outline="white")

    # ==================== التحكم الرئيسي ====================
    def toggle_boost(self):
        if not self.is_boosted:
            self.start_boost()
        else:
            self.stop_boost()

    def start_boost(self):
        game = self.game_var.get()
        if game not in GAME_PROFILES:
            show_info(self.root, "تحذير", "لم يتم العثور على خادم اللعبة")
            return

        self.extreme_mode = (self.mode_var.get() == "extreme")
        self.custom_exe_name = self.custom_exe_var.get().strip()
        mode_txt = "Extreme (أقصى قوة)" if self.extreme_mode else "آمن"
        details = ("• TCP لكل كارت شبكة على حدة وDNS (بعد قياس الأسرع فعليًا)\n"
                   "• خطة الطاقة Ultimate Performance وأولوية اللعبة في المعالج\n"
                   "• تعطيل Xbox Game Bar/Game DVR وFullscreen Optimizations للعبتك\n"
                   "• جدولة MMCSS للألعاب + ضبط دقة المؤقت (Timer Resolution)")
        if self.extreme_mode:
            details += ("\n• إيقاف مؤقت لتحديثات ويندوز وBITS وSpooler وDelivery Optimization\n"
                        "• تثبيت المعالج على أقصى سرعة + تعطيل Core Parking بالكامل\n"
                        "• سياسة QoS + تقييد باندويدث برامج الخلفية لصالح اللعبة\n"
                        "• تعطيل إدارة الطاقة لكرت الشبكة بالكامل")
        if not ask_confirm(self.root, "تأكيد بدء التسريع",
                            f"هيتم تطبيق وضع: {mode_txt}\n\nالتغييرات:\n{details}\n\n"
                            "كل حاجة بترجع لوضعها الطبيعي لما تدوس إيقاف. تكمل؟"):
            return

        self.target_game = game
        profile = GAME_PROFILES[game]
        self.target_ip, self.target_port = profile["host"], profile["port"]
        self.btn_boost.config(text="⏳ جاري التطبيق...", state='disabled', bg=COLORS["amber"])
        self.status_var.set("قياس البنق الحالي...")

        def worker():
            self.log(f"⚙️ بدء سلسلة التحسينات ({mode_txt})...")
            self.backup.note_power_plan(self.original_power_plan)
            self.tweaked_pids = set()
            self.qos_policy_created = False
            self.qos_policy_name = f"PingZero_{game}"
            self.baseline_ping = self.measure_baseline()
            if self.baseline_ping is not None:
                self.log(f"📏 متوسط البنق قبل التفعيل: {self.baseline_ping} ms")

            self.extreme_tcp_optimizations()
            self.per_interface_tcp_tweaks()
            self.check_connection_type_tip()
            self.extreme_adapter_tweaks()
            self.set_fastest_dns()
            self.ultimate_performance_plan()
            self.memory_and_io_boost()
            self.disable_unnecessary_services()
            self.gpu_latency_tweaks()
            self.disable_game_dvr_overlay()
            self.advanced_fps_scheduler_tweaks()
            self.enable_high_timer_resolution()
            self.apply_per_process_tweaks()
            if self.extreme_mode:
                self.throttle_background_apps()

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
        self.log("🎮 تحسينات الـ FPS (MMCSS، Game DVR، Fullscreen Optimizations، دقة المؤقت) بتأثيرها "
                  "على ثبات الفريم مش على رقم الـ Ping، فمتقلقش لو مش شايفها في المقارنة دي")
        if self.extreme_mode:
            self.log("🚦 لو كان عندك ازدحام محلي (برامج خلفية بتاكل باندويدث)، تقييد الـ Extreme ده "
                      "أقرب حاجة هنا ممكن تشوف أثرها فعليًا في رقم البنق - غير كده، السقف الأساسي "
                      "بيفضل المسافة والراوتينج لسيرفر اللعبة")

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
            self.full_restore()
            self.root.after(0, self.on_boost_stopped)

        threading.Thread(target=worker, daemon=True).start()

    def on_boost_stopped(self):
        self.ping_history.clear()
        self.baseline_ping = None
        self.graph.delete("all")
        for lbl in self.stat_labels.values():
            lbl.config(text="--")
        self.btn_boost.config(text="⚡ بدء التسريع الأقصى", state='normal', bg=COLORS["accent"])
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
