import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

app = Flask(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


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

        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        except FileNotFoundError:
            yield "data: ERROR:yt-dlp n'est pas installé. Lancez : pip install yt-dlp\n\n"
            return

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
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


if __name__ == "__main__":
    app.run(debug=True)
