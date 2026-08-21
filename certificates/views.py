"""Certificate views including the public verification page."""
from django.shortcuts import get_object_or_404, render

from .models import Certificate
from .services import validate_certificate_number


def verify_page(request):
    """Public lookup form for certificate verification."""
    return render(request, "certificates/verify.html")


def verify_detail(request, number):
    """Public certificate verification result page (no sensitive data)."""
    certificate = validate_certificate_number(number)
    return render(
        request,
        "certificates/verify_detail.html",
        {"certificate": certificate, "search_number": number},
    )
