# SDS 4.3 — Inbox views
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from ..forms import InboxForm
from ..models import Action, Area, InboxItem, Priority, Project
from .mixins import UserScopedMixin


class InboxListView(UserScopedMixin, ListView):
    model = InboxItem
    template_name = 'gtd/inbox/list.html'
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        return super().get_queryset().filter(processed_at__isnull=True)


class InboxCreateView(UserScopedMixin, CreateView):
    model = InboxItem
    form_class = InboxForm
    template_name = 'gtd/inbox/add.html'
    success_url = '/gtd/inbox/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


@login_required
@require_POST
def quick_capture(request: HttpRequest) -> JsonResponse:
    """AJAX/htmx POST for quick inbox capture."""
    form = InboxForm(request.POST, user=request.user)
    if form.is_valid():
        form.save()
        inbox_count = InboxItem.objects.filter(
            user=request.user, processed_at__isnull=True,
        ).count()
        response = JsonResponse({'status': 'ok'})
        response['X-Inbox-Count'] = str(inbox_count)
        return response
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@login_required
def inbox_process(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    """Conveyor belt processing view. SDS 4.3."""
    if pk:
        inbox_item = get_object_or_404(
            InboxItem, pk=pk, user=request.user, processed_at__isnull=True,
        )
    else:
        inbox_item = _get_next_unprocessed(request.user)

    if not inbox_item:
        if request.htmx:
            return render(request, 'gtd/partials/inbox_empty.html')
        return render(request, 'gtd/inbox/process.html', {'inbox_item': None})

    template = 'gtd/partials/inbox_process_item.html' if request.htmx else 'gtd/inbox/process.html'
    return render(request, template, {'inbox_item': inbox_item})


# Alias for URL routing
InboxProcessView = inbox_process


class InboxProcessedView(UserScopedMixin, ListView):
    model = InboxItem
    template_name = 'gtd/inbox/processed.html'
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        return super().get_queryset().filter(processed_at__isnull=False)


class InboxProcessedDetailView(UserScopedMixin, DetailView):
    model = InboxItem
    template_name = 'gtd/inbox/processed_detail.html'


@login_required
@require_POST
def convert_inbox_to_action(request: HttpRequest, pk: int) -> HttpResponse:
    """Convert inbox item to action. SDS 3.3."""
    inbox_item = get_object_or_404(InboxItem, pk=pk, user=request.user)
    default_project = Project.objects.filter(user=request.user, is_protected=True).first()
    default_area = Area.objects.filter(user=request.user).first()
    default_priority = Priority.objects.first()

    Action.objects.create(
        name=inbox_item.item[:70] if inbox_item.item else 'Untitled',
        project=default_project,
        area=default_area,
        priority=default_priority,
        user=request.user,
    )
    inbox_item.mark_processed(note='Converted to action')

    next_item = _get_next_unprocessed(request.user, current_pk=pk)
    if next_item:
        return redirect('inbox_process_item', pk=next_item.pk)
    return redirect('inbox_process')


@login_required
@require_POST
def convert_inbox_to_project(request: HttpRequest, pk: int) -> HttpResponse:
    """Convert inbox item to project. SDS 3.3."""
    inbox_item = get_object_or_404(InboxItem, pk=pk, user=request.user)
    default_area = Area.objects.filter(user=request.user).first()
    from ..models import Status
    default_status = Status.objects.get(name='PROPOSED')

    Project.objects.create(
        name=inbox_item.item[:70] if inbox_item.item else 'Untitled',
        area=default_area,
        status=default_status,
        user=request.user,
    )
    inbox_item.mark_processed(note='Converted to project')

    next_item = _get_next_unprocessed(request.user, current_pk=pk)
    if next_item:
        return redirect('inbox_process_item', pk=next_item.pk)
    return redirect('inbox_process')


@login_required
@require_POST
def archive_inbox_item(request: HttpRequest, pk: int) -> HttpResponse:
    """Archive inbox item as not actionable. SDS 3.3."""
    inbox_item = get_object_or_404(InboxItem, pk=pk, user=request.user)
    inbox_item.mark_processed(note='Archived — not actionable')

    next_item = _get_next_unprocessed(request.user, current_pk=pk)
    if next_item:
        return redirect('inbox_process_item', pk=next_item.pk)
    return redirect('inbox_process')


@login_required
@require_POST
def delete_inbox_item(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete inbox item. SDS 3.3."""
    inbox_item = get_object_or_404(InboxItem, pk=pk, user=request.user)
    inbox_item.delete()

    next_item = _get_next_unprocessed(request.user)
    if next_item:
        return redirect('inbox_process_item', pk=next_item.pk)
    return redirect('inbox_process')


def _get_next_unprocessed(user, current_pk: int | None = None):
    """Get the next unprocessed item (oldest first), excluding current."""
    qs = InboxItem.objects.filter(user=user, processed_at__isnull=True)
    if current_pk:
        qs = qs.exclude(pk=current_pk)
    return qs.order_by('created_at').first()
