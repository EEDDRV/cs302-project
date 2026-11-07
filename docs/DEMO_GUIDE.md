# Prompt Platoon — Demonstration Guide

This guide explains how to demonstrate the working image CAPTCHA prediction API on a local computer. Start with the [README](../README.md) if you have not installed and initialized the application.

## Before the demonstration

In the extracted project folder, complete the following once:

```bash
python -m pip install -r requirements.txt
python init_db.py
python seed_demo.py
```

`seed_demo.py` saves the bearer token to `.env` automatically. There is no MySQL server to configure and no virtual environment is required.

If you also intend to demonstrate the human-approval gate, run:

```bash
python seed_demo.py --review-users
python create_demo_release.py
```

Set strong passwords for the demo reviewer and admin when prompted. Keep the inactive model ID printed by the second command.

## Main demonstration: authenticated prediction

### Terminal 1: Start the server

```bash
python app.py
```

Leave this terminal open. The application is available at http://127.0.0.1:5000/ by default.

### Terminal 2: Send a real sample image

Open a second terminal in the project folder:

```bash
python demo_api.py samples/03aca642-8bc3-4819-befe-f1436567b1cb.jpg
```

The script reads the token from `.env`, sends the image to `/api/solve`, and prints the AI prediction, processing time, and correlation ID. This calls the running HTTP API rather than importing the solver directly.

### Optional: Browser demonstration

Visit http://127.0.0.1:5000/ to show the image upload UI, or http://127.0.0.1:5000/samples to browse example images. Use the demo API token stored in `.env` where the interface requests a token. Do not display or publish the token during a screen recording.

## Optional technical evidence

**Tests:** From a separate terminal, run:

```bash
python -m pytest -v
```

The tests exercise the application boundary, Flask route, SQLite persistence, guardrail failures, and model release approval without requiring the live model for the business-rule tests.

**Operational log:** Open `logs/run.jsonl` after making an API request. Events are recorded in JSON-lines format with identifiers and outcomes, without logging raw uploaded images or bearer tokens.

**Human approval gate:** With the server running and the inactive model ID obtained above, run these commands, replacing `MODEL_ID` with the printed number:

```bash
curl -i -u m3_admin -X POST http://127.0.0.1:5000/api/admin/models/MODEL_ID/activate
curl -i -u m3_reviewer -X POST http://127.0.0.1:5000/api/admin/models/MODEL_ID/approve
curl -i -u m3_admin -X POST http://127.0.0.1:5000/api/admin/models/MODEL_ID/activate
```

Enter the relevant password when prompted. The initial activation is denied; review by a separate user permits subsequent activation. Only **model metadata** changes, not the loaded model weights.

## Suggested three-minute recording

| Time | Demonstration | Evidence |
| --- | --- | --- |
| 0:00–0:30 | Show the running Flask server and sample image | Application starts and has a user-facing interface |
| 0:30–1:15 | Run `demo_api.py` with the sample image | Actual authenticated HTTP request and AI prediction |
| 1:15–1:40 | Show `logs/run.jsonl` | Readable operational log |
| 1:40–2:30 | Show denied activation, reviewer approval, approved activation | Human-in-the-loop release gate |
| 2:30–3:00 | Show `python -m pytest -v` output | Automated tests and guardrail coverage |

A live test run may take longer depending on your computer; you can display previously collected terminal output during a short recording if you explain when it was generated. Avoid exposing credentials or `.env` contents.

## Stopping or restarting

Press **Ctrl+C** in the Flask terminal. On the next run, you can start the server again with `python app.py`; the SQLite database and seeded records persist in the local database file. You normally do not need to repeat initialization.
