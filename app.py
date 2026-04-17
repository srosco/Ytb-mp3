import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
import winreg
from tkinter import filedialog

import pystray
from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from PIL import Image, ImageDraw

app = Flask(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
APP_NAME = "Convertisseur YTB"
APP_PATH = os.path.abspath(sys.argv[0])
PORT = 5000
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- Config ---

def load_saved_folder():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f).get("folder", "")
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def save_folder(path):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"folder": path}, f)


# --- Startup Windows ---

def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run")
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


def enable_startup():
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                      f'"{pythonw}" "{APP_PATH}"')
    winreg.CloseKey(key)


def disable_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass


# --- Tray icon ---

def make_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill="#e52d27")
    draw.polygon([(24, 18), (24, 46), (48, 32)], fill="white")
    return img


def build_menu(tray_icon):
    def open_app(icon, item):
        webbrowser.open(f"http://localhost:{PORT}")

    def toggle_startup(icon, item):
        if is_startup_enabled():
            disable_startup()
        else:
            enable_startup()
        icon.menu = build_menu(icon)
        icon.update_menu()

    def quit_app(icon, item):
        icon.stop()
        os._exit(0)

    startup_label = (
        "✓ Démarrer avec Windows" if is_startup_enabled()
        else "  Démarrer avec Windows"
    )

    return pystray.Menu(
        pystray.MenuItem("Ouvrir (localhost:5000)", open_app, default=True),
        pystray.MenuItem(startup_label, toggle_startup),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quitter", quit_app),
    )


# --- Flask routes ---

@app.route("/")
def index():
    return render_template("index.html", saved_folder=load_saved_folder())


@app.route("/choose-folder", methods=["POST"])
def choose_folder():
    result = {"path": ""}

    def open_dialog():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Choisir le dossier de destination")
        root.destroy()
        result["path"] = folder or ""

    t = threading.Thread(target=open_dialog)
    t.start()
    t.join()

    if result["path"]:
        save_folder(result["path"])

    return jsonify({"path": result["path"]})


@app.route("/convert")
def convert():
    url = request.args.get("url", "").strip()
    folder = request.args.get("folder", "").strip()

    def generate():
        if not url:
            yield "data: ERROR:URL manquante.\n\n"
            return
        if not folder:
            yield "data: ERROR:Aucun dossier sélectionné.\n\n"
            return
        if not os.path.isdir(folder):
            yield "data: ERROR:Le dossier sélectionné n'existe pas.\n\n"
            return

        NO_WINDOW = subprocess.CREATE_NO_WINDOW

        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True,
                           creationflags=NO_WINDOW)
        except FileNotFoundError:
            yield "data: ERROR:yt-dlp n'est pas installé. Lancez : pip install yt-dlp\n\n"
            return

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True,
                           creationflags=NO_WINDOW)
        except FileNotFoundError:
            yield "data: ERROR:ffmpeg n'est pas installé. Téléchargez-le sur https://ffmpeg.org et ajoutez-le au PATH.\n\n"
            return

        yield "data: STATUS:Téléchargement en cours...\n\n"

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--format", "bestaudio/best",
            "--output", os.path.join(folder, "%(title)s.%(ext)s"),
            "--newline",
            url,
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        )

        filename = None
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            if "[ExtractAudio]" in line or "Destination:" in line:
                yield "data: STATUS:Conversion en MP3...\n\n"
            if "Destination:" in line:
                parts = line.split("Destination:")
                if len(parts) > 1:
                    filename = parts[1].strip().split("/")[-1].split("\\")[-1]

        process.wait()

        if process.returncode == 0:
            if filename:
                yield f"data: DONE:Terminé ! Fichier : {filename}\n\n"
            else:
                yield "data: DONE:Terminé !\n\n"
        else:
            yield "data: ERROR:La conversion a échoué. Vérifiez l'URL ou votre connexion.\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# --- Main ---

if __name__ == "__main__":
    # Flask dans un thread background
    flask_thread = threading.Thread(
        target=lambda: app.run(port=PORT, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    # Icône tray
    tray = pystray.Icon(APP_NAME, make_icon(), APP_NAME)
    tray.menu = build_menu(tray)
    tray.run()
