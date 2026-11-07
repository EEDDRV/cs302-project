"""Exercise the real Flask HTTP endpoint with an image path."""
import argparse
import os
from pathlib import Path
import requests
from dotenv import load_dotenv


def main():
    """Send an image to the authenticated API and display its prediction."""
    load_dotenv(Path(__file__).resolve().parent / ".env")
    parser = argparse.ArgumentParser(description="Call the Prompt Platoon image CAPTCHA API")
    parser.add_argument("image_path", type=Path, help="Path to image to predict")
    parser.add_argument("--url", default=os.getenv("API_URL", "http://127.0.0.1:5000/api/solve"))
    parser.add_argument("--captcha-type", default="image")
    args = parser.parse_args()
    if not args.image_path.is_file():
        parser.error(f"Image file not found: {args.image_path}")
    token = os.getenv("DEMO_API_TOKEN")
    if not token:
        parser.error("Set DEMO_API_TOKEN in .env or the environment")
    try:
        with args.image_path.open("rb") as image_file:
            response = requests.post(args.url, headers={"Authorization": f"Bearer {token}"},
                                     data={"captcha_type": args.captcha_type},
                                     files={"image": (args.image_path.name, image_file)}, timeout=45)
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        parser.exit(1, f"Request failed: {exc}\n")
    print(f"CAPTCHA Type: {args.captcha_type}")
    print(f"Image: {args.image_path}")
    if not response.ok:
        parser.exit(1, f"HTTP {response.status_code}: {payload.get('error', 'Unknown error')}\n")
    print(f"Prediction: {payload['result']}")
    print(f"Processing Time: {payload['processing_time_ms']} ms")
    print(f"Correlation ID: {response.headers.get('X-Correlation-ID', 'unavailable')}")


if __name__ == "__main__":
    main()
