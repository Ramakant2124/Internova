"""Generate docs/Internship_Lifecycle_Guide.pdf (step-by-step student lifecycle)."""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "docs")
OUT_PATH = os.path.join(OUT_DIR, "Internship_Lifecycle_Guide.pdf")

os.makedirs(OUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
title = ParagraphStyle(
    "TitleX", parent=styles["Title"], fontSize=20, spaceAfter=6,
)
subtitle = ParagraphStyle(
    "SubtitleX", parent=styles["Normal"], fontSize=10,
    textColor=colors.grey, alignment=TA_CENTER, spaceAfter=18,
)
h1 = ParagraphStyle("H1X", parent=styles["Heading1"], fontSize=14,
                    textColor=colors.HexColor("#1F4E79"), spaceBefore=14, spaceAfter=6)
h2 = ParagraphStyle("H2X", parent=styles["Heading2"], fontSize=11.5,
                    textColor=colors.HexColor("#2E75B6"), spaceBefore=10, spaceAfter=4)
body = ParagraphStyle("BodyX", parent=styles["BodyText"], fontSize=10,
                      leading=14, spaceAfter=6)
bullet = ParagraphStyle("BulletX", parent=body, leftIndent=12, bulletIndent=2,
                        spaceAfter=3)

STEPS = [
    (
        "Step 1 - College creates the student account",
        [
            "Log in to the College portal (college_admin / Demo@12345).",
            "Go to Students and click Add Student.",
            "Enter student details (name, email, department, year) and submit.",
            "The system creates the login account with the default password "
            "Demo@12345 (or a generated one).",
            "Result: the student appears in the College dashboard list. It does "
            "NOT appear on the Faculty, Company or other dashboards yet.",
        ],
    ),
    (
        "Step 2 - Student logs in and completes the profile",
        [
            "Student opens /student/login/ and logs in (username e.g. student1, "
            "password Demo@12345).",
            "The student dashboard shows their profile, allocation status and "
            "available internship listings.",
            "The student can upload documents (offer letter, joining report, etc.).",
        ],
    ),
    (
        "Step 3 - Student applies to an internship",
        [
            "From the student dashboard the student browses active internships "
            "and clicks Apply.",
            "An internship application is created with status Pending.",
            "The student can have one active allocation at a time.",
        ],
    ),
    (
        "Step 4 - College reviews and approves the application (allocation)",
        [
            "The College dashboard shows pending applications.",
            "The college reviews and approves the application.",
            "Approval creates an ACTIVE allocation linking Student -> Internship "
            "(-> Company). Start/end dates are set.",
            "Notifications inform the student (and company) that the allocation "
            "is live.",
        ],
    ),
    (
        "Step 5 - Student selects a Faculty Mentor (new feature)",
        [
            "On the student's Mentor page, the system lists all Faculty members "
            "of the student's college.",
            "The student selects a mentor; the assignment is stored in the DB "
            "(FacultyAssignment, active=True).",
            "Changing the mentor deactivates the old assignment and creates a "
            "new one - no duplicate active mentors (unique constraint).",
            "Result: the student appears on the selected mentor's dashboard "
            "(Faculty -> My Students).",
            "A student from another college cannot pick that college's faculty "
            "(403 PermissionDenied).",
        ],
    ),
    (
        "Step 6 - Company verifies a Supervisor; Supervisor marks attendance "
        "(new feature)",
        [
            "Each internship has CompanySupervisors (contact records) with a "
            "hashed PIN/password. After allocation, the company links an intern "
            "to a supervisor via Assign Supervisor - stored as "
            "SupervisorAssignment (active=True, one active supervisor per "
            "intern/internship).",
            "Supervisors get a login account (username supervisor1..5, "
            "password Demo@12345, PIN 1234) and open /supervisor/login/.",
            "Company Dashboard -> Intern Attendance -> Select Supervisor -> "
            "Enter PIN -> verify -> Show All Assigned Interns. The company is "
            "now scoped to that supervisor (session-based, must belong to the "
            "same company).",
            "The supervisor view lives at /company/supervisor/<id>/... and only "
            "lists interns assigned to that supervisor; Attendance -> Mark "
            "Attendance is scoped the same way.",
            "Each Attendance record is stored with the supervisor and "
            "marked_by fields. Duplicates for the same student/date are "
            "rejected.",
            "The company exits the supervisor view via an Exit button that "
            "clears the session (no direct attendance management outside the "
            "PIN-verified flow).",
        ],
    ),
    (
        "Step 7 - Company assigns tasks via the supervisor; supervisor "
        "reviews; faculty monitors (new feature)",
        [
            "Company portal -> Tasks -> Assign Task. The form requires BOTH "
            "the intern (student) AND a supervisor (mandatory).",
            "The task is stored with assigned_by = company user and "
            "supervisor = selected supervisor; the supervisor is also "
            "auto-linked to the intern via SupervisorAssignment.",
            "A task without a supervisor is rejected by validation.",
            "The supervisor view -> Tasks lists tasks of their interns and "
            "can Approve / Reject SUBMITTED tasks.",
            "Faculty dashboard shows ALL tasks (title, description, student, "
            "supervisor, status, progress, start, due) VIEW-ONLY - no "
            "assign, edit, review or reassign buttons.",
        ],
    ),
    (
        "Step 8 - Faculty reviews work logs and weekly progress",
        [
            "Students submit Daily Work Logs and Weekly Progress reports.",
            "Faculty reviews each submission (approve / revise) - this is the "
            "faculty's review responsibility.",
            "Reviews and auto-calculations update the progress summary on the "
            "faculty and college dashboards.",
        ],
    ),
    (
        "Step 9 - Data calculations happen automatically",
        [
            "Attendance percentage = present / working days (excludes "
            "Sundays), shown per student.",
            "Weekly progress average = mean of the student's weekly progress "
            "reports.",
            "Pending/overdue task counts are computed from task status vs due "
            "date.",
            "If attendance drops below the warning threshold, the college gets "
            "attendance warnings.",
        ],
    ),
    (
        "Step 10 - Documents, completion and certificate",
        [
            "Students upload required documents (offer letter, joining and "
            "completion reports) in their portal.",
            "College or company uploads/generates the completion certificate "
            "with a certificate number (e.g. INT-2026-000002).",
            "Anyone can verify a certificate publicly at "
            "/certificates/verify/<number>/ (shows student and company names).",
        ],
    ),
    (
        "Step 11 - Interactions between dashboards (summary)",
        [
            "Adding one student: it appears ONLY on the college dashboard by "
            "default.",
            "After Step 5 (mentor selection) it also appears on the chosen "
            "faculty dashboard.",
            "After Step 4 (application approval) + Step 6 (supervisor "
            "assignment) it appears on the company dashboard and in the "
            "supervisor view (Assigned Interns).",
            "Workflow: Company -> Supervisor -> Intern -> Task. Faculty and "
            "college only view task progress.",
            "A company needs to re-verify a supervisor PIN to enter the "
            "supervisor view; Supervisor A never sees Supervisor B's interns.",
        ],
    ),
]

ROLES = [
    ("College", "Creates student accounts, approves applications, sees "
     "analytics and reports, uploads certificates."),
    ("Faculty / Mentor", "Sees assigned students, reviews work logs and weekly "
     "progress, and views task progress for all of their students "
     "(view-only - cannot assign or review tasks)."),
    ("Company", "Posts internships, manages students and supervisors, assigns "
     "tasks (with mandatory intern + supervisor), requests completion, "
     "uploads certificates. Enters attendance via Intern Attendance -> "
     "PIN verify -> supervisor view."),
    ("Supervisor", "Supervisor view at /company/supervisor/<id>/...: marks "
     "attendance for their own assigned interns, analytics/reports with "
     "CSV/XLSX/PDF export, approves/rejects their task submissions."),
    ("Student", "Applies to internships, selects a mentor, works on tasks, "
     "logs progress, uploads documents, views own attendance/certificate."),
]

TEST_RESULTS = [
    ("manage.py check", "System check identified no issues (0 silenced)"),
    ("manage.py test", "Ran 114 tests ... OK (all 14 apps)"),
    ("Smoke check", "All portal pages return 200 incl. supervisor view "
     "pages under /company/supervisor/<id>/; company PIN verify flow works "
     "(correct PIN -> students list, exit -> 403 on next access, wrong PIN "
     "rejected); removed /supervisor/dashboard/ returns 404; faculty "
     "/faculty/tasks/ view-only"),
    ("DB migrations", "5 new migrations: accounts.0002 (SUPERVISOR role), "
     "internships.0002 (CompanySupervisor.user + SupervisorAssignment), "
     "internships.0003 (CompanySupervisor.pin), tasks.0002 (Task.supervisor), "
     "attendance.0002 (marked_by/supervisor)"),
]

FILES_MODIFIED = [
    "accounts/models.py - Role.SUPERVISOR; get_profile/display_name handle "
    "supervisor_profile",
    "accounts/decorators.py - supervisor_required + SupervisorRequiredMixin; "
    "get_role_dashboard_url() sends supervisors to supervisors:dashboard",
    "accounts/forms.py - SupervisorAuthenticationForm; accounts/views.py - "
    "SupervisorLoginView; accounts/urls.py - /supervisor/login/",
    "accounts/factories.py - create_supervisor(); seed_demo.py - supervisor "
    "accounts, assignments, marked attendance (--force flag)",
    "internships/models.py - CompanySupervisor.user (OneToOne); "
    "SupervisorAssignment model",
    "internships/services.py - assign_supervisor() service",
    "tasks/models.py - Task.supervisor FK; tasks/services.py - create_task "
    "accepts supervisor",
    "attendance/ - Attendance.supervisor + marked_by; attendance/services.py "
    "- mark_attendance accepts marked_by/supervisor; attendance/reports.py - "
    "10 report types; attendance/analytics.py - intern/supervisor analytics",
    "supervisors/ - access.py (PIN session + supervisor_template_required "
    "decorator), context_processors.py, views (dashboard, students, "
    "attendance, analytics, reports + CSV/XLSX/PDF export, tasks, progress, "
    "notifications), urls (app_name, /company/supervisor/<id>/), tests",
    "companies/ - attendance_select + attendance_exit (PIN verify/exit), "
    "SupervisorVerifyForm, /company/attendance/ URLs; task_assign requires "
    "intern + supervisor; student_assign_supervisor view",
    "internwebsite/urls.py - company/supervisor/ mounted before company/",
    "faculty/ - removed task_assign/task_review views, urls, forms, template; "
    "tasks.html now view-only",
    "templates/supervisors/ - dashboard, students, attendance, analytics, "
    "reports, tasks, progress, notifications; partials/sidebar.html - "
    "Intern Attendance + Supervisor View nav blocks",
    "accounts/home.html - Supervisor portal login card",
    "README.md - five portals + PIN-verified Intern Attendance flow "
    "documented",
]


def build_story():
    story = []
    story.append(Paragraph("Internship Management System", title))
    story.append(Paragraph(
        "Student Lifecycle - Step-by-Step Guide (how a student is created, "
        "applies, gets approved, and all data interactions)", subtitle))
    story.append(Paragraph("Introduction", h1))
    story.append(Paragraph(
        "The platform connects Colleges, Faculty/Mentors, Companies, "
        "Supervisors and Students. A student enters the system through the "
        "College, then moves through application, approval, mentor "
        "assignment, supervisor assignment, attendance, task and progress "
        "tracking, and finally certification. This document explains every "
        "step, who does what, and how the data is calculated. "
        "Demo credentials: all portal accounts use password Demo@12345 "
        "(admin superuser: admin / Admin@12345).", body))
    for name, lines in STEPS:
        story.append(Paragraph(name, h2))
        for line in lines:
            story.append(Paragraph(line, bullet, bulletText="-"))
    story.append(Paragraph("Role-Based Access Control", h1))
    for role, desc in ROLES:
        story.append(Paragraph(
            f"<b>{role}</b> - {desc}", bullet, bulletText="&bull;"))
    story.append(Paragraph("Verification Summary (Deliverable 6)", h1))
    t = Table(
        [["Check", "Result"]] + [[Paragraph(f"<b>{a}</b>", body),
                                  Paragraph(b, body)] for a, b in TEST_RESULTS],
        colWidths=[70 * mm, 110 * mm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F2F6FA")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Files / Components Changed", h2))
    for line in FILES_MODIFIED:
        story.append(Paragraph(line, bullet, bulletText="-"))
    return story


def main():
    doc = SimpleDocTemplate(
        OUT_PATH, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Internship Lifecycle Guide",
        author="Internship Management System",
    )
    doc.build(build_story())
    print("Wrote", OUT_PATH)


if __name__ == "__main__":
    main()
