import os

EXCLUDE_DIRS = {"zecc", "__pycache__", ".git", ".pytest_cache", "node_modules"}

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    level = root.replace(".", "", 1).count(os.sep)
    indent = "    " * level
    print(f"{indent}{os.path.basename(root) or '.'}/")
    for f in sorted(files):
        if f.endswith((".py", ".json", ".md")):
            print(f"{indent}    {f}")