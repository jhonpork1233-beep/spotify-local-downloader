import tkinter as tk
from tkinter import ttk
import threading
import subprocess
import sys
import os
import re
import queue
import json
import urllib.request


PYTHON = sys.executable
HOME = os.path.expanduser("~")
OUTPUT_DIR = os.path.join(HOME, "Music", "Spotify Downloads")
YOUTUBE_SEARCH_LIMIT = 8
DURATION_TOLERANCE_SECONDS = 8

os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_duration_value(value):
    if value is None:
        return None

    try:
        seconds = float(value)
        if seconds > 1000:
            seconds = seconds / 1000
        return int(round(seconds))
    except (TypeError, ValueError):
        pass

    colon_parts = str(value).strip().split(":")
    if 2 <= len(colon_parts) <= 3 and all(part.isdigit() for part in colon_parts):
        parts = [int(part) for part in colon_parts]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0] * 3600 + parts[1] * 60 + parts[2]

    match = re.fullmatch(
        r"P(?:T)?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?",
        str(value).strip(),
        re.IGNORECASE,
    )
    if not match:
        return None

    hours = float(match.group(1) or 0)
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    return int(round(hours * 3600 + minutes * 60 + seconds))


def find_meta_content(html, name):
    patterns = [
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_spotify_duration(html):
    for meta_name in ("music:duration", "twitter:audio:duration"):
        value = find_meta_content(html, meta_name)
        duration = parse_duration_value(value)
        if duration:
            return duration

    json_patterns = [
        r'"duration_ms"\s*:\s*(\d+)',
        r'"duration"\s*:\s*"([^"]+)"',
        r'"duration"\s*:\s*(\d+)',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            duration = parse_duration_value(match.group(1))
            if duration:
                return duration

    return None


def format_duration(seconds):
    if not seconds:
        return "unknown"

    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes}:{seconds:02d}"


def get_song_info(url):
    try:
        req = urllib.request.Request(
            url.strip(),
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")

        match = re.search(r"<title>(.*?)</title>", html)

        if match:
            title = match.group(1)
            title = re.sub(r"\s*[|\-]\s*Spotify.*$", "", title).strip()
            title = re.sub(r"^Listen to\s+", "", title).strip()
            return {
                "title": title,
                "duration": extract_spotify_duration(html),
            }

    except Exception:
        return None

    return None


def get_song_name(url):
    info = get_song_info(url)
    return info["title"] if info else None


def youtube_result_url(info):
    url = info.get("webpage_url") or info.get("original_url")
    if url:
        return url

    video_id = info.get("id") or info.get("url")
    if video_id and re.fullmatch(r"[\w-]{11}", str(video_id)):
        return f"https://www.youtube.com/watch?v={video_id}"

    return video_id


def search_youtube_candidates(song_name):
    cmd = [
        PYTHON,
        "-m",
        "yt_dlp",
        f"ytsearch{YOUTUBE_SEARCH_LIMIT}:{song_name} audio",
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        "--socket-timeout",
        "30",
        "--retries",
        "3",
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=90,
    )

    candidates = []

    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue

        try:
            info = json.loads(line)
        except json.JSONDecodeError:
            continue

        url = youtube_result_url(info)
        duration = parse_duration_value(info.get("duration"))

        if url:
            candidates.append(
                {
                    "title": info.get("title") or "Unknown title",
                    "url": url,
                    "duration": duration,
                }
            )

    return candidates


def choose_best_youtube_match(song_name, spotify_duration):
    candidates = search_youtube_candidates(song_name)

    if not candidates:
        return None, []

    if not spotify_duration:
        return candidates[0], candidates

    timed_candidates = [
        candidate
        for candidate in candidates
        if candidate["duration"] is not None
    ]

    if not timed_candidates:
        return candidates[0], candidates

    timed_candidates.sort(
        key=lambda candidate: abs(candidate["duration"] - spotify_duration)
    )

    best = timed_candidates[0]
    difference = abs(best["duration"] - spotify_duration)

    if difference <= DURATION_TOLERANCE_SECONDS:
        return best, candidates

    return None, candidates


class DownloaderApp:
    def __init__(self, root):
        self.root = root

        self.root.title("Spotify Downloader")
        self.root.geometry("920x720")
        self.root.minsize(760, 560)
        self.root.configure(bg="#0b0f0d")
        self.root.resizable(True, True)

        self.skip_flag = False
        self.running = True
        self.queue = queue.Queue()

        self.urls = []
        self.total = 0

        self._build_ui()

        self.root.after(100, self.process_queue)
        self.overall_label.config(text="Ready")

    def _build_ui(self):
        self.colors = {
            "bg": "#0b0f0d",
            "panel": "#111815",
            "panel_2": "#151f1a",
            "border": "#24352d",
            "accent": "#1ed760",
            "accent_hover": "#32e372",
            "fg": "#f3fff7",
            "muted": "#9fb3a7",
            "soft": "#d7f5df",
            "input": "#07100c",
            "line": "#58705f",
        }

        self._setup_styles()

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        app = tk.Frame(self.root, bg=self.colors["bg"])
        app.grid(row=0, column=0, sticky="nsew")
        app.grid_columnconfigure(0, weight=1)
        app.grid_rowconfigure(2, weight=4)
        app.grid_rowconfigure(5, weight=3)

        self._build_header(app)
        self._build_input_panel(app)
        self._build_controls(app)
        self._build_status_panel(app)
        self._build_log_panel(app)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Spotify.Horizontal.TProgressbar",
            troughcolor="#172019",
            background=self.colors["accent"],
            bordercolor="#172019",
            lightcolor=self.colors["accent"],
            darkcolor=self.colors["accent"],
        )

        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background="#24352d",
            darkcolor="#24352d",
            lightcolor="#24352d",
            troughcolor="#0e1511",
            bordercolor="#0e1511",
            arrowcolor=self.colors["muted"],
        )

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=self.colors["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 14))
        header.grid_columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="Spotify Downloader",
            font=("Segoe UI", 24, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["accent"],
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            header,
            text="Local audio queue",
            font=("Segoe UI", 10),
            bg=self.colors["bg"],
            fg=self.colors["muted"],
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.overall_label = tk.Label(
            header,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["soft"],
        )
        self.overall_label.grid(row=0, column=1, sticky="e", padx=(18, 0))

        self.overall_bar = ttk.Progressbar(
            parent,
            mode="determinate",
            maximum=1,
            style="Spotify.Horizontal.TProgressbar",
        )
        self.overall_bar.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 16))

    def _build_input_panel(self, parent):
        input_panel = self._panel(parent)
        input_panel.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 16))
        input_panel.grid_columnconfigure(0, weight=1)
        input_panel.grid_rowconfigure(1, weight=1)

        input_header = tk.Frame(input_panel, bg=self.colors["panel"])
        input_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        input_header.grid_columnconfigure(0, weight=1)

        tk.Label(
            input_header,
            text="Spotify links",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["fg"],
        ).grid(row=0, column=0, sticky="w")

        self.link_count_label = tk.Label(
            input_header,
            text="0 links",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["muted"],
        )
        self.link_count_label.grid(row=0, column=1, sticky="e")

        editor = tk.Frame(input_panel, bg=self.colors["input"])
        editor.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        editor.grid_columnconfigure(1, weight=1)
        editor.grid_rowconfigure(0, weight=1)

        self.line_numbers = tk.Text(
            editor,
            width=4,
            padx=8,
            pady=10,
            takefocus=0,
            border=0,
            background=self.colors["input"],
            foreground=self.colors["line"],
            state="disabled",
            font=("Cascadia Mono", 10),
            wrap="none",
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        self.url_box = tk.Text(
            editor,
            height=10,
            bg=self.colors["input"],
            fg=self.colors["fg"],
            insertbackground=self.colors["accent"],
            selectbackground="#214b33",
            selectforeground=self.colors["fg"],
            font=("Cascadia Mono", 10),
            bd=0,
            padx=8,
            pady=10,
            wrap="none",
        )
        self.url_box.grid(row=0, column=1, sticky="nsew")

        self.url_scrollbar = ttk.Scrollbar(
            editor,
            command=self._sync_scroll,
            style="Vertical.TScrollbar",
        )
        self.url_scrollbar.grid(row=0, column=2, sticky="ns")

        self.url_box.config(yscrollcommand=self._on_url_scroll)
        self.url_box.bind("<KeyRelease>", self.update_line_numbers)
        self.url_box.bind("<MouseWheel>", self.update_line_numbers)
        self.url_box.bind("<Configure>", self.update_line_numbers)
        self.update_line_numbers()

    def _build_controls(self, parent):
        controls = tk.Frame(parent, bg=self.colors["bg"])
        controls.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 16))
        controls.grid_columnconfigure(1, weight=1)

        self.download_btn = self._button(
            controls,
            "Download",
            self.colors["accent"],
            "#07100c",
            self.start_downloads,
            self.colors["accent_hover"],
        )
        self.download_btn.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.clear_btn = self._button(
            controls,
            "Clear",
            "#25322b",
            self.colors["fg"],
            self.clear_links,
            "#33463b",
        )
        self.clear_btn.grid(row=0, column=1, sticky="w")

        self.open_folder_btn = self._button(
            controls,
            "Open folder",
            "#25322b",
            self.colors["fg"],
            self.open_output_folder,
            "#33463b",
        )
        self.open_folder_btn.grid(row=0, column=2, sticky="e", padx=(0, 10))

        self.skip_btn = self._button(
            controls,
            "Skip current",
            "#25322b",
            self.colors["fg"],
            self.skip,
            "#33463b",
        )
        self.skip_btn.grid(row=0, column=3, sticky="e")

    def _build_status_panel(self, parent):
        status_panel = self._panel(parent)
        status_panel.grid(row=4, column=0, sticky="ew", padx=28, pady=(0, 16))
        status_panel.grid_columnconfigure(0, weight=1)

        self.song_label = tk.Label(
            status_panel,
            text="Waiting...",
            font=("Segoe UI", 13, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["fg"],
            justify="left",
            anchor="w",
            wraplength=680,
        )
        self.song_label.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))

        self.status_label = tk.Label(
            status_panel,
            text="",
            font=("Segoe UI", 9),
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            justify="left",
            anchor="w",
            wraplength=680,
        )
        self.status_label.grid(row=1, column=0, sticky="ew", padx=18)

        self.song_bar = ttk.Progressbar(
            status_panel,
            mode="indeterminate",
            style="Spotify.Horizontal.TProgressbar",
        )
        self.song_bar.grid(row=2, column=0, sticky="ew", padx=18, pady=(12, 18))
        status_panel.bind("<Configure>", self._update_status_wrap)

    def _build_log_panel(self, parent):
        log_panel = self._panel(parent)
        log_panel.grid(row=5, column=0, sticky="nsew", padx=28, pady=(0, 24))
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(1, weight=1)

        tk.Label(
            log_panel,
            text="Activity",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["fg"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        self.log_box = tk.Text(
            log_panel,
            height=8,
            bg=self.colors["input"],
            fg=self.colors["muted"],
            insertbackground=self.colors["fg"],
            selectbackground="#214b33",
            font=("Cascadia Mono", 9),
            bd=0,
            padx=12,
            pady=10,
            state="disabled",
            wrap="word",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def _panel(self, parent):
        return tk.Frame(
            parent,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["border"],
        )

    def _button(self, parent, text, bg, fg, command, active_bg):
        button = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            bd=0,
            padx=22,
            pady=10,
            cursor="hand2",
            command=command,
        )

        button.bind(
            "<Enter>",
            lambda _event: button.config(bg=active_bg)
            if button["state"] != "disabled"
            else None,
        )
        button.bind("<Leave>", lambda _event: button.config(bg=bg))
        return button

    def _sync_scroll(self, *args):
        self.url_box.yview(*args)
        self.line_numbers.yview(*args)

    def _on_url_scroll(self, first, last):
        self.url_scrollbar.set(first, last)
        self.line_numbers.yview_moveto(first)

    def _set_button_enabled(self, button, enabled):
        button.config(state="normal" if enabled else "disabled")

    def _update_status_wrap(self, event):
        wrap = max(320, event.width - 40)
        self.song_label.config(wraplength=wrap)
        self.status_label.config(wraplength=wrap)

    def clear_links(self):
        self.url_box.delete("1.0", "end")
        self.update_line_numbers()
        self.overall_label.config(text="Ready")
        self.overall_bar["value"] = 0
        self.song_label.config(text="Waiting...")
        self.status_label.config(text="")

    def open_output_folder(self):
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            os.startfile(OUTPUT_DIR)
        except Exception as e:
            self.log(f"[error] Could not open folder: {e}")

    def update_line_numbers(self, event=None):
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", "end")

        line_count = int(self.url_box.index("end-1c").split(".")[0])
        numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert("1.0", numbers)
        self.line_numbers.config(state="disabled")

        raw = self.url_box.get("1.0", "end")
        count = len([line for line in raw.splitlines() if line.strip()])
        self.link_count_label.config(text=f"{count} link" if count == 1 else f"{count} links")

    def start_downloads(self):
        raw = self.url_box.get("1.0", "end")

        self.urls = [
            line.strip()
            for line in raw.splitlines()
            if line.strip()
        ]

        self.total = len(self.urls)

        if not self.urls:
            self.log("[error] No Spotify links pasted.")
            return

        self.overall_bar["maximum"] = self.total
        self.overall_bar["value"] = 0
        self.skip_btn.config(text="Skip current")
        self._set_button_enabled(self.download_btn, False)
        self._set_button_enabled(self.clear_btn, False)
        self._set_button_enabled(self.skip_btn, True)

        threading.Thread(
            target=self.run_downloads,
            daemon=True,
        ).start()

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def skip(self):
        self.skip_flag = True
        self.log("[skip] Skip requested...")

    def process_queue(self):
        while not self.queue.empty():
            action, data = self.queue.get()

            if action == "log":
                self.log(data)

            elif action == "overall_text":
                self.overall_label.config(text=data)

            elif action == "overall_val":
                self.overall_bar["value"] = data

            elif action == "status":
                self.song_label.config(text=data[0])
                self.status_label.config(text=data[1])

            elif action == "bar_start":
                self.song_bar.start(12)

            elif action == "bar_stop":
                self.song_bar.stop()

            elif action == "finish":
                self.skip_btn.config(text="Done")
                self._set_button_enabled(self.skip_btn, False)
                self._set_button_enabled(self.download_btn, True)
                self._set_button_enabled(self.clear_btn, True)

        self.root.after(100, self.process_queue)

    def run_downloads(self):
        done = 0

        for i, url in enumerate(self.urls):
            if not self.running:
                break

            self.skip_flag = False

            self.queue.put(("overall_text", f"Song {i + 1} of {self.total}"))
            self.queue.put(("overall_val", i))
            self.queue.put(("log", f"\n[{i + 1}/{self.total}] Fetching metadata..."))
            self.queue.put(("status", ("Fetching song info...", url[:60] + "...")))
            self.queue.put(("bar_start", None))

            info = get_song_info(url)

            if not info:
                self.queue.put(("log", "[error] Could not get song name, skipping"))
                self.queue.put(("bar_stop", None))
                continue

            name = info["title"]
            spotify_duration = info["duration"]

            self.queue.put(("log", f"[song] {name}"))
            if spotify_duration:
                self.queue.put(
                    ("log", f"[spotify] Duration: {format_duration(spotify_duration)}")
                )
            else:
                self.queue.put(("log", "[spotify] Duration unavailable"))

            self.queue.put(("status", (name, "Searching YouTube...")))

            if self.skip_flag:
                self.queue.put(("bar_stop", None))
                continue

            try:
                match, candidates = choose_best_youtube_match(name, spotify_duration)
            except Exception as e:
                self.queue.put(("log", f"[error] YouTube search failed: {e}"))
                self.queue.put(("bar_stop", None))
                continue

            if not match:
                checked = len(candidates)
                self.queue.put(
                    (
                        "log",
                        f"[skip] No close duration match found after checking {checked} results",
                    )
                )
                self.queue.put(("bar_stop", None))
                continue

            if spotify_duration and match["duration"]:
                diff = abs(match["duration"] - spotify_duration)
                self.queue.put(
                    (
                        "log",
                        "[match] "
                        f"{format_duration(spotify_duration)} on Spotify, "
                        f"{format_duration(match['duration'])} on YouTube, "
                        f"{diff}s difference",
                    )
                )

            self.queue.put(("log", f"[youtube] {match['title']}"))

            cmd = [
                PYTHON,
                "-m",
                "yt_dlp",
                match["url"],
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
                "-o",
                os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
                "--no-playlist",
                "--socket-timeout",
                "30",
                "--retries",
                "3",
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                )

                self.queue.put(("status", (name, "Downloading...")))

                while True:
                    if self.skip_flag:
                        proc.terminate()
                        self.queue.put(("log", "[skip] Skipped"))
                        break

                    line = proc.stdout.readline()

                    if not line and proc.poll() is not None:
                        break

                    if line:
                        line = line.strip()

                        if "[download]" in line or "ETA" in line:
                            self.queue.put(("status", (name, line[:90])))

                        elif "ERROR" in line:
                            self.queue.put(("log", f"[warning] {line[:120]}"))

                proc.wait()

                if not self.skip_flag:
                    if proc.returncode == 0:
                        self.queue.put(("log", "[ok] Done"))
                        done += 1
                    else:
                        self.queue.put(("log", f"[error] Failed (exit {proc.returncode})"))

            except Exception as e:
                self.queue.put(("log", f"[error] {e}"))

            self.queue.put(("bar_stop", None))

        self.queue.put(("overall_val", self.total))
        self.queue.put(("overall_text", f"Done: {done}/{self.total} downloaded"))
        self.queue.put(("status", ("All done!", f"Files saved to {OUTPUT_DIR}")))
        self.queue.put(("finish", None))
        self.queue.put(("log", f"\n[finished] {done} songs in {OUTPUT_DIR}"))


def run_app():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()
