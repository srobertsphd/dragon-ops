"""
Authentication views for login and logout functionality.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def login_view(request):
    """Unified login page for all user types (regular, staff, admin)"""
    if request.user.is_authenticated:
        return redirect("members:landing")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, "members/login.html")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                from django.utils.http import url_has_allowed_host_and_scheme

                if url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
            return redirect("members:landing")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "members/login.html")


def logout_view(request):
    """Logout view that redirects to login page"""
    logout(request)
    return redirect("members:login")
