import os
import json
import datetime
import random
import base64
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ─── CONFIG ──────────────────────────────────────────────────────────────────

SPREADSHEET_ID  = os.getenv(
    "SPREADSHEET_ID",
    "1m7192nwRRpGiU-UCqf2IxImNOMUL98cKawnXae1i_vs",
)
KEY_FILE        = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", "service_account.json")
SCOPES          = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
SHEET_TAB_NAME  = os.getenv("SHEET_TAB_NAME", "Weekly Reports")


def _load_service_account_credentials():
    """Support service account credentials from:
    - a file path
    - raw JSON content
    - base64-encoded JSON content
    """
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", KEY_FILE)
    if not raw:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY is not set.")

    if os.path.exists(raw):
        with open(raw, "r", encoding="utf-8") as f:
            raw_text = f.read()

        try:
            info = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Service account file '{raw}' is not valid JSON. "
                f"Download the key from Google Cloud IAM → Service Accounts → Keys."
            ) from exc

        if (
            info.get("type") == "service_account"
            and "client_email" in info
            and "token_uri" in info
        ):
            return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

        raise ValueError(
            f"Service account file '{raw}' is missing required fields. "
            "Expected keys for Google Service Account JSON: type='service_account', "
            "'client_email', and 'token_uri'. "
            "Make sure this is not an OAuth client secret file."
        )

    raw = raw.strip()

    if raw.startswith("-----BEGIN PRIVATE KEY-----"):
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_KEY appears to be a raw private key, not a full "
            "service account JSON object."
        )

    candidate_payloads = []
    candidate_payloads.append(raw)

    try:
        candidate_payloads.append(base64.b64decode(raw).decode("utf-8").strip())
    except Exception:
        pass

    info = None
    for payload in candidate_payloads:
        try:
            info = json.loads(payload)
            break
        except (TypeError, json.JSONDecodeError):
            continue

    if not isinstance(info, dict):
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_KEY must be a path to a service account key file, "
            "raw JSON text, or base64-encoded JSON text."
        )

    if info.get("type") != "service_account" or not (
        "client_email" in info and "token_uri" in info
    ):
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_KEY contains JSON but not a service_account object. "
            "Expected fields include 'type': 'service_account', 'client_email', and 'token_uri'. "
            "Use the JSON key downloaded from Google Service Accounts, not an OAuth client secret."
        )

    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def resolve_sheet_name(service) -> str:
    """Return the configured sheet name, or a safe fallback."""
    resp = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        fields="sheets(properties.title)",
    ).execute()

    sheet_titles = [
        item.get("properties", {}).get("title")
        for item in resp.get("sheets", [])
        if item.get("properties", {}).get("title")
    ]

    if not sheet_titles:
        raise ValueError("Spreadsheet has no sheets.")

    if SHEET_TAB_NAME in sheet_titles:
        return SHEET_TAB_NAME

    normalized = SHEET_TAB_NAME.strip().lower()
    for title in sheet_titles:
        if title.strip().lower() == normalized:
            return title

    fallback = sheet_titles[0]
    print(f"⚠️ Sheet '{SHEET_TAB_NAME}' not found. Using first sheet: '{fallback}'.")
    return fallback

# ─── REPORT GENERATION ───────────────────────────────────────────────────────

def generate_report() -> pd.DataFrame:
    """
    Swap this out for your real data source:
      - Query a database (psycopg2 / SQLAlchemy)
      - Read from an API
      - Pull from a CSV / Parquet file

    Here we simulate a weekly ML model performance report —
    the kind you'd attach to the Premier League Predictor.
    """
    today = datetime.date.today()
    week_label = f"W{today.isocalendar()[1]}-{today.year}"

    rows = []
    models = ["LogisticRegression", "RandomForest", "XGBoost"]
    for model in models:
        rows.append({
            "week":            week_label,
            "run_date":        today.isoformat(),
            "model":           model,
            "accuracy":        round(random.uniform(0.58, 0.74), 4),
            "precision":       round(random.uniform(0.55, 0.72), 4),
            "recall":          round(random.uniform(0.50, 0.70), 4),
            "f1_score":        round(random.uniform(0.54, 0.71), 4),
            "matches_scored":  random.randint(30, 50),
            "notes":           "Auto-generated via Google Sheets API",
        })
    return pd.DataFrame(rows)


# ─── GOOGLE SHEETS HELPERS ───────────────────────────────────────────────────

def get_sheets_service():
    creds = _load_service_account_credentials()
    return build("sheets", "v4", credentials=creds)


def ensure_header_exists(service, sheet_name: str, header_row: list[str]):
    """Write header row only if the sheet is empty."""
    escaped_sheet = sheet_name.replace("'", "''")
    sheet_range = lambda r: "'" + escaped_sheet + "'!" + r

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_range("A1:Z1"),
    ).execute()

    if "values" not in result:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_range("A1"),
            valueInputOption="RAW",
            body={"values": [header_row]},
        ).execute()
        print("✓ Header row written.")
    else:
        print("✓ Header already present — skipping.")


def append_rows(service, sheet_name: str, df: pd.DataFrame):
    """Append all rows from df to the sheet (after the last filled row)."""
    values = df.values.tolist()
    body = {"values": values}
    escaped_sheet = sheet_name.replace("'", "''")
    sheet_range = "'" + escaped_sheet + "'!A1"

    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_range,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()

    updated = result.get("updates", {}).get("updatedRows", 0)
    print(f"✓ Appended {updated} row(s) to '{sheet_name}'.")
    return updated


# ─── ALSO EXPORT A LOCAL CSV (for audit trail / Drive upload) ────────────────

def export_csv(df: pd.DataFrame) -> str:
    today = datetime.date.today().isoformat()
    filename = f"report_{today}.csv"
    df.to_csv(filename, index=False)
    print(f"✓ CSV saved locally: {filename}")
    return filename


def upload_csv_to_drive(csv_path: str):
    """
    Optional: also push the CSV file to a Drive folder.
    Requires 'https://www.googleapis.com/auth/drive' scope.
    """
    from googleapiclient.http import MediaFileUpload

    creds = _load_service_account_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    folder_id = os.getenv("DRIVE_FOLDER_ID")   # optional: pin to a folder
    metadata = {
        "name": os.path.basename(csv_path),
        "mimeType": "text/csv",
        **({"parents": [folder_id]} if folder_id else {}),
    }
    media = MediaFileUpload(csv_path, mimetype="text/csv")
    file = drive_service.files().create(
        body=metadata, media_body=media, fields="id,name"
    ).execute()
    print(f"✓ Uploaded to Drive: {file['name']} (id={file['id']})")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("── Google Sheets Auto-Reporter ──")

    df = generate_report()
    print(f"  Generated {len(df)} rows for {df['week'].iloc[0]}")

    # 1. Append to Google Sheet
    service = get_sheets_service()
    actual_sheet_name = resolve_sheet_name(service)
    print("  Using sheet:", actual_sheet_name)
    ensure_header_exists(service, actual_sheet_name, df.columns.tolist())
    append_rows(service, actual_sheet_name, df)

    # 2. Export local CSV (uncomment upload_csv_to_drive to also push to Drive)
    csv_path = export_csv(df)
    # upload_csv_to_drive(csv_path)

    print("── Done ──")


if __name__ == "__main__":
    main()
