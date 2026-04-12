# YouTube → MP3 Converter

Application web locale pour convertir des vidéos YouTube en fichier MP3 à la meilleure qualité possible.

## Fonctionnalités

- Conversion YouTube → MP3 en qualité maximale (VBR 0 / ~320kbps)
- Sélection du dossier de destination via une fenêtre native Windows
- Le dossier de destination est mémorisé entre les sessions
- Statut de la conversion en temps réel (téléchargement, conversion, terminé)
- Icône dans la barre des tâches (system tray) — tourne en fond de manière discrète
- Option de démarrage automatique avec Windows

## Prérequis

- Python 3.10+
- [ffmpeg](https://ffmpeg.org) ajouté au PATH

```bash
# Installer ffmpeg via winget
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
```

## Installation

```bash
git clone https://github.com/srosco/Ytb-mp3.git
cd Ytb-mp3
pip install -r requirements.txt
```

## Lancement

```bash
pythonw app.py
```

Une icône rouge apparaît dans la barre des tâches. Clic droit pour accéder au menu.

Ouvrir l'interface : [http://localhost:5000](http://localhost:5000)

## Utilisation

1. Cliquer **Choisir** pour sélectionner le dossier de destination
2. Coller l'URL YouTube
3. Cliquer **Convertir**
4. Le fichier MP3 est sauvegardé dans le dossier choisi

## Menu tray

| Option | Description |
|--------|-------------|
| Ouvrir (localhost:5000) | Ouvre l'interface dans le navigateur |
| Démarrer avec Windows | Active / désactive le lancement automatique au démarrage |
| Quitter | Arrête l'application |

## Stack

- Python + Flask
- yt-dlp
- ffmpeg
- pystray + Pillow
- HTML / CSS / JS vanilla (Server-Sent Events)
