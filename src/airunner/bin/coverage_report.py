import subprocess

def main():
    commands = [
        ["coverage", "erase"],
        ["coverage", "run", "-m", "pytest"],
        ["coverage", "report"],
    ]

    with open("coverage_report.txt", "w") as report_file:
        for cmd in commands:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=report_file if "report" in cmd else None)
            if result.returncode != 0:
                print(f"Command failed: {' '.join(cmd)}")
                exit(result.returncode)

