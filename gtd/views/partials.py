# SDS 3.2 — Profile and account management views
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from ..forms import AccountDeletionForm, UserProfileForm
from ..models import UserProfile


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'gtd/profile/profile.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['form'] = UserProfileForm(instance=self.request.user)
        context['profile'] = getattr(self.request.user, 'userprofile', None)
        return context

    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
        return render(request, self.template_name, {
            'form': form,
            'profile': getattr(request.user, 'userprofile', None),
        })


@login_required
def update_preferences(request: HttpRequest) -> HttpResponse:
    """Update user preferences and redirect to profile. SDS 3.2."""
    if request.method == 'POST':
        profile = UserProfile.objects.get(user=request.user)
        pref = request.POST.get('preferred_project_view')
        if pref in ('board', 'list'):
            profile.preferred_project_view = pref
            profile.save(update_fields=['preferred_project_view'])
    return redirect('profile')


@login_required
def regenerate_api_key(request: HttpRequest) -> HttpResponse:
    """Regenerate API key and redirect to profile. SDS 3.2."""
    if request.method == 'POST':
        profile = UserProfile.objects.get(user=request.user)
        profile.generate_api_key()
    return redirect('profile')


@login_required
def account_delete_confirm(request: HttpRequest) -> HttpResponse:
    """Account deletion confirmation. SDS 3.2."""
    if request.method == 'POST':
        form = AccountDeletionForm(request.POST, user=request.user)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            return render(request, 'gtd/profile/account_deleted.html')
    else:
        form = AccountDeletionForm(user=request.user)
    return render(request, 'gtd/profile/account_delete_confirm.html', {'form': form})
