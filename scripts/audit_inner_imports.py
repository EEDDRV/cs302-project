"""Print reproducible inner-layer imports and flag outward dependencies."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = ("entities", "use_cases")
ALLOWED_TOP = {"entities", "use_cases"}
# The final project currently uses these standard-library modules in its core.
STDLIB = {"dataclasses", "typing", "time", "abc", "collections", "enum", "uuid", "datetime"}


def main() -> int:
    """Inspect all Python files in the inner layers.

    Returns:
        Zero when imports stay inward or standard-library-only, else one.
    """
    file_count = 0
    import_count = 0
    violations = []
    for folder in SCOPES:
        for path in sorted((ROOT / folder).rglob("*.py")):
            file_count += 1
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or "."]
                else:
                    continue
                for name in names:
                    import_count += 1
                    top = name.split(".")[0]
                    relative = isinstance(node, ast.ImportFrom) and node.level > 0
                    print(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")
                    if not relative and top not in STDLIB | ALLOWED_TOP:
                        violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")
    print(f"\nFiles examined: {file_count}")
    print(f"Imports examined: {import_count}")
    print(f"Outward/nonstandard imports found: {len(violations)}")
    for item in violations:
        print(f"  REVIEW: {item}")
    return bool(violations)


if __name__ == "__main__":
    raise SystemExit(main())
