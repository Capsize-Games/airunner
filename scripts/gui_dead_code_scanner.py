import os
from vulture import Vulture

def scan_for_dead_code(target_directory: str):
    if not os.path.exists(target_directory):
        print(f"Error: The directory '{target_directory}' does not exist.")
        return

    # Initialize Vulture. verbose=False prevents internal debugging prints.
    vulture_checker = Vulture(verbose=False)
    excluded_suffixes = ('_ui.py', '_rc.py')
    
    # Track files to verify if any are completely unused
    scanned_files = []

    # Step 1: Collect all valid Python files
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

    # Step 2: Run the static analysis across all collected files
    vulture_checker.scavenge(scanned_files)
    
    # Step 3: Parse and categorize the results
    unused_code_items = vulture_checker.get_unused_code()
    
    if not unused_code_items:
        print("No obsolete code detected.")
        return

    print("=== OBSOLETE CODE REPORT ===")
    print(f"Scanned {len(scanned_files)} files in '{target_directory}'\n")

    # Group findings by file for cleaner output formatting
    findings_by_file = {}
    for item in unused_code_items:
        # Vulture types include: 'function', 'class', 'variable', 'import', etc.
        findings_by_file.setdefault(item.filename, []).append(item)

    for filename in sorted(findings_by_file.keys()):
        print(f"File: {filename}")
        items = findings_by_file[filename]
        
        # Check if the entire file is obsolete (e.g., entry point or module never imported anywhere)
        # Vulture marks an entire file as unused by checking if its top-level module name is unused.
        whole_file_unused = any(item.typ == 'unreachable' and item.first_lineno == 1 for item in items)
        
        if whole_file_unused:
            print("  [!] WARNING: This entire file appears to be completely unreferenced in the codebase.")
            print("-" * 60)
            continue

        for item in sorted(items, key=lambda x: x.first_lineno):
            # Format: Line X: Unused function 'my_old_func' (60% confidence)
            print(f"  - Line {item.first_lineno:3d}: Unused {item.typ} '{item.name}' ({item.confidence}% confidence)")
        print("-" * 60)

if __name__ == "__main__":
    target_path = os.path.join("src", "airunner")
    scan_for_dead_code(target_path)