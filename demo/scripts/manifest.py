#!/usr/bin/env python3

import hashlib
import sys
from pathlib import Path
import shutil


def calculate_file_hash(filepath: Path, algorithm: str = 'sha256') -> str:
    """Calculate hash of a file using specified algorithm."""
    hash_obj = hashlib.new(algorithm)
    
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def run_write(input_file: str) -> None:
    """Process file containing file paths, calculate hashes, and append to lines."""
    lines = []
    
    with open(input_file, 'r') as f:
        for line in f:
            parts = line.strip().split(' ')
            if len(parts) < 1:
                lines.append(line)
                continue

            filepath_str = parts[0]
            if not filepath_str:
                lines.append(line)
                continue
                
            filepath = Path(filepath_str)
            try:
                file_hash = calculate_file_hash(filepath)
            except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
                print(f"Unable to process file: {filepath_str}")
                raise e

            lines.append(f"{filepath_str} {file_hash}\n")
    
    with open(input_file, 'w') as f:
        f.writelines(lines)

    print(f"✅ Wrote {input_file}\n")
    sys.exit(0)


def run_check(input_file: str) -> None:
    errors = 0
    valid_files = 0
    with open(input_file, 'r') as f:
        for line in f:
            parts = line.strip().split(' ')

            if len(parts) == 1:
                print(f"❌ Invalid line: {line}. Expected format: [file_path] [hash]")
                errors += 1
                continue

            if len(parts) < 2:
                continue

            filepath_str = parts[0].strip()
            if not filepath_str:
                continue

            expected_hash = parts[1].strip()
            if not expected_hash:
                continue

            filepath = Path(filepath_str)
            try:
                file_hash = calculate_file_hash(filepath)
            except Exception:
                print(f"❌ {filepath} [Failed to calculate hash]")
                errors += 1
                continue

            if file_hash != expected_hash:
                print(f"❌ {filepath} [Hash is incorrect]")
                errors += 1
                continue

            print(f"✅ {filepath}")
            valid_files += 1
    if errors > 0:
        print(f"\n{errors} errors found.")
        sys.exit(1)
    else:
        print(f"\nValidated {valid_files} files from {input_file}")
        sys.exit(0)


def run_materialize(input_file: Path, output_dir: Path) -> None:
    errors = 0
    valid_files = 0

    if output_dir.exists():
        shutil.rmtree(output_dir)
        print(f"⚠️ Deleted {output_dir.absolute()}")

    output_dir.mkdir()
    print(f"✅ Created {output_dir.absolute()}")

    with open(input_file, 'r') as f:
        for line in f:
            parts = line.strip().split(' ')

            filepath_str = parts[0].strip()
            if not filepath_str:
                continue

            filepath = Path(filepath_str)
            if not filepath.exists():
                errors += 1
                print(f"❌ {filepath} does not exist.")
                continue

            try:
                shutil.copy2(filepath, output_dir)
                print(f"✅ Copied {filepath} to {output_dir.absolute()}")
                valid_files += 1
            except Exception as e:
                print(f"❌ An error occurred: {e}")
    if errors > 0:
        print(f"\n{errors} errors.")
        sys.exit(1)
    else:
        print(f"\nMaterialized {valid_files} files from {input_file} to {output_dir.absolute()}")
        sys.exit(0)


def usage():
    print("Usage: python manifest.py <manifest_file> [check|materialize|write]")


def main():
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)
   
    action = sys.argv[2]
    input_file = Path(sys.argv[1])

    if action not in ['check', 'materialize', 'write']:
        usage()
        sys.exit(1)
    
    if not input_file.exists():
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
  
    if action == 'write':
        run_write(input_file)
    elif action == 'check':
        run_check(input_file)
    elif action == 'materialize':
        output_dir = Path(input_file.name.split('.')[0])
        run_materialize(input_file, output_dir)
    else:
        usage()
        sys.exit(1)
    

if __name__ == "__main__":
    main()
