# SDS 3.7 — Configuration views (Domains, Areas, Contexts)
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..forms import AreaForm, ContextForm, DomainForm
from ..models import Area, Context, Domain
from .mixins import UserScopedMixin


# --- Domains ---

class DomainListView(UserScopedMixin, ListView):
    model = Domain
    template_name = 'gtd/config/domain_list.html'


class DomainCreateView(UserScopedMixin, CreateView):
    model = Domain
    form_class = DomainForm
    template_name = 'gtd/config/domain_form.html'
    success_url = reverse_lazy('domain_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class DomainUpdateView(UserScopedMixin, UpdateView):
    model = Domain
    form_class = DomainForm
    template_name = 'gtd/config/domain_form.html'
    success_url = reverse_lazy('domain_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class DomainDeleteView(UserScopedMixin, DeleteView):
    model = Domain
    template_name = 'gtd/config/domain_confirm_delete.html'
    success_url = reverse_lazy('domain_list')


# --- Areas ---

class AreaListView(UserScopedMixin, ListView):
    model = Area
    template_name = 'gtd/config/area_list.html'


class AreaCreateView(UserScopedMixin, CreateView):
    model = Area
    form_class = AreaForm
    template_name = 'gtd/config/area_form.html'
    success_url = reverse_lazy('area_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class AreaUpdateView(UserScopedMixin, UpdateView):
    model = Area
    form_class = AreaForm
    template_name = 'gtd/config/area_form.html'
    success_url = reverse_lazy('area_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class AreaDeleteView(UserScopedMixin, DeleteView):
    model = Area
    template_name = 'gtd/config/area_confirm_delete.html'
    success_url = reverse_lazy('area_list')


# --- Contexts ---

class ContextListView(UserScopedMixin, ListView):
    model = Context
    template_name = 'gtd/config/context_list.html'


class ContextCreateView(UserScopedMixin, CreateView):
    model = Context
    form_class = ContextForm
    template_name = 'gtd/config/context_form.html'
    success_url = reverse_lazy('context_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ContextUpdateView(UserScopedMixin, UpdateView):
    model = Context
    form_class = ContextForm
    template_name = 'gtd/config/context_form.html'
    success_url = reverse_lazy('context_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ContextDeleteView(UserScopedMixin, DeleteView):
    model = Context
    template_name = 'gtd/config/context_confirm_delete.html'
    success_url = reverse_lazy('context_list')
