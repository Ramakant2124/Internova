"""URLs for certificates."""
from django.urls import path

from . import views

app_name = "certificates"

urlpatterns = [
    path("verify/", views.verify_page, name="verify_page"),
    path("verify/<str:number>/", views.verify_detail, name="verify_detail"),
]
