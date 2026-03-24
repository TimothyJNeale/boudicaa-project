# SDS 7.4 — API viewsets
from datetime import date, timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gtd.models import (
    Action,
    Area,
    Context,
    Domain,
    InboxItem,
    Priority,
    Project,
    Status,
    UserProfile,
    WorkSession,
)
from .permissions import IsOwner
from .serializers import (
    ActionSerializer,
    AreaSerializer,
    ContextSerializer,
    DomainSerializer,
    InboxItemSerializer,
    PrioritySerializer,
    ProjectSerializer,
    StatusSerializer,
    UserProfileSerializer,
    WorkSessionSerializer,
)


# ── Inbox ─────────────────────────────────────────────────────────────


class InboxViewSet(viewsets.ModelViewSet):
    serializer_class = InboxItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InboxItem.objects.filter(
            user=self.request.user, processed_at__isnull=True,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def convert_to_action(self, request, pk=None):
        item = self.get_object()
        action_obj = Action.objects.create(
            name=item.item[:70],
            notes=f"Converted from inbox item on {item.created_at.strftime('%Y-%m-%d')}\n\n{item.item}",
            project=Project.objects.get(user=request.user, is_protected=True),
            area=item.area or Area.objects.filter(user=request.user).first(),
            priority=Priority.objects.get(name='Medium'),
            user=request.user,
        )
        item.mark_processed('Converted to action')
        return Response(ActionSerializer(action_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def convert_to_project(self, request, pk=None):
        item = self.get_object()
        project = Project.objects.create(
            name=item.item[:70],
            description=item.item[:255],
            notes=f"Converted from inbox item on {item.created_at.strftime('%Y-%m-%d')}",
            area=item.area or Area.objects.filter(user=request.user).first(),
            status=Status.objects.get(name='PROPOSED'),
            user=request.user,
        )
        item.mark_processed('Converted to project')
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        item = self.get_object()
        item.mark_processed('Archived — not actionable')
        return Response(InboxItemSerializer(item).data)


# ── Actions ───────────────────────────────────────────────────────────


class ActionViewSet(viewsets.ModelViewSet):
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Action.objects.filter(user=self.request.user)
        if 'project' in self.request.query_params:
            qs = qs.filter(project_id=self.request.query_params['project'])
        if 'area' in self.request.query_params:
            qs = qs.filter(area_id=self.request.query_params['area'])
        if 'priority' in self.request.query_params:
            qs = qs.filter(priority_id=self.request.query_params['priority'])
        if 'context' in self.request.query_params:
            qs = qs.filter(context_id=self.request.query_params['context'])
        if 'complete' in self.request.query_params:
            if self.request.query_params['complete'] == 'true':
                qs = qs.complete()
            else:
                qs = qs.incomplete()
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False)
    def today(self, request):
        actions = self.get_queryset().incomplete().filter(
            Q(scheduled_start__date=date.today()) | Q(scheduled_end__date=date.today()),
        )
        return Response(ActionSerializer(actions, many=True).data)

    @action(detail=False)
    def overdue(self, request):
        actions = self.get_queryset().overdue()
        return Response(ActionSerializer(actions, many=True).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        action_obj = self.get_object()
        action_obj.complete()
        return Response(ActionSerializer(action_obj).data)


# ── Projects ──────────────────────────────────────────────────────────


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Project.objects.filter(user=self.request.user, is_protected=False)
        if 'status' in self.request.query_params:
            qs = qs.filter(status__name=self.request.query_params['status'])
        if 'area' in self.request.query_params:
            qs = qs.filter(area_id=self.request.query_params['area'])
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True)
    def actions(self, request, pk=None):
        project = self.get_object()
        actions = Action.objects.filter(project=project)
        return Response(ActionSerializer(actions, many=True).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        project = self.get_object()
        action_handling = request.data.get('action_handling', 'complete_all')
        if not project.can_complete_safely:
            return Response(
                {'error': 'Cannot complete: project has active sub-projects'},
                status=status.HTTP_409_CONFLICT,
            )
        incomplete = Action.objects.filter(project=project, ended_at__isnull=True)
        if action_handling == 'move_to_open':
            open_project = Project.objects.get(user=request.user, is_protected=True)
            incomplete.update(project=open_project)
        else:
            incomplete.update(ended_at=timezone.now())
        project.mark_complete('COMPLETED')
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=['post'])
    def abandon(self, request, pk=None):
        project = self.get_object()
        reason = request.data.get('reason', '')
        action_handling = request.data.get('action_handling', 'complete_all')
        if not project.can_complete_safely:
            return Response(
                {'error': 'Cannot abandon: project has active sub-projects'},
                status=status.HTTP_409_CONFLICT,
            )
        incomplete = Action.objects.filter(project=project, ended_at__isnull=True)
        if action_handling == 'move_to_open':
            open_project = Project.objects.get(user=request.user, is_protected=True)
            incomplete.update(project=open_project)
        else:
            incomplete.update(ended_at=timezone.now())
        if reason:
            project.notes = (project.notes or '') + f"\n\nABANDONED: {reason}"
            project.save(update_fields=['notes', 'updated_at'])
        project.mark_complete('ABANDONED')
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        project = self.get_object()
        target_status = request.data.get('status', 'NEXT')
        reason = request.data.get('reason', '')
        if target_status not in ['NEXT', 'IN ACTION']:
            return Response(
                {'error': 'Can only reopen to NEXT or IN ACTION'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if reason:
            project.notes = (project.notes or '') + f"\n\nRE-OPENED from {project.status.name}: {reason}"
            project.save(update_fields=['notes', 'updated_at'])
        project.status = Status.objects.get(name=target_status)
        project.ended_at = None
        project.save()
        return Response(ProjectSerializer(project).data)


# ── Work Sessions ─────────────────────────────────────────────────────


class WorkSessionViewSet(viewsets.ModelViewSet):
    serializer_class = WorkSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkSession.objects.filter(user=self.request.user).with_related()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False)
    def active(self, request):
        session = self.get_queryset().active().first()
        if not session:
            return Response(None)
        return Response(WorkSessionSerializer(session).data)

    @action(detail=False, methods=['post'], url_path='start/(?P<action_id>[0-9]+)')
    def start(self, request, action_id=None):
        # Stop any active session first
        active_session = WorkSession.objects.filter(
            user=request.user, finished_at__isnull=True,
        ).first()
        if active_session:
            active_session.finish()
        action_obj = Action.objects.get(pk=action_id, user=request.user)
        session = WorkSession.objects.create(
            action=action_obj, user=request.user, started_at=timezone.now(),
        )
        return Response(WorkSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def stop(self, request):
        active_session = WorkSession.objects.filter(
            user=request.user, finished_at__isnull=True,
        ).first()
        if not active_session:
            return Response({'error': 'No active session'}, status=status.HTTP_400_BAD_REQUEST)
        active_session.finish()
        return Response(WorkSessionSerializer(active_session).data)


# ── Reference Data ────────────────────────────────────────────────────


class DomainViewSet(viewsets.ModelViewSet):
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Domain.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AreaViewSet(viewsets.ModelViewSet):
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Area.objects.filter(user=self.request.user).select_related('domain')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContextViewSet(viewsets.ModelViewSet):
    serializer_class = ContextSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Context.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PriorityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PrioritySerializer
    queryset = Priority.objects.all()
    permission_classes = [IsAuthenticated]


class StatusViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StatusSerializer
    queryset = Status.objects.all()
    permission_classes = [IsAuthenticated]


# ── User Profile ──────────────────────────────────────────────────────


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.userprofile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_api_key(request):
    """Regenerate the user's API key."""
    profile = UserProfile.objects.get(user=request.user)
    new_key = profile.generate_api_key()
    return Response({'api_key': new_key})


# ── Review Report ─────────────────────────────────────────────────────


class GenerateReviewView(APIView):
    """SDS 4.8.2 — Generate automated review report."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from gtd.views.review import ReviewReportGenerator
        report = ReviewReportGenerator(request.user).generate()
        return Response(report)
