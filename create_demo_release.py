"""Add inactive metadata for testing the model-release human approval gate."""
from config import get_config
from frameworks_and_drivers.sqlite_gateway import SQLiteGateway


def main():
    """Insert an inactive model metadata record and print its ID."""
    with SQLiteGateway(get_config())._connect() as db:
        cursor = db.execute(
            """INSERT INTO AI_Model (ModelName, Version, Framework, ArtifactLocation, IsActive)
               VALUES ('M3 release review demo','pending','PyTorch',
                       'captcha_solver/adapters/image/captcha_model.pt',0)"""
        )
        model_id = cursor.lastrowid
    print(f"Inactive model metadata ID: {model_id}")
    print("This record does not install or load different model weights.")


if __name__ == "__main__":
    main()
