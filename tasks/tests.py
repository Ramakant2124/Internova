# tasks module

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.factories import (
    create_college,
    create_company,
    create_faculty,
    create_internship,
    create_student,
)
from notifications.models import Notification
from tasks.models import Task, TaskPriority, TaskStatus
from tasks.services import create_task, review_task


class TaskTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.company = create_company()
        self.faculty = create_faculty(self.college)
        self.student = create_student(self.college)
        self.internship = create_internship(self.company)

    def test_create_task_notifies_student(self):
        task = create_task(
            title="Build landing page",
            description="Use the existing template.",
            student=self.student,
            internship=self.internship,
            assigned_by=self.faculty.user,
            due_date=timezone.localdate() + timedelta(days=7),
            priority=TaskPriority.HIGH,
        )
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(self.student.tasks.count(), 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student.user, notification_type="TASK"
            ).exists()
        )

    def test_review_task_approve_sets_percentage(self):
        task = create_task(
            title="Fix bug",
            description="Investigate and fix.",
            student=self.student,
            internship=self.internship,
            assigned_by=self.faculty.user,
        )
        task.status = TaskStatus.SUBMITTED
        task.save(update_fields=["status"])
        review_task(task, True, self.faculty.user, "Great work.")
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.APPROVED)
        self.assertEqual(task.progress_percentage, 100)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student.user, notification_type="TASK_APPROVAL"
            ).exists()
        )

    def test_review_task_reject(self):
        task = create_task(
            title="Fix bug",
            description="Investigate and fix.",
            student=self.student,
            internship=self.internship,
            assigned_by=self.faculty.user,
        )
        review_task(task, False, self.faculty.user, "Needs changes.")
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.REJECTED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student.user, notification_type="TASK_REJECTION"
            ).exists()
        )

    def test_is_overdue(self):
        task = create_task(
            title="Old task",
            description="Long overdue.",
            student=self.student,
            internship=self.internship,
            assigned_by=self.faculty.user,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        self.assertTrue(task.is_overdue)
        task.status = TaskStatus.COMPLETED
        self.assertFalse(task.is_overdue)
