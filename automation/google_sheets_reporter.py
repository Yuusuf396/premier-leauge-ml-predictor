import os
import json
import datetime
import random
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ─── CONFIG ──────────────────────────────────────────────────────────────────

SPREADSHEET_ID  = os.getenv(
    "SPREADSHEET_ID",
    "1m7192nwRRpGiU-UCqf2IxImNOMUL98cKawnXae1i_vs",
)
SHEET_TAB_NAME  = "Weekly Reports"
KEY_FILE        = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", "service_account.json")
SCOPES          = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

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
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def ensure_header_exists(service, header_row: list[str]):
    """Write header row only if the sheet is empty."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_TAB_NAME}!A1:Z1",
    ).execute()

    if "values" not in result:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_TAB_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [header_row]},
        ).execute()
        print("✓ Header row written.")
    else:
        print("✓ Header already present — skipping.")


def append_rows(service, df: pd.DataFrame):
    """Append all rows from df to the sheet (after the last filled row)."""
    values = df.values.tolist()
    body = {"values": values}

    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_TAB_NAME}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()

    updated = result.get("updates", {}).get("updatedRows", 0)
    print(f"✓ Appended {updated} row(s) to '{SHEET_TAB_NAME}'.")
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

    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE, scopes=["https://www.googleapis.com/auth/drive"]
    )
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
    ensure_header_exists(service, df.columns.tolist())
    append_rows(service, df)

    # 2. Export local CSV (uncomment upload_csv_to_drive to also push to Drive)
    csv_path = export_csv(df)
    # upload_csv_to_drive(csv_path)

    print("── Done ──")


if __name__ == "__main__":
    main()
