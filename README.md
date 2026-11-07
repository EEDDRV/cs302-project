# Prompt Platoon — Image CAPTCHA Prediction API

Prompt Platoon is a Python application that accepts an image through an authenticated HTTP API and returns a text prediction from a locally hosted AI model. It also includes a browser-based demonstration interface, sample images, a command-line API client, and automated tests.

**This repository is a local demonstration prototype.** It is not intended to be exposed directly to the public internet. Only submit images you own or are authorized to process.

## Features

- Flask HTTP API with bearer-token authentication.
- Local PyTorch image inference using the bundled model (`captcha_solver/`).
- Browser interface for uploading images and browsing samples.
- `demo_api.py` command-line client that calls the real HTTP endpoint.
- Local SQLite database through Python's built-in `sqlite3` library; no MySQL server is needed.
- Request limits, redacted operational logs, a model-release approval demonstration, and automated tests.

## Requirements

- **Python 3.10 or newer**, with `pip` available.
- An internet connection for installing Python dependencies (the included model runs locally after installation).
- Sufficient disk space and memory for installing and loading PyTorch and the included model.
- A terminal or command prompt. Commands below work in Windows PowerShell, Command Prompt, macOS Terminal, or a Linux shell, provided `python` points to the intended Python installation.

**Not required:** MySQL, Docker, a GPU, or a Python virtual environment. A virtual environment is optional, but the steps below do not use one.

> On some Windows installations, replace `python` with `py` in every command. Check your installation using `python --version` or `py --version`.

## Quick start

### 1. Extract the project and open a terminal

Extract the ZIP, then open a terminal **inside the `prompt_platoon_m3` folder**. This is the directory containing `app.py`, `requirements.txt`, and `seed_demo.py`. All commands below assume this working directory.

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

The initial installation can take longer than subsequent runs because PyTorch may require a large download. If your Python installation restricts global package installation, try:

```bash
python -m pip install --user -r requirements.txt
```

The `--user` option is not supported in all Python configurations. If it fails, use a Python installation that permits package installation, or consult your operating system's Python packaging guidance. A virtual environment is **not required by this application**.

### 3. Initialize the SQLite database

```bash
python init_db.py
```

This creates `prompt_platoon.sqlite3` in the project directory by default and initializes its 11 tables. No separate database server or credentials are necessary. Running the command again does not delete the existing records.

### 4. Create the demonstration account and API token

```bash
python seed_demo.py
```

This creates the sample customer, a usable API key, and the image model/adapter metadata. It also **creates or updates `.env` automatically**, saving the token as `DEMO_API_TOKEN`. You do not have to copy the token into another file. If an existing token is configured, the script reuses it. Other settings in `.env` are retained.

**Keep `.env` private:** it contains the bearer token. Do not share it, publish it, or commit it to version control. Only the token hash is saved in the database.

### 5. Start the API server

```bash
python app.py
```

Leave this terminal running. By default, Flask serves the application at **http://127.0.0.1:5000**. Visit this address to use the existing browser interface. The sample gallery is at **http://127.0.0.1:5000/samples**.

> You must keep `python app.py` running while making requests from the browser or command-line client. Stop it with **Ctrl+C**.

### 6. Test a real prediction from another terminal

Open a **second** terminal in the same project directory, and run:

```bash
python demo_api.py samples/03aca642-8bc3-4819-befe-f1436567b1cb.jpg
```

The client reads the token from `.env`, uploads the provided sample image to the running Flask server, and prints the predicted text, processing time, and correlation ID. The answer depends on the model output; there is no hard-coded expected prediction.

**Expected output format** (illustrative only):

```text
CAPTCHA Type: image
Image: samples/03aca642-8bc3-4819-befe-f1436567b1cb.jpg
Prediction: <model-predicted-text>
Processing Time: <milliseconds> ms
Correlation ID: <request-id>
```

For a different image, replace the filename. Paths containing spaces should be quoted, for example:

```bash
python demo_api.py "C:\Users\Example\Pictures\my image.png"
```

To call an API at a non-default address:

```bash
python demo_api.py samples/03aca642-8bc3-4819-befe-f1436567b1cb.jpg --url http://127.0.0.1:8000/api/solve
```

## Using the HTTP API

### Check model readiness

`GET /api/health` returns a JSON readiness response. Example:

```bash
curl http://127.0.0.1:5000/api/health
```

### Submit an image

`POST /api/solve` accepts `multipart/form-data` with:

| Field | Purpose |
| --- | --- |
| `image` | Uploaded image file (PNG, JPEG, GIF, WEBP, or BMP) |
| `captcha_type` | Solver type, currently `image` |
| `Authorization` header | `Bearer <API_TOKEN>` |

Example for a terminal with a token already available as an environment variable:

```bash
curl -X POST http://127.0.0.1:5000/api/solve \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -F "captcha_type=image" \
  -F "image=@samples/03aca642-8bc3-4819-befe-f1436567b1cb.jpg"
```

For Windows users, `demo_api.py` is the simplest cross-platform way to make this request without copying the token. The example above uses Unix shell line continuations; put it on one line in PowerShell or Command Prompt.

A successful response has this structure:

```json
{
  "result": "predicted text",
  "captcha_type": "image",
  "processing_time_ms": 123
}
```

The HTTP response also includes an `X-Correlation-ID` header. Invalid inputs and unauthorized requests produce JSON errors. Image uploads are limited to 5 MiB by default. The API may reject an invalid token, unsupported type, oversized image, exhausted quota, or model failure.

## Automated tests

From the project root, run:

```bash
python -m pytest -v
```

The test suite exercises the application use case, authentication and quotas, guardrail handling, SQLite integration, the Flask route, model-release approval, and the ability to substitute a solver adapter. Most business-rule tests use fake solvers rather than invoking the PyTorch model. The separate `demo_api.py` command tests real model inference over HTTP.

## Configuration

The application reads its settings from `.env` in the project directory. `seed_demo.py` creates the file from `.env.example` if needed. You can edit the non-secret settings after initialization and restart Flask to apply them.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Host address Flask listens on |
| `PORT` | `5000` | HTTP port |
| `DEBUG` | `false` | Flask debug mode; keep disabled outside local debugging |
| `DB_PATH` | `prompt_platoon.sqlite3` | SQLite database location, relative to project folder unless absolute |
| `DEMO_API_TOKEN` | Generated by `seed_demo.py` | Client bearer token; keep secret |
| `MAX_IMAGE_BYTES` | `5242880` | Maximum image size (5 MiB) |
| `MAX_INFERENCE_MS` | `10000` | Post-inference duration guardrail in milliseconds |
| `MAX_CASE_COST_USD` | `0.00` | Configured maximum estimated external model cost per request |
| `ESTIMATED_CASE_COST_USD` | `0.00` | Estimated external model cost for the local model |

The cost estimate defaults to zero because inference uses a bundled local model, not a paid vendor API. **`MAX_INFERENCE_MS` checks the duration after inference returns; it is not a hard interruption or timeout.** The demo API key also has monthly and per-minute request limits in the database.

The bundled `database_schema_original.sql` is the team's original MySQL schema retained for reference. The running application uses the corresponding SQLite-compatible definition in `frameworks_and_drivers/sqlite_schema.py`. **Do not execute the MySQL DDL against SQLite.**

## Operational log and privacy

Request outcomes are written as structured JSON lines to `logs/run.jsonl`. Selected events are also written to `SystemAuditLog` in SQLite. Logs are intended to show operation and errors while avoiding raw CAPTCHA images and bearer tokens. Because the provided schema requires a non-null value for `SolvingRequest.CaptchaContentPayload`, the application stores a redaction marker there instead of image bytes; other request metadata and predictions may be stored in SQLite.

The local database, `.env`, and log files are excluded from version control by `.gitignore`. Do not upload them with a public project archive.

## Optional: human approval demonstration

The application includes a model **metadata** release-review flow to demonstrate a human approval gate. It does **not** replace the running PyTorch weights.

1. Set up the demo users (you will be prompted for passwords of at least 12 characters):

   ```bash
   python seed_demo.py --review-users
   ```

2. Create an inactive model metadata record:

   ```bash
   python create_demo_release.py
   ```

   Record the model ID printed by the command.

3. With Flask running, try activation as the admin, approve as the reviewer, and activate again. Replace `MODEL_ID` with the value from the previous step:

   ```bash
   curl -i -u m3_admin -X POST http://127.0.0.1:5000/api/admin/models/MODEL_ID/activate
   curl -i -u m3_reviewer -X POST http://127.0.0.1:5000/api/admin/models/MODEL_ID/approve
   curl -i -u m3_admin -X POST http://127.0.0.1:5000/api/admin/models/MODEL_ID/activate
   ```

   Each `curl` request prompts for the respective account password. The first activation should be denied until a **different** reviewer approves the release. This feature is for controlled local demonstration; HTTP Basic authentication should not be exposed over an unencrypted public network.

See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for a short presentation sequence.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `python` is not recognized | Install Python 3.10+ and ensure it is on PATH, or try `py` on Windows. |
| `ModuleNotFoundError` | Run `python -m pip install -r requirements.txt` with the same Python interpreter used to start the application. |
| `Connection refused` from `demo_api.py` | Start `python app.py` in a separate terminal and confirm the URL/port. |
| `Bearer token required` or HTTP 401 | Run `python seed_demo.py` and confirm `.env` contains `DEMO_API_TOKEN`; restart the CLI. |
| `no such table` / missing database | Run `python init_db.py` in the project folder, then `python seed_demo.py`; confirm `DB_PATH` points to the expected file. |
| Port 5000 is already in use | Stop the competing process or change `PORT` in `.env`, restart Flask, and use `demo_api.py --url` with the new port. |
| An image is rejected | Check that it is a supported, valid image within the configured size limit. |
| Model initialization or inference fails | Confirm all dependencies installed and `captcha_solver/adapters/image/captcha_model.pt` is present. Review terminal errors and `logs/run.jsonl`. |
| `pytest` command isn't found | Run tests as `python -m pytest -v`; pytest is included in `requirements.txt`. |

## Repository layout

```text
prompt_platoon_m3/
├── app.py                         # Flask entry point / dependency composition
├── init_db.py                     # Initialize embedded SQLite database
├── seed_demo.py                   # Create demo data and save token to .env
├── demo_api.py                    # CLI client for the real HTTP API
├── create_demo_release.py         # Create an inactive model metadata record
├── config.py                      # Environment configuration
├── .env.example                   # Settings template (safe to share)
├── requirements.txt
├── entities/                      # Application data types
├── use_cases/                     # Model-independent application logic
├── interface_adapters/            # HTTP and model integration
├── frameworks_and_drivers/        # SQLite gateway and schema
├── governance/                    # Redacted audit and model approval
├── captcha_solver/                # Original image model and solver package
├── templates/                     # Browser interface
├── static/                        # Browser assets
├── samples/                       # Sample images
├── tests/                         # Automated test suite
└── docs/                          # Demo instructions and audit evidence
```

For architectural decisions and source-code audit notes, see [docs/AUDIT_EVIDENCE.md](docs/AUDIT_EVIDENCE.md). That document is implementation evidence, not a substitute for a separate project report.
