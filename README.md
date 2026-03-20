# 📽️ Premium Telegram Video Downloader (GUI)

A high-performance, cross-platform desktop application designed to capture media from Telegram channels. Features advanced scanning, randomized anti-bot delays, and full download history management.

## ✨ Features

- **Advanced Scanning Logic**:
  - Scan **Newer** or **Older** message ranges relative to your current history.
  - Optional **Start/Resume** pinpointing from cold message IDs or Telegram links.
  - Automatic channel entity resolution.
- **Bulk Download Manager**:
  - **Randomized Anti-Bot Delays**: Configure custom min-max delay windows (e.g., 5-15s) to mimic human behavior and avoid Telegram platform bans.
  - **Real-time Countdown**: Live UI status bar showing seconds until next file download.
  - **Graceful Control**: Integrated Pause, Resume, and Stop controls during every phase.
- **Robust Database Engine**:
  - SQLite3-backed history ensures you never download the same file twice.
  - Import/Export bulk lists via JSON for cross-device migration.
  - Force re-download capability for previously "completed" items.
- **Premium User Experience**:
  - **Dynamic Scroll Lock**: Table stays at your current position even as history is updated in the background.
  - Dark mode by default with optimized font stacks for **macOS**, **Windows**, and **Linux**.
  - Precise speed calculation (MB/s) and progress tracking.

## 🚀 Setup & Installation

### 1. Requirements
- Python 3.9 or higher
- Telegram API Credentials ([Get them at my.telegram.org](https://my.telegram.org/auth))

### 2. Environment Configuration
Copy the template and fill in your `API_ID` and `API_HASH`:
```bash
cp .env.example .env
```

### 3. Dependency Installation
Follow the standard Python practices:
```bash
# Initialize virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Install required packages
pip install -r requirements.txt
```

### 4. Running the Application
```bash
python tg_downloader_gui.py
```

## 📦 Distribution (Build)
To package the app into a standalone executable (`.app`, `.exe`, or binary) for any platform:
```bash
python build_app.py
```

## ⚙️ Project Architecture
- `tg_downloader_gui.py`: Central UI entry and event loop orchestration.
- `core/`: Client communication, parsing logic, and SQLite database management.
- `gui/`: Sub-modules for custom signals, workers, and premium dialogs.
- `build_app.py`: Cross-platform PyInstaller automation script.

## 🛠 Tech Stack
-   **Telethon 1.x**: High-level Telegram API library.
-   **PyQt6**: Cross-platform GUI framework.
-   **SQLite3**: Persistent download tracking.

## 📄 License
MIT License. Open-source developed for professional media archiving.
