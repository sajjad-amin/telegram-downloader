import subprocess
import sys
import os

def build():
    print("🚀 Starting Cross-Platform Build...")
    
    # 1. Install/Verify Dependencies
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "telethon", "PyQt6"])
    
    # 2. PyInstaller Command Construction
    # --onefile: Single executable
    # --windowed: No terminal window on launch (GUI mode)
    # --name: Executable name
    cmd = [
        "pyinstaller",
        "--noconfirm",
        # We REMOVE --onefile here for better Stability/Size on macOS
        "--windowed",
        "--name", "TG Downloader",
        "--clean",
        "--add-data", f"core{os.pathsep}core",
        "--add-data", f"gui{os.pathsep}gui",
        "tg_downloader_gui.py"
    ]
    
    # Platform-specific adjustments
    if sys.platform == "darwin":
        os.environ["MACOSX_DEPLOYMENT_TARGET"] = "11.0"
        if os.path.exists("icon.icns"):
            cmd += ["--icon", "icon.icns"]
    elif sys.platform.startswith("win"):
        if os.path.exists("icon.ico"):
            cmd += ["--icon", "icon.ico"]
            
    try:
        subprocess.check_call(cmd)
        
        # Cleanup the .spec file after successful build
        spec_file = "TG Downloader.spec"
        if os.path.exists(spec_file):
            os.remove(spec_file)
            print(f"🧹 Cleaned up {spec_file}")
            
        print("\n✅ Build Successful! Check the 'dist' folder for your executable.")
    except Exception as e:
        print(f"\n❌ Build Failed: {e}")

if __name__ == "__main__":
    build()
