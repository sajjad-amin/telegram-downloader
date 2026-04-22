import sys
import os
import time
import json
import asyncio
import threading
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QProgressBar, QFileDialog,
                             QInputDialog, QMessageBox, QDialog, QTabWidget, QTextEdit,
                             QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView, QComboBox)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from core.telegram_client import TelegramDownloader
from core.utils import parse_telegram_link, parse_channel_entity
from core.database import Database
from gui.signals import WorkerSignals
from gui.dialogs import CredentialsDialog

HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".telegram_video_downloader")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

DB_FILE = os.path.join(CONFIG_DIR, "downloads.db")
ACTIVE_PROFILE_FILE = os.path.join(CONFIG_DIR, "active_profile")

def get_active_profile_name():
    if os.path.exists(ACTIVE_PROFILE_FILE):
        with open(ACTIVE_PROFILE_FILE, "r") as f:
            return f.read().strip()
    return None

def set_active_profile(name):
    if name == "Default" or not name:
        if os.path.exists(ACTIVE_PROFILE_FILE): os.remove(ACTIVE_PROFILE_FILE)
    else:
        with open(ACTIVE_PROFILE_FILE, "w") as f:
            f.write(name)

def get_config_paths():
    active_p = get_active_profile_name()
    
    # Auto-pick first profile if none active and root is empty
    root_configured = os.path.exists(os.path.join(CONFIG_DIR, "settings.ini")) and \
                      os.path.exists(os.path.join(CONFIG_DIR, "my_account.session"))
                      
    if not active_p and not root_configured:
        profiles = get_all_profiles()
        if profiles:
            active_p = profiles[0]
            set_active_profile(active_p)

    cd = os.path.join(CONFIG_DIR, active_p) if active_p else CONFIG_DIR
    return cd, os.path.join(cd, "settings.ini"), \
           os.path.join(cd, "my_account"), \
           os.path.join(cd, "downloads.db")

def get_all_profiles():
    if not os.path.exists(CONFIG_DIR): return []
    return sorted([d for d in os.listdir(CONFIG_DIR) 
                  if os.path.isdir(os.path.join(CONFIG_DIR, d)) and d.isdigit()])


class TelegramDownloaderApp(QWidget):
    def __init__(self, loop=None):
        super().__init__()
        try:
            self.loop = loop or asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        self.init_paths()
        self.downloader = None
        self.signals = WorkerSignals()
        
        self.start_time, self.initial_bytes = None, 0
        self.is_fetching, self.is_fetch_paused = False, False
        self.is_single_paused = False
        self.is_bulk_running, self.is_bulk_paused = False, False
        
        self.current_message, self.current_file_path = None, None
        self.page_size, self.current_page = 100, 0
        self.selected_ids_memory, self.max_selection = [], 100

        self.init_ui()
        self.connect_signals()
        self.refresh_profiles_combo()
        
        if not self.api_id or not self.api_hash:
            if not self.show_credentials_dialog(): sys.exit()

        threading.Thread(target=self.run_asyncio_loop, daemon=True).start()

    def closeEvent(self, event):
        self.is_fetching, self.is_bulk_running = False, False
        self.settings.setValue("chk_v", self.chk_v.isChecked()); self.settings.setValue("chk_a", self.chk_a.isChecked())
        self.settings.setValue("chk_p", self.chk_p.isChecked()); self.settings.setValue("chk_f", self.chk_f.isChecked())
        self.settings.setValue("delay_min", self.delay_min.text()); self.settings.setValue("delay_max", self.delay_max.text())
        self.settings.sync()
        if self.loop.is_running(): self.loop.call_soon_threadsafe(self.loop.stop)
        event.accept()

    def init_ui(self):
        self.setWindowTitle("Telegram Video Downloader")
        # Modern Compact Styling
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #cfcfcf; }
            QLineEdit, QTextEdit, QTableWidget { background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; padding: 4px; selection-background-color: #0078d4; }
            QPushButton { background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px; padding: 4px 12px; }
            QPushButton:hover { background-color: #3d3d3d; border-color: #0078d4; }
            QPushButton#grey_btn { color: #888; }
            QProgressBar { border: 1px solid #333; border-radius: 4px; text-align: center; height: 14px; font-size: 10px; }
            QProgressBar::chunk { background-color: #0078d4; }
            QTabWidget::pane { border: 1px solid #333; }
            QTabBar::tab { background: #1e1e1e; padding: 6px 20px; border: 1px solid #333; border-bottom: none; }
            QTabBar::tab:selected { background: #2d2d2d; border-top: 2px solid #0078d4; }
            QHeaderView::section { background-color: #1e1e1e; padding: 4px; border: none; border-right: 1px solid #333; border-bottom: 1px solid #333; }
        """)

        main_layout = QVBoxLayout(); main_layout.setContentsMargins(8, 8, 8, 8); self.tabs = QTabWidget()
        
        self.tab_single = QWidget(); single_layout = QVBoxLayout(self.tab_single)
        self.link_entry = QLineEdit(); self.link_entry.setPlaceholderText("Paste Telegram message link here...")
        self.link_entry.setText(self.settings.value("last_single_url", ""))
        single_layout.addWidget(self.link_entry)
        btn_row = QHBoxLayout(); self.btn_select_location = QPushButton("Select Destination"); self.btn_start_download = QPushButton("Start Download"); self.btn_pause_resume = QPushButton("Pause/Resume")
        
        # Enable start button if we have a saved path
        last_fp = self.settings.value("last_single_fp", "")
        if last_fp and os.path.exists(os.path.dirname(last_fp)):
            self.current_file_path = last_fp
            self.btn_start_download.setEnabled(True)
            self.single_status_label = QLabel(f"Resume: {os.path.basename(last_fp)}") if hasattr(self, 'single_status_label') else None # Handled below
        
        self.btn_select_location.setEnabled(True) # Always allow choosing new location
        self.btn_pause_resume.setEnabled(False)
        btn_row.addWidget(self.btn_select_location); btn_row.addWidget(self.btn_start_download); btn_row.addWidget(self.btn_pause_resume)
        self.btn_select_location.clicked.connect(self.on_select_location_click); self.btn_start_download.clicked.connect(self.on_start_download_click); self.btn_pause_resume.clicked.connect(self.on_pause_resume_click)
        single_layout.addLayout(btn_row)
        
        # Internal Single Tab Status Bar
        self.single_progress_bar = QProgressBar(); self.single_progress_bar.setVisible(False)
        self.single_status_label = QLabel("Ready to download.")
        if last_fp: self.single_status_label.setText(f"Last used: {os.path.basename(last_fp)}")
        self.single_status_label.setWordWrap(True)
        
        self.btn_open_folder_single = QPushButton("📂 Open Folder"); self.btn_open_folder_single.setObjectName("grey_btn"); self.btn_open_folder_single.setVisible(False)
        self.btn_open_folder_single.clicked.connect(lambda: self.open_folder(os.path.dirname(self.current_file_path)))
        
        single_layout.addStretch()
        single_layout.addWidget(self.single_progress_bar); 
        status_row_s = QHBoxLayout(); status_row_s.addWidget(self.single_status_label, 1); status_row_s.addWidget(self.btn_open_folder_single); single_layout.addLayout(status_row_s)
        self.tab_bulk = QWidget(); bulk_layout = QVBoxLayout(self.tab_bulk)
        chan_row = QHBoxLayout(); chan_row.addWidget(QLabel("Channel Source:")); self.bulk_channel_input = QLineEdit()
        self.bulk_channel_input.setText(self.settings.value("last_channel_link", "")); self.bulk_channel_input.textChanged.connect(self.update_fetch_button_text); chan_row.addWidget(self.bulk_channel_input, 1); bulk_layout.addLayout(chan_row)

        filt_row = QHBoxLayout()
        self.chk_v = QCheckBox("Vids"); self.chk_v.setChecked(str(self.settings.value("chk_v", "true")).lower() == "true")
        self.chk_a = QCheckBox("Audio"); self.chk_a.setChecked(str(self.settings.value("chk_a", "false")).lower() == "true")
        self.chk_p = QCheckBox("Photos"); self.chk_p.setChecked(str(self.settings.value("chk_p", "false")).lower() == "true")
        self.chk_f = QCheckBox("Files"); self.chk_f.setChecked(str(self.settings.value("chk_f", "false")).lower() == "true")
        filt_row.addWidget(QLabel("Include:")); filt_row.addWidget(self.chk_v); filt_row.addWidget(self.chk_a); filt_row.addWidget(self.chk_p); filt_row.addWidget(self.chk_f)
        filt_row.addStretch(); filt_row.addWidget(QLabel("Delay (s):")); 
        self.delay_min = QLineEdit(); self.delay_min.setFixedWidth(40); self.delay_min.setText(str(self.settings.value("delay_min", "5")))
        self.delay_max = QLineEdit(); self.delay_max.setFixedWidth(40); self.delay_max.setText(str(self.settings.value("delay_max", "15")))
        filt_row.addWidget(self.delay_min); filt_row.addWidget(QLabel("-")); filt_row.addWidget(self.delay_max)
        bulk_layout.addLayout(filt_row)

        start_row = QHBoxLayout(); start_row.addWidget(QLabel("Start/Resume from ID (Optional):")); self.start_link_box = QLineEdit(); self.start_link_box.setPlaceholderText("Paste ID or message link to scan from a specific point.")
        self.start_link_box.textChanged.connect(self.update_fetch_button_text)
        start_row.addWidget(self.start_link_box); bulk_layout.addLayout(start_row)

        fetch_row = QHBoxLayout()
        self.btn_fetch_new = QPushButton("Scan Newer"); self.btn_fetch_new.setEnabled(False); self.btn_fetch_new.clicked.connect(lambda: self.on_fetch_bulk_list(direction='new'))
        self.btn_fetch_old = QPushButton("Scan Older"); self.btn_fetch_old.setEnabled(False); self.btn_fetch_old.clicked.connect(lambda: self.on_fetch_bulk_list(direction='old'))
        self.btn_f_pause = QPushButton("Pause Scan"); self.btn_f_pause.setEnabled(False); self.btn_f_stop = QPushButton("Stop Scan"); self.btn_f_stop.setEnabled(False); self.btn_f_pause.clicked.connect(self.on_toggle_fetch_pause); self.btn_f_stop.clicked.connect(self.on_stop_fetch)
        fetch_row.addWidget(self.btn_fetch_new); fetch_row.addWidget(self.btn_fetch_old); fetch_row.addWidget(self.btn_f_pause); fetch_row.addWidget(self.btn_f_stop); bulk_layout.addLayout(fetch_row)

        mgmt_row = QHBoxLayout(); self.chk_master_sel = QCheckBox("Select All Page"); self.chk_master_sel.stateChanged.connect(self.on_master_sel_changed); self.btn_unsel_global = QPushButton("Deselect All Global"); self.btn_unsel_global.setObjectName("grey_btn"); self.btn_unsel_global.clicked.connect(self.deselect_all_global)
        self.view_filter = QComboBox(); self.view_filter.addItems(["All Files", "Pending Only", "Videos Only", "Audio Only", "Photos Only", "Files Only"]); self.view_filter.currentIndexChanged.connect(lambda: (setattr(self, 'current_page', 0), self.load_bulk_list_to_table()))
        self.sort_box = QComboBox(); self.sort_box.addItems(["Newest First", "Oldest First", "Largest First", "By Status", "By Type"]); self.sort_box.currentIndexChanged.connect(lambda: (setattr(self, 'current_page', 0), self.load_bulk_list_to_table())); mgmt_row.addWidget(self.chk_master_sel); mgmt_row.addWidget(self.btn_unsel_global); mgmt_row.addStretch(); mgmt_row.addWidget(QLabel("View:")); mgmt_row.addWidget(self.view_filter); mgmt_row.addWidget(QLabel("Sort:")); mgmt_row.addWidget(self.sort_box); bulk_layout.addLayout(mgmt_row)

        info_row = QHBoxLayout(); self.lbl_tot = QLabel("Loaded: 0 files"); self.lbl_sel = QLabel("Selected: 0/100"); self.lbl_sel.setStyleSheet("color: #ffa500; font-weight: bold;"); info_row.addWidget(self.lbl_tot); info_row.addStretch(); info_row.addWidget(self.lbl_sel); bulk_layout.addLayout(info_row); self.bulk_table = QTableWidget(0, 6); self.bulk_table.setHorizontalHeaderLabels(["", "ID", "Type", "Name", "Size", "Status"]); self.bulk_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents); self.bulk_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch); bulk_layout.addWidget(self.bulk_table); self.pagi_layout = QHBoxLayout(); bulk_layout.addLayout(self.pagi_layout)
        
        foot_row = QHBoxLayout(); self.btn_bulk_f = QPushButton("Set Destination"); self.btn_bulk_f.clicked.connect(self.on_select_bulk_location); self.btn_bulk_s = QPushButton("Start Download"); self.btn_bulk_s.setEnabled(False); self.btn_bulk_s.clicked.connect(self.on_start_bulk_download); self.btn_bulk_p = QPushButton("Pause/Resume"); self.btn_bulk_p.setEnabled(False); self.btn_bulk_p.clicked.connect(self.on_stop_bulk_download)
        btn_del = QPushButton("Delete Selected"); btn_del.clicked.connect(self.on_delete_selected); 
        btn_exp_lnks = QPushButton("Export Links (TXT)"); btn_exp_lnks.clicked.connect(self.on_export_links_txt);
        btn_exp = QPushButton("Export JSON"); btn_exp.clicked.connect(self.on_export_list); btn_imp = QPushButton("Import JSON"); btn_imp.clicked.connect(self.on_import_list); btn_wipe = QPushButton("Clear Database"); btn_wipe.clicked.connect(self.on_clear_bulk_list)
        foot_row.addWidget(self.btn_bulk_f); foot_row.addWidget(self.btn_bulk_s); foot_row.addWidget(self.btn_bulk_p); foot_row.addStretch(); 
        foot_row.addWidget(btn_del); foot_row.addWidget(btn_exp_lnks); foot_row.addWidget(btn_exp); foot_row.addWidget(btn_imp); foot_row.addWidget(btn_wipe); bulk_layout.addLayout(foot_row)
        
        # Internal Bulk Tab Status Bar
        self.bulk_progress_bar = QProgressBar(); self.bulk_progress_bar.setVisible(False)
        self.bulk_status_label = QLabel("Scan a channel to start.")
        
        self.btn_open_folder_bulk = QPushButton("📂 Open Folder"); self.btn_open_folder_bulk.setObjectName("grey_btn"); self.btn_open_folder_bulk.setVisible(False)
        self.btn_open_folder_bulk.clicked.connect(lambda: self.open_folder(self.settings.value("last_bulk_dir", "")))
        
        bulk_layout.addWidget(self.bulk_progress_bar)
        status_row_b = QHBoxLayout(); status_row_b.addWidget(self.bulk_status_label, 1); status_row_b.addWidget(self.btn_open_folder_bulk); bulk_layout.addLayout(status_row_b)
        self.tabs.addTab(self.tab_single, "Single"); self.tabs.addTab(self.tab_bulk, "Bulk")
        
        # Profile Management Tab
        self.tab_profile = QWidget(); prof_layout = QVBoxLayout(self.tab_profile)
        prof_info = QLabel("<h3>Profile Management</h3>Manage multiple Telegram accounts. Each profile maintains its own session, database, and settings.")
        prof_info.setWordWrap(True); prof_layout.addWidget(prof_info)
        
        self.profile_table = QTableWidget(0, 4); self.profile_table.setHorizontalHeaderLabels(["Name", "Account", "Folder", "Action"])
        self.profile_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        prof_layout.addWidget(self.profile_table)
        
        prof_btn_row = QHBoxLayout()
        btn_add_acc = QPushButton("+ Add New Account"); btn_add_acc.clicked.connect(self.on_add_account_click)
        btn_refresh_p = QPushButton("Refresh List"); btn_refresh_p.setObjectName("grey_btn"); btn_refresh_p.clicked.connect(self.load_profiles_to_table)
        prof_btn_row.addWidget(btn_add_acc); prof_btn_row.addStretch(); prof_btn_row.addWidget(btn_refresh_p)
        prof_layout.addLayout(prof_btn_row)
        prof_layout.addStretch()
        
        self.tabs.addTab(self.tab_profile, "Profiles")
        
        # Header with Profile Selector
        header_layout = QHBoxLayout(); header_layout.addWidget(QLabel("<h2>Telegram Downloader</h2>")); header_layout.addStretch()
        self.prof_combo = QComboBox(); self.prof_combo.setMinimumWidth(180)
        self.prof_combo.currentIndexChanged.connect(self.on_profile_combo_changed)
        header_layout.addWidget(QLabel("Active Profile:")); header_layout.addWidget(self.prof_combo)
        
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.load_profiles_to_table()

    def connect_signals(self):
        # Mapping signals to their respective tab widgets
        self.signals.single_progress.connect(lambda p, t: (self.single_progress_bar.setValue(int(p)), self.single_progress_bar.setVisible(True), self.single_status_label.setText(t)))
        self.signals.single_status.connect(lambda t, c: (self.single_status_label.setText(t), self.single_status_label.setStyleSheet(f"color: {c};")))
        
        self.signals.bulk_progress.connect(lambda p, t: (self.bulk_progress_bar.setValue(int(p)), self.bulk_progress_bar.setVisible(True), self.bulk_status_label.setText(t)))
        self.signals.bulk_status.connect(lambda t, c: (self.bulk_status_label.setText(t), self.bulk_status_label.setStyleSheet(f"color: {c};")))
        
        self.signals.ask_phone.connect(self.prompt_phone); self.signals.ask_code.connect(self.prompt_code); self.signals.ask_location_success.connect(self.on_ask_location_success); self.signals.success.connect(self.on_success); self.signals.error.connect(self.on_error); self.signals.ready.connect(self.on_ready); self.signals.bulk_list_fetched.connect(self.on_bulk_list_fetched); self.signals.bulk_table_refresh.connect(self.load_bulk_list_to_table)

    def run_asyncio_loop(self): asyncio.set_event_loop(self.loop); self.initialize_client(); self.loop.run_forever()
    def initialize_client(self):
        try: self.downloader = TelegramDownloader(self.session_file, self.api_id, self.api_hash, loop=self.loop); asyncio.run_coroutine_threadsafe(self.check_login(), self.loop)
        except Exception as e: self.signals.error.emit(str(e))
    async def check_login(self):
        try:
            await self.downloader.connect()
            if not await self.downloader.is_authorized(): self.signals.ask_phone.emit()
            else: self.signals.ready.emit()
        except Exception as e: self.signals.error.emit(str(e))
    def on_ready(self): 
        self.update_status("Connected", "#34c759")
        self.btn_select_location.setEnabled(True); self.btn_fetch_new.setEnabled(True); self.btn_fetch_old.setEnabled(True); self.load_bulk_list_to_table(); self.update_fetch_button_text()
    def update_status(self, text, color="#ffffff"):
        self.signals.single_status.emit(text, color)
        self.signals.bulk_status.emit(text, color)
        
    def init_paths(self):
        self.curr_config_dir, self.settings_file, self.session_file, self.db_file = get_config_paths()
        # CRITICAL: Ensure the directory exists before SQlite tries to open the DB
        if not os.path.exists(self.curr_config_dir):
            os.makedirs(self.curr_config_dir)
            
        self.settings = QSettings(self.settings_file, QSettings.Format.IniFormat)
        self.db = Database(self.db_file)
        # Check both cases for maximum compatibility
        self.api_id = self.settings.value("api_id", self.settings.value("api_id", ""))
        self.api_hash = self.settings.value("api_hash", self.settings.value("api_hash", ""))
        # Inherit credentials from root if missing in profile
        if not self.api_id:
            root_cfg = QSettings(os.path.join(CONFIG_DIR, "settings.ini"), QSettings.Format.IniFormat)
            self.api_id = root_cfg.value("api_id", root_cfg.value("api_id", ""))
            self.api_hash = root_cfg.value("api_hash", root_cfg.value("api_hash", ""))
            if self.api_id:
                self.settings.setValue("api_id", self.api_id)
                self.settings.setValue("api_hash", self.api_hash)
                self.settings.sync()
        
    def refresh_profiles_combo(self):
        self.prof_combo.blockSignals(True); self.prof_combo.clear()
        profiles = get_all_profiles()
        for p in profiles:
            p_dir = os.path.join(CONFIG_DIR, p)
            p_cfg = QSettings(os.path.join(p_dir, "settings.ini"), QSettings.Format.IniFormat)
            name = p_cfg.value("account_name", p_cfg.value("account_name", ""))
            label = f"{name} ({p})" if name else p
            self.prof_combo.addItem(label, p)
        
        active = get_active_profile_name()
        if not active and profiles:
            active = profiles[0]; set_active_profile(active)
            
        idx = self.prof_combo.findData(active)
        if idx >= 0: self.prof_combo.setCurrentIndex(idx)
        self.prof_combo.blockSignals(False)

    def is_any_download_active(self):
        # Checks if either single or bulk download is currently in progress
        single_active = self.btn_pause_resume.isEnabled() and not self.is_single_paused
        return single_active or self.is_bulk_running

    def on_profile_combo_changed(self, idx):
        if self.is_any_download_active():
            QMessageBox.warning(self, "Action Blocked", "Cannot switch profiles while a download is active. Please pause or finish first.")
            self.refresh_profiles_combo() # Revert to previous
            return

        name = self.prof_combo.itemData(idx)
        set_active_profile(name)
        QMessageBox.information(self, "Profile Switched", f"Profile '{name or 'Default'}' is now active.\nThe application will now re-initialize.")
        self.reinit_app()

    def reinit_app(self):
        # Stop everything
        self.is_fetching = False; self.is_bulk_running = False
        if self.downloader: asyncio.run_coroutine_threadsafe(self.downloader.disconnect(), self.loop)
        
        # Reload paths and data
        self.init_paths()

        # CRITICAL: Ensure we have credentials before initializing client
        if not self.api_id or not self.api_hash:
            if not self.show_credentials_dialog():
                self.update_status("Error: Missing API Credentials", "#ff453a")
                return

        self.load_bulk_list_to_table(); self.load_profiles_to_table()
        
        # Start Client
        self.initialize_client()

    def load_profiles_to_table(self):
        profiles = get_all_profiles()
        self.profile_table.setRowCount(len(profiles))
        for i, p in enumerate(profiles):
            p_dir = os.path.join(CONFIG_DIR, p)
            p_cfg = QSettings(os.path.join(p_dir, "settings.ini"), QSettings.Format.IniFormat)
            name = p_cfg.value("account_name", p_cfg.value("account_name", ""))
            
            self.profile_table.setItem(i, 0, QTableWidgetItem(name or "-"))
            self.profile_table.setItem(i, 1, QTableWidgetItem(f"+{p}"))
            self.profile_table.setItem(i, 2, QTableWidgetItem(p))
            
            act_row = QHBoxLayout(); act_row.setContentsMargins(0, 0, 0, 0); act_row.setSpacing(2)
            btn_name = QPushButton("Name"); btn_name.clicked.connect(lambda chk, phone=p, old=name: self.on_set_profile_name(phone, old))
            btn_del = QPushButton("Remove"); btn_del.setObjectName("grey_btn")
            btn_del.clicked.connect(lambda chk, phone=p: self.on_remove_profile(phone))
            act_row.addWidget(btn_name); act_row.addWidget(btn_del); 
            act_w = QWidget(); act_w.setLayout(act_row)
            self.profile_table.setCellWidget(i, 3, act_w)

    def on_set_profile_name(self, phone, old_name):
        name, ok = QInputDialog.getText(self, "Profile Name", f"Set name for account +{phone}:", text=old_name)
        if ok:
            p_dir = os.path.join(CONFIG_DIR, phone)
            p_cfg = QSettings(os.path.join(p_dir, "settings.ini"), QSettings.Format.IniFormat)
            p_cfg.setValue("account_name", name.strip())
            p_cfg.sync()
            self.load_profiles_to_table()
            self.refresh_profiles_combo()

    def on_remove_profile(self, name):
        if self.is_any_download_active():
            QMessageBox.warning(self, "Action Blocked", "Cannot remove profiles while a download is active.")
            return

        text, ok = QInputDialog.getText(self, "Confirm Removal", f"To delete profile {name}, type CONFIRM:")
        if ok and text == "CONFIRM":
            shutil_path = os.path.join(CONFIG_DIR, name)
            import shutil; shutil.rmtree(shutil_path)
            
            # If deleted the active one, find a replacement
            if get_active_profile_name() == name:
                remaining = get_all_profiles()
                if remaining: set_active_profile(remaining[0])
                else: set_active_profile(None)
                
                self.refresh_profiles_combo()
                self.reinit_app()
            else:
                self.load_profiles_to_table()
                self.refresh_profiles_combo()
        elif ok:
            QMessageBox.warning(self, "Invalid Confirmation", "Profile was NOT deleted. You must type 'CONFIRM' exactly.")

    def on_add_account_click(self):
        ph, ok = QInputDialog.getText(self, "Add Account", "Enter Phone Number (with +country code):")
        if ok and ph:
            clean_p = ph.replace("+", "")
            p_dir = os.path.join(CONFIG_DIR, clean_p)
            if not os.path.exists(p_dir): 
                os.makedirs(p_dir)
                # Pre-seed credentials from current session for convenience
                if self.api_id and self.api_hash:
                    new_cfg = QSettings(os.path.join(p_dir, "settings.ini"), QSettings.Format.IniFormat)
                    new_cfg.setValue("api_id", self.api_id)
                    new_cfg.setValue("api_hash", self.api_hash)
                    new_cfg.sync()
            
            set_active_profile(clean_p)
            self.refresh_profiles_combo()
            self.reinit_app()

    async def start_new_login_flow(self, phone):
        # Deprecated: Handled by reinit_app + standard login flow
        pass

    def update_fetch_button_text(self):
        lk = self.bulk_channel_input.text().strip(); ent, _ = parse_channel_entity(lk)
        s_raw = self.start_link_box.text().strip()
        
        # Determine current search point
        m_id = None
        if s_raw:
            _, p_mid = parse_channel_entity(s_raw)
            try: m_id = int(p_mid or s_raw)
            except: pass
            
        if ent:
            mx, mn = self.db.get_max_message_id(ent), self.db.get_min_message_id(ent)
            
            # Button 1: Scan New
            ref_new = m_id if m_id is not None else mx
            t_new = f"Scan Newer (from {ref_new})" if ref_new else "Scan Channel"
            self.btn_fetch_new.setText(t_new)
            self.btn_fetch_new.setVisible(True)
                
            # Button 2: Scan Old
            # We show "Scan Older" if we have data or if the user provided a manual ID
            ref_old = m_id if m_id is not None else mn
            if ref_old:
                self.btn_fetch_old.setText(f"Scan Older (from {ref_old})")
                self.btn_fetch_old.setVisible(True)
                self.btn_fetch_old.setEnabled(True)
            else:
                self.btn_fetch_old.setVisible(False)
        else:
            self.btn_fetch_new.setText("Scan Channel"); 
            self.btn_fetch_old.setVisible(False)

    def on_check_changed(self, state, db_id):
        if state == 2:
            if len(self.selected_ids_memory) >= self.max_selection:
                QMessageBox.warning(self, "Limit", "Selection capped at 100."); self.load_bulk_list_to_table(); return
            if db_id not in self.selected_ids_memory: self.selected_ids_memory.append(db_id)
        elif db_id in self.selected_ids_memory: self.selected_ids_memory.remove(db_id)
        self.lbl_sel.setText(f"Selected: {len(self.selected_ids_memory)}/100")

    def load_bulk_list_to_table(self):
        # Save scroll 
        v_bar = self.bulk_table.verticalScrollBar()
        scroll_val = v_bar.value()

        smap = {0: ("message_id", "DESC"), 1: ("message_id", "ASC"), 2: ("file_size", "DESC"), 3: ("status", "ASC"), 4: ("file_type", "ASC")}
        sf, o = smap.get(self.sort_box.currentIndex(), ("message_id", "DESC"))
        st_f, ty_f = None, None
        v_idx = self.view_filter.currentIndex()
        if v_idx == 1: st_f = 'pending' # Pending Only
        elif v_idx >= 2: ty_f = ['video', 'audio', 'photo', 'file'][v_idx-2]
        
        items = self.db.get_items_paged(self.page_size, self.current_page * self.page_size, sf, o, st_f, ty_f)
        tot_all, tot_fil = self.db.get_total_count(), self.db.get_total_count(st_f, ty_f)
        
        # Ensure current_page doesn't exceed total pages if count changed
        tp = (tot_fil+self.page_size-1)//self.page_size if tot_fil else 1
        if self.current_page >= tp: self.current_page = max(0, tp-1)

        self.lbl_tot.setText(f"Loaded: {tot_all} | Active: {tot_fil}"); self.lbl_sel.setText(f"Selected: {len(self.selected_ids_memory)}/100")
        self.chk_master_sel.blockSignals(True); self.chk_master_sel.setChecked(False); self.chk_master_sel.blockSignals(False)
        self.bulk_table.setRowCount(0)
        for r, it in enumerate(items):
            self.bulk_table.insertRow(r); chk = QCheckBox(); chk.setProperty("db_id", it[0])
            if it[0] in self.selected_ids_memory: chk.setChecked(True)
            chk.stateChanged.connect(lambda s, cid=it[0]: self.on_check_changed(s, cid)); self.bulk_table.setCellWidget(r, 0, chk)
            self.bulk_table.setItem(r, 1, QTableWidgetItem(str(it[2]))); self.bulk_table.setItem(r, 2, QTableWidgetItem(it[4])); self.bulk_table.setItem(r, 3, QTableWidgetItem(it[5]))
            sz = it[6]/1048576 if it[6] else 0; self.bulk_table.setItem(r, 4, QTableWidgetItem(f"{sz:.1f} MB"))
            s, status = QTableWidgetItem(), it[7]
            if status == 'completed': s.setText("✅ Done"); s.setBackground(Qt.GlobalColor.darkGreen)
            elif status == 'downloading': s.setText("🔄 DL..."); s.setBackground(Qt.GlobalColor.blue)
            elif status == 'failed': s.setText("❌ Fail"); s.setBackground(Qt.GlobalColor.darkRed)
            else: s.setText("⏳ Wait")
            self.bulk_table.setItem(r, 5, s)
        self.update_pagination_bar(tot_fil)
        if not self.is_bulk_running:
            loc = self.settings.value("last_bulk_dir", None)
            self.btn_bulk_s.setEnabled(tot_fil > 0 and bool(loc))
        
        # Restore scroll
        v_bar.setValue(scroll_val)

    def on_master_sel_changed(self, state):
        page_ids = [self.bulk_table.cellWidget(i, 0).property("db_id") for i in range(self.bulk_table.rowCount())]
        if state == 2:
            for db_id in page_ids:
                if db_id not in self.selected_ids_memory and len(self.selected_ids_memory) < self.max_selection: self.selected_ids_memory.append(db_id)
        else:
            for db_id in page_ids:
                if db_id in self.selected_ids_memory: self.selected_ids_memory.remove(db_id)
        self.load_bulk_list_to_table()

    def deselect_all_global(self): self.selected_ids_memory = []; self.load_bulk_list_to_table()

    def update_pagination_bar(self, total):
        tp = (total+self.page_size-1)//self.page_size if total else 1
        while self.pagi_layout.count():
            x = self.pagi_layout.takeAt(0);
            if x.widget(): x.widget().deleteLater()
        self.pagi_layout.addStretch()
        p_nums = range(tp) if tp <= 10 else list(range(3)) + ["..."] + list(range(max(3, self.current_page-1), min(tp-3, self.current_page+2))) + ["..."] + list(range(tp-3, tp))
        seen = set()
        for p in p_nums:
            if p == "...": self.pagi_layout.addWidget(QLabel("..."))
            elif p not in seen:
                btn = QPushButton(str(p+1)); btn.setObjectName("page_btn"); seen.add(p)
                if p == self.current_page: btn.setEnabled(False)
                btn.clicked.connect(lambda c, val=p: (setattr(self, 'current_page', val), self.load_bulk_list_to_table())); self.pagi_layout.addWidget(btn)
        self.pagi_layout.addStretch()

    # --- Fetch Logic ---
    def on_fetch_bulk_list(self, direction='new'):
        lk = self.bulk_channel_input.text().strip(); self.settings.setValue("last_channel_link", lk); ent, _ = parse_channel_entity(lk);
        if not ent: return
        min_id, max_id, s_lk = 0, 0, self.start_link_box.text().strip()
        manual_id = None
        if s_lk: 
            _, p_mid = parse_channel_entity(s_lk)
            try: manual_id = int(p_mid or s_lk)
            except: pass
            
        if direction == 'new': min_id = manual_id if manual_id is not None else self.db.get_max_message_id(ent)
        else:
            mn_db = self.db.get_min_message_id(ent); max_id = manual_id if manual_id is not None else (mn_db - 1 if mn_db is not None else 0)
        
        flt = []
        if self.chk_v.isChecked(): flt.append('video')
        if self.chk_a.isChecked(): flt.append('audio')
        if self.chk_p.isChecked(): flt.append('photo')
        if self.chk_f.isChecked(): flt.append('file')
        self.is_fetching, self.is_fetch_paused = True, False; self.btn_fetch_new.setEnabled(False); self.btn_fetch_old.setEnabled(False); self.btn_f_pause.setEnabled(True); self.btn_f_stop.setEnabled(True)
        asyncio.run_coroutine_threadsafe(self.fetch_task(ent, min_id, max_id, flt), self.loop)

    async def fetch_task(self, ent, min_id, max_id, flt):
        try:
            c = 0
            # Ensure we pass absolute integers to the client helper
            s_min = int(min_id) if min_id is not None else 0
            s_max = int(max_id) if max_id is not None else 0
            
            async for m, mt in self.downloader.iter_channel_messages(ent, min_id=s_min, max_id=s_max, filter_types=flt):
                if not self.is_fetching: break
                while self.is_fetch_paused: await asyncio.sleep(0.5)
                
                # Safe size detection
                f_sz = 0
                if hasattr(m.media, 'document') and m.media.document:
                    f_sz = m.media.document.size
                elif hasattr(m.media, 'photo') and m.media.photo:
                    try: f_sz = m.media.photo.sizes[-1].size
                    except: f_sz = 0
                
                self.db.add_item(ent, m.id, int(m.date.timestamp()), mt, f"{m.date.strftime('%Y%md_%H%M%S')}_{m.id}", f_sz)
                c += 1
                if c % 25 == 0: 
                    self.signals.bulk_status.emit(f"Importing: {c} items discovered...", "#007aff")
                    self.signals.bulk_table_refresh.emit()
                await asyncio.sleep(0.02)
            self.signals.bulk_list_fetched.emit([c])
        except Exception as e: 
            import traceback
            err_msg = f"Fetch Error: {str(e)}\n\n{traceback.format_exc()}"
            self.signals.error.emit(err_msg)
        finally: 
            self.is_fetching = False
            self.loop.call_soon_threadsafe(lambda: (self.btn_f_pause.setEnabled(False), self.btn_f_stop.setEnabled(False), self.btn_fetch_new.setEnabled(True), self.btn_fetch_old.setEnabled(True), self.update_fetch_button_text()))

    def on_toggle_fetch_pause(self): self.is_fetch_paused = not self.is_fetch_paused; self.btn_f_pause.setText("Resume" if self.is_fetch_paused else "Pause")
    def on_stop_fetch(self): self.is_fetching = False
    def on_bulk_list_fetched(self, args): self.current_page = 0; self.load_bulk_list_to_table(); self.update_status(f"Import {args[0]} records.", "#34c759")

    # --- Bulk Manager ---
    def on_select_bulk_location(self):
        f = QFileDialog.getExistingDirectory(self, "Select Folder", self.settings.value("last_bulk_dir", HOME_DIR))
        if f: 
            self.settings.setValue("last_bulk_dir", f)
            if not self.is_bulk_running: self.btn_bulk_s.setEnabled(True)
    def on_start_bulk_download(self):
        loc = self.settings.value("last_bulk_dir", None)
        if not loc: return
        self.is_bulk_running, self.is_bulk_paused = True, False
        self.btn_bulk_f.setEnabled(False); self.btn_bulk_s.setEnabled(False); self.btn_bulk_p.setEnabled(True)
        asyncio.run_coroutine_threadsafe(self.bulk_manager(loc, list(self.selected_ids_memory)), self.loop)
    async def bulk_manager(self, loc, ids):
        # Copy ids to a local work list so we can track progress
        queue = list(ids) if ids else []
        
        while self.is_bulk_running:
            # If we have a specific selection, process only that. 
            # Otherwise, fetch all globally pending items.
            p = self.db.get_pending_items(queue if queue else None)
            if not p: break
            
            # Filter p to only include things we actually want to process in this pass
            # (i.e. not 'completed')
            to_process = [it for it in p if it[7] != 'completed']
            if not to_process: break
            
            for it in to_process:
                if not self.is_bulk_running: break
                while self.is_bulk_paused: await asyncio.sleep(0.5)
                
                try:
                    m = await self.downloader.get_message(it[1], it[2])
                    if not m or not m.media:
                        self.db.update_status(it[1], it[2], 'failed')
                        if it[0] in queue: queue.remove(it[0])
                        self.signals.bulk_table_refresh.emit()
                        continue

                    fp = os.path.join(loc, f"{it[5]}{self.downloader.get_extension(m.media)}")
                    self.db.update_status(it[1], it[2], 'downloading')
                    self.signals.bulk_table_refresh.emit()
                    
                    self.start_time, self.initial_bytes = None, 0
                    await self.downloader.download_media(m, fp, self.bulk_progress_cb, lambda: self.is_bulk_paused, lambda: not self.is_bulk_running)
                    
                    if self.is_bulk_running and not self.is_bulk_paused:
                        self.db.update_status(it[1], it[2], 'completed', fp)
                        if it[0] in self.selected_ids_memory:
                            self.selected_ids_memory.remove(it[0])
                        if it[0] in queue:
                            queue.remove(it[0])
                        self.signals.bulk_table_refresh.emit()
                        
                        import random
                        try:
                            mi, mx = int(self.delay_min.text()), int(self.delay_max.text())
                            wait_s = random.randint(min(mi, mx), max(mi, mx))
                        except: wait_s = 5
                        
                        for rem in range(wait_s, 0, -1):
                            if not self.is_bulk_running or self.is_bulk_paused: break
                            self.signals.bulk_status.emit(f"Waiting: next download in {rem}s...", "#ffa500")
                            await asyncio.sleep(1)
                    else:
                        # If stopped/paused during download, mark as pending to allow resume
                        self.db.update_status(it[1], it[2], 'pending')
                        self.signals.bulk_table_refresh.emit()
                        break
                except Exception as e:
                    import traceback
                    err_details = f"{str(e)}\n{traceback.format_exc()}"
                    print(f"Bulk item failed: {it[1]}:{it[2]} - {err_details}")
                    self.db.update_status(it[1], it[2], 'failed')
                    if it[0] in queue: queue.remove(it[0])
                    self.signals.bulk_table_refresh.emit()
                    # If it's a "File Not Found" or similar OS error, maybe permissions?
                    if "Permission denied" in str(e):
                        self.signals.bulk_status.emit(f"Permission Error: {it[5]}", "#ff453a")
                        break
            
            # If we processed our specific queue, we're done
            if queue: break
            if not self.is_bulk_paused: break
        self.is_bulk_running = False
        self.loop.call_soon_threadsafe(lambda: (
            self.btn_bulk_f.setEnabled(True), 
            self.btn_bulk_s.setEnabled(True), 
            self.btn_bulk_p.setEnabled(False), 
            self.btn_bulk_p.setText("Stop/Pause"),
            self.btn_open_folder_bulk.setVisible(True)
        ))
        self.signals.bulk_status.emit("Bulk task completed.", "#34c759")

    def on_stop_bulk_download(self): self.is_bulk_paused = not self.is_bulk_paused; self.btn_bulk_p.setText("Resume" if self.is_bulk_paused else "Stop/Pause")
    def on_clear_bulk_list(self):
        if QMessageBox.question(self, "Clear", "Wipe all DB?") == QMessageBox.StandardButton.Yes: 
            self.db.clear_all(); self.selected_ids_memory = []; self.load_bulk_list_to_table(); self.update_fetch_button_text(); self.signals.bulk_status.emit("Database wiped.", "#ff453a")
    def on_delete_selected(self):
        if self.selected_ids_memory: 
            self.db.delete_items(self.selected_ids_memory); self.selected_ids_memory = []; self.load_bulk_list_to_table(); self.update_fetch_button_text(); self.signals.bulk_status.emit("Selected items deleted.", "#ff453a")
    def on_export_list(self):
        # Determine items to export: selection vs all
        if self.selected_ids_memory:
            items = self.db.get_items_by_id(self.selected_ids_memory)
            msg = f"Export selected ({len(items)}) items to JSON?"
        else:
            items = self.db.get_all_items()
            msg = f"No selection. Export all ({len(items)}) items to JSON?"

        if QMessageBox.question(self, "Export", msg) == QMessageBox.StandardButton.Yes:
            p, _ = QFileDialog.getSaveFileName(self, "Export JSON", "", "JSON (*.json)")
            if p:
                with open(p, 'w') as f:
                    f.write(json.dumps(items))
                self.signals.bulk_status.emit(f"Exported {len(items)} items to JSON.", "#34c759")

    def on_export_links_txt(self):
        # Determine items
        if self.selected_ids_memory:
            items = self.db.get_items_by_id(self.selected_ids_memory)
            msg = f"Export links for {len(items)} selected items to TXT?"
        else:
            items = self.db.get_all_items()
            msg = f"Export links for ALL ({len(items)}) items to TXT?"

        if QMessageBox.question(self, "Export TXT", msg) == QMessageBox.StandardButton.Yes:
            p, _ = QFileDialog.getSaveFileName(self, "Export Links (TXT)", "", "Text (*.txt)")
            if p:
                links = []
                for it in items:
                    c_id, m_id = str(it[1]), str(it[2])
                    # If it's a numeric private ID (starts with -100)
                    if c_id.startswith("-100"):
                        clean_id = c_id.replace("-100", "")
                        links.append(f"https://t.me/c/{clean_id}/{m_id}")
                    elif c_id.startswith("-") or c_id.isdigit():
                        # Other group types or public numeric IDs (rare in this format but for safety)
                        links.append(f"https://t.me/c/{c_id.lstrip('-')}/{m_id}")
                    else:
                        # Username based public link
                        links.append(f"https://t.me/{c_id}/{m_id}")
                
                with open(p, 'w') as f:
                    f.write("\n".join(links))
                self.signals.bulk_status.emit(f"Exported {len(links)} links to TXT.", "#34c759")
    def on_import_list(self):
        p, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
        if p:
            with open(p, 'r') as f: itm = json.load(f);
            for it in itm: self.db.add_item(it[1], it[2], it[3], it[4], it[5], it[6])
            self.signals.bulk_status.emit("Database imported from JSON.", "#34c759"); self.on_ready()

    # --- Single actions ---
    def on_select_location_click(self):
        u = self.link_entry.text().strip()
        c, m = parse_telegram_link(u)
        if c and m: asyncio.run_coroutine_threadsafe(self.prepare_single(c, m), self.loop)
    async def prepare_single(self, c, m):
        try:
            msg = await self.downloader.get_message(c, m)
            if msg and msg.media: 
                self.current_message = msg
                self.signals.ask_location_success.emit(msg, self.downloader.get_extension(msg.media))
        except: pass
    def on_ask_location_success(self, msg, ex):
        # Using DontConfirmOverwrite because our logic handles Resuming from existing files
        # We also use DontUseNativeDialog on Mac to ensure the option is strictly respected
        p, _ = QFileDialog.getSaveFileName(self, "Save / Resume File", 
                                           os.path.join(self.settings.value("last_download_dir", HOME_DIR), f"DL_{msg.id}{ex}"),
                                           options=QFileDialog.Option.DontConfirmOverwrite)
        if p: 
            self.current_message, self.current_file_path = msg, p
            self.btn_start_download.setEnabled(True)
            self.settings.setValue("last_download_dir", os.path.dirname(p))
            self.settings.setValue("last_single_fp", p)
            self.settings.setValue("last_single_url", self.link_entry.text().strip())
            self.single_status_label.setText(f"Destination: {os.path.basename(p)}")

    def on_start_download_click(self):
        # If we have a saved link but no message loaded, we must fetch it first
        if not self.current_message:
            u = self.link_entry.text().strip()
            c, m = parse_telegram_link(u)
            if c and m:
                # We do a 'background' prepare then chain the download
                asyncio.run_coroutine_threadsafe(self.auto_resume_single(c, m), self.loop)
                return

        self.start_time, self.initial_bytes = None, 0
        self.is_single_paused = False
        self.btn_select_location.setEnabled(False); self.btn_start_download.setEnabled(False); self.btn_pause_resume.setEnabled(True)
        asyncio.run_coroutine_threadsafe(self.run_download(), self.loop)

    async def auto_resume_single(self, c, m):
        try:
            self.signals.single_status.emit("Resolving link for resume...", "#007aff")
            msg = await self.downloader.get_message(c, m)
            if msg and msg.media:
                self.current_message = msg
                # Now we can safely trigger the actual download call on the main thread
                self.loop.call_soon_threadsafe(self.on_start_download_click)
            else:
                self.signals.error.emit("Message has no media or vanished.")
        except Exception as e:
            self.signals.error.emit(f"Resume resolution failed: {e}")
    async def run_download(self):
        try: await self.downloader.download_media(self.current_message, self.current_file_path, self.single_progress_cb, lambda: self.is_single_paused, lambda: False); self.signals.success.emit(self.current_file_path)
        except Exception as e: self.signals.error.emit(str(e))

    # --- Worker Thread Helpers ---
    async def single_progress_cb(self, c, t):
        if self.start_time is None: self.start_time, self.initial_bytes = time.time(), c
        cur_mb, tot_mb = c/1048576, t/1048576; e = time.time()-self.start_time; p = (c/t)*100 if t else 0; s = ((c-self.initial_bytes)/e)/1048576 if e>0 else 0
        self.signals.single_progress.emit(p, f"{p:.1f}% | {cur_mb:.1f} / {tot_mb:.1f}MB | {s:.2f}MB/s")
    async def bulk_progress_cb(self, c, t):
        if self.start_time is None: self.start_time, self.initial_bytes = time.time(), c
        cur_mb, tot_mb = c/1048576, t/1048576; e = time.time()-self.start_time; p = (c/t)*100 if t else 0; s = ((c-self.initial_bytes)/e)/1048576 if e>0 else 0
        self.signals.bulk_progress.emit(p, f"{p:.1f}% | {cur_mb:.1f} / {tot_mb:.1f}MB | {s:.2f}MB/s")
    def update_status(self, t, c="#e0e0e0"): self.signals.single_status.emit(t, c); self.signals.bulk_status.emit(t, c)
    def on_success(self, p): 
        m = f"Done: {os.path.basename(p)}\n📁 {os.path.dirname(p)}"
        self.signals.single_status.emit(m, "#34c759"); self.signals.bulk_status.emit(m, "#34c759")
        self.btn_select_location.setEnabled(True); self.btn_pause_resume.setEnabled(False); self.btn_pause_resume.setText("Pause/Resume")
        self.btn_open_folder_single.setVisible(True); self.btn_open_folder_bulk.setVisible(True)
    def on_error(self, m): 
        QMessageBox.critical(self, "Error", m); self.on_ready()
        self.btn_select_location.setEnabled(True); self.btn_pause_resume.setEnabled(False); self.btn_pause_resume.setText("Pause/Resume")
        self.btn_open_folder_single.setVisible(False); self.btn_open_folder_bulk.setVisible(False)
    def on_pause_resume_click(self): 
        self.is_single_paused = not self.is_single_paused
        self.btn_pause_resume.setText("Resume" if self.is_single_paused else "Pause/Resume")
        self.btn_open_folder_single.setVisible(False); self.btn_open_folder_bulk.setVisible(False)

    def open_folder(self, path):
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def prompt_phone(self):
        ph, ok = QInputDialog.getText(self, "Login", "Phone:")
        if ok: asyncio.run_coroutine_threadsafe(self.downloader.send_code(ph), self.loop); self.signals.ask_code.emit(ph)
    def prompt_code(self, ph):
        cd, ok = QInputDialog.getText(self, "OTP", "Code:")
        if ok: asyncio.run_coroutine_threadsafe(self.downloader.sign_in(ph, cd), self.loop); self.signals.ready.emit()
    def show_credentials_dialog(self):
        d = CredentialsDialog(self)
        if d.exec() == QDialog.DialogCode.Accepted:
            aid, ah = d.get_credentials()
            # Save to current profile
            self.settings.setValue("api_id", aid); self.settings.setValue("api_hash", ah)
            self.settings.sync()
            
            # Update local memory
            self.api_id, self.api_hash = aid, ah
            return True
        return False

if __name__ == '__main__':
    if sys.platform == 'darwin': os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    window = TelegramDownloaderApp()
    window.resize(1100, 800)
    window.show()
    sys.exit(app.exec())