# ⚡ SYNTRIX — Technical Event & Registration Portal

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/Flask-3.0-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20Supabase%20Postgres-3ECF8E.svg?logo=supabase&logoColor=white)](https://supabase.com/)
[![Deployment](https://img.shields.io/badge/Deploy-Vercel%20Serverless-black.svg?logo=vercel&logoColor=white)](https://vercel.com/)
[![Design](https://img.shields.io/badge/UI-Cyberpunk%20Dark%20Theme-55d8ff.svg)](#design--aesthetic)

> **"Think. Code. Survive."** — A full-stack technical symposium registration and management portal built with **Flask (Python)**, **Vanilla HTML5/CSS3**, and dual database engine support (**SQLite** for local development & **Supabase PostgreSQL** with Row-Level Security for production).

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Event Structure & Rounds](#-event-structure--rounds)
- [Project Architecture & Directory Layout](#-project-architecture--directory-layout)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Local Quickstart](#-local-quickstart)
  - [1. Windows Setup (PowerShell / Command Prompt)](#1-windows-setup-powershell--cmd)
  - [2. macOS / Linux Setup](#2-macos--linux-setup)
- [Database Configuration & Management](#-database-configuration--management)
  - [SQLite (Default / Local Development)](#sqlite-default--local-development)
  - [Supabase Postgres (Cloud / Production)](#supabase-postgres-cloud--production)
  - [Database Comparison](#database-comparison)
- [Environment Variables](#-environment-variables)
- [Admin Portal & Organizer Workflow](#-admin-portal--organizer-workflow)
- [Deployment Guide](#-deployment-guide)
  - [Deploying to Vercel](#deploying-to-vercel-recommended)
  - [Deploying to Traditional VPS (Gunicorn / Nginx)](#deploying-to-traditional-vps-gunicorn--nginx)
- [Security & Validation Safeguards](#-security--validation-safeguards)
- [Pre-Launch Checklist](#-pre-launch-checklist)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 🌟 Overview

**SYNTRIX** is a modern, responsive web application designed for collegiate technical symposiums and hackathons. It streamlines team registrations, enforces strict registration quotas, validates participant eligibility, secures payment verification workflows, and provides organizers with a dashboard for live monitoring and data export.

Designed to be lightweight with **zero bulky JavaScript frameworks or node_modules runtime dependencies**, the entire application runs natively on Flask 3 with standard library integrations, ensuring fast cold starts (<200ms) on serverless platforms such as Vercel.

---

## ✨ Key Features

### 🎨 Frontend & User Experience
* **Futuristic Dark Aesthetic**: Styled with pure CSS variables, glassmorphic headers, neon accent highlights (`#55d8ff`), animated orbits, floating challenge badges, and responsive CSS grids.
* **Solo or Duo Registrations**: Allows either a single participant or a team of two (Participant 2 fields are fully optional).
* **Live Slot Counter**: Shows remaining team spots (e.g., `37 of 50 team slots remaining`). Automatically displays a "TEAM LIMIT HIT" lock banner when full.
* **Automatic Uppercase Normalization**: Instant client-side and server-side capitalization for team names, participant names, and college register numbers.
* **In-App Payment QR Scanner**: Embeds the UPI/payment scanner directly in the form layout with client-side image preview before upload.
* **Community Onboarding**: Post-registration success screen with a direct link to join the official SYNTRIX WhatsApp Community.

### 🛡️ Backend & Concurrency Controls
* **Strict 50-Team Cap**: Enforced atomically using transactional locks (`pg_advisory_xact_lock` in Supabase Postgres and `BEGIN IMMEDIATE` transactions in SQLite) to prevent race conditions during high-traffic registration rushes.
* **Duplicate Prevention**: Case-insensitive unique checks across team names and register numbers (preventing a student from being submitted multiple times across different teams or within the same team).
* **Payment Screenshot Validation**: Strict 4 MB upload ceiling, file extension whitelisting (`PNG`, `JPG`, `JPEG`, `WEBP`), and **binary magic-byte inspection** to prevent spoofed file uploads.
* **Dual Database Architecture**: Switch seamlessly between local zero-configuration SQLite and hosted Supabase PostgreSQL via an environment flag (`DATABASE_BACKEND`).
* **Vercel Serverless Ready**: Gracefully respects Vercel's read-only filesystem by bypassing local file initialization and deferring database operations until route invocation.

### 📊 Organizer & Admin Capabilities
* **Protected Dashboard**: Secured via constant-time HMAC password verification (`ADMIN_PASSWORD`).
* **Payment Proof Inspector**: View uploaded payment screenshots inline directly from the browser (`Content-Disposition: inline`) with strict security headers (`X-Content-Type-Options: nosniff`).
* **Payment Approval Workflow**: Toggle statuses between `Pending`, `Verified`, and `Rejected` with optional feedback/rejection reason tracking.
* **Slot Reallocation**: Removing an invalid or rejected team immediately frees up a slot for another team.
* **One-Click CSV Export**: Downloads complete team lists, participant details, system preferences, payment statuses, and timestamps as `event_registrations.csv`.

---

## 🎯 Event Structure & Rounds

| Round # | Challenge Name | Focus Domain | Description |
| :---: | :--- | :--- | :--- |
| **01** | **Code Bingo** | Programming (Python · C · Java) | Solve foundational coding questions and map solutions on a Bingo grid to complete lines using logic and speed. |
| **02** | **Script Game** | SQL Database Challenges | Face 20 SQL questions in a high-stakes glass-bridge challenge. Correct answers yield safe jumps; incorrect answers break the glass. |
| **03** | **AI Forensics: The Missing File** | Prompt Engineering & Investigation | Investigate digital evidence, emails, hidden files, and reports using generative AI prompt engineering to solve the case. |
| **04** | **Debug to Survive** | Survival Debugging Challenge | Navigate a virtual survival map, debug complex code snippets under time pressure, and collect letters to qualify for the finals. |

### Event Rules & Eligibility
* **Max Teams**: Exactly 50 Teams.
* **Team Composition**: 1 to 2 members.
* **Round Duration**: 30 minutes per round.
* **Target Cohort**: Second-year engineering students exclusively.
* **Eligible Branches**:
  - Computer Science and Engineering (CSE)
  - Artificial Intelligence and Data Science (AI & DS)
  - Artificial Intelligence and Machine Learning (AI & ML)
  - Information Technology (IT)
  - Cyber Security
* **Hardware Setup**: Participants may bring their own laptops or request an on-campus laboratory workstation during registration.

---

## 📂 Project Architecture & Directory Layout

```text
syntrix-vercel-fixed/
├── app.py                      # Core Flask application, routing, auth & database controller
├── requirements.txt            # Minimal Python dependencies (Flask>=3.0,<4.0)
├── sql.md                      # Complete Supabase PostgreSQL schema, triggers & RLS policies
├── README.md                   # Project documentation & operational runbook
├── public/                     # Static assets served by Flask / Vercel
│   └── static/
│       ├── style.css           # Custom dark cyberpunk design system & responsive styling
│       └── payment_scanner.jpeg# Payment UPI QR code image displayed on the form
└── templates/                  # Jinja2 HTML templates
    ├── base.html               # Master layout, navigation bar, flash alerts & footer
    ├── index.html              # Landing page (hero, statistics, rounds & eligibility)
    ├── register.html           # Registration form, slot counter & payment upload
    ├── registration_success.html # Success confirmation & WhatsApp community CTA
    ├── admin_login.html        # Secure organizer login form
    ├── dashboard.html          # Admin dashboard for payment reviews & team tracking
    └── error.html              # Friendly custom error pages (404, 413, 500, 503)
```

---

## 💻 Tech Stack

* **Language**: Python 3.10+
* **Framework**: Flask 3.0.x
* **Frontend**: HTML5, CSS3 (Modern Flexbox & Grid, CSS variables), JavaScript (Vanilla ES6)
* **Databases**:
  * Local: SQLite 3 (native Python standard library)
  * Production: Supabase PostgreSQL 15+ (accessed via PostgREST Data API using `urllib.request`)
* **Deployment Target**: Vercel (Python Serverless Function) / Docker / VPS (Gunicorn)

---

## ⚙️ Prerequisites

Before getting started, make sure you have:
1. **Python 3.10 or newer** installed (`python --version` or `py --version`).
2. **Git** installed (if cloning from a repository).
3. A free **[Supabase](https://supabase.com)** account (if testing or running with cloud PostgreSQL).

---

## 🚀 Local Quickstart

### 1. Windows Setup (PowerShell / CMD)

```powershell
# Navigate into the project directory
cd d:\syntrix-registration-web\syntrix-vercel-fixed

# Create a virtual environment
py -m venv .venv

# Activate the virtual environment
.venv\Scripts\activate

# Install dependencies (Flask & python-dotenv)
pip install -r requirements.txt

# Configure your settings in .env file (open with Notepad, VS Code, etc.)
notepad .env

# Start the development server
python app.py
```

### 2. macOS / Linux Setup

```bash
# Navigate to project folder
cd /path/to/syntrix-vercel-fixed

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure your settings in .env
nano .env

# Start the Flask app
python3 app.py
```

Visit the following URLs in your browser:
* **Landing Page**: `http://127.0.0.1:5000/`
* **Registration Form**: `http://127.0.0.1:5000/register`
* **Admin Login**: `http://127.0.0.1:5000/admin` *(Default password if unset: `change-me`)*
* **Health Check**: `http://127.0.0.1:5000/health`

---

## 🗄️ Database Configuration & Management

The application features an abstraction layer supporting two backends via the `DATABASE_BACKEND` environment variable.

### SQLite (Default / Local Development)
* **Storage Location**: Automatically created at `instance/event.db`.
* **Automatic Migrations**: When starting up locally, `init_db()` in `app.py` checks schema columns and automatically migrates legacy databases without data loss (e.g., adding payment proof columns or making Participant 2 optional).
* **Inspecting Local Records**: Open `instance/event.db` in **[DB Browser for SQLite](https://sqlitebrowser.org/)** or inspect directly via CLI:
  ```bash
  sqlite3 instance/event.db "SELECT id, team_name, participant1_name, payment_status FROM registrations;"
  ```

### Supabase Postgres (Cloud / Production)
Supabase provides hosted PostgreSQL with serialized concurrency locks and Row-Level Security.

#### Setup Steps:
1. Log in to your [Supabase Dashboard](https://supabase.com/dashboard) and create a new project.
2. Navigate to **SQL Editor** → **New Query**.
3. Copy and run the entire SQL script from [`sql.md`](./sql.md). This creates:
   - The `public.registrations` table.
   - Case-insensitive unique indexes on `team_name` and register numbers.
   - The transactional trigger function `enforce_registration_limits()` with `pg_advisory_xact_lock(632184730)` to strictly enforce the 50-team cap under concurrent submissions.
   - Row-Level Security (RLS) granting access only to `service_role` and revoking public access from `anon`/`authenticated`.
4. Retrieve your project credentials from **Project Settings → API**:
   - `Project URL` (e.g., `https://xyzcompany.supabase.co`)
   - `service_role` secret key (Never use the public `anon` key).
5. Set your environment variables:
   ```bash
   export DATABASE_BACKEND=supabase
   export SUPABASE_URL=https://your-project.supabase.co
   export SUPABASE_SERVICE_ROLE_KEY=your-service-role-secret-key
   ```

### Database Comparison

| Feature | SQLite | Supabase PostgreSQL |
| :--- | :--- | :--- |
| **Best Used For** | Local testing, offline execution | Production, Vercel deployments, multi-instance servers |
| **Network Required** | ❌ No (runs fully offline) | ✔️ Yes (connects via HTTPS PostgREST API) |
| **Team Cap Protection** | Table lock (`BEGIN IMMEDIATE`) | DB trigger with advisory lock (`pg_advisory_xact_lock`) |
| **Storage Persistence** | Local file in `instance/` (ephemeral on serverless) | Cloud-hosted, persistent, and automatically backed up |
| **File Storage Mechanism** | Binary BLOB in database table | Hex-encoded `bytea` in database table |
| **Access Control** | Local file permissions | Strict Row Level Security (RLS) via service key |

> [!IMPORTANT]
> The app deliberately does **not** dual-write across databases. The selected backend (`DATABASE_BACKEND`) is the single source of truth to avoid data drift.

---

## 🔐 Environment Variables

Configure these settings in your terminal, `.env` file, or cloud platform dashboard (e.g., Vercel / Railway / Render):

| Variable | Required? | Default | Description |
| :--- | :---: | :---: | :--- |
| `DATABASE_BACKEND` | Optional | `sqlite` *(or `supabase` on Vercel)* | Selects the active database engine (`sqlite` or `supabase`). |
| `SUPABASE_URL` | **Required** if Supabase | `""` | The HTTPS endpoint for your Supabase project (e.g., `https://xyz.supabase.co`). |
| `SUPABASE_SERVICE_ROLE_KEY` | **Required** if Supabase | `""` | The secret `service_role` API key (bypasses RLS from server side). **Keep private!** |
| `SECRET_KEY` | **Recommended** | `change-this-secret-key...` | Flask session secret key used for signing cookies. Use a long random string. |
| `ADMIN_PASSWORD` | **Recommended** | `change-me` | Master password required to access `/admin` and the organizer dashboard. |
| `WHATSAPP_COMMUNITY_URL` | Optional | `""` | Full WhatsApp invite link (must start with `https://chat.whatsapp.com/`). |
| `VERCEL` | Auto-set | `None` | Automatically injected by Vercel; sets `DATABASE_BACKEND=supabase` by default. |

---

## 👩‍💼 Admin Portal & Organizer Workflow

1. Navigate to `/admin` and enter the `ADMIN_PASSWORD`.
2. The **Organizer Dashboard** (`/admin/dashboard`) displays:
   - Live registration counts vs. the 50-team maximum limit.
   - Comprehensive participant breakdown (names, register numbers, departments, emails, phones).
   - Indication of whether Participant 2 is present or if it is a solo registration.
   - Declared system preference (BYOD vs. lab workstation required).
3. **Reviewing Payment Proof**:
   - Click **"View screenshot ↗"** on any row to open the uploaded payment screenshot in a secure browser tab.
   - Select **Verified** or **Rejected** from the dropdown.
   - If rejecting, enter an optional explanation (e.g., *"Unreadable transaction reference"*) and click **Save**.
4. **Deleting Registrations**:
   - Click the red **"Remove"** button to delete a test entry or cancelled registration.
   - A confirmation dialog prevents accidental deletion. Deleting a record immediately decrements the counter and reopens an available team slot.
5. **Exporting Records**:
   - Click **"Export CSV ↓"** in the top action bar to download the full, up-to-date registry for attendance and check-in desks.

---

## 🚀 Deployment Guide

### Deploying to Vercel (Recommended)

Because Vercel serverless functions have a read-only, ephemeral filesystem, **Supabase PostgreSQL must be used**.

1. **Push your code to GitHub**:
   Ensure all files (`app.py`, `requirements.txt`, `sql.md`, `templates/`, `public/`) are located at the root of your GitHub repository.
2. **Execute Database Setup**:
   Run the SQL statements from [`sql.md`](./sql.md) once in your Supabase SQL Editor.
3. **Import to Vercel**:
   - Log in to [Vercel](https://vercel.com/) and click **Add New → Project**.
   - Select your GitHub repository.
   - Framework Preset: **Other** or **Flask**.
   - Root Directory: `./`
4. **Configure Environment Variables**:
   In **Settings → Environment Variables**, add:
   - `DATABASE_BACKEND` = `supabase`
   - `SUPABASE_URL` = `https://your-project-id.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` = `your-supabase-service-role-secret`
   - `ADMIN_PASSWORD` = `A_Strong_Organizer_Password`
   - `SECRET_KEY` = `Generate_A_Long_Random_String_Here`
   - `WHATSAPP_COMMUNITY_URL` = `https://chat.whatsapp.com/YourCommunityCode`
5. **Deploy & Validate**:
   - Click **Deploy**.
   - Check `https://your-app.vercel.app/health`. It should return `{"status": "ok"}`.
   - Perform a test registration and verify that the record arrives in Supabase and the Admin Dashboard.

### Deploying to Traditional VPS (Gunicorn / Nginx)

For persistent Linux servers (Ubuntu/Debian) using SQLite or Supabase:

```bash
# Install Gunicorn in your virtual environment
pip install gunicorn

# Run with Gunicorn (4 worker processes)
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

Then configure Nginx as a reverse proxy forwarding requests to `http://127.0.0.1:8000` with an SSL certificate from Let's Encrypt (`certbot`).

---

## 🛡️ Security & Validation Safeguards

* **No Secret Leaks**: The frontend never exposes Supabase keys or database credentials. All database interactions occur strictly on the server.
* **Strict RLS Lockdown**: Direct public reads and writes via Supabase's `anon` key are completely revoked; only the server's `service_role` key has table access.
* **Timing Attack Protection**: Admin password comparisons utilize `hmac.compare_digest` to prevent timing analysis attacks.
* **MIME & Magic-Byte Validation**: File extensions alone are not trusted. The server verifies magic byte signatures (`\x89PNG`, `\xff\xd8\xff`, `RIFF...WEBP`) before saving uploaded proof.
* **Upload Limits**: Hard ceiling of 4 MB prevents Denial of Service (DoS) attacks and stays well within Vercel's ~4.5 MB request payload ceiling.
* **Case-Insensitive Uniqueness**: Team names and student register numbers are trimmed and converted to uppercase to eliminate duplicate bypasses via casing tricks.

---

## 📝 Pre-Launch Checklist

Before sharing the live link with students:

- [ ] Run [`sql.md`](./sql.md) on your production Supabase database.
- [ ] Set a strong `ADMIN_PASSWORD` and unique `SECRET_KEY`.
- [ ] Replace `public/static/payment_scanner.jpeg` with the official event payment QR code if modified.
- [ ] Update `WHATSAPP_COMMUNITY_URL` to the official invite link.
- [ ] Confirm venue, timings, and contact numbers in `templates/index.html`.
- [ ] Confirm the listed eligible branches in `STREAMS` in `app.py` match department guidelines.
- [ ] Submit a test team registration to verify that the submission, file upload, and admin review flow work end-to-end.
- [ ] Remove the test entry from the Admin Dashboard before opening registrations.

---

## ❓ Troubleshooting & FAQs

### Q: Why does the registration say "TEAM LIMIT HIT"?
> **A:** The system has reached its maximum capacity of 50 registered teams. If a team withdraws or is removed by an administrator in `/admin/dashboard`, a slot will reopen automatically.

### Q: I get an HTTP 413 (Payload Too Large) error when registering.
> **A:** The uploaded payment screenshot exceeds 4 MB. Compress the screenshot or upload a PNG/JPG below 4 MB.

### Q: Supabase throws error code `23514` or `23505`.
> **A:**
> - `23514`: Check violation triggered because 50 teams have already registered.
> - `23505`: Unique constraint violation indicating that the team name or register number is already registered.

### Q: Why can't I use SQLite on Vercel?
> **A:** Vercel functions run in ephemeral, stateless execution environments where the local filesystem is read-only. Any file written to disk is destroyed as soon as the lambda terminates. Always configure `DATABASE_BACKEND=supabase` when deploying to Vercel.

---

## 👥 Credits & Support

**SYNTRIX Tech Event**  
Organized by the Department of Computer Science & Engineering / Artificial Intelligence & Data Science.

For technical inquiries or system configuration assistance, contact your event organizing committee or web master.
