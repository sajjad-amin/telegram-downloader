# Telegram Video Downloader (TGDL)

A professional, cross-platform Telegram media downloader supporting GUI, CLI, and Web interfaces. Built for high-speed downloads, multi-account management, and reliable session persistence.

## 🚀 Features

- **Triple Interface**: 
  - **GUI (PyQt6)**: Desktop-native experience.
  - **CLI (Console)**: Advanced automation and terminal-speed operations.
  - **Web (React/Flask)**: Modern, responsive dashboard perfect for VPS/Remote usage.
- **Multi-Account Profiles**: Manage dozens of Telegram accounts. Each profile is sandboxed with its own session file, individual settings, and download database.
- **Robust Downloads**: Built-in resume support, anti-blocking delays, and recursive directory management.
- **High-Density Data**: File management via sortable tables, bulk actions, and nested folder navigation.
- **Real-time Monitoring**: Socket.io integration provides instant progress updates on the Web dashboard.

## 🛠️ Installation

### Prerequisites
- **Python 3.10+**
- **Node.js & NPM** (Only for Web build)
- **Telegram API Credentials**: Get your `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org/apps).

### Setup
1. **Clone & Navigate**:
   ```bash
   git clone https://github.com/sajjad-amin/telegram-downloader.git
   cd telegram-downloader
   ```
2. **Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements_web.txt
   ```
3. **Configuration**:
   Copy `.env.example` to `.env` and fill in your credentials.
   ```bash
   cp .env.example .env
   ```

## 📖 Usage

### 🎨 GUI Mode
Native desktop interface:
```bash
python tg_downloader_gui.py
```

### ⌨️ CLI Mode
Automated downloads and profile switching:
```bash
python console.py --help
```

### 🌐 Web Mode (Production / VPS)
The Web UI is served via Flask and handles both API and static assets.

1. **Build Frontend Assets**:
   ```bash
   cd web && npm install && npm run build
   cd ..
   ```
2. **Start with PM2**:
   ```bash
   pm2 start ecosystem.config.js
   ```
3. **Access**: Navigate to `http://your-vps-ip:5001`. Use the credentials defined in your `.env`.

## 📁 Project Structure
- `core/`: Shared downloading and client logic.
- `gui/`: PyQt6 UI components.
- `web/`: React frontend and Flask backend.
- `~/.telegram_video_downloader/`: Home for all profiles, sessions, and databases.

## 📄 License
MIT
