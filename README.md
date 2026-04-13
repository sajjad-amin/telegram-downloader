# TG Downloader

A professional Telegram media downloader with support for both GUI and CLI interfaces.

## Features

- **Double Interface**: GUI (PyQt6) for visual management and CLI for automation.
- **Multi-Account Profiles**: Manage multiple Telegram accounts. Each profile maintains its own session, settings, and download database.
- **Resume Support**: Interrupted downloads can be resumed without losing data.
- **Batch Downloading**: Scan channels or use a `links.txt` file to download multiple files with built-in anti-blocking delays.
- **Database Tracking**: Keeps a record of download status (completed, pending, failed) to avoid duplicates.
- **Modern UI**: A sleek, compact dark-mode interface.

## Installation

### Prerequisites
- Python 3.8+
- [API ID and API Hash](https://my.telegram.org/apps) from Telegram.

### Setup (Virtual Environment)
1. Clone the repository:
   ```bash
   git clone https://github.com/sajjad-amin/telegram-downloader.git
   cd telegram-downloader
   ```
2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### GUI Mode
Launch the visual interface:
```bash
python tg_downloader_gui.py
```
- **Profiles**: Switch accounts via the top-right dropdown. Use the "Profiles" tab to add or remove accounts.
- **Single**: Download a single file via message link.
- **Bulk**: Scan a channel and download multiple files in batch.

### CLI Mode
For command-line operations:
```bash
python console.py
```
- Run without arguments for help documentation.
- `python console.py [URL]` to download a single file.
- `python console.py links.txt` to download links from a text file.
- `python console.py --profile` to manage account profiles.

## Building Standalone App
To create a standalone executable for your platform:
```bash
python build.py
```
- The output can be found in the `dist/` folder.
- macOS users can generate a `.dmg` installer (requires `create-dmg`).
```bash
brew install create-dmg
```

## Configuration
All data is stored in `~/.telegram_video_downloader/`.
- `active_profile`: Stores the current active profile reference.
- Profile subfolders: Each contains its own `my_account.session`, `downloads.db`, and `settings.ini`.

## License
MIT
