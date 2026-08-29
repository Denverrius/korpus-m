# -*- coding: utf-8 -*-
"""
Multi-bot supervisor runner:
Runs both Korpus-M (@korpus_m_admin_bot) and Na Bulvare (@na_bulvare_bot) bots simultaneously.
"""
import subprocess
import time
import sys

print("🚀 Starting Korpus-M & Na Bulvare Telegram Bots...", flush=True)

p1 = subprocess.Popen([sys.executable, "bot.py"])
p2 = subprocess.Popen([sys.executable, "restaurant_bot.py"])

try:
    while True:
        if p1.poll() is not None:
            print("⚠️ Korpus-M bot stopped, restarting in 2s...", flush=True)
            time.sleep(2)
            p1 = subprocess.Popen([sys.executable, "bot.py"])
        if p2.poll() is not None:
            print("⚠️ Restaurant bot stopped, restarting in 2s...", flush=True)
            time.sleep(2)
            p2 = subprocess.Popen([sys.executable, "restaurant_bot.py"])
        time.sleep(5)
except KeyboardInterrupt:
    p1.terminate()
    p2.terminate()
