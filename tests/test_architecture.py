"""Static import-boundary checks for entities and use cases."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISALLOWED = {"flask", "torch", "pymysql", "bcrypt", "PIL", "requests", "captcha_solver"}


def test_inner_layers_have_no_external_dependencies():
    for folder in ("entities", "use_cases"):
        for module in (ROOT / folder).glob("*.py"):
            tree = ast.parse(module.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                assert not DISALLOWED.intersection(names), f"{module}: {names}"
