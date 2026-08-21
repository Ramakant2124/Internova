document.addEventListener("DOMContentLoaded", function () {
    // Mobile sidebar toggle
    var sidebarToggleBtn = document.querySelector('[data-sidebar-toggle]');
    if (!sidebarToggleBtn) {
        sidebarToggleBtn = document.querySelector('.sidebar-toggle');
    }
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener("click", function (e) {
            e.preventDefault();
            document.body.classList.toggle("sidebar-open");
        });
    }

    // Click on backdrop closes the mobile sidebar
    var backdrop = document.querySelector(".sidebar-backdrop");
    if (backdrop) {
        backdrop.addEventListener("click", function () {
            document.body.classList.remove("sidebar-open");
        });
    }

    // Autodismiss alert messages after 6 seconds
    var alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(function (alertEl) {
        setTimeout(function () {
            var closeBtn = alertEl.querySelector(".btn-close");
            if (closeBtn) {
                var dismissEvent = new bootstrap.Alert(alertEl);
                dismissEvent.close();
            }
        }, 6000);
    });
});
