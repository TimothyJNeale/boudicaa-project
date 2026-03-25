# SDS 3.1 — Authentication and public views
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def public_home(request: HttpRequest) -> HttpResponse:
    """Marketing/landing page."""
    if request.user.is_authenticated:
        return redirect('today')
    return render(request, 'public_home.html')


def signupuser(request: HttpRequest) -> HttpResponse:
    """User registration. Blocked by PROTECTED_MODE."""
    if getattr(settings, 'PROTECTED_MODE', False):
        return render(request, 'boudicaa/signupuser.html', {
            'error': 'Registration is currently closed.',
        })

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('today')
        return render(request, 'boudicaa/signupuser.html', {'form': form})

    return render(request, 'boudicaa/signupuser.html', {'form': UserCreationForm()})


def loginuser(request: HttpRequest) -> HttpResponse:
    """Login page."""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('today')
        return render(request, 'boudicaa/loginuser.html', {
            'error': 'Invalid username or password.',
        })
    return render(request, 'boudicaa/loginuser.html')


def logoutuser(request: HttpRequest) -> HttpResponse:
    """Logout. POST-only."""
    if request.method == 'POST':
        logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


def verification_sent(request: HttpRequest) -> HttpResponse:
    """Stub — email verification not implemented in v3."""
    return render(request, 'boudicaa/verification_sent.html')


def verify_email(request: HttpRequest, token: str) -> HttpResponse:
    """Stub — email verification not implemented in v3."""
    return render(request, 'boudicaa/verification_sent.html')


def resend_verification(request: HttpRequest) -> HttpResponse:
    """Stub — email verification not implemented in v3."""
    return render(request, 'boudicaa/resend_verification.html')
