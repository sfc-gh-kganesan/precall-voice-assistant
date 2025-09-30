import subprocess
from pathlib import Path


def get_repo_abs_path(relative_path):
    """
    Convert a path relative to the git repo root to an absolute path.

    Args:
        relative_path: Path relative to the git repository root

    Returns:
        Path object representing the absolute path

    Raises:
        subprocess.CalledProcessError: If not in a git repository
    """
    # Get the git repository root
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)

    repo_root = result.stdout.strip()

    # Combine repo root with relative path
    absolute_path = Path(repo_root) / relative_path

    return absolute_path


# Example usage:
if __name__ == "__main__":
    # Example: get absolute path for a file in the repo
    abs_path = get_repo_abs_path(".gitignore")
    print(f"Absolute path: {abs_path}")

    # Check if the path exists
    if abs_path.exists():
        print("File exists!")
    else:
        print("File does not exist")
