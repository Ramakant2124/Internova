"""Seed the database with realistic demo data for all four portals.

Creates:
  - 1 college admin (college_admin)
  - 3 faculty members (faculty1 .. faculty3)
  - 5 companies (company1 .. company5)
  - 20 students (student1 .. student20)
  - internships, applications, allocations, faculty mentors, attendance,
    work logs, weekly progress, tasks, documents, certificates, feedback,
    evaluations and notifications.

All accounts use the password: Demo@12345
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    CollegeProfile,
    CompanyProfile,
    FacultyProfile,
    StudentProfile,
)
from attendance.models import Attendance, AttendanceStatus
from certificates.services import (
    request_verification,
    upload_certificate,
    verify_certificate,
)
from documents.models import Document, DocumentType
from internships.models import (
    AllocationStatus,
    ApplicationStatus,
    CompanySupervisor,
    FacultyAssignment,
    Internship,
    InternshipAllocation,
    InternshipStatus,
    InternshipType,
    SupervisorAssignment,
)
from internships.services import (
    allocate_internship,
    assign_faculty,
    assign_supervisor,
    review_application,
)
from notifications.services import create_notification
from progress.models import (
    DailyWorkLog,
    Feedback,
    PerformanceEvaluation,
    ReviewStatus,
    WeeklyProgress,
)
from tasks.models import Task, TaskPriority

PASSWORD = "Demo@12345"

DEPARTMENTS = ["Computer Science", "Electronics", "Mechanical", "Civil", "IT"]
COMPANIES = [
    ("TechNova Solutions", "TN", "Software", "Pune"),
    ("InfraBuild Industries", "IB", "Construction", "Mumbai"),
    ("MediCore Labs", "MC", "Healthcare", "Bengaluru"),
    ("EcoEnergy Pvt Ltd", "EE", "Renewable Energy", "Delhi"),
    ("FinEdge Analytics", "FE", "Finance", "Hyderabad"),
]
INTERNSHIPS = [
    ("Software Development Intern", "Develop web applications and REST APIs with the product team.", "Python, Django, JavaScript", 25000),
    ("Civil Engineering Intern", "Assist with site supervision, drafting and project documentation.", "AutoCAD, MS Project", 15000),
    ("Biomedical Research Intern", "Support laboratory research and clinical data analysis.", "Lab Skills, Statistics", 18000),
    ("Solar Energy Systems Intern", "Design and test solar installations and energy audits.", "Electrical, PV Systems", 20000),
    ("Data Analytics Intern", "Build dashboards and analyse financial datasets.", "Python, SQL, Power BI", 22000),
]


class Command(BaseCommand):
    help = "Seed the database with realistic demo data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing data before seeding.",
        )

    def _create_user(self, username, role, email, **extra):
        user = get_user_model()(username=username, email=email, role=role, **extra)
        user.set_password(PASSWORD)
        user.save()
        return user

    def _wipe(self):
        from django.apps import apps

        for model in reversed(apps.get_models()):
            if model._meta.app_label == "auth":
                continue
            try:
                model.objects.all().delete()
            except Exception:
                pass

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        today = timezone.localdate()
        if options["force"]:
            self.stdout.write("Deleting existing data...")
            self._wipe()
        if User.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Database already has users. Use --force to re-seed."
            ))
            return

        # ------------------------------------------------------------- college
        college_user = self._create_user(
            "college_admin", User.Role.COLLEGE, "college@example.edu",
            first_name="State", last_name="Admin", is_staff=True, is_superuser=True,
        )
        college = CollegeProfile.objects.create(
            user=college_user,
            college_name="State Institute of Technology",
            college_code="SIT",
            city="Pune",
            state="Maharashtra",
            contact_email="college@example.edu",
            contact_phone="+91-9876500001",
            website="https://example.edu",
        )

        # ------------------------------------------------------------- faculty
        faculty = []
        for i in range(1, 4):
            user = self._create_user(
                f"faculty{i}", User.Role.FACULTY,
                f"faculty{i}@example.edu",
                first_name="Prof", last_name=f"Faculty{i}",
            )
            faculty.append(FacultyProfile.objects.create(
                user=user,
                employee_id=f"EMP00{i}",
                full_name=f"Prof. Faculty {i}",
                department=DEPARTMENTS[i - 1],
                designation="Assistant Professor",
                phone=f"+91-98765001{i}",
                email=f"faculty{i}@example.edu",
                college=college,
                specialization=DEPARTMENTS[i - 1] + " Engineering",
            ))

        # ------------------------------------------------------------ companies
        companies = []
        supervisors = []
        for i, (name, code, industry, city) in enumerate(COMPANIES, start=1):
            user = self._create_user(
                f"company{i}", User.Role.COMPANY,
                f"hr@company{i}.example",
                first_name=f"HR{i}",
            )
            company = CompanyProfile.objects.create(
                user=user,
                company_name=name,
                company_code=code,
                industry=industry,
                website=f"https://www.company{i}.example",
                email=f"hr@company{i}.example",
                phone=f"+91-98765{i}000",
                address=f"Tower {i}, Business Park",
                city=city,
                state="India",
            )
            supervisor_user = self._create_user(
                f"supervisor{i}", User.Role.SUPERVISOR,
                f"supervisor{i}@company{i}.example",
                first_name="Supervisor", last_name=str(i),
            )
            supervisor = CompanySupervisor.objects.create(
                company=company,
                user=supervisor_user,
                name=f"Supervisor {i}",
                designation="Team Lead",
                email=f"supervisor{i}@company{i}.example",
                phone=f"+91-98765{i}111",
            )
            supervisor.set_pin("1234")
            supervisor.save(update_fields=["pin"])
            supervisors.append(supervisor)
            companies.append(company)

        # ------------------------------------------------------------- students
        students = []
        for i in range(1, 21):
            user = self._create_user(
                f"student{i}", User.Role.STUDENT,
                f"student{i}@student.example",
                first_name="Student", last_name=str(i),
            )
            students.append(StudentProfile.objects.create(
                user=user,
                student_id=f"SIT2026{i:03d}",
                full_name=f"Student {i}",
                email=f"student{i}@student.example",
                phone=f"+91-9876{i:04d}",
                department=random.choice(DEPARTMENTS),
                course="B.Tech",
                year=random.choice([2, 3, 4]),
                semester=random.choice([4, 6, 8]),
                college=college,
                city="Pune",
                state="Maharashtra",
                skills="Python, SQL, Communication",
                cgpa=round(random.uniform(6.5, 9.4), 2),
            ))

        # ---------------------------------------------------------- internships
        internship_objs = []
        for i, (title, desc, skills, stipend) in enumerate(INTERNSHIPS, start=1):
            internship = Internship.objects.create(
                title=title,
                description=desc,
                company=companies[i - 1],
                location=companies[i - 1].city,
                internship_type=random.choice(
                    [InternshipType.ONSITE, InternshipType.REMOTE, InternshipType.HYBRID]
                ),
                skills_required=skills,
                stipend=stipend,
                duration="3 months",
                available_positions=5,
                status=InternshipStatus.APPLIED,
                created_by=college_user,
            )
            internship_objs.append(internship)

        # statuses: 1-2 APPROVED, 3-4 ACTIVE, 5 COMPLETED
        for internship in internship_objs[:2]:
            internship.transition_to(InternshipStatus.APPROVED, changed_by=college_user)
        internship3 = internship_objs[2]
        internship3.start_date = today - timedelta(days=30)
        internship3.end_date = today + timedelta(days=30)
        internship3.transition_to(InternshipStatus.ALLOCATED, changed_by=college_user)
        internship3.transition_to(InternshipStatus.ACTIVE, changed_by=college_user)
        internship4 = internship_objs[3]
        internship4.start_date = today - timedelta(days=15)
        internship4.end_date = today + timedelta(days=45)
        internship4.transition_to(InternshipStatus.ALLOCATED, changed_by=college_user)
        internship4.transition_to(InternshipStatus.ACTIVE, changed_by=college_user)
        internship5 = internship_objs[4]
        internship5.start_date = today - timedelta(days=90)
        internship5.end_date = today - timedelta(days=5)
        internship5.transition_to(InternshipStatus.ALLOCATED, changed_by=college_user)
        internship5.transition_to(InternshipStatus.ACTIVE, changed_by=college_user)
        internship5.transition_to(
            InternshipStatus.COMPLETED, changed_by=college_user, reason="Internship completed"
        )

        # --------------------------------------------------------- applications
        # 1-10 applied to internship1, 11-16 to internship2, 17-20 to internship5
        apps1 = [s for s in students[:10]]
        for s in apps1:
            from internships.services import apply_to_internship
            apply_to_internship(s, internship_objs[0], "I am enthusiastic about this role.")
        for i, s in enumerate(students[10:16]):
            from internships.services import apply_to_internship
            apply_to_internship(s, internship_objs[1], "I bring strong fundamentals and teamwork.")
            if i < 2:
                review_application(s.applications.get(internship=internship_objs[1]),
                                   approved=False, reviewer=college_user, comments="Role filled.")
        for s in students[16:20]:
            from internships.services import apply_to_internship
            apply_to_internship(s, internship_objs[4], "I am keen to join after completion.")

        # ---------------------------------------------------------- allocations
        # internship3: students 1-4 active; internship4: 5-8 active;
        # internship5: 9-10 completed; internship1: 11-12 active (start future)
        alloc_specs = [
            (internship_objs[2], students[0:4], today - timedelta(days=30), today + timedelta(days=30)),
            (internship_objs[3], students[4:8], today - timedelta(days=15), today + timedelta(days=45)),
            (internship_objs[4], students[8:10], today - timedelta(days=90), today - timedelta(days=5)),
            (internship_objs[0], students[10:12], today + timedelta(days=7), today + timedelta(days=97)),
        ]
        allocations = []
        for internship, group, start, end in alloc_specs:
            for s in group:
                alloc = allocate_internship(
                    s, internship, college_user, start_date=start, end_date=end
                )
                allocations.append(alloc)
        # mark completed internship5 allocations as COMPLETED
        InternshipAllocation.objects.filter(
            internship=internship_objs[4], status=AllocationStatus.ACTIVE
        ).update(status=AllocationStatus.COMPLETED)

        # ------------------------------------------------- faculty assignments
        for s in students[0:4]:
            assign_faculty(faculty[0], s, internship_objs[2], college_user)
        for s in students[4:8]:
            assign_faculty(faculty[1], s, internship_objs[3], college_user)
        for s in students[8:10]:
            assign_faculty(faculty[2], s, internship_objs[4], college_user)
        for s in students[10:12]:
            assign_faculty(faculty[2], s, internship_objs[0], college_user)

        # ------------------------------------------- supervisor assignments
        # each company's supervisor is linked to the students allocated to that
        # company's active internships.
        for alloc in allocations:
            if alloc.internship.status != InternshipStatus.ACTIVE:
                continue
            supervisor = supervisors[companies.index(alloc.internship.company)]
            assign_supervisor(supervisor, alloc.student, alloc.internship, alloc.internship.company.user)

        # ---------------------------------------------------------- attendance
        for alloc in allocations:
            if alloc.internship.status != InternshipStatus.ACTIVE:
                continue
            supervisor = supervisors[companies.index(alloc.internship.company)]
            start = alloc.start_date or today
            for offset in range(0, min(20, (today - start).days + 1)):
                day = start + timedelta(days=offset)
                if day.weekday() >= 5:
                    continue
                roll = random.random()
                if roll < 0.88:
                    status = AttendanceStatus.PRESENT
                elif roll < 0.92:
                    status = AttendanceStatus.HALF_DAY
                elif roll < 0.96:
                    status = AttendanceStatus.LEAVE
                else:
                    status = AttendanceStatus.ABSENT
                Attendance.objects.get_or_create(
                    student=alloc.student,
                    internship=alloc.internship,
                    date=day,
                    defaults={
                        "status": status,
                        "check_in": timezone.datetime(2026, 1, 1, 9, 30).time(),
                        "check_out": timezone.datetime(2026, 1, 1, 17, 30).time(),
                        "marked_by": supervisor.user,
                        "supervisor": supervisor,
                    },
                )

        # ------------------------------------- work logs + weekly progress
        log_titles = [
            "Completed assigned module and wrote unit tests.",
            "Attended team standup and pair-programmed on the API.",
            "Documented the workflow and prepared a short demo.",
            "Fixed reported bugs and updated the tracker.",
            "Researched requirements and drafted implementation notes.",
        ]
        for alloc in allocations:
            if alloc.internship.status != InternshipStatus.ACTIVE:
                continue
            for k in range(5):
                day = (alloc.start_date or today) + timedelta(days=k * 3 + 1)
                DailyWorkLog.objects.create(
                    student=alloc.student,
                    internship=alloc.internship,
                    date=day,
                    work_description=random.choice(log_titles),
                    hours_worked=random.choice([4, 6, 8]),
                    status=ReviewStatus.APPROVED if k < 4 else ReviewStatus.PENDING,
                    review_comments="Good work, keep it up!" if k < 4 else "",
                )
            for k in range(3):
                week_start = (alloc.start_date or today) + timedelta(days=k * 7)
                WeeklyProgress.objects.create(
                    student=alloc.student,
                    internship=alloc.internship,
                    week_start=week_start,
                    week_end=week_start + timedelta(days=6),
                    summary=f"Week {k + 1}: progressed steadily and met goals.",
                    progress_percentage=random.randint(35, 90),
                    status=ReviewStatus.APPROVED if k < 2 else ReviewStatus.PENDING,
                    review_comments="On track." if k < 2 else "",
                )

        # ---------------------------------------------------------------- tasks
        task_titles = [
            "Implement login page",
            "Fix pagination bug",
            "Write API docs",
            "Prepare test report",
            "Refactor database queries",
        ]
        for i, s in enumerate(students[0:8]):
            internship = allocations[i // 2].internship
            supervisor = supervisors[companies.index(internship.company)]
            for j in range(2):
                Task.objects.create(
                    title=task_titles[(i + j) % len(task_titles)],
                    description="Complete the task and submit for review.",
                    student=s,
                    internship=internship,
                    assigned_by=internship.company.user,
                    supervisor=supervisor,
                    start_date=today - timedelta(days=3),
                    due_date=today + timedelta(days=7),
                    priority=random.choice(
                        [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH]
                    ),
                    status="SUBMITTED" if j == 1 else random.choice(["PENDING", "IN_PROGRESS"]),
                    progress_percentage=random.randint(0, 100),
                    student_comments="Submitted my work, please review." if j == 1 else "",
                )

        # ------------------------------------------------------------ documents
        doc_titles = {
            DocumentType.OFFER_LETTER: "Offer Letter",
            DocumentType.JOINING_LETTER: "Joining Letter",
            DocumentType.INTERNSHIP_AGREEMENT: "Internship Agreement",
        }
        for s in students[0:4]:
            for dtype, title in list(doc_titles.items())[:2]:
                Document.objects.create(
                    student=s,
                    internship=allocations[0].internship,
                    document_type=dtype,
                    title=title,
                    file=ContentFile(b"%PDF-1.4 demo document", name="demo.pdf"),
                    status="APPROVED",
                    verification_comments="Verified by college.",
                )
        Document.objects.create(
            student=students[0],
            internship=allocations[0].internship,
            document_type=DocumentType.OTHER,
            title="Demo Pending Document",
            file=ContentFile(b"%PDF-1.4 pending document", name="pending.pdf"),
            status="PENDING",
        )

        # ----------------------------------------------------------- certificates
        for s in students[8:10]:
            cert = upload_certificate(
                s, internship_objs[4],
                ContentFile(b"%PDF-1.4 demo certificate", name="certificate.pdf"),
                issue_date=today - timedelta(days=2),
            )
            request_verification(cert, cert.student.user)
            verify_certificate(cert, college_user, True, "All checks passed.")
        for s in students[0:2]:
            upload_certificate(
                s, internship_objs[2],
                ContentFile(b"%PDF-1.4 demo certificate", name="certificate.pdf"),
            )

        # ---------------------------------------------- feedback + evaluations
        feedback_types = [Feedback.FeedbackType.FACULTY, Feedback.FeedbackType.COMPANY]
        for s in students[0:8]:
            for ft in feedback_types:
                Feedback.objects.create(
                    student=s,
                    internship=allocations[0].internship,
                    given_by=college_user,
                    feedback_type=ft,
                    rating=random.randint(3, 5),
                    comments="Great progress, keep up the good work.",
                )
        for i, s in enumerate(students[0:4]):
            PerformanceEvaluation.objects.create(
                student=s,
                internship=internship_objs[2],
                faculty=faculty[0],
                technical_skills=4, communication=4, professionalism=5,
                task_completion=4, punctuality=4, teamwork=5,
                comments="Strong performer.",
            )

        # --------------------------------------------------------- notifications
        for s in students:
            create_notification(
                recipient=s.user,
                title="Welcome to InternPortal",
                message="Your account is ready. Complete your profile and apply for internships.",
                notification_type="GENERAL",
                related_url="/student/profile/",
            )
        create_notification(
            recipient=college_user,
            title="Demo data ready",
            message="Seed data loaded successfully. Review pending approvals on the dashboard.",
            notification_type="GENERAL",
            related_url="/college/approvals/",
        )

        # ------------------------------------------------------------- summary
        self.stdout.write(self.style.SUCCESS("Demo data created successfully!\n"))
        self.stdout.write(f"All passwords: {PASSWORD}")
        self.stdout.write("Logins:")
        self.stdout.write(f"  College:   username=college_admin")
        for i in range(1, 4):
            self.stdout.write(f"  Faculty{i}: username=faculty{i}")
        for i in range(1, 6):
            self.stdout.write(f"  Company{i}: username=company{i}")
        for i in range(1, 6):
            self.stdout.write(f"  Supervisor{i}: username=supervisor{i}")
        for i in range(1, 21):
            self.stdout.write(f"  Student{i}: username=student{i}")
