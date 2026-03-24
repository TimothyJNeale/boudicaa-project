# SDS 3.2 — Profile and account management views
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from ..forms import AccountDeletionForm, UserProfileForm


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
