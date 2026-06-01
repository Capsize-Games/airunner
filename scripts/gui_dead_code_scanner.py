import os
from vulture import Vulture

def scan_for_dead_code(target_directory: str, whitelist_path: str = None):
    if not os.path.exists(target_directory):
        print(f"Error: The directory '{target_directory}' does not exist.")
        return

    vulture_checker = Vulture(verbose=False)
    excluded_suffixes = ('_ui.py', '_rc.py')
    scanned_files = []

    # Step 1: Collect valid source files
    for root, _, files in os.walk(target_directory):
        for file in files:
            if file.endswith('.py'):
                if file.endswith(excluded_suffixes):
                    continue
                
                full_path = os.path.join(root, file)
                scanned_files.append(full_path)

    if not scanned_files:
        print("No valid Python files found to scan.")
        return

    # Step 2: Inject the whitelist file into the scanned paths if it exists
    if whitelist_path and os.path.exists(whitelist_path):
        scanned_files.append(whitelist_path)
    elif whitelist_path:
        print(f"Warning: Whitelist file '{whitelist_path}' specified but not found.")

    # Step 3: Scavenge all target files + whitelist together
    vulture_checker.scavenge(scanned_files)
    
    unused_code_items = vulture_checker.get_unused_code()
    
    if not unused_code_items:
        print("No obsolete code detected.")
        return

    print("=== OBSOLETE CODE REPORT ===")
    print(f"Scanned {len(scanned_files)} paths (including whitelist if present)\n")

    findings_by_file = {}
    for item in unused_code_items:
        # Ignore findings that originate from within the whitelist file itself
        if whitelist_path and os.path.abspath(item.filename) == os.path.abspath(whitelist_path):
            continue
        findings_by_file.setdefault(item.filename, []).append(item)

    for filename in sorted(findings_by_file.keys()):
        print(f"File: {filename}")
        items = findings_by_file[filename]
        
        whole_file_unused = any(item.typ == 'unreachable' and item.first_lineno == 1 for item in items)
        if whole_file_unused:
            print("  [!] WARNING: This entire file appears to be completely unreferenced.")
            print("-" * 60)
            continue

        for item in sorted(items, key=lambda x: x.first_lineno):
            print(f"  - Line {item.first_lineno:3d}: Unused {item.typ} '{item.name}' ({item.confidence}% confidence)")
        print("-" * 60)

if __name__ == "__main__":
    # Target directory to check
    target_path = os.path.join("src", "airunner")
    
    # Path to the whitelist file located in your project root
    whitelist_file = "vulture_whitelist.py"
    
    scan_for_dead_code(target_path, whitelist_path=whitelist_file)