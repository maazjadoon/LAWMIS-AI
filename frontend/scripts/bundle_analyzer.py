"""
frontend/scripts/bundle_analyzer.py
───────────────────────────────────
CLI script to build and analyze build output asset sizes.

Usage:
  python scripts/bundle_analyzer.py
"""

import subprocess
import os
from pathlib import Path


def analyze_bundle():
    print("Building application for production bundle analysis...")
    
    # Run npm run build
    try:
        subprocess.run("npm run build", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return

    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("Error: 'dist' folder not found after build.")
        return

    assets_dir = dist_dir / "assets"
    if not assets_dir.exists():
        print("No assets folder found inside dist/")
        return

    print("\n📦 Bundle Analysis Results:")
    print("=" * 60)
    print(f"{'Filename':40} | {'Size (KB)':15}")
    print("=" * 60)

    total_size_bytes = 0
    for root, _, files in os.walk(assets_dir):
        for file in files:
            path = Path(root) / file
            size_kb = path.stat().st_size / 1024
            total_size_bytes += path.stat().st_size
            print(f"{file:40} | {size_kb:12.2f} KB")

    print("=" * 60)
    print(f"{'Total Bundle Size':40} | {total_size_bytes / 1024:12.2f} KB\n")


if __name__ == "__main__":
    analyze_bundle()
