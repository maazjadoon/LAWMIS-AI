"""
frontend/scripts/component_generator.py
───────────────────────────────────────
CLI script to automate component creation in Vite React (TS).
Generates:
  1. Component boilerplate file (.tsx)
  2. Component styles file (.css)
  3. Package index (.ts) for clean exports

Usage:
  python scripts/component_generator.py <ComponentName>
"""

import sys
from pathlib import Path


def generate_component(name: str):
    # Ensure name is Capitalized
    name = name[0].upper() + name[1:]
    target_dir = Path("src/components") / name

    if target_dir.exists():
        print(f"Error: Component '{name}' already exists at {target_dir}")
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write Component.tsx
    tsx_content = f"""import React from 'react';
import './{name}.css';

interface {name}Props {{
  className?: string;
}}

export const {name}: React.FC<{name}Props> = ({{ className = '' }}) => {{
  return (
    <div className={`{name.lower()}-container ${{className}}`}>
      <h3>{name} Component</h3>
    </div>
  );
}};
"""
    with open(target_dir / f"{name}.tsx", "w", encoding="utf-8") as f:
        f.write(tsx_content)

    # 2. Write Component.css
    css_content = f""".{name.lower()}-container {{
  padding: 1rem;
  border-radius: 8px;
  background-color: var(--card-bg, #ffffff);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}}
"""
    with open(target_dir / f"{name}.css", "w", encoding="utf-8") as f:
        f.write(css_content)

    # 3. Write index.ts
    index_content = f"""export * from './{name}';
"""
    with open(target_dir / "index.ts", "w", encoding="utf-8") as f:
        f.write(index_content)

    print(f"Successfully generated component '{name}' inside {target_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/component_generator.py <ComponentName>")
        sys.exit(1)
    generate_component(sys.argv[1])
