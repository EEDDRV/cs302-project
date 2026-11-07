"""Exercise the production Flask route with an alternate outer solver adapter.

This demonstration uses the seeded local SQLite DB and .env token. It replaces
only the composition-root's solver binding for this process; it does not edit
app.py, the use case, the entity layer, or the original captcha_solver package.
"""
import argparse
import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from interface_adapters.audit_alternate_solver import AuditAlternateSolverAdapter


def git_files() -> list[str]:
    """Read all tracked edits and untracked files from the Git working tree.

    Returns:
        A list of Git porcelain lines, or an empty list outside a Git repo.
    """
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    return result.stdout.splitlines() if result.returncode == 0 else []


def main() -> int:
    """Run the primary HTTP use case with an alternate injected solver.

    Returns:
        Zero on successful substitution, otherwise a nonzero exit status.
    """
    parser = argparse.ArgumentParser(description="M3 real-route solver adapter swap audit")
    parser.add_argument("image_path", type=Path, help="Path to a real image file")
    args = parser.parse_args()
    image_path = args.image_path.resolve()
    if not image_path.is_file():
        parser.error(f"Image does not exist: {image_path}")

    load_dotenv(ROOT / ".env")
    token = os.getenv("DEMO_API_TOKEN")
    if not token:
        parser.error("DEMO_API_TOKEN missing: first run python init_db.py and python seed_demo.py")

    import app as app_module

    # Patch only the composition root's dependency reference. build_app()
    # constructs a real route, store, auth gateway, observer, and interactor.
    # The alternate adapter is the only substituted production dependency.
    with patch.object(app_module, "ExistingSolverAdapter", AuditAlternateSolverAdapter):
        flask_app = app_module.build_app()

    with flask_app.test_client() as client:
        response = client.post(
            "/api/solve",
            headers={"Authorization": f"Bearer {token}"},
            data={"captcha_type": "image", "image": (io.BytesIO(image_path.read_bytes()), image_path.name)},
            content_type="multipart/form-data",
        )

    payload = response.get_json(silent=True) or {}
    print("Adapter swap: ExistingSolverAdapter -> AuditAlternateSolverAdapter")
    print("Gateway contract: use_cases.ports.SolverPort")
    print(f"Route: POST /api/solve (Flask test client; no separate server necessary)")
    print(f"Image: {image_path}")
    print(f"HTTP status: {response.status_code}")
    print(f"Response: {payload}")
    print("\nGit status (tracked changes AND untracked files):")
    changes = git_files()
    if changes:
        for line in changes:
            print(f"  {line}")
    else:
        print("  No changes visible (or Git not initialized).")
    print("\nExpected added audit files:")
    print("  interface_adapters/audit_alternate_solver.py")
    print("  scripts/verify_adapter_swap.py")
    print("These files are audit evidence; other Git changes may predate this test.")
    print("No production entity/use-case/solver package files are edited by this script.")
    if response.status_code != 200 or payload.get("result") != "AUDIT_SWAP_OK":
        print("SWAP CHECK FAILED: Inspect .env, database seed, and HTTP response.", file=sys.stderr)
        return 1
    print("SWAP CHECK PASSED: Real Flask API used alternate adapter via SolverPort.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
