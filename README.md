# Spotify Local Downloader

Simple GUI tool to save audio locally from Spotify song links.

<img width="1142" height="927" alt="image" src="https://github.com/user-attachments/assets/2fb827e0-b599-490f-87f0-e50c38c04ece" />


## Features

- Paste Spotify links directly
- Batch download multiple songs
- Simple GUI
- Saves MP3 files locally
- Beginner friendly

## 1. Install Python

Download Python:

https://www.python.org/downloads/

<img width="832" height="508" alt="image" src="https://github.com/user-attachments/assets/f6efd1b5-b778-4f00-815c-17fac67d2c03" />

Important: enable **Add Python to PATH** during installation.

If you miss this checkbox, the app may not run when you type `python` in the terminal.

## 2. Install FFmpeg

Open Command Prompt and run:

```bash
winget install ffmpeg
```


If Windows asks for permission, accept it and let the install finish.

## 3. Download the Project

If you use Git, open terminal inside the folder where you want the project and run:

```bash
git clone https://github.com/jhonpork1233-beep/spotify-local-downloader.git
```


If you do not use Git, click the green **Code** button on GitHub, then click **Download ZIP**. After that, unzip the folder.

## 4. Install Requirements

Open terminal in the project folder.

Then run:

```bash
pip install -r requirements.txt
```

This installs the Python package used by the app.

## 5. Run the App

In the same terminal, run:

```bash
python main.py
```

If the app opens, you are good.

## 6. Paste Spotify Links

In Spotify, copy the song link.


Paste one Spotify link per line inside the app.

Example:

```text
https://open.spotify.com/track/...
https://open.spotify.com/track/...
https://open.spotify.com/track/...
```

## 7. Download

Click **Download**.

Songs are saved automatically to:

```text
Music/Spotify Downloads
```

You can also click **Open folder** inside the app.

## Notes

This project was originally made for personal use and later cleaned up because people on Reddit wanted it :)

Educational/personal-use project only. Please respect artists, copyright, platforms, and your local laws.

