import json

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def diff(a, b, path=""):
    """Recursively diff two JSON-compatible values, yielding (path, kind, detail) tuples."""
    diffs = []

    if isinstance(a, dict) and isinstance(b, dict):
        keys = set(a.keys()) | set(b.keys())
        for key in sorted(keys):
            new_path = f"{path}.{key}" if path else key
            if key not in a:
                diffs.append((new_path, "added", b[key]))
            elif key not in b:
                diffs.append((new_path, "removed", a[key]))
            else:
                diffs.extend(diff(a[key], b[key], new_path))

    elif isinstance(a, list) and isinstance(b, list):
        max_len = max(len(a), len(b))
        for i in range(max_len):
            new_path = f"{path}[{i}]"
            if i >= len(a):
                diffs.append((new_path, "added", b[i]))
            elif i >= len(b):
                diffs.append((new_path, "removed", a[i]))
            else:
                diffs.extend(diff(a[i], b[i], new_path))

    else:
        if a != b:
            diffs.append((path, "changed", {"old": a, "new": b}))

    return diffs


def print_diff(results):
    if not results:
        print("No differences found.")
        return
    print(f"Found {len(results)} difference(s):\n")
    for path, kind, detail in results:
        if kind == "changed":
            print(f"[CHANGED] {path}\n    old: {detail['old']}\n    new: {detail['new']}\n")
        elif kind == "added":
            print(f"[ADDED] {path}\n    value: {detail}\n")
        elif kind == "removed":
            print(f"[REMOVED] {path}\n    value: {detail}\n")

