#!/usr/bin/env python3
"""
Entrypoint for airunner-create-theme
"""


def main():
    # Inline the logic from the previous script
    import sys
    from pathlib import Path

    def create_theme(theme_name):
        base_dir = Path(__file__).parent.parent / "gui" / "styles"
        theme_dir = base_dir / f"{theme_name}_theme"
        if theme_dir.exists():
            print(f"Theme directory {theme_dir} already exists.")
            sys.exit(1)
        theme_dir.mkdir(parents=True)
        # Create variables.qss
        (theme_dir / "variables.qss").write_text(
            """/* VARIABLES */\n@primary-color: #000000;\n@darkprimary-color: #000000;\n@darkerprimary-color: #000000;\n@secondary-color: #000000;\n@darksecondary-color: #000000;\n@darkersecondary-color: #000000;\n@success-color: #00A800;\n@danger-color: #FF5555;\n@warning-color: #FFAA00;\n@info-color: #00A8D8;\n@light-color: #C8C8C8;\n@dim-color: #666666;\n@dark-color: #000;\n@line-color-light: #333;\n@line-color-dark: #222;\n/* END_VARIABLES */\n"""
        )
        # Create styles.qss
        (theme_dir / "styles.qss").write_text(
            """/* Add your theme-specific QSS rules here */\n"""
        )
        # Create manifest.txt
        (theme_dir / "manifest.txt").write_text(
            """variables.qss\n../master.qss\n"""
        )
        print(f"Created new theme in {theme_dir}")

    if len(sys.argv) != 2:
        print("Usage: airunner-create-theme <theme_name>")
        sys.exit(1)
    create_theme(sys.argv[1])


if __name__ == "__main__":
    main()
