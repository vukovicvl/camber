"""Build Camber into a Windows .exe installer.

Run from the camber folder in PowerShell:
    python scripts/build_exe.py

This script:
  1. Installs PyInstaller if missing
  2. Runs PyInstaller with camber.spec
  3. Prints next steps for Inno Setup (optional full installer)
"""
import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def run(cmd: str):
    print(f"\n{'='*60}")
    print(f"  {cmd}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(1)


def main():
    # Step 1: Ensure PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} found.")
    except ImportError:
        print("Installing PyInstaller...")
        run(f"{sys.executable} -m pip install pyinstaller")

    # Step 2: Clean previous build
    for d in ["build", "dist"]:
        if os.path.exists(d):
            print(f"Cleaning {d}/...")
            shutil.rmtree(d)

    # Step 3: Run PyInstaller
    run(f"{sys.executable} -m PyInstaller camber.spec --noconfirm")

    # Step 4: Verify
    exe_path = os.path.join("dist", "Camber", "Camber.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n{'='*60}")
        print(f"  BUILD SUCCESSFUL")
        print(f"  {exe_path} ({size_mb:.1f} MB)")
        print(f"{'='*60}")
        print(f"\nYou can now:")
        print(f"  1. Run directly:  .\\dist\\Camber\\Camber.exe")
        print(f"  2. Create installer: open installer.iss in Inno Setup")
        print(f"     Download Inno Setup: https://jrsoftware.org/isinfo.php")
    else:
        print("\nERROR: Camber.exe not found after build.")
        sys.exit(1)


if __name__ == "__main__":
    main()
