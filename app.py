from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, abort
import sqlite3
import csv
import io
import hmac
import os
import re
import logging
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from functools import wraps

BASE_DIR = Path(__file__).resolve().parent

# Automatically load environment variables from .env file if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=ENV_PATH)
    except ImportError:
        # Built-in lightweight fallback parser if python-dotenv is not installed
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v

DB_PATH = BASE_DIR / "instance" / "event.db"
ON_VERCEL = bool(os.environ.get("VERCEL"))
# Vercel's filesystem is read-only/ephemeral, so SQLite cannot be used there:
# default to Supabase when deployed, SQLite for local development.
DATABASE_BACKEND = os.environ.get(
    "DATABASE_BACKEND", "supabase" if ON_VERCEL else "sqlite"
).strip().lower()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()


class SupabaseError(Exception):
    def __init__(self, message, status_code=None, code=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def supabase_request(method, resource, query=None, body=None, prefer=None):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
            "when DATABASE_BACKEND=supabase."
        )
    url = f"{SUPABASE_URL}/rest/v1/{resource}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Accept": "application/json",
    }
    payload = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read()
    except urllib.error.HTTPError as error:
        response_body = error.read()
        try:
            details = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            details = {}
        if not isinstance(details, dict):
            details = {}
        raise SupabaseError(
            details.get("message", "Supabase request failed."),
            status_code=error.code,
            code=details.get("code"),
        ) from error
    except urllib.error.URLError as error:
        raise SupabaseError("Could not connect to Supabase.") from error
    if not response_body:
        return None
    return json.loads(response_body.decode("utf-8"))


def supabase_registrations(select, **query):
    return supabase_request(
        "GET",
        "registrations",
        query={"select": select, **query},
    )


def registration_count():
    if DATABASE_BACKEND == "supabase":
        return len(supabase_registrations("id"))
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) AS count FROM registrations").fetchone()["count"]


def registration_fields():
    return (
        "id,team_name,participant1_name,participant1_regno,"
        "participant1_department,participant1_email,participant1_phone,"
        "participant2_name,participant2_regno,participant2_department,"
        "participant2_email,participant2_phone,year_of_study,"
        "system_preference,payment_proof_filename,payment_proof_mimetype,"
        "payment_status,payment_rejection_reason,created_at"
    )


def registration_rows():
    if DATABASE_BACKEND == "supabase":
        rows = supabase_registrations(registration_fields(), order="created_at.desc")
        for row in rows:
            row["payment_proof"] = bool(row["payment_proof_filename"])
        return rows
    with get_db() as conn:
        rows = conn.execute(
            "SELECT " + registration_fields() + ", "
            "payment_proof IS NOT NULL AS payment_proof "
            "FROM registrations ORDER BY created_at DESC"
        ).fetchall()
    return rows

app = Flask(__name__, static_folder="public/static", static_url_path="/static")
app.logger.setLevel(logging.INFO)
# Vercel functions reject request bodies above ~4.5 MB, so the limit is 4 MB.
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 + (400 * 1024)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")

STREAMS = [
    "Computer Science and Engineering (CSE)",
    "Artificial Intelligence and Data Science (AI & DS)",
    "Artificial Intelligence and Machine Learning (AI & ML)",
    "Information Technology (IT)",
    "Cyber Security"
]
MAX_TEAMS = 50
# Set these environment variables before deployment.
WHATSAPP_COMMUNITY_URL = os.environ.get("WHATSAPP_COMMUNITY_URL", "").strip()
MAX_PAYMENT_UPLOAD_BYTES = 4 * 1024 * 1024
ALLOWED_PAYMENT_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def get_db():
    if DATABASE_BACKEND == "supabase":
        raise RuntimeError("Supabase uses its REST API; use the Supabase repository functions.")
    if DATABASE_BACKEND != "sqlite":
        raise RuntimeError("DATABASE_BACKEND must be either 'sqlite' or 'supabase'.")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create the registration table and migrate older databases safely."""
    if DATABASE_BACKEND == "supabase":
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY when "
                "DATABASE_BACKEND=supabase."
            )
        supabase_registrations("id", limit=1)
        return
    if DATABASE_BACKEND != "sqlite":
        raise RuntimeError("DATABASE_BACKEND must be either 'sqlite' or 'supabase'.")
    with get_db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL UNIQUE,
            participant1_name TEXT NOT NULL,
            participant1_regno TEXT NOT NULL UNIQUE,
            participant1_department TEXT NOT NULL,
            participant1_email TEXT NOT NULL,
            participant1_phone TEXT NOT NULL,
            participant2_name TEXT,
            participant2_regno TEXT UNIQUE,
            participant2_department TEXT,
            participant2_email TEXT,
            participant2_phone TEXT,
            year_of_study TEXT NOT NULL,
            system_preference TEXT NOT NULL,
            payment_proof BLOB,
            payment_proof_filename TEXT,
            payment_proof_mimetype TEXT,
            payment_status TEXT NOT NULL DEFAULT 'Pending',
            payment_rejection_reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)
        columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(registrations)")}
        migrations = {
            "payment_proof": "BLOB",
            "payment_proof_filename": "TEXT",
            "payment_proof_mimetype": "TEXT",
            "payment_status": "TEXT NOT NULL DEFAULT 'Pending'",
            "payment_rejection_reason": "TEXT",
        }
        for column, declaration in migrations.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE registrations ADD COLUMN {column} {declaration}")
        # Older versions required participant 2. Rebuild only when needed so
        # existing registrations are preserved while making participant 2 optional.
        optional_fields = ("participant2_name", "participant2_regno", "participant2_department", "participant2_email", "participant2_phone")
        if any(columns.get(field) and columns[field]["notnull"] for field in optional_fields):
            conn.execute("ALTER TABLE registrations RENAME TO registrations_old")
            conn.execute("""
            CREATE TABLE registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL UNIQUE,
                participant1_name TEXT NOT NULL,
                participant1_regno TEXT NOT NULL UNIQUE,
                participant1_department TEXT NOT NULL,
                participant1_email TEXT NOT NULL,
                participant1_phone TEXT NOT NULL,
                participant2_name TEXT,
                participant2_regno TEXT UNIQUE,
                participant2_department TEXT,
                participant2_email TEXT,
                participant2_phone TEXT,
                year_of_study TEXT NOT NULL,
                system_preference TEXT NOT NULL,
                payment_proof BLOB,
                payment_proof_filename TEXT,
                payment_proof_mimetype TEXT,
                payment_status TEXT NOT NULL DEFAULT 'Pending',
                payment_rejection_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.execute("""
            INSERT INTO registrations (
                id, team_name, participant1_name, participant1_regno,
                participant1_department, participant1_email, participant1_phone,
                participant2_name, participant2_regno, participant2_department,
                participant2_email, participant2_phone, year_of_study,
                system_preference, payment_proof, payment_proof_filename,
                payment_proof_mimetype, payment_status, payment_rejection_reason,
                created_at
            ) SELECT id, team_name, participant1_name, participant1_regno,
                participant1_department, participant1_email, participant1_phone,
                participant2_name, participant2_regno, participant2_department,
                participant2_email, participant2_phone, year_of_study,
                system_preference, payment_proof, payment_proof_filename,
                payment_proof_mimetype, payment_status, payment_rejection_reason,
                created_at FROM registrations_old
            """)
            conn.execute("DROP TABLE registrations_old")

def uppercase_text(value):
    return (value or "").strip().upper()


def allowed_image_upload(upload):
    if not upload or not upload.filename:
        return False, "Please upload your payment screenshot."
    filename = upload.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_PAYMENT_EXTENSIONS:
        return False, "Payment screenshot must be PNG, JPG, JPEG, or WEBP."
    content = upload.read(MAX_PAYMENT_UPLOAD_BYTES + 1)
    upload.seek(0)
    if len(content) > MAX_PAYMENT_UPLOAD_BYTES:
        return False, "Payment screenshot must be 4 MB or smaller."
    signatures = {
        "png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "jpg": content.startswith(b"\xff\xd8\xff"),
        "jpeg": content.startswith(b"\xff\xd8\xff"),
        "webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
    }
    if not signatures.get(extension, False):
        return False, "The uploaded file does not appear to be a valid image."
    return True, content


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    try:
        registered_teams = registration_count()
    except (SupabaseError, RuntimeError):
        app.logger.exception("Could not read registration count")
        registered_teams = 0
    return render_template("index.html", registered_teams=registered_teams, max_teams=MAX_TEAMS)

@app.route("/register", methods=["GET", "POST"])
def register():
    try:
        registered_teams = registration_count()
    except (SupabaseError, RuntimeError):
        app.logger.exception("Could not read registration count")
        registered_teams = 0
    if request.method == "POST":
        if registered_teams >= MAX_TEAMS:
            flash("TEAM LIMIT HIT — all 50 team slots are filled. Registrations are now closed. Thank you for your interest!", "error")
            return render_template("register.html", data=request.form, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=True)

        fields = [
            "team_name", "participant1_name", "participant1_regno",
            "participant1_department", "participant1_email", "participant1_phone",
            "participant2_name", "participant2_regno", "participant2_department",
            "participant2_email", "participant2_phone", "year_of_study",
            "system_preference"
        ]
        data = {field: request.form.get(field, "").strip() for field in fields}
        # Normalize human-entered identifiers/names on the server as well as in the browser.
        for key in ("team_name", "participant1_name", "participant1_regno", "participant2_name", "participant2_regno"):
            data[key] = uppercase_text(data[key])
        for key in ("participant1_email", "participant2_email"):
            data[key] = data[key].lower()
        required_fields = ["team_name", "participant1_name", "participant1_regno", "participant1_department", "participant1_email", "participant1_phone", "year_of_study", "system_preference"]
        has_participant2 = any(data[k] for k in ("participant2_name", "participant2_regno", "participant2_department", "participant2_email", "participant2_phone"))
        if any(not data[k] for k in required_fields):
            flash("Please complete all required team and Participant 1 fields.", "error")
            return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)
        if has_participant2 and any(not data[k] for k in ("participant2_name", "participant2_regno", "participant2_department", "participant2_email", "participant2_phone")):
            flash("Participant 2 is optional. If you add them, complete all five Participant 2 fields.", "error")
            return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)
        if data["year_of_study"] != "Second Year":
            flash("This event is open only to second-year students.", "error")
            return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)
        email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        if not email_re.match(data["participant1_email"]):
            flash("Please enter a valid email address for Participant 1.", "error")
            return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)
        if has_participant2:
            if data["participant1_regno"].lower() == data["participant2_regno"].lower():
                flash("Participants must have different register numbers.", "error")
                return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)
            if not email_re.match(data["participant2_email"]):
                flash("Please enter a valid email address for Participant 2.", "error")
                return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)
        departments = [data["participant1_department"]] + ([data["participant2_department"]] if has_participant2 else [])
        if not all(department in STREAMS for department in departments):
            flash("Please choose a department from the list.", "error")
            return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)

        upload = request.files.get("payment_screenshot")
        valid_upload, upload_result = allowed_image_upload(upload)
        if not valid_upload:
            flash(upload_result, "error")
            return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=False)
        payment_bytes = upload_result
        original_filename = (upload.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])[:180]
        extension = original_filename.rsplit(".", 1)[-1].lower()
        payment_mimetype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}[extension]

        try:
            if DATABASE_BACKEND == "supabase":
                rows = supabase_registrations(
                    "team_name,participant1_regno,participant2_regno",
                )
                submitted_regnos = {
                    value for value in (data["participant1_regno"], data["participant2_regno"])
                    if value
                }
                duplicate = any(
                    row["team_name"].strip().upper() == data["team_name"]
                    or row["participant1_regno"].strip().upper() in submitted_regnos
                    or (row["participant2_regno"] or "").strip().upper() in submitted_regnos
                    for row in rows
                )
                current_count = len(rows)
                if current_count >= MAX_TEAMS:
                    flash("TEAM LIMIT HIT — all 50 team slots are filled. Registrations are now closed. Thank you for your interest!", "error")
                    return render_template("register.html", data=data, streams=STREAMS, registered_teams=current_count, max_teams=MAX_TEAMS, registration_full=True)
                if duplicate:
                    flash("That team name or participant register number is already registered (case-insensitive check).", "error")
                    return render_template("register.html", data=data, streams=STREAMS, registered_teams=current_count, max_teams=MAX_TEAMS, registration_full=False)
                payload = {key: data[key] or None for key in fields}
                payload.update({
                    "payment_proof": "\\x" + payment_bytes.hex(),
                    "payment_proof_filename": original_filename,
                    "payment_proof_mimetype": payment_mimetype,
                    "payment_status": "Pending",
                })
                supabase_request(
                    "POST",
                    "registrations",
                    query={"select": "id"},
                    body=payload,
                    prefer="return=minimal",
                )
            else:
                with get_db() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    current_count = conn.execute("SELECT COUNT(*) AS count FROM registrations").fetchone()["count"]
                    if current_count >= MAX_TEAMS:
                        conn.rollback()
                        flash("TEAM LIMIT HIT — all 50 team slots are filled. Registrations are now closed. Thank you for your interest!", "error")
                        return render_template("register.html", data=data, streams=STREAMS, registered_teams=current_count, max_teams=MAX_TEAMS, registration_full=True)
                    duplicate = conn.execute("""
                        SELECT 1 FROM registrations
                        WHERE UPPER(TRIM(team_name)) = ?
                           OR UPPER(TRIM(participant1_regno)) = ?
                           OR UPPER(TRIM(COALESCE(participant2_regno,''))) = ?
                           OR (? <> '' AND UPPER(TRIM(participant1_regno)) = ?)
                           OR (? <> '' AND UPPER(TRIM(COALESCE(participant2_regno,''))) = ?)
                        LIMIT 1
                    """, (data["team_name"], data["participant1_regno"], data["participant1_regno"], data["participant2_regno"], data["participant2_regno"], data["participant2_regno"], data["participant2_regno"])).fetchone()
                    if duplicate:
                        conn.rollback()
                        flash("That team name or participant register number is already registered (case-insensitive check).", "error")
                        return render_template("register.html", data=data, streams=STREAMS, registered_teams=current_count, max_teams=MAX_TEAMS, registration_full=False)
                    conn.execute("""
                    INSERT INTO registrations (
                        team_name, participant1_name, participant1_regno,
                        participant1_department, participant1_email, participant1_phone,
                        participant2_name, participant2_regno, participant2_department,
                        participant2_email, participant2_phone, year_of_study, system_preference,
                        payment_proof, payment_proof_filename, payment_proof_mimetype, payment_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                    """, tuple(data[k] or None for k in fields) + (
                        sqlite3.Binary(payment_bytes),
                        original_filename,
                        payment_mimetype,
                    ))
            return redirect(url_for("registration_success"))
        except sqlite3.IntegrityError:
            flash("That team name or a participant register number is already registered. Check the details or contact the organizers.", "error")
        except SupabaseError as error:
            app.logger.exception("Supabase error while saving registration")
            if error.code == "23514":
                flash("TEAM LIMIT HIT — all 50 team slots are filled. Registrations are now closed. Thank you for your interest!", "error")
                return render_template("register.html", data=data, streams=STREAMS, registered_teams=registration_count(), max_teams=MAX_TEAMS, registration_full=True)
            if error.code == "23505":
                flash("That team name or a participant register number is already registered. Check the details or contact the organizers.", "error")
            else:
                flash("We could not save your registration. Please try again or contact the organizers.", "error")
        except sqlite3.Error:
            app.logger.exception("SQLite error while saving registration")
            flash("We could not save your registration. Please try again or contact the organizers.", "error")
        registered_teams = registration_count()
        return render_template("register.html", data=data, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=registered_teams >= MAX_TEAMS)
    return render_template("register.html", data={}, streams=STREAMS, registered_teams=registered_teams, max_teams=MAX_TEAMS, registration_full=registered_teams >= MAX_TEAMS)

@app.route("/registration-success")
def registration_success():
    return render_template("registration_success.html", whatsapp_url=WHATSAPP_COMMUNITY_URL)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", "").encode(), ADMIN_PASSWORD.encode()):
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Incorrect admin password.", "error")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
@admin_required
def dashboard():
    rows = registration_rows()
    return render_template("dashboard.html", registrations=rows, max_teams=MAX_TEAMS)


@app.route("/admin/payment-proof/<int:registration_id>")
@admin_required
def payment_proof(registration_id):
    if DATABASE_BACKEND == "supabase":
        rows = supabase_registrations(
            "payment_proof,payment_proof_mimetype,payment_proof_filename",
            id=f"eq.{registration_id}",
            limit=1,
        )
        row = rows[0] if rows else None
        if row and row["payment_proof"]:
            encoded_proof = row["payment_proof"]
            if not encoded_proof.startswith("\\x"):
                raise SupabaseError("Supabase returned payment proof in an unsupported format.")
            proof = bytes.fromhex(encoded_proof[2:])
        else:
            proof = None
    else:
        with get_db() as conn:
            row = conn.execute("SELECT payment_proof, payment_proof_mimetype, payment_proof_filename FROM registrations WHERE id = ?", (registration_id,)).fetchone()
        proof = row["payment_proof"] if row else None
    if not row or not proof:
        abort(404)
    return Response(proof, mimetype=row["payment_proof_mimetype"] or "application/octet-stream", headers={"Content-Disposition": "inline; filename=payment-proof-image", "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})


@app.route("/admin/payment-status/<int:registration_id>", methods=["POST"])
@admin_required
def update_payment_status(registration_id):
    status = request.form.get("payment_status", "Pending")
    reason = request.form.get("payment_rejection_reason", "").strip()[:500]
    if status not in {"Pending", "Verified", "Rejected"}:
        abort(400)
    if DATABASE_BACKEND == "supabase":
        supabase_request(
            "PATCH",
            "registrations",
            query={"id": f"eq.{registration_id}"},
            body={
                "payment_status": status,
                "payment_rejection_reason": reason if status == "Rejected" else None,
            },
            prefer="return=minimal",
        )
    else:
        with get_db() as conn:
            conn.execute("UPDATE registrations SET payment_status = ?, payment_rejection_reason = ? WHERE id = ?", (status, reason if status == "Rejected" else None, registration_id))
    flash("Payment proof status updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/remove/<int:registration_id>", methods=["POST"])
@admin_required
def remove_registration(registration_id):
    if DATABASE_BACKEND == "supabase":
        supabase_request(
            "DELETE",
            "registrations",
            query={"id": f"eq.{registration_id}"},
        )
    else:
        with get_db() as conn:
            conn.execute("DELETE FROM registrations WHERE id = ?", (registration_id,))
    flash("Team registration removed.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/export.csv")
@admin_required
def export_csv():
    rows = registration_rows()
    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow([row[key] for key in row.keys()])
    else:
        writer.writerow(["No registrations yet"])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=event_registrations.csv"}
    )

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/health")
def health():
    return {"status": "ok"}

def error_page(code, heading, message):
    return render_template("error.html", code=code, heading=heading, message=message), code


@app.errorhandler(SupabaseError)
@app.errorhandler(RuntimeError)
def backend_unavailable(error):
    """Show a friendly page (and log the details) instead of a bare 500."""
    app.logger.exception("Backend error: %s", error)
    return error_page(503, "Service temporarily unavailable.",
                      "We could not reach the database. Please try again in a moment.")


@app.errorhandler(404)
def not_found(_error):
    return error_page(404, "Page not found.", "The page you are looking for does not exist.")


@app.errorhandler(500)
def server_error(_error):
    return error_page(500, "Something went wrong.", "Please try again or contact the organizers.")


@app.route("/favicon.ico")
def favicon():
    return Response(status=204)


@app.errorhandler(413)
def too_large(_error):
    flash("Payment screenshot must be 4 MB or smaller.", "error")
    return redirect(url_for("register"))


# Do NOT touch the database at import time on Vercel: a failure here crashes
# the whole function (500 FUNCTION_INVOCATION_FAILED). Supabase tables are
# created once via sql.md; SQLite is only initialised for local development.
if DATABASE_BACKEND == "sqlite" and not ON_VERCEL:
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
