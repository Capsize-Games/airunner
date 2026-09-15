import subprocess


def main():
    for lang in [
        "english",
        "japanese",
    ]:
        subprocess.run(
            [
                "pyside6-lrelease",
                f"./src/airunner/translations/{lang}.ts",
                "-qm",
                f"./src/airunner/translations/{lang}.qm",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
