# 📽️ Telegram Video Downloader (GUI)

A premium, feature-rich desktop application for downloading media (Videos, Audio, Photos, Files) from Telegram channels with advanced batch management, anti-bot delays, and full session control.

![Main Interface](screenshot_placeholder.png)

## ✨ Features

- **Dual Modes**: 
  - **Single**: Download a specific message from a link.
  - **Bulk**: Scan entire channels and selectively batch-download.
- **Advanced Scanning**: 
  - Scan Newer/Older messages from history.
  - Resume from specific Message ID or Telegram Link.
  - Filter by media type (Videos, Audo, Photos, Files).
- **Premium Bulk Manager**:
  - **Randomized Delays**: Anti-bot randomization (min/max range) to prevent account bans.
  - **Real-time Countdown**: Live timer for the next download.
  - **Smart Pagination**: 25-item pages with scroll preservation.
  - **Force Re-download**: Re-fetch selected "Done" items.
- **Modern UI**:
  - Mac-optimized styling with `-apple-system` font support.
  - Dark mode by default.
  - Detailed progress status and speed calculation (MB/s).
- **Persistent Storage**:
  - Settings, Session, and Download History (SQLite) are saved in `~/.telegram_video_downloader` (non-root install).

## 🚀 Installation

### 1. Requirements
- Python 3.9+ 
- Telegram API Credentials ([Get them here](https://my.telegram.org/auth))

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/TelegramVideoDownloader.git
cd TelegramVideoDownloader

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install telethon PyQt6
```

### 3. Usage
```bash
python tg_downloader_gui.py
```

## ⚙️ Configuration
On first launch, the app will ask for your **API ID** and **API HASH**. 
These are stored securely in your local user directory.

- **Bulk Delay**: Use a range like `5` to `15` seconds to stay safe from Telegram's rate limits.
- **Import/Export**: You can export your download list to JSON for backup or migration.

### 📦 Building the Executable (Optional)
If you want to package the app into a standalone `.exe` (Windows), `.app` (Mac), or binary (Linux):

```bash
# Running the build script
python3 build_app.py
```
This will create a standalone executable in the `dist/` folder.

## 🛠 Platform Support

-   **🖥 Windows**: Fully supported. Optimized font fallback for Segoe UI.
-   **🍎 macOS**: Native high-DPI support and Apple System Font integration.
-   **🐧 Linux**: Tested on Ubuntu. Supports Cantarell/Fira fonts. (Note: May require `libxcb` for PyQt6 UI).

## ⚙️ Project Structure
- `tg_downloader_gui.py`: Main entry point and UI logic.
- `core/telegram_client.py`: Core logic for Telegram API communication.
- `core/database.py`: SQLite-based download tracking.
- `build_app.py`: Automated cross-platform packaging script.
