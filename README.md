# Internship Management System

A Django web application that manages the complete internship lifecycle for a
college: internship postings from companies, student applications, college
approval, faculty mentoring, daily attendance, progress tracking, task
assignment, document verification, certificate generation with public
verification, notifications, and role-scoped reports with CSV/XLSX/PDF export.

## Features

- **Five portals** with role-based access control:
  - **College** – manages students, companies, internships, applications,
    allocations, faculty, and approves/rejects workflows.
  - **Faculty** – mentors assigned students, reviews attendance, work logs and
    weekly progress, and monitors tasks **view-only** (cannot assign or
    review tasks).
  - **Company** – posts internships, manages students and supervisors,
    assigns tasks (with mandatory intern **and** supervisor selection),
    requests completion, uploads certificates.
  - **Supervisor** – no standalone dashboard: supervisors log in and land on
    their Supervisor View at `/company/supervisor/<id>/...`, and companies
    reach it via **Dashboard → Intern Attendance → Select Supervisor → Enter
    PIN → Show All Assigned Interns**. Supervisors manage attendance, analytics
    and reports for **their own assigned interns only** (Supervisor A never
    sees Supervisor B's interns).
  - **Student** – browses internships, checks in/out, submits work logs and
    weekly progress, uploads documents and certificates, views mentor and
    company info.
- **Task workflow**: Company assigns tasks to interns **through their
  assigned supervisor** (`Company → Supervisor → Intern`); supervisors approve
  or reject submissions; faculty can only view progress.
- **Internship lifecycle**: Applied → Approved → Allocated → Active →
  Completed, with an approval trail and audit history.
- **Attendance engine**: weekday working-days calculation, half-day/leave/absent
  handling, automatic low-attendance warnings, self check-in/check-out, plus
  supervisor-scoped daily/weekly/monthly reports and analytics with CSV/XLSX/PDF
  export.
- **Progress tracking**: daily work logs and weekly progress reports with
  approve / reject / request-changes review.
- **Documents**: extension and size validation, owner/role-scoped secure
  downloads.
- **Certificates**: unique `INT-YYYY-XXXXXX` numbers and a public verification
  page (`/certificates/verify/<number>/`).
- **Notifications**: per-user inbox with read/unread state.
- **Reports & analytics**: 8 report types (students, companies, faculty,
  attendance, progress, completion, certificates, irregular) with CSV, XLSX
  and PDF export, plus a Chart.js analytics dashboard.

## Tech Stack

- Python 3.14 / Django 6
- SQLite (development) / PostgreSQL (production, via `psycopg`)
- Bootstrap 5, Chart.js
- openpyxl (XLSX export), reportlab (PDF export)

## Getting Started

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env           # Windows
# cp .env.example .env           # Linux / macOS
#   Edit SECRET_KEY, DEBUG, ALLOWED_HOSTS as needed.

# 4. Prepare the database
python manage.py migrate

# 5. (Optional) Load demo data
python manage.py seed_demo

# 6. Run the development server
python manage.py runserver
```

Open http://127.0.0.1:8000/ (home page) to choose a portal.

## Demo Accounts

After running `python manage.py seed_demo`, all accounts use the password
`Demo@12345`:

| Role       | Usernames                                   | Portal URL            |
| ---------- | ------------------------------------------- | --------------------- |
| College    | `college_admin`                             | `/college/login/`     |
| Faculty    | `faculty1`, `faculty2`, `faculty3`          | `/faculty/login/`     |
| Company    | `company1` … `company5`                     | `/company/login/`     |
| Supervisor | `supervisor1` … `supervisor5`               | `/supervisor/login/`  |
| Student    | `student1` … `student20`                    | `/student/login/`     |

An admin superuser is also created: `admin` (password `Admin@12345`).
Supervisor PINs (used in the company **Intern Attendance** flow) default to
`1234`.

## Environment Variables (`.env`)

| Variable                  | Default                     | Purpose                                        |
| ------------------------- | --------------------------- | ---------------------------------------------- |
| `SECRET_KEY`              | (required)                  | Django secret key – change in production       |
| `DEBUG`                   | `True`                      | Debug mode (set `False` in production)         |
| `ALLOWED_HOSTS`           | `localhost,127.0.0.1`       | Comma-separated allowed hosts                  |
| `DATABASE_URL`            | (empty → SQLite)            | e.g. `postgres://USER:PASSWORD@HOST:5432/DB`   |
| `EMAIL_BACKEND`           | console                     | SMTP backend for production                    |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | – | SMTP settings                        |
| `DEFAULT_FROM_EMAIL`      | `noreply@example.com`       | Sender address for emails                      |
| `TIME_ZONE`               | `UTC`                       | Application time zone                          |
| `ATTENDANCE_WARNING_THRESHOLD` | `75`                    | % below which students get attendance warnings |
| `MAX_UPLOAD_SIZE_MB`      | `5`                         | Max size for file uploads                      |

## Running Tests

```bash
python manage.py test
```

The suite covers the role guards, the internship lifecycle, attendance rules,
progress review, certificate flow, document download permissions, task review,
notifications, portal actions, and report generation/export across all apps.

## Management Commands

- `python manage.py seed_demo [--force]` – loads demo college, faculty,
  companies, supervisors, students, internships, applications, allocations,
  attendance, tasks, documents, certificates, feedback and notifications.
  Use `--force` to delete existing data before re-seeding.
- `python manage.py update_internship_statuses` – transitions internships to
  **Active**/**Completed** based on dates and sends attendance warnings.

## Project Structure

```
accounts/       Users, profiles, authentication, role decorators, factories
internships/    Internship, applications, allocations, faculty assignment
attendance/     Attendance records, summaries, warnings
progress/       Daily work logs, weekly progress, evaluations, feedback, approvals
tasks/          Task assignment and review
documents/      Document upload, validation, secure download
certificates/   Certificate management + public verification
notifications/  Per-user notification inbox
reports/        Analytics and report views with CSV/XLSX/PDF export
students/       Student portal
college/        College portal
faculty/        Faculty portal
companies/      Company portal (Intern Attendance select + PIN verify)
supervisors/    Supervisor view: attendance, analytics, reports, tasks, progress
templates/      Shared and role-specific templates
static/         Static assets
media/          Uploaded files (documents, certificates, attachments)
```

## Production Notes

1. Set `DEBUG=False`, a strong `SECRET_KEY`, and list real domains in
   `ALLOWED_HOSTS`.
2. Point `DATABASE_URL` at PostgreSQL and run `python manage.py migrate`.
3. Run with a WSGI server such as Gunicorn:
   `gunicorn internwebsite.wsgi:application`.
4. Serve `/static/` and `/media/` via your web server (nginx/Apache/CDN).
5. Configure a real SMTP `EMAIL_BACKEND` so password/reset and notifications
   emails work.
6. Never commit the real `.env` file (it is gitignored).
