# -*- coding: utf-8 -*-
"""
Multi-bot runner for Railway:
Runs Korpus-M bot (@korpus_m_admin_bot) and Na Bulvare restaurant bot (@na_bulvare_bot) simultaneously with auto-restart.
"""
import subprocess
import time
import sys

print("🚀 Starting all bots on Railway...", flush=True)

p1 = subprocess.Popen([sys.executable, "bot.py"])
p2 = subprocess.Popen([sys.executable, "restaurant_bot.py"])

try:
    while True:
        if p1.poll() is not None:
            print("⚠️ Korpus-M bot stopped, restarting...", flush=True)
            p1 = subprocess.Popen([sys.executable, "bot.py"])
        if p2.poll() is not None:
            print("⚠️ Na Bulvare bot stopped, restarting...", flush=True)
            p2 = subprocess.Popen([sys.executable, "restaurant_bot.py"])
        time.sleep(5)
except KeyboardInterrupt:
    p1.terminate()
    p2.terminate()
