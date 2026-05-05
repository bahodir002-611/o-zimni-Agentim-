#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BAHODIR AI AGENT — GALAXY EDITION

"""

import os, sys, json, time, math, random, threading, subprocess, tempfile, re, shutil, pwd
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor

import tkinter as tk
from tkinter import ttk
import speech_recognition as sr
import requests

# ══════════════════════════════════════════


REAL_USER = os.environ.get("SUDO_USER") or os.environ.get("USER") or "user"
REAL_HOME = os.path.expanduser(f"~{REAL_USER}")
IS_ROOT   = (os.geteuid() == 0) if hasattr(os, "geteuid") else False
try:    REAL_UID = pwd.getpwnam(REAL_USER).pw_uid
except: REAL_UID = 1000
XDG_RUNTIME = f"/run/user/{REAL_UID}"
DBUS_ADDR   = f"unix:path={XDG_RUNTIME}/bus"

# ══ RANGLAR ══
C_BG    = "#000008"
C_BG2   = "#00000f"
C_GREEN = "#00ff41"
C_LG    = "#39ff14"
C_DIM   = "#003010"
C_BOR   = "#00aa22"
C_RED   = "#ff0040"
C_AMBER = "#ffcc00"
C_CYAN  = "#00ffff"
C_BLUE  = "#0080ff"
C_PURP  = "#aa00ff"
C_PINK  = "#ff00aa"
C_WHITE = "#ffffff"

_cmd_cache = {}
_app_cache = {}

SYSTEM_PROMPT = f"""Sen {AGENT_NAME} - Linux kompyuterni ovoz bilan TO'LIQ boshqaruvchi super aqlli agent.
Foydalanuvchi: {REAL_USER} (HOME={REAL_HOME})
Root: {"HA" if IS_ROOT else "YO'Q"} | OS: Kali Linux

Foydalanuvchi O'zbek, Rus yoki Ingliz tilida gapiradi.
FAQAT JSON formatda javob qaytar. Boshqa hech narsa yozma.

Format: {{"action":"harakat","params":{{}},"reply":"qisqa javob"}}
Sequence: {{"action":"sequence","steps":[{{"action":"...","params":{{}}}}],"reply":"javob"}}

BARCHA HARAKATLAR:
- chat
- youtube_play        params: {{"query":"..."}}
- youtube_search      params: {{"query":"..."}}
- web_search          params: {{"query":"..."}}
- open_url            params: {{"url":"..."}}
- open_app            params: {{"app":"dastur nomi"}}
- close_app           params: {{"app":"..."}}
- terminal_run        params: {{"cmd":"bash buyrug'i"}}
- shell_cmd           params: {{"cmd":"fon buyrug'i","sudo":false}}
- shell_capture       params: {{"cmd":"natija kerak buyruq"}}
- create_file         params: {{"name":"fayl.txt","content":"matn","path":"{REAL_HOME}"}}
- create_dir          params: {{"path":"{REAL_HOME}/yangi_papka"}}
- gui_type            params: {{"text":"..."}}
- gui_key             params: {{"key":"Return|ctrl+c|super|..."}}
- gui_click           params: {{"x":500,"y":400}}
- delay               params: {{"sec":2}}
- volume_up/volume_down/volume_set  params: {{"level":70}}
- brightness_up/brightness_down/brightness_set  params: {{"level":50}}
- screenshot
- lock_screen
- shutdown/reboot
- get_time/get_date

MUHIM QOIDALAR:
1. FAQAT JSON qaytar — markdown yo'q, izoh yo'q
2. reply qisqa (5-7 so'z), o'zbek tilida
3. YouTube: HAR DOIM youtube_play
4. Dastur: HAR DOIM open_app
5. Terminal buyruq: HAR DOIM terminal_run (natija ko'rinadi)
6. Fayl qidirish: terminal_run + find buyrug'i

TERMINAL MISOLLARI:
  "fayl qidir" → {{"action":"terminal_run","params":{{"cmd":"find {REAL_HOME} -name '*.py' 2>/dev/null | head -20"}},"reply":"Fayllar qidirilmoqda"}}
  "ip manzil" → {{"action":"terminal_run","params":{{"cmd":"ip addr show"}},"reply":"IP ko'rsatildi"}}
  "disk joy" → {{"action":"terminal_run","params":{{"cmd":"df -h"}},"reply":"Disk holati"}}
  "papka yarat" → {{"action":"create_dir","params":{{"path":"{REAL_HOME}/test"}},"reply":"Papka yaratildi"}}
  "fayl yarat" → {{"action":"create_file","params":{{"name":"test.txt","content":"salom","path":"{REAL_HOME}"}},"reply":"Fayl yaratildi"}}

Ovoz xatolari: verishak→wireshark, brupsute→burpsuite, enmap→nmap,
rasuliginjo→janob rasul gunchoq, kalkulyator→calculator, metasloyt→metasploit
"""

# ══════════════════════════════════════════
# YORDAMCHI
# ══════════════════════════════════════════
def which(cmd):
    if cmd in _cmd_cache: return _cmd_cache[cmd]
    r = shutil.which(cmd); _cmd_cache[cmd] = r; return r

def pick_terminal():
    for t in ["x-terminal-emulator","gnome-terminal","konsole","xfce4-terminal",
              "mate-terminal","tilix","kitty","alacritty","xterm"]:
        if which(t): return t
    return None

def popen_as_user(cmd, shell=False):
    env = os.environ.copy()
    extra = {
        "DISPLAY": env.get("DISPLAY",":0"),
        "XAUTHORITY": env.get("XAUTHORITY",f"{REAL_HOME}/.Xauthority"),
        "XDG_RUNTIME_DIR": XDG_RUNTIME,
        "DBUS_SESSION_BUS_ADDRESS": DBUS_ADDR,
        "PULSE_SERVER": f"unix:{XDG_RUNTIME}/pulse/native",
        "HOME":REAL_HOME,"USER":REAL_USER,"LOGNAME":REAL_USER,
        "PATH":f"{REAL_HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/bin",
    }
    if env.get("WAYLAND_DISPLAY"): extra["WAYLAND_DISPLAY"] = env["WAYLAND_DISPLAY"]
    if IS_ROOT and REAL_USER != "root":
        ea = [f"{k}={v}" for k,v in extra.items()]
        if shell: return subprocess.Popen(["sudo","-u",REAL_USER,"env"]+ea+["bash","-c",cmd],
                                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return subprocess.Popen(["sudo","-u",REAL_USER,"env"]+ea+list(cmd),
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    env.update(extra)
    if shell: return subprocess.Popen(cmd,shell=True,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return subprocess.Popen(list(cmd),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def run_in_terminal(cmd, terminal):
    """Terminal oynasida buyruqni ishga tushiradi — natija ko'rinadi"""
    if not terminal:
        for t in ["x-terminal-emulator","gnome-terminal","xterm","konsole","xfce4-terminal"]:
            if which(t): terminal = t; break
    if not terminal:
        subprocess.Popen(cmd,shell=True); return

    wrap = f'{cmd}; echo ""; echo "=== TUGADI ==="; read -p "Enter bosing..."'
    if terminal in ["gnome-terminal","mate-terminal","tilix"]:
        args = [terminal,"--","bash","-c",wrap]
    elif terminal in ["konsole","qterminal"]:
        args = [terminal,"-e","bash","-c",wrap]
    elif terminal == "xfce4-terminal":
        args = [terminal,"-e",f'bash -c \'{wrap}\'']
    else:
        args = [terminal,"-e","bash","-c",wrap]
    popen_as_user(args)

APP_ALIASES = {
    "telegram":   ["telegram-desktop","Telegram","flatpak run org.telegram.desktop"],
    "chrome":     ["google-chrome","google-chrome-stable","chromium","chromium-browser"],
    "firefox":    ["firefox","firefox-esr"],
    "brave":      ["brave-browser","brave"],
    "browser":    ["firefox","google-chrome","chromium"],
    "vscode":     ["code","codium","vscodium"],
    "code":       ["code","codium"],
    "files":      ["nautilus","dolphin","thunar","pcmanfm","nemo"],
    "nautilus":   ["nautilus","thunar","dolphin"],
    "terminal":   ["x-terminal-emulator","gnome-terminal","konsole","xfce4-terminal"],
    "vlc":        ["vlc"],
    "gedit":      ["gedit","mousepad","kate"],
    "calculator": ["gnome-calculator","kcalc","qalculate-gtk"],
    "spotify":    ["spotify","flatpak run com.spotify.Client"],
    "discord":    ["discord","flatpak run com.discordapp.Discord"],
    "zoom":       ["zoom"],
    "libreoffice":["libreoffice"],
    "wireshark":  ["wireshark","wireshark-gtk"],
    "burpsuite":  ["burpsuite","BurpSuiteCommunity"],
    "burp":       ["burpsuite"],
    "zaproxy":    ["zaproxy","zap.sh"],
    "maltego":    ["maltego"],"ghidra":["ghidra"],
    "ettercap":   ["ettercap-graphical"],
    "nmap":       ["nmap"],"hydra":["hydra"],"sqlmap":["sqlmap"],
    "metasploit": ["msfconsole"],"msfconsole":["msfconsole"],
    "john":       ["john"],"aircrack":["aircrack-ng"],"hashcat":["hashcat"],
    "nikto":      ["nikto"],"gobuster":["gobuster"],"dirb":["dirb"],
    "ffuf":       ["ffuf"],"netcat":["nc"],"tcpdump":["tcpdump"],"tshark":["tshark"],
}
CLI_ONLY = {"nmap","hydra","sqlmap","msfconsole","john","aircrack-ng","hashcat",
            "nikto","gobuster","dirb","ffuf","nc","tcpdump","tshark","netcat","metasploit"}
VOICE_ALIASES = {
    "verishak":"wireshark","verisharq":"wireshark","verishark":"wireshark",
    "brupsute":"burpsuite","burpsut":"burpsuite","bryup suyud":"burpsuite",
    "gidra":"hydra","xidra":"hydra","gidrotuli":"hydra",
    "enmap":"nmap","nimap":"nmap",
    "metasloyt":"metasploit","metaspoit":"metasploit",
    "kalkulyator":"calculator","kalkulator":"calculator",
    "fayllar":"files","telegramm":"telegram",
    "chrom":"chrome","krom":"chrome",
}

def norm_app(n):
    n=n.lower().strip()
    if n in VOICE_ALIASES: return VOICE_ALIASES[n]
    for bad,good in VOICE_ALIASES.items():
        if bad in n: return good
    return n

def find_bin(name):
    if name in _app_cache: return _app_cache[name]
    if which(name): _app_cache[name]=which(name); return _app_cache[name]
    dirs=[f"{REAL_HOME}/Downloads",f"{REAL_HOME}/Applications",
          f"{REAL_HOME}/opt",f"{REAL_HOME}/.local/bin","/opt","/usr/local/bin"]
    for d in dirs:
        if not os.path.isdir(d): continue
        for v in [name,name.lower(),name.capitalize()]:
            for p in [f"{d}/{v}/{v}",f"{d}/{v}.AppImage",f"{d}/{v}"]:
                if os.path.isfile(p) and os.access(p,os.X_OK):
                    _app_cache[name]=p; return p
    try:
        r=subprocess.run(["find",f"{REAL_HOME}/Downloads","/opt","-maxdepth","4",
                          "-type","f","-iname",name,"-executable"],
                         capture_output=True,text=True,timeout=3)
        lines=[l for l in r.stdout.splitlines() if l.strip()]
        if lines: _app_cache[name]=lines[0]; return lines[0]
    except: pass
    return None

def open_app_smart(app_name, terminal):
    app_l=norm_app(app_name)
    aliases=APP_ALIASES.get(app_l,[app_name,app_l])
    if app_name not in aliases: aliases=[app_name]+aliases
    is_cli=app_l in CLI_ONLY
    if is_cli:
        cmd=aliases[0] if aliases else app_l
        path=which(cmd) or find_bin(cmd)
        if path:
            sudo_set={"wireshark","tcpdump","nmap","tshark","aircrack-ng"}
            run_in_terminal(f"sudo {path}" if app_l in sudo_set else path, terminal)
            return f"Terminal: {cmd}"
        raise RuntimeError(f"'{cmd}' topilmadi. sudo apt install {cmd}")
    for cand in [c for c in aliases if " " not in c]:
        path=which(cand) or find_bin(cand)
        if path: popen_as_user([path]); return cand
    for fp in [c for c in aliases if c.startswith("flatpak run")]:
        aid=fp.replace("flatpak run ","").strip()
        try:
            r=subprocess.run(["flatpak","info",aid],capture_output=True,timeout=2)
            if r.returncode==0: popen_as_user(fp,shell=True); return fp
        except: pass
    for s in [app_name,app_l]:
        dirs=[f"{REAL_HOME}/.local/share/applications","/usr/share/applications"]
        ned=s.lower().replace(" ","")
        for d in dirs:
            if not os.path.isdir(d): continue
            for fn in os.listdir(d):
                if fn.endswith(".desktop") and ned in fn.lower().replace("-","").replace("_",""):
                    did=fn.replace(".desktop","")
                    if which("gtk-launch"): popen_as_user(["gtk-launch",did]); return did
    raise RuntimeError(f"'{app_name}' topilmadi")

def youtube_play_smart(query):
    import urllib.parse
    query = query.strip()
    
    if not query:
        return "Query bo'sh"
    
    # TEZ VA TO'G'RI USUL
    if which("yt-dlp") and which("mpv"):
        try:
            # Bitta so'rovda ENG YAXSHI FORMAT (video+audio birga)
            r = subprocess.run(
                ["yt-dlp", "-f", "best", "-g", "--no-warnings", f"ytsearch1:{query}"],
                capture_output=True, text=True, timeout=20
            )
            url = r.stdout.strip().split('\n')[0] if r.stdout else None
            
            if url:
                subprocess.Popen([
                    "mpv",
                    "--geometry=1024x670",
                    "--force-window=yes",
                    "--keepaspect-window",
                    "--no-border",
                    "--cache=yes",
                    url
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"🎵 {query}"
        except Exception as e:
            print(f"yt-dlp xato: {e}")
    
    # FALLBACK: brauzer
    encoded = urllib.parse.quote_plus(query)
    subprocess.Popen(["xdg-open", f"https://www.youtube.com/results?search_query={encoded}"])
    return f"🔍 Brauzer: {query}"

# ══════════════════════════════════════════
def quick_match(text):
    t=text.lower().strip()
    yt_kw=["yutub","youtube","qo'shiq","qoshiq","musiqa","kuy","ashula","qo'y","qoy","play","ijro"]
    if any(w in t for w in yt_kw):
        q=t
        for rm in ["yutubdan","youtubdan","qo'y","qoy","musiqa","qo'shiq","kuy","ashula","yutub","youtube"]:
            q=q.replace(rm,"").strip()
        fixes={"rasuliginjo":"janob rasul gunchoq","janob rasmni":"janob rasul gunchoq",
               "rasulginjo":"janob rasul gunchoq","rasulgincho":"janob rasul gunchoq"}
        for bad,good in fixes.items(): q=q.replace(bad,good)
        q=q.strip(" ,-.")
        if not q or len(q)<2: q=text
        return {"action":"youtube_play","params":{"query":q},"reply":f"{q} qo'yilmoqda"}
    if any(w in t for w in ["kalkulator","kalkulyator","calculator"]):
        return {"action":"open_app","params":{"app":"calculator"},"reply":"Kalkulator ochildi"}
    if t in ["terminal","terminal och","terminalni och"]:
        return {"action":"open_app","params":{"app":"terminal"},"reply":"Terminal ochildi"}
    if any(w in t for w in ["screenshot","ekran surati","skrinshat"]):
        return {"action":"screenshot","params":{},"reply":"Ekran surati olindi"}
    if t in ["soat necha","vaqt","hozir soat necha"]:
        return {"action":"get_time","params":{},"reply":f"Soat {time.strftime('%H:%M')}"}
    if "ovoz" in t:
        if any(w in t for w in ["oshir","ko'paytir","baland"]): return {"action":"volume_up","params":{},"reply":"Ovoz oshirildi"}
        if any(w in t for w in ["pasayt","kamayt","past"]): return {"action":"volume_down","params":{},"reply":"Ovoz kamaytirildi"}
    if any(w in t for w in ["yorqin","ekran nuri"]):
        if any(w in t for w in ["oshir","ko'paytir"]): return {"action":"brightness_up","params":{},"reply":"Yorqinlik oshirildi"}
        if any(w in t for w in ["pasayt","kamayt"]): return {"action":"brightness_down","params":{},"reply":"Yorqinlik kamaytirildi"}
    return None

# ══════════════════════════════════════════
# GALAKTIKA ANIMATSIYALARI
# ══════════════════════════════════════════
class StarField:
    """Yulduzlar maydoni — 3D parallax"""
    def __init__(self, canvas, w, h, count=200):
        self.canvas=canvas; self.w=w; self.h=h
        self.running=False
        self.stars=[]
        for _ in range(count):
            x=random.uniform(0,w); y=random.uniform(0,h)
            z=random.uniform(0.1,1.0)
            color=random.choice([C_WHITE,"#aaaaaa","#88ccff","#ffaaaa",C_CYAN,C_BLUE])
            size=random.uniform(0.5,2.5)*z
            item=canvas.create_oval(x-size,y-size,x+size,y+size,fill=color,outline="")
            spd=random.uniform(0.2,1.5)*z
            self.stars.append({"item":item,"x":x,"y":y,"z":z,"spd":spd,"color":color,"size":size})

    def start(self): self.running=True; self._tick()
    def stop(self): self.running=False

    def _tick(self):
        if not self.running: return
        for s in self.stars:
            s["x"]-=s["spd"]
            if s["x"]<0:
                s["x"]=self.w+5
                s["y"]=random.uniform(0,self.h)
            sz=s["size"]
            try:
                self.canvas.coords(s["item"],s["x"]-sz,s["y"]-sz,s["x"]+sz,s["y"]+sz)
            except: pass
        self.canvas.after(30,self._tick)

class NebulaRing:
    """Portlovchi nebula halqasi — har holat uchun boshqacha"""
    def __init__(self, canvas, cx, cy):
        self.canvas=canvas; self.cx=cx; self.cy=cy
        self.mode="idle"; self.phase=0; self.running=False
        self.particles=[]
        # Asosiy halqalar
        self.rings=[]
        for r,col,w in [(95,C_BOR,1),(75,C_DIM,1),(55,C_DIM,1)]:
            item=canvas.create_oval(cx-r,cy-r,cx+r,cy+r,outline=col,width=w,fill="")
            self.rings.append({"item":item,"r":r,"col":col})
        # Plyonka chiziqlar (36 ta)
        self.bars=[]
        for i in range(36):
            a=(2*math.pi*i)/36
            x1=cx+math.cos(a)*80; y1=cy+math.sin(a)*80
            x2=cx+math.cos(a)*95; y2=cy+math.sin(a)*95
            bar=canvas.create_line(x1,y1,x2,y2,fill=C_DIM,width=2)
            self.bars.append(bar)
        # Portlash zarrachalari
        self.sparks=[]
        for _ in range(20):
            item=canvas.create_oval(cx,cy,cx+2,cy+2,fill="",outline="")
            self.sparks.append({"item":item,"angle":random.uniform(0,2*math.pi),
                                "r":0,"spd":random.uniform(1,4),"life":0,"active":False})
        # Markaziy matn
        self.main_text=canvas.create_text(cx,cy-15,text=AGENT_NAME,
            font=("Courier",22,"bold"),fill=C_LG,anchor="center")
        self.sub_text=canvas.create_text(cx,cy+15,text="TAYYOR",
            font=("Courier",10),fill=C_BOR,anchor="center")

    def set_mode(self,mode):
        self.mode=mode
        # Portlash trigger
        if mode in ["listening","done"]:
            for s in self.sparks:
                s["angle"]=random.uniform(0,2*math.pi)
                s["r"]=0; s["spd"]=random.uniform(2,6)
                s["life"]=0; s["active"]=True

    def start(self): self.running=True; self._animate()
    def stop(self): self.running=False

    def _animate(self):
        if not self.running: return
        self.phase+=0.12
        m=self.mode

        # Rang va animatsiya holat bo'yicha
        if m=="listening":
            main_col=C_LG; sub="TINGLAYAPMAN"; bar_base=20; bar_amp=30; bar_col=C_LG
            ring_col=[C_LG,"#88ff44",C_BOR]; pulse=abs(math.sin(self.phase*2))*5
        elif m=="thinking":
            main_col=C_AMBER; sub="TAHLIL"; bar_base=8; bar_amp=18; bar_col=C_AMBER
            ring_col=[C_AMBER,"#ffaa00",C_DIM]; pulse=abs(math.sin(self.phase*3))*3
        elif m=="done":
            main_col=C_CYAN; sub="BAJARILDI!"; bar_base=12; bar_amp=25; bar_col=C_CYAN
            ring_col=[C_CYAN,C_BLUE,"#0044ff"]; pulse=abs(math.sin(self.phase))*8
        elif m=="error":
            main_col=C_RED; sub="XATO"; bar_base=5; bar_amp=15; bar_col=C_RED
            ring_col=[C_RED,"#aa0020",C_DIM]; pulse=abs(math.sin(self.phase*4))*4
        else:
            main_col=C_LG; sub="TAYYOR"; bar_base=3; bar_amp=5; bar_col=C_DIM
            ring_col=[C_BOR,C_DIM,C_DIM]; pulse=0

        # Halqalar
        for i,(ring,col) in enumerate(zip(self.rings,ring_col)):
            r=ring["r"]+pulse*(i+1)*0.5
            try:
                self.canvas.itemconfig(ring["item"],outline=col)
                self.canvas.coords(ring["item"],
                    self.cx-r,self.cy-r,self.cx+r,self.cy+r)
            except: pass

        # Barlar
        for i,bar in enumerate(self.bars):
            a=(2*math.pi*i)/36
            amp=bar_base+bar_amp*abs(math.sin(self.phase+i*0.35))
            ri=82; ro=82+amp
            x1=self.cx+math.cos(a)*ri; y1=self.cy+math.sin(a)*ri
            x2=self.cx+math.cos(a)*ro; y2=self.cy+math.sin(a)*ro
            try:
                self.canvas.coords(bar,x1,y1,x2,y2)
                self.canvas.itemconfig(bar,fill=bar_col)
            except: pass

        # Portlash zarrachalari
        for s in self.sparks:
            if not s["active"]: continue
            s["r"]+=s["spd"]
            s["life"]+=1
            if s["r"]>120 or s["life"]>40:
                s["active"]=False
                try: self.canvas.itemconfig(s["item"],fill="",outline="")
                except: pass
                continue
            x=self.cx+math.cos(s["angle"])*s["r"]
            y=self.cy+math.sin(s["angle"])*s["r"]
            alpha=max(0,1-s["life"]/40)
            col=bar_col if alpha>0.5 else C_DIM
            sz=max(1,3-s["life"]//15)
            try:
                self.canvas.coords(s["item"],x-sz,y-sz,x+sz,y+sz)
                self.canvas.itemconfig(s["item"],fill=col,outline="")
            except: pass

        # Matn
        try:
            self.canvas.itemconfig(self.main_text,fill=main_col)
            self.canvas.itemconfig(self.sub_text,fill=bar_col,text=sub)
        except: pass

        self.canvas.after(40,self._animate)

class LightningEffect:
    """Chaqmoq chiziqlar — ish bajarganda"""
    def __init__(self, canvas, w, h):
        self.canvas=canvas; self.w=w; self.h=h
        self.bolts=[]; self.running=False

    def trigger(self, color=C_CYAN):
        """Chaqmoq qo'zg'atish"""
        for _ in range(random.randint(3,7)):
            x1=random.uniform(0,self.w)
            y1=random.uniform(0,100)
            points=[x1,y1]
            cx,cy=x1,y1
            for _ in range(random.randint(4,8)):
                cx+=random.uniform(-80,80)
                cy+=random.uniform(20,60)
                cx=max(0,min(self.w,cx))
                cy=max(0,min(self.h,cy))
                points+=[cx,cy]
            try:
                item=self.canvas.create_line(points,fill=color,width=random.randint(1,3),
                                             smooth=True)
                self.bolts.append((item,time.time()))
            except: pass
        self.canvas.after(200,self._cleanup)

    def _cleanup(self):
        now=time.time()
        alive=[]
        for item,t in self.bolts:
            if now-t>0.3:
                try: self.canvas.delete(item)
                except: pass
            else:
                alive.append((item,t))
        self.bolts=alive

class ScanLine:
    """Skanerlash chizig'i"""
    def __init__(self, canvas, w, h):
        self.canvas=canvas; self.w=w; self.h=h
        self.y=0; self.running=False
        self.line=canvas.create_line(0,0,w,0,fill=C_BOR,width=1)

    def start(self): self.running=True; self._tick()
    def stop(self): self.running=False

    def _tick(self):
        if not self.running: return
        self.y=(self.y+2)%self.h
        try: self.canvas.coords(self.line,0,self.y,self.w,self.y)
        except: pass
        self.canvas.after(20,self._tick)

# ══════════════════════════════════════════
# ASOSIY UI
# ══════════════════════════════════════════
class BahodirAgent:
    def __init__(self, root):
        self.root=root
        self.root.title(f"◈ {AGENT_NAME} AI — GALAXY EDITION ◈")
        self.root.geometry("900x700")
        self.root.configure(bg=C_BG)
        self.root.resizable(False,False)
        self.terminal=pick_terminal()
        self.busy=False
        self.executor=ThreadPoolExecutor(max_workers=3)

        # Mikrofon BIR MARTA ochiladi
        self.recognizer=None
        self.mic=None
        self._src=None

        self._build_ui()
        self.root.after(800,self._init_agent)

    def _build_ui(self):
        # ── Asosiy fon kanvasi
        self.bg_cvs=tk.Canvas(self.root,width=900,height=700,bg=C_BG,highlightthickness=0)
        self.bg_cvs.place(x=0,y=0)

        # Yulduzlar maydoni
        self.stars=StarField(self.bg_cvs,900,700,250)

        # Skanerlash chizig'i
        self.scan=ScanLine(self.bg_cvs,900,700)

        # Chaqmoq effekti
        self.lightning=LightningEffect(self.bg_cvs,900,700)

        # ── Header
        tk.Label(self.root,text=f"◈  {AGENT_NAME}  AI  AGENT  ◈",
                 font=("Courier",26,"bold"),fg=C_LG,bg=C_BG
                 ).place(x=0,y=10,width=900)
        tk.Label(self.root,text="GALAXY EDITION  •  GROQ AI  •  FULL LINUX  •  VOICE CONTROL",
                 font=("Courier",8),fg=C_BOR,bg=C_BG
                 ).place(x=0,y=50,width=900)
        self.time_var=tk.StringVar()
        tk.Label(self.root,textvariable=self.time_var,
                 font=("Courier",10),fg=C_BOR,bg=C_BG,anchor="e"
                 ).place(x=760,y=12,width=140)
        self._tick_time()

        # Header chiziq
        hc=tk.Canvas(self.root,width=900,height=2,bg=C_BG,highlightthickness=0)
        hc.place(x=0,y=70); hc.create_line(0,1,900,1,fill=C_BOR)

        # ── Markaziy nebula doira
        self.center_cvs=tk.Canvas(self.root,width=260,height=260,bg=C_BG,highlightthickness=0)
        self.center_cvs.place(x=320,y=80)
        self.nebula=NebulaRing(self.center_cvs,130,130)

        # ── Katta status banner
        self.bn_cvs=tk.Canvas(self.root,width=900,height=56,bg=C_BG,highlightthickness=0)
        self.bn_cvs.place(x=0,y=350)
        self.bn_rect=self.bn_cvs.create_rectangle(15,4,885,52,outline=C_BOR,fill=C_BG,width=2)
        self.bn_txt=self.bn_cvs.create_text(450,28,text="[ YUKLANMOQDA... ]",
            font=("Courier",15,"bold"),fill=C_GREEN,anchor="center")
        # Burchak bezaklari
        for x,y,dx,dy in [(15,4,1,1),(885,4,-1,1),(15,52,1,-1),(885,52,-1,-1)]:
            for sz in [8,5,2]:
                self.bn_cvs.create_rectangle(x,y,x+dx*sz,y+dy*sz,outline=C_BOR,fill="")

        # ── Oxirgi buyruq
        self.cmd_var=tk.StringVar()
        tk.Label(self.root,textvariable=self.cmd_var,
                 font=("Courier",9),fg=C_BOR,bg=C_BG,
                 wraplength=860,justify="center"
                 ).place(x=20,y=413,width=860)

        # ── Sezgirlik slider
        sl_frame=tk.Frame(self.root,bg=C_BG)
        sl_frame.place(x=30,y=435,width=550)
        tk.Label(sl_frame,text="◈ MIC SEZGIRLIGI:",font=("Courier",9),
                 fg=C_BOR,bg=C_BG).pack(side="left")
        self.sens_var=tk.IntVar(value=300)
        ttk.Scale(sl_frame,from_=50,to=5000,orient="horizontal",
                  variable=self.sens_var,command=self._upd_sens
                  ).pack(side="left",padx=8,fill="x",expand=True)
        self.sens_lbl=tk.Label(sl_frame,text="300",font=("Courier",9),
                               fg=C_LG,bg=C_BG,width=5)
        self.sens_lbl.pack(side="left")

        # ── Log oyna
        lf=tk.Frame(self.root,bg=C_BOR,padx=1,pady=1)
        lf.place(x=30,y=460,width=840,height=165)
        li=tk.Frame(lf,bg=C_BG2); li.pack(fill="both",expand=True)
        tk.Label(li,text="◈ GALAXY COMMAND LOG",font=("Courier",8),
                 fg=C_BOR,bg=C_BG2,anchor="w").pack(fill="x",padx=8,pady=(3,0))
        sc=tk.Scrollbar(li); sc.pack(side="right",fill="y")
        self.log_box=tk.Text(li,font=("Courier",9),bg=C_BG2,fg=C_GREEN,
                             relief="flat",state="disabled",wrap="word",yscrollcommand=sc.set)
        self.log_box.pack(fill="both",expand=True,padx=8,pady=(0,4))
        sc.config(command=self.log_box.yview)
        for tag,col in [("user",C_LG),("ai",C_GREEN),("error",C_RED),
                        ("warn",C_AMBER),("fast",C_CYAN),("done",C_CYAN),
                        ("dim",C_BOR),("info",C_GREEN)]:
            self.log_box.tag_config(tag,foreground=col)

        # ── Tugmalar
        bf=tk.Frame(self.root,bg=C_BG)
        bf.place(x=30,y=635,width=840,height=48)

        # GAPIR tugmasi — yirik, ko'zga tashlanadi
        gf=tk.Frame(bf,bg=C_BOR,padx=2,pady=2)
        gf.pack(side="left",padx=10)
        self.btn=tk.Button(gf,text="🎤   G A P I R",
            font=("Courier",14,"bold"),fg=C_LG,bg=C_BG,
            activeforeground=C_BG,activebackground=C_LG,
            relief="flat",bd=0,cursor="hand2",padx=20,pady=6,
            command=self._on_gapir)
        self.btn.pack()

        # CHIQISH
        qf=tk.Frame(bf,bg=C_RED,padx=2,pady=2)
        qf.pack(side="right",padx=10)
        tk.Button(qf,text="⏻  CHIQISH",
            font=("Courier",12,"bold"),fg=C_RED,bg=C_BG,
            activeforeground=C_BG,activebackground=C_RED,
            relief="flat",bd=0,cursor="hand2",padx=12,pady=6,
            command=self._shutdown).pack()

        # Chap dekor panel
        lp=tk.Canvas(self.root,width=18,height=350,bg=C_BG,highlightthickness=0)
        lp.place(x=0,y=80)
        lp.create_line(16,0,16,350,fill=C_BOR,width=1)
        for i in range(9):
            y=15+i*38
            lp.create_rectangle(4,y,14,y+20,outline=C_DIM,fill=C_BG)

        # O'ng dekor
        rp=tk.Canvas(self.root,width=18,height=350,bg=C_BG,highlightthickness=0)
        rp.place(x=882,y=80)
        rp.create_line(2,0,2,350,fill=C_BOR,width=1)
        for i in range(9):
            y=15+i*38
            rp.create_rectangle(4,y,14,y+20,outline=C_DIM,fill=C_BG)

    def _tick_time(self):
        self.time_var.set(time.strftime("[ %H:%M:%S ]"))
        self.root.after(1000,self._tick_time)

    def _upd_sens(self,*a):
        v=self.sens_var.get()
        self.sens_lbl.config(text=str(v))
        if self.recognizer: self.recognizer.energy_threshold=v

    # ── HOLAT O'ZGARTIRISH
    def set_mode(self,mode,sub=None):
        cfg={
            "idle":     (C_LG,   C_BOR,  "TAYYOR",       "[ TAYYOR — GAPIR TUGMASINI BOSING ]",  C_BOR,  C_GREEN),
            "listening":(C_LG,   C_LG,   "TINGLAYAPMAN", "[ 🎤  SIZI  TINGLAYAPMAN... ]",         C_LG,   C_LG),
            "thinking": (C_AMBER,C_AMBER,"TAHLIL",        "[ ⚡  GROQ AI TAHLIL QILMOQDA... ]",   C_AMBER,C_AMBER),
            "done":     (C_CYAN, C_CYAN, "BAJARILDI!",   "[ ✅  BAJARILDI,  XO'JAYIN! ]",         C_CYAN, C_CYAN),
            "error":    (C_RED,  C_RED,  "XATO",          "[ ❌  XATO YUZBERDI ]",                 C_RED,  C_RED),
        }
        _,_,_,bn_t,bn_c,_ = cfg.get(mode,cfg["idle"])
        def _do():
            self.nebula.set_mode(mode)
            self.bn_cvs.itemconfig(self.bn_txt,text=sub or bn_t,fill=bn_c)
            self.bn_cvs.itemconfig(self.bn_rect,outline=bn_c)
            # Chaqmoq — faqat bajarilganda
            if mode=="done":
                self.lightning.trigger(C_CYAN)
                self.root.after(150,lambda:self.lightning.trigger(C_LG))
            elif mode=="listening":
                self.lightning.trigger(C_LG)
        self.root.after(0,_do)

    def log(self,msg,tag="info"):
        def _do():
            self.log_box.configure(state="normal")
            ts=time.strftime("%H:%M:%S")
            self.log_box.insert("end",f"[{ts}] ","dim")
            self.log_box.insert("end",msg+"\n",tag)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0,_do)

    def set_cmd(self,t): self.root.after(0,lambda:self.cmd_var.set(t))

    # ── TTS — espeak (tez, offline)
    def _speak(self,text):
        def _do():
            r=subprocess.run(["espeak","-v","ru+f3","-s","155","-a","180",text],capture_output=True)
            if r.returncode!=0:
                subprocess.run(["espeak-ng","-v","ru",text],capture_output=True)
        threading.Thread(target=_do,daemon=True).start()

    # ── GROQ
    def _ask_groq(self,text):
        try:
            r=requests.post(GROQ_URL,
                headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":GROQ_MODEL,
                      "messages":[{"role":"system","content":SYSTEM_PROMPT},
                                  {"role":"user","content":text}],
                      "temperature":0.1,"max_tokens":400},
                timeout=10)
            if r.status_code==200:
                raw=r.json()["choices"][0]["message"]["content"].strip()
                return self._parse(raw)
            return {"action":"chat","params":{},"reply":f"API xato {r.status_code}"}
        except Exception as e:
            return {"action":"chat","params":{},"reply":f"Xato: {str(e)[:30]}"}

    def _parse(self,raw):
        raw=re.sub(r"^```(?:json)?\s*|\s*```$","",raw.strip(),flags=re.MULTILINE)
        cands=[]; depth=0; start=-1
        for i,ch in enumerate(raw):
            if ch=="{":
                if depth==0: start=i
                depth+=1
            elif ch=="}":
                depth-=1
                if depth==0 and start>=0:
                    cands.append(raw[start:i+1]); start=-1
        cands.sort(key=len,reverse=True)
        for c in cands:
            c2=re.sub(r"\\'","'",c); c2=re.sub(r",(\s*[}\]])","\\1",c2)
            for a in [c,c2]:
                try: return json.loads(a)
                except: continue
        return {"action":"chat","params":{},"reply":raw[:80]}

    # ── INIT
    def _init_agent(self):
        self.stars.start()
        self.scan.start()
        self.nebula.start()
        self.set_mode("idle")

        def _setup():
            self.log("Tizim ishga tushirilmoqda...")
            if IS_ROOT: self.log(f"🔐 ROOT rejim — user: {REAL_USER}","warn")
            else: self.log(f"👤 User: {REAL_USER}","dim")

            checks={"espeak":"espeak","xdotool":"xdotool",
                    "xdg-open":"xdg-open","mpv":"mpv","yt-dlp":"yt-dlp"}
            for name,cmd in checks.items():
                if which(cmd): self.log(f"  ✓ {name}","done")
                else: self.log(f"  ✗ {name} yo'q","warn")
            if self.terminal: self.log(f"💻 Terminal: {self.terminal}","dim")

            try:
                self.recognizer=sr.Recognizer()
                self.recognizer.dynamic_energy_threshold=False
                self.recognizer.energy_threshold=300
                self.recognizer.pause_threshold=0.5
                self.recognizer.phrase_threshold=0.3
                self.recognizer.non_speaking_duration=0.5

                self.sens_var.set(300)
                self.root.after(0,lambda:self.sens_lbl.config(text="300"))

                self.mic=sr.Microphone()
                self._src=self.mic.__enter__()
                self.log("✅ Mikrofon tayyor — BIR MARTA ochildi","done")
                self.log(f"🔧 Sezgirlik: {self.recognizer.energy_threshold:.0f} | Pauza: {self.recognizer.pause_threshold}s","dim")
            except Exception as e:
                self.log(f"❌ Mikrofon: {e}","error")
                self.set_mode("error"); return

            self.log("🚀 GALAXY AGENT TAYYOR!","done")
            self.set_mode("idle")
            self._speak(f"Salom! Men {AGENT_NAME}. Nima qilamiz?")

        threading.Thread(target=_setup,daemon=True).start()

    # ── GAPIR
    def _on_gapir(self):
        if self.busy or not self.recognizer or not self._src: return
        threading.Thread(target=self._voice_thread,daemon=True).start()

    def _voice_thread(self):
        self.busy=True
        self.root.after(0,lambda:self.btn.config(state="disabled",text="⏳  TINGLAYAPMAN..."))
        self.set_mode("listening")
        self.log("🎤 Gapiring...","dim")

        try:
            self.recognizer.energy_threshold=self.sens_var.get()
            audio=self.recognizer.listen(self._src,timeout=3,phrase_time_limit=5)
        except sr.WaitTimeoutError:
            self.log("⏰ Ovoz eshitilmadi","warn")
            self.set_mode("idle"); self._reset_btn(); return
        except Exception as e:
            self.log(f"❌ Tinglash: {e}","error")
            self.set_mode("error"); self._reset_btn(); return

        self.set_mode("thinking","OVOZ TANILMOQDA...")
        self.log("🔊 Tanilmoqda...")
        text=""
        for lang in ["uz-UZ","ru-RU","en-US"]:
            try:
                text=self.recognizer.recognize_google(audio,language=lang)
                if text: break
            except sr.UnknownValueError: continue
            except sr.RequestError as e:
                self.log(f"STT: {e}","error"); break

        if not text:
            self.log("❓ Tushunilmadi","warn")
            self.set_mode("idle"); self._reset_btn(); return

        self.set_cmd(f"»  {text}")
        self.log(f"👤 Siz: {text}","user")

        if text.lower() in ["xayr","chiqish","stop","poka","bye","quit"]:
            self._speak("Xayr! Ko'rishguncha.")
            self.root.after(1500,self._shutdown); return

        # Tezkor lokal
        t0=time.time()
        quick=quick_match(text)
        if quick:
            ms=int((time.time()-t0)*1000)
            self.log(f"⚡ TEZKOR ({ms}ms): {quick['action']}","fast")
            res=quick
        else:
            self.set_mode("thinking","GROQ AI TAHLIL QILMOQDA...")
            self.log("🤔 Groq AI ga yuborilmoqda...")
            t0=time.time()
            res=self._ask_groq(text)
            self.log(f"Groq ({time.time()-t0:.1f}s): {res.get('action')}","dim")

        action=res.get("action","chat")
        params=res.get("params",{})
        steps=res.get("steps")
        reply=res.get("reply","Tushunmadim")
        self.log(f"🤖 {AGENT_NAME}: {reply}","ai")

        self.set_mode("thinking","BAJARILMOQDA...")
        result=self._exec(action,params,steps)
        if action!="chat":
            self.log(f"⚙️ {result}","info")

        # BAJARILDI — chaqmoq, animatsiya
        self.set_mode("done")
        self.set_cmd(f"✅  {reply}")
        self._speak(reply)
        time.sleep(2)
        self.set_mode("idle")
        self._reset_btn()

    def _reset_btn(self):
        self.busy=False
        self.root.after(0,lambda:self.btn.config(state="normal",text="🎤   G A P I R"))

    # ── EXEC
    def _exec(self,action,params=None,steps=None):
        params=params or {}
        T=self.terminal  # qisqa

        DANGEROUS=["mkfs",":(){ :|:& };:","dd if=/dev/zero of=/dev/"]
        def is_dangerous(cmd):
            return any(d in cmd for d in DANGEROUS)

        try:
            if action=="sequence":
                res=[]
                for st in (steps or []):
                    r=self._exec(st.get("action","chat"),st.get("params",{}),st.get("steps"))
                    res.append(f"{st.get('action')}→{r}")
                return " | ".join(res)

            if action=="chat": return "Suhbat"
            if action=="delay": time.sleep(float(params.get("sec",1))); return "Kutildi"

            if action=="youtube_play":
                q=params.get("query","").strip()
                return youtube_play_smart(q) if q else "Query bo'sh"

            if action=="youtube_search":
                q=params.get("query","")
                popen_as_user(["xdg-open",f"https://www.youtube.com/results?search_query={quote_plus(q)}"])
                return f"YouTube: {q}"

            if action=="web_search":
                q=params.get("query","")
                popen_as_user(["xdg-open",f"https://www.google.com/search?q={quote_plus(q)}"])
                return f"Google: {q}"

            if action=="open_url":
                popen_as_user(["xdg-open",params.get("url","")]); return "Ochildi"

            if action=="open_app":
                app=params.get("app","")
                if not app: return "Nom bo'sh"
                return open_app_smart(app,T)

            if action=="close_app":
                subprocess.run(["pkill","-f",params.get("app","")],capture_output=True)
                return "Yopildi"

            if action=="terminal_run":
                cmd=params.get("cmd","").strip()
                if not cmd: return "Buyruq bo'sh"
                if is_dangerous(cmd): return "❌ Xavfli buyruq bloklandi"
                run_in_terminal(cmd,T)
                return f"Terminal: {cmd[:60]}"

            if action=="shell_cmd":
                cmd=params.get("cmd","").strip()
                if not cmd: return "Bo'sh"
                if is_dangerous(cmd): return "❌ Xavfli bloklandi"
                if params.get("sudo",False) and not IS_ROOT: cmd=f"sudo {cmd}"
                subprocess.Popen(cmd,shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                return f"$ {cmd[:50]}"

            if action=="shell_capture":
                cmd=params.get("cmd","").strip()
                if not cmd: return "Bo'sh"
                if is_dangerous(cmd): return "❌ Xavfli bloklandi"
                try:
                    r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=20)
                    out=(r.stdout+r.stderr).strip()[:500]
                    self.log(f"📜 {out}","dim"); return "Natija log da"
                except subprocess.TimeoutExpired: return "Vaqt tugadi"

            if action=="create_file":
                name=params.get("name","")
                content=params.get("content","")
                path=params.get("path",REAL_HOME)
                if not name: return "Fayl nomi kerak"
                full=os.path.join(path,name)
                os.makedirs(os.path.dirname(full),exist_ok=True)
                with open(full,"w",encoding="utf-8") as f: f.write(content)
                return f"Fayl: {full}"

            if action=="create_dir":
                path=params.get("path","").strip()
                if not path: return "Yo'l kerak"
                os.makedirs(path,exist_ok=True)
                return f"Papka: {path}"

            if action=="gui_type":
                if not which("xdotool"): return "xdotool yo'q"
                subprocess.run(["xdotool","type","--delay","15",params.get("text","")]); return "Yozildi"

            if action=="gui_key":
                if not which("xdotool"): return "xdotool yo'q"
                subprocess.run(["xdotool","key",params.get("key","Return")]); return "Bosildi"

            if action=="gui_click":
                if not which("xdotool"): return "xdotool yo'q"
                x,y=params.get("x",0),params.get("y",0)
                subprocess.run(["xdotool","mousemove",str(x),str(y),"click","1"]); return f"Klik ({x},{y})"

            if action=="screenshot":
                ts=time.strftime("%Y%m%d_%H%M%S")
                p=os.path.join(REAL_HOME,"Pictures",f"ss_{ts}.png")
                os.makedirs(os.path.dirname(p),exist_ok=True)
                for t in [["scrot",p],["gnome-screenshot","-f",p],["maim",p]]:
                    if which(t[0]): subprocess.run(t,capture_output=True); return f"Saqlandi: {p}"
                return "Tool yo'q"

            if action=="lock_screen":
                for t,c in [("loginctl",["loginctl","lock-session"]),
                            ("xdg-screensaver",["xdg-screensaver","lock"]),
                            ("gnome-screensaver-command",["gnome-screensaver-command","-l"])]:
                    if which(t): subprocess.Popen(c); return "Qulflandi"
                return "Tool yo'q"

            if action=="shutdown":
                subprocess.Popen(["shutdown","now"] if IS_ROOT else ["sudo","shutdown","now"])
                return "O'chirilmoqda"
            if action=="reboot":
                subprocess.Popen(["reboot"] if IS_ROOT else ["sudo","reboot"]); return "Qayta yuklanmoqda"

            if action=="brightness_up":
                subprocess.run(["brightnessctl","set","+10%"],capture_output=True); return "Yorqinlik +"
            if action=="brightness_down":
                subprocess.run(["brightnessctl","set","10%-"],capture_output=True); return "Yorqinlik -"
            if action=="brightness_set":
                subprocess.run(["brightnessctl","set",f"{params.get('level',50)}%"],capture_output=True)
                return f"Yorqinlik {params.get('level',50)}%"
            if action=="volume_up":
                subprocess.run(["pactl","set-sink-volume","@DEFAULT_SINK@","+10%"],capture_output=True); return "Ovoz +"
            if action=="volume_down":
                subprocess.run(["pactl","set-sink-volume","@DEFAULT_SINK@","-10%"],capture_output=True); return "Ovoz -"
            if action=="volume_set":
                subprocess.run(["pactl","set-sink-volume","@DEFAULT_SINK@",f"{params.get('level',50)}%"],capture_output=True)
                return f"Ovoz {params.get('level',50)}%"
            if action=="get_time": return time.strftime("%H:%M")
            if action=="get_date": return time.strftime("%d.%m.%Y")

            return f"Noma'lum: {action}"
        except Exception as e:
            return f"Xato: {str(e)[:80]}"

    def _shutdown(self):
        self.busy=False
        try: self.stars.stop()
        except: pass
        try: self.scan.stop()
        except: pass
        try: self.nebula.stop()
        except: pass
        try:
            if self._src and self.mic: self.mic.__exit__(None,None,None)
        except: pass
        try: self.executor.shutdown(wait=False)
        except: pass
        self.root.destroy()

# ══════════════════════════════════════════
if __name__=="__main__":
    print(f"""
╔══════════════════════════════════════════════════╗
║   ◈  {AGENT_NAME} AI — GALAXY EDITION  ◈           ║
║   Groq + Voice + Stars + Lightning + Nebula    ║
║   User: {REAL_USER:<10}  Root: {"YES 🔐" if IS_ROOT else "NO  "}              ║
╚══════════════════════════════════════════════════╝
Ishlatish:
  sudo -E env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY python3 bahodir_galaxy.py
    """)
    root=tk.Tk()
    app=BahodirAgent(root)
    root.mainloop()
                              