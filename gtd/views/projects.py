# SDS 4.5 — Project views
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from django.utils import timezone

from ..forms import ActionQuickAddForm, ProjectForm
from ..models import Action, Project, Status
from .mixins import UserScopedMixin

# SDS 4.5 — Board view status groupings
STATUS_GROUPS = {
    'Proposed': ['PROPOSED'],
    'Someday': ['SOMEDAY'],
    'Queued': ['NEXT', 'WAITING', 'LONG'],
    'Active': ['IN ACTION', 'BACK BURNER'],
    'Paused': ['PAUSED', 'SUSPENDED'],
    'Done': ['COMPLETED', 'ABANDONED'],
}


class ProjectListView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        profile = getattr(self.request.user, 'userprofile', None)
        pref = profile.preferred_project_view if profile else 'board'
        if pref == 'list':
            return ['gtd/projects/list.html']
        return ['gtd/projects/board.html']

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        show_archived = self.request.GET.get('archived', '') == '1'

        projects = Project.objects.filter(user=user, is_protected=False)

        # Board context
        columns = []
        for group_name, statuses in STATUS_GROUPS.items():
            if group_name == 'Done' and not show_archived:
                continue
            column_projects = projects.filter(status__name__in=statuses)
            columns.append({
                'name': group_name,
                'statuses': statuses,
                'projects': column_projects,
            })

        context.update({
            'columns': columns,
            'projects': projects,
            'show_archived': show_archived,
        })
        return context


class ProjectCreateView(UserScopedMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'gtd/projects/form.html'
    success_url = '/gtd/projects/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ProjectDetailView(UserScopedMixin, DetailView):
    model = Project
    template_name = 'gtd/projects/detail.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['actions'] = Action.objects.filter(
            project=self.object, user=self.request.user,
        ).order_by('display_order', 'name')
        return context


class ProjectUpdateView(UserScopedMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'gtd/projects/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self) -> str:
        return f'/gtd/projects/{self.object.pk}/'


class ProjectSidePanelView(UserScopedMixin, DetailView):
    model = Project
    template_name = 'gtd/partials/project_side_panel.html'


class ProjectActionsView(UserScopedMixin, ListView):
    model = Action
    template_name = 'gtd/partials/project_action_list.html'

    def get_queryset(self):
        return Action.objects.filter(
            project_id=self.kwargs['pk'],
            user=self.request.user,
        ).order_by('display_order', 'name')


class ProjectActionAddView(LoginRequiredMixin, CreateView):
    model = Action
    form_class = ActionQuickAddForm
    template_name = 'gtd/partials/project_action_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project'] = get_object_or_404(
            Project, pk=self.kwargs['pk'], user=self.request.user,
        )
        return kwargs

    def get_success_url(self) -> str:
        return f'/gtd/projects/{self.kwargs["pk"]}/'


@login_required
@require_POST
def project_panel_save(request: HttpRequest, pk: int) -> HttpResponse:
    """Save project from side panel. SDS 4.5."""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    form = ProjectForm(request.POST, instance=project, user=request.user)
    if form.is_valid():
        form.save()
    return render(request, 'gtd/partials/project_side_panel.html', {
        'project': project,
        'form': form,
    })


@login_required
@require_POST
def project_action_reorder(request: HttpRequest, pk: int) -> JsonResponse:
    """Save drag-and-drop action order. SDS 4.5."""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    order = json.loads(request.body).get('order', [])
    for index, action_id in enumerate(order):
        Action.objects.filter(
            pk=action_id, project=project, user=request.user,
        ).update(display_order=index)
    return JsonResponse({'status': 'ok'})


@login_required
def complete_project(request: HttpRequest, pk: int) -> HttpResponse:
    """Complete a project. SDS 4.5/7.4."""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        if not project.can_complete_safely:
            return render(request, 'gtd/projects/complete_confirm.html', {
                'project': project,
                'error': 'Cannot complete: project has active sub-projects.',
            })
        action_handling = request.POST.get('action_handling', 'complete_all')
        incomplete = Action.objects.filter(project=project, ended_at__isnull=True)
        if action_handling == 'move_to_open':
            open_project = Project.objects.get(user=request.user, is_protected=True)
            incomplete.update(project=open_project)
        else:
            incomplete.update(ended_at=timezone.now())
        project.mark_complete('COMPLETED')
        return redirect('project_list')
    incomplete_count = Action.objects.filter(project=project, ended_at__isnull=True).count()
    return render(request, 'gtd/projects/complete_confirm.html', {
        'project': project,
        'incomplete_count': incomplete_count,
        'can_complete': project.can_complete_safely,
    })


@login_required
def abandon_project(request: HttpRequest, pk: int) -> HttpResponse:
    """Abandon a project. SDS 4.5/7.4."""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        if not project.can_complete_safely:
            return render(request, 'gtd/projects/abandon_confirm.html', {
                'project': project,
                'error': 'Cannot abandon: project has active sub-projects.',
            })
        action_handling = request.POST.get('action_handling', 'complete_all')
        incomplete = Action.objects.filter(project=project, ended_at__isnull=True)
        if action_handling == 'move_to_open':
            open_project = Project.objects.get(user=request.user, is_protected=True)
            incomplete.update(project=open_project)
        else:
            incomplete.update(ended_at=timezone.now())
        reason = request.POST.get('reason', '')
        if reason:
            project.notes = (project.notes or '') + f"\n\nABANDONED: {reason}"
            project.save(update_fields=['notes', 'updated_at'])
        project.mark_complete('ABANDONED')
        return redirect('project_list')
    incomplete_count = Action.objects.filter(project=project, ended_at__isnull=True).count()
    return render(request, 'gtd/projects/abandon_confirm.html', {
        'project': project,
        'incomplete_count': incomplete_count,
        'can_complete': project.can_complete_safely,
    })


@login_required
def reopen_project(request: HttpRequest, pk: int) -> HttpResponse:
    """Reopen a completed/abandoned project. SDS 4.5."""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        new_status = Status.objects.get(name='IN ACTION')
        project.status = new_status
        project.ended_at = None
        project.save(update_fields=['status', 'ended_at', 'updated_at'])
        return redirect('project_detail', pk=project.pk)
    return render(request, 'gtd/projects/reopen_confirm.html', {'project': project})
