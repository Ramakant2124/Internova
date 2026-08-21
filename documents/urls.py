"""URLs for documents."""
from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("<int:pk>/download/", views.download_document, name="download"),
]
