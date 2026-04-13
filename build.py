import os
import sys
import shutil
import platform
import subprocess

def check_dependencies():
    print("Ensuring dependencies are installed...")
    deps = ["pyinstaller", "psutil", "PyQt6", "telethon", "cryptg"]
    
    if platform.system().lower() == "darwin":
        deps.append("dmgbuild")
        
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + deps)
    except subprocess.CalledProcessError:
        print("Failed to install dependencies. Please check your internet connection.")
        sys.exit(1)

def build_app():
    os_name = platform.system().lower()
    app_name = "TG Downloader"
    main_script = "tg_downloader_gui.py"
    
    print(f"\n--- Starting Build Process for {os_name.upper()} ---")
    
    # PyInstaller arguments
    pyinstaller_args = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={app_name}",
        "--clean",
    ]
    
    icon_dir = "images"
    
    if os_name == "windows":
        icon_path = os.path.join(icon_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            pyinstaller_args.append(f"--icon={icon_path}")
        
    elif os_name == "darwin": # macOS
        os.environ["MACOSX_DEPLOYMENT_TARGET"] = "11.0"
        icon_path = os.path.join(icon_dir, "app_icon.icns")
        if os.path.exists(icon_path):
            pyinstaller_args.append(f"--icon={icon_path}")
        
    else: # Linux
        icon_path = os.path.join(icon_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            pyinstaller_args.append(f"--icon={icon_path}")
        
    # Add main script
    pyinstaller_args.append(main_script)
    
    # Run PyInstaller
    print("\nRunning PyInstaller...")
    subprocess.check_call(pyinstaller_args)

    # Cleanup the .spec file
    spec_file = f"{app_name}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)

    print("\n✅ Build Completed Successfully!")

    # MacOS DMG creation
    if os_name == "darwin":
        print("\n📦 Packaging into DMG...")
        
        app_path = os.path.abspath(f'dist/{app_name}.app')
        dmg_path = os.path.abspath(f'dist/{app_name}.dmg')
        bg_path_abs = os.path.abspath(os.path.join('images', 'dmg_background.png'))
        icon_path_abs = os.path.abspath(os.path.join('images', 'app_icon.icns'))

        if not shutil.which("create-dmg"):
            print("❌ 'create-dmg' not found. Please run 'brew install create-dmg' to create DMGs.")
            return

        staging_dir = os.path.abspath('dist/dmg_staging')
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        os.makedirs(staging_dir)

        dest_app_path = os.path.join(staging_dir, f'{app_name}.app')
        shutil.copytree(app_path, dest_app_path, symlinks=True)

        print("🔐 Code-signing (Ad-hoc)...")
        try:
            subprocess.check_call(["codesign", "--force", "--deep", "-s", "-", dest_app_path])
        except: pass

        if os.path.exists(dmg_path):
            os.remove(dmg_path)

        cmd = [
            "create-dmg",
            "--volname", "TG Downloader",
            "--window-pos", "200", "120",
            "--window-size", "640", "640",
            "--icon-size", "120",
            "--text-size", "14",
            "--icon", f"{app_name}.app", "175", "324",
            "--hide-extension", f"{app_name}.app",
            "--app-drop-link", "465", "324"
        ]

        if os.path.exists(bg_path_abs):
            cmd.extend(["--background", bg_path_abs])

        if os.path.exists(icon_path_abs):
            cmd.extend(["--volicon", icon_path_abs])

        cmd.extend([dmg_path, staging_dir])

        try:
            print("Creating DMG...")
            subprocess.check_call(cmd)
            print(f"✅ DMG created: {dmg_path}")
        except Exception as e:
            print(f"❌ DMG creation failed: {e}")
        finally:
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)

if __name__ == "__main__":
    check_dependencies()
    build_app()
