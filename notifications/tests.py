# notifications module

from django.test import TestCase
from django.urls import reverse

from accounts.factories import create_college, create_student
from notifications.models import Notification
from notifications.services import create_notification, unread_count


class NotificationTest(TestCase):
    def setUp(self):
        self.college = create_college()
        self.student = create_student(self.college)

    def test_create_notification(self):
        notification = create_notification(
            self.student.user, "Hello", "Body", related_url="/student/dashboard/"
        )
        self.assertEqual(self.student.user.notifications.count(), 1)
        self.assertEqual(unread_count(self.student.user), 1)
        self.assertEqual(notification.related_url, "/student/dashboard/")

    def test_mark_read(self):
        notification = create_notification(self.student.user, "Hello")
        notification.mark_read()
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(unread_count(self.student.user), 0)

    def test_mark_all_read_and_clear(self):
        create_notification(self.student.user, "A")
        create_notification(self.student.user, "B")
        self.client.force_login(self.student.user)
        response = self.client.post(reverse("notifications:mark_all_read"))
        self.assertRedirects(response, reverse("notifications:list"))
        self.assertEqual(
            self.student.user.notifications.filter(is_read=False).count(), 0
        )
        response = self.client.post(reverse("notifications:clear_all"))
        self.assertRedirects(response, reverse("notifications:list"))
        self.assertEqual(self.student.user.notifications.count(), 0)

    def test_list_requires_login(self):
        response = self.client.get(reverse("notifications:list"))
        self.assertRedirects(response, "/home/?next=/notifications/")
