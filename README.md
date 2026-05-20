# Spotify Local Downloader

Simple GUI tool to save audio locally from Spotify song links.

![App Screenshot](assets/app.png)

## Features

- Paste Spotify links directly
- Batch download multiple songs
- Simple GUI
- Saves MP3 files locally
- Beginner friendly

## 1. Install Python

Download Python:

https://www.python.org/downloads/

![Python installer showing Add Python to PATH](assets/python-path.png)

Important: enable **Add Python to PATH** during installation.

If you miss this checkbox, the app may not run when you type `python` in the terminal.

## 2. Install FFmpeg

Open Command Prompt and run:

```bash
winget install ffmpeg
```

![Terminal showing FFmpeg install](assets/ffmpeg-install.png)

If Windows asks for permission, accept it and let the install finish.

## 3. Download the Project

If you use Git, open terminal inside the folder where you want the project and run:

```bash
git clone YOUR_REPO_LINK
```

![GitHub Code button or Download ZIP button](assets/download-project.png)

If you do not use Git, click the green **Code** button on GitHub, then click **Download ZIP**. After that, unzip the folder.

## 4. Install Requirements

Open terminal in the project folder.

Then run:

```bash
pip install -r requirements.txt
```

![Successful pip install](assets/pip-install.png)

This installs the Python package used by the app.

## 5. Run the App

In the same terminal, run:

```bash
python main.py
```

![App launching](assets/app-launch.png)

If the app opens, you are good.

## 6. Paste Spotify Links

In Spotify, copy the song link.

![Spotify copy link menu](assets/spotify-link.png)

Paste one Spotify link per line inside the app.

Example:

```text
https://open.spotify.com/track/...
https://open.spotify.com/track/...
https://open.spotify.com/track/...
```

## 7. Download

Click **Download**.

![App downloading songs](assets/download-demo.png)

Songs are saved automatically to:

```text
Music/Spotify Downloads
```

You can also click **Open folder** inside the app.

## Notes

This project was originally made for personal use and later cleaned up because people on Reddit wanted it :)

Educational/personal-use project only. Please respect artists, copyright, platforms, and your local laws.

## Screenshot Folder

Keep screenshots inside the `assets/` folder:

```text
assets/app.png
assets/python-path.png
assets/ffmpeg-install.png
assets/download-project.png
assets/pip-install.png
assets/app-launch.png
assets/spotify-link.png
assets/download-demo.png
```

This keeps the repo clean and makes the README easier for beginners to follow.
