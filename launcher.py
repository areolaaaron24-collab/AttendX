import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

intro = os.path.join(BASE_DIR, "intro.py")
main = os.path.join(BASE_DIR, "main.py")

subprocess.run([sys.executable, intro], cwd=BASE_DIR)

subprocess.Popen([sys.executable, main], cwd=BASE_DIR)