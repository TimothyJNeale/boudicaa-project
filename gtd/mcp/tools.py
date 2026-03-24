"""MCP tool implementations for Boudicaa. SDS 8.2."""
import json
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from mcp.types import TextContent, Tool

from gtd.models import (
    Action,
    Area,
    InboxItem,
    Project,
    WorkSession,
)


class GTDTools:
    """Read and safe-write tools exposed via MCP protocol."""

    def __init__(self):
        self.tools = {
            # Read operations
            'get_todays_actions': self._get_todays_actions,
            'get_upcoming_actions': self._get_upcoming_actions,
            'get_inbox_count': self._get_inbox_count,
            'get_inbox_items': self._get_inbox_items,
            'get_projects': self._get_projects,
            'get_project_detail': self._get_project_detail,
            'get_action_detail': self._get_action_detail,
            'get_active_timer': self._get_active_timer,
            'get_time_report': self._get_time_report,
            'get_unscheduled_tasks': self._get_unscheduled_tasks,
            'get_overdue_actions': self._get_overdue_actions,
            # Safe write operations
            'add_inbox_item': self._add_inbox_item,
            'start_timer': self._start_timer,
            'stop_timer': self._stop_timer,
            'complete_action': self._complete_action,
            'create_action': self._create_action,
            'reschedule_action': self._reschedule_action,
        }

    def get_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name='get_todays_actions',
                description="Get today's actions including overdue items and active timer",
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer', 'description': 'User ID'},
                        'include_overdue': {'type': 'boolean', 'default': True},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_upcoming_actions',
                description='Get actions scheduled for the next N days',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'days': {'type': 'integer', 'default': 7},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_inbox_count',
                description='Get the count of unprocessed inbox items',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_inbox_items',
                description='Get unprocessed inbox items',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_projects',
                description='Get active projects, optionally filtered by status',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'status': {'type': 'string', 'description': 'Filter by status name'},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_project_detail',
                description='Get detailed information about a specific project',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'project_id': {'type': 'integer'},
                    },
                    'required': ['user_id', 'project_id'],
                },
            ),
            Tool(
                name='get_action_detail',
                description='Get detailed information about a specific action',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'action_id': {'type': 'integer'},
                    },
                    'required': ['user_id', 'action_id'],
                },
            ),
            Tool(
                name='get_active_timer',
                description='Get the currently running timer, if any',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_time_report',
                description='Get time tracking report for a date range',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'period': {
                            'type': 'string',
                            'enum': ['today', 'week', 'month'],
                            'default': 'today',
                        },
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_unscheduled_tasks',
                description='Get standalone tasks without scheduled dates',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='get_overdue_actions',
                description='Get all overdue actions',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='add_inbox_item',
                description='Add a new item to the inbox',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'text': {'type': 'string'},
                        'area': {'type': 'string', 'description': 'Area name (optional)'},
                    },
                    'required': ['user_id', 'text'],
                },
            ),
            Tool(
                name='start_timer',
                description='Start a work session timer for an action',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'action_id': {'type': 'integer'},
                    },
                    'required': ['user_id', 'action_id'],
                },
            ),
            Tool(
                name='stop_timer',
                description='Stop the currently running timer',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                    },
                    'required': ['user_id'],
                },
            ),
            Tool(
                name='complete_action',
                description='Mark an action as complete',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'action_id': {'type': 'integer'},
                    },
                    'required': ['user_id', 'action_id'],
                },
            ),
            Tool(
                name='create_action',
                description='Create a new action in a project',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'project_id': {'type': 'integer'},
                        'scheduled_start': {'type': 'string', 'description': 'ISO date'},
                        'scheduled_end': {'type': 'string', 'description': 'ISO date'},
                    },
                    'required': ['user_id', 'name', 'project_id'],
                },
            ),
            Tool(
                name='reschedule_action',
                description='Change the scheduled dates for an action',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'user_id': {'type': 'integer'},
                        'action_id': {'type': 'integer'},
                        'scheduled_start': {'type': 'string', 'description': 'ISO datetime'},
                        'scheduled_end': {'type': 'string', 'description': 'ISO datetime'},
                    },
                    'required': ['user_id', 'action_id'],
                },
            ),
        ]

    async def execute(self, name: str, arguments: dict) -> list[TextContent]:
        from django.contrib.auth.models import User

        if name not in self.tools:
            return [TextContent(type='text', text=json.dumps({
                'error': f'Unknown tool: {name}',
            }))]

        user_id = arguments.pop('user_id', None)
        if not user_id:
            return [TextContent(type='text', text=json.dumps({
                'error': 'user_id is required',
            }))]

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return [TextContent(type='text', text=json.dumps({
                'error': 'User not found',
            }))]

        try:
            result = await self.tools[name](user, **arguments)
            return [TextContent(type='text', text=json.dumps(result, default=str))]
        except Exception as e:
            return [TextContent(type='text', text=json.dumps({
                'error': str(e),
            }))]

    # ── Read operations ─────────────────────────────────────────────────

    async def _get_todays_actions(self, user, include_overdue=True):
        today = timezone.now().date()
        result = {'date': str(today)}

        # Active timer
        active = WorkSession.objects.filter(
            user=user, finished_at__isnull=True,
        ).select_related('action', 'action__project').first()
        if active:
            result['active_timer'] = {
                'action': active.action.name,
                'project': active.action.project.name,
                'elapsed_minutes': active.elapsed_minutes,
            }

        # Overdue
        if include_overdue:
            overdue = Action.objects.filter(user=user).overdue()
            result['overdue'] = [
                {
                    'id': a.id, 'name': a.name,
                    'project': a.project.name,
                    'due': str(a.scheduled_end.date()),
                }
                for a in overdue.select_related('project')
            ]

        # Today's actions
        today_actions = Action.objects.filter(user=user).incomplete().filter(
            Q(scheduled_start__date=today) | Q(scheduled_end__date=today),
        ).select_related('priority', 'project')
        result['today'] = [
            {
                'id': a.id, 'name': a.name,
                'priority': a.priority.name,
                'project': a.project.name,
                'scheduled_start': str(a.scheduled_start.time()) if a.scheduled_start else None,
            }
            for a in today_actions
        ]

        return result

    async def _get_upcoming_actions(self, user, days=7):
        today = timezone.now().date()
        end_date = today + timedelta(days=days)
        actions = Action.objects.filter(user=user).incomplete().filter(
            scheduled_start__date__range=(today, end_date),
        ).select_related('priority', 'project').order_by('scheduled_start')
        return {
            'period': f'{today} to {end_date}',
            'actions': [
                {
                    'id': a.id, 'name': a.name,
                    'project': a.project.name,
                    'priority': a.priority.name,
                    'date': str(a.scheduled_start.date()),
                }
                for a in actions
            ],
        }

    async def _get_inbox_count(self, user):
        count = InboxItem.objects.filter(
            user=user, processed_at__isnull=True,
        ).count()
        return {'count': count}

    async def _get_inbox_items(self, user):
        items = InboxItem.objects.filter(
            user=user, processed_at__isnull=True,
        ).order_by('-created_at')
        return {
            'count': items.count(),
            'items': [
                {
                    'id': i.id,
                    'text': i.item,
                    'area': i.area.name if i.area else None,
                    'created_at': str(i.created_at),
                }
                for i in items
            ],
        }

    async def _get_projects(self, user, status=None):
        qs = Project.objects.filter(
            user=user, is_protected=False,
        ).select_related('status', 'area', 'area__domain')
        if status:
            qs = qs.filter(status__name=status)
        return {
            'projects': [
                {
                    'id': p.id, 'name': p.name,
                    'status': p.status.name,
                    'area': str(p.area),
                    'incomplete_actions': p.incomplete_action_count,
                }
                for p in qs
            ],
        }

    async def _get_project_detail(self, user, project_id):
        project = Project.objects.select_related(
            'status', 'area', 'area__domain',
        ).get(pk=project_id, user=user)
        actions = project.action_set.all().select_related('priority')
        return {
            'id': project.id,
            'name': project.name,
            'status': project.status.name,
            'area': str(project.area),
            'description': project.description,
            'notes': project.notes,
            'created_at': str(project.created_at),
            'actions': [
                {
                    'id': a.id, 'name': a.name,
                    'priority': a.priority.name,
                    'complete': a.is_complete,
                    'scheduled_start': str(a.scheduled_start) if a.scheduled_start else None,
                }
                for a in actions
            ],
        }

    async def _get_action_detail(self, user, action_id):
        action = Action.objects.select_related(
            'project', 'area', 'priority', 'context',
        ).get(pk=action_id, user=user)
        return {
            'id': action.id,
            'name': action.name,
            'project': action.project.name,
            'area': str(action.area),
            'priority': action.priority.name,
            'context': action.context.name if action.context else None,
            'notes': action.notes,
            'scheduled_start': str(action.scheduled_start) if action.scheduled_start else None,
            'scheduled_end': str(action.scheduled_end) if action.scheduled_end else None,
            'is_complete': action.is_complete,
            'is_overdue': action.is_overdue,
            'is_recurring': action.is_recurring,
            'total_time_minutes': int(action.total_time_worked.total_seconds() / 60),
        }

    async def _get_active_timer(self, user):
        active = WorkSession.objects.filter(
            user=user, finished_at__isnull=True,
        ).select_related('action', 'action__project').first()
        if not active:
            return {'active': False}
        return {
            'active': True,
            'session_id': active.id,
            'action': active.action.name,
            'project': active.action.project.name,
            'started_at': str(active.started_at),
            'elapsed_minutes': active.elapsed_minutes,
        }

    async def _get_time_report(self, user, period='today'):
        today = timezone.now().date()
        if period == 'today':
            sessions = WorkSession.objects.for_user(user).for_date(today)
        elif period == 'week':
            iso = today.isocalendar()
            sessions = WorkSession.objects.for_user(user).for_week(iso[0], iso[1])
        elif period == 'month':
            sessions = WorkSession.objects.for_user(user).for_month(today.year, today.month)
        else:
            sessions = WorkSession.objects.none()

        sessions = sessions.completed().with_related()
        total_minutes = sum(s.elapsed_minutes for s in sessions)
        return {
            'period': period,
            'total_minutes': total_minutes,
            'total_formatted': f'{total_minutes // 60}h {total_minutes % 60}m',
            'sessions': [
                {
                    'action': s.action.name,
                    'project': s.action.project.name,
                    'minutes': s.elapsed_minutes,
                    'date': str(s.started_at.date()),
                }
                for s in sessions
            ],
        }

    async def _get_unscheduled_tasks(self, user):
        tasks = Action.objects.filter(user=user).unscheduled_standalone().select_related(
            'priority',
        )
        return {
            'count': tasks.count(),
            'tasks': [
                {'id': t.id, 'name': t.name, 'priority': t.priority.name}
                for t in tasks
            ],
        }

    async def _get_overdue_actions(self, user):
        overdue = Action.objects.filter(user=user).overdue().select_related(
            'project', 'priority',
        )
        return {
            'count': overdue.count(),
            'actions': [
                {
                    'id': a.id, 'name': a.name,
                    'project': a.project.name,
                    'priority': a.priority.name,
                    'due': str(a.scheduled_end.date()),
                }
                for a in overdue
            ],
        }

    # ── Safe write operations ───────────────────────────────────────────

    async def _add_inbox_item(self, user, text, area=None):
        area_obj = None
        if area:
            area_obj = Area.objects.filter(user=user, name__icontains=area).first()

        item = InboxItem.objects.create(item=text, area=area_obj, user=user)
        count = InboxItem.objects.filter(
            user=user, processed_at__isnull=True,
        ).count()

        return {
            'status': 'created',
            'item_id': item.id,
            'text': text,
            'inbox_count': count,
        }

    async def _start_timer(self, user, action_id):
        # Stop any active session
        active = WorkSession.objects.filter(
            user=user, finished_at__isnull=True,
        ).first()
        stopped_info = None
        if active:
            active.finish()
            stopped_info = {
                'action': active.action.name,
                'duration_minutes': active.elapsed_minutes,
            }

        action_obj = Action.objects.get(pk=action_id, user=user)
        session = WorkSession.objects.create(
            action=action_obj, user=user, started_at=timezone.now(),
        )

        result = {
            'status': 'started',
            'action': action_obj.name,
            'session_id': session.id,
        }
        if stopped_info:
            result['stopped_previous'] = stopped_info

        return result

    async def _stop_timer(self, user):
        active = WorkSession.objects.filter(
            user=user, finished_at__isnull=True,
        ).first()
        if not active:
            return {'status': 'no_active_session'}

        active.finish()
        return {
            'status': 'stopped',
            'action': active.action.name,
            'duration_minutes': active.elapsed_minutes,
        }

    async def _complete_action(self, user, action_id):
        action_obj = Action.objects.get(pk=action_id, user=user)
        action_obj.complete()

        result = {
            'status': 'completed',
            'action': action_obj.name,
        }
        if action_obj.is_recurring:
            result['next_occurrence'] = 'Generated'
        return result

    async def _create_action(self, user, name, project_id,
                             scheduled_start=None, scheduled_end=None):
        from dateutil.parser import parse as parse_date

        project = Project.objects.get(pk=project_id, user=user)
        from gtd.models import Priority
        priority = Priority.objects.get(name='Medium')

        action = Action.objects.create(
            name=name,
            project=project,
            area=project.area,
            priority=priority,
            user=user,
            scheduled_start=parse_date(scheduled_start) if scheduled_start else None,
            scheduled_end=parse_date(scheduled_end) if scheduled_end else None,
        )
        return {
            'status': 'created',
            'action_id': action.id,
            'name': action.name,
            'project': project.name,
        }

    async def _reschedule_action(self, user, action_id,
                                 scheduled_start=None, scheduled_end=None):
        from dateutil.parser import parse as parse_date

        action = Action.objects.get(pk=action_id, user=user)
        if scheduled_start:
            action.scheduled_start = parse_date(scheduled_start)
        if scheduled_end:
            action.scheduled_end = parse_date(scheduled_end)
        action.save(update_fields=['scheduled_start', 'scheduled_end', 'updated_at'])

        return {
            'status': 'rescheduled',
            'action': action.name,
            'scheduled_start': str(action.scheduled_start) if action.scheduled_start else None,
            'scheduled_end': str(action.scheduled_end) if action.scheduled_end else None,
        }
