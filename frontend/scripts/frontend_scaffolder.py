"""
frontend/scripts/frontend_scaffolder.py
───────────────────────────────────────
CLI script to scaffold core SPA directories and templates.

Usage:
  python scripts/frontend_scaffolder.py --init
"""

import sys
from pathlib import Path


def scaffold_project():
    dirs = [
        "src/components",
        "src/hooks",
        "src/store",
        "src/styles",
        "src/types",
    ]

    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"Verified directory structure: {d}/")

    print("\nProject directories successfully scaffolded. Happy coding!")


if __name__ == "__main__":
    scaffold_project()
