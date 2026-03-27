# SDS 3.2–3.8 — GTD URL configuration
from django.urls import path

from .views import (
    # Inbox
    InboxListView,
    InboxCreateView,
    InboxProcessView,
    InboxProcessedView,
    InboxProcessedDetailView,
    quick_capture,
    convert_inbox_to_action,
    convert_inbox_to_project,
    archive_inbox_item,
    delete_inbox_item,
    # Today
    TodayView,
    TodayMoreView,
    ActionSidePanelView,
    UnscheduledTasksView,
    complete_action,
    uncomplete_action,
    update_action_from_panel,
    # Projects
    ProjectListView,
    ProjectCreateView,
    ProjectDetailView,
    ProjectUpdateView,
    ProjectSidePanelView,
    ProjectActionsView,
    ProjectActionAddView,
    project_panel_save,
    project_action_reorder,
    complete_project,
    abandon_project,
    reopen_project,
    # Time
    TimeDailyView,
    WorkSessionListView,
    WorkSessionCreateView,
    WorkSessionUpdateView,
    start_work_session,
    stop_work_session,
    # Reports
    DailyReportView,
    WeeklyReportView,
    MonthlyByDayView,
    MonthlyByProjectView,
    MonthlyByAreaView,
    MonthlyByActionView,
    # Review
    WeeklyReviewView,
    # Config
    DomainListView,
    DomainCreateView,
    DomainUpdateView,
    DomainDeleteView,
    AreaListView,
    AreaCreateView,
    AreaUpdateView,
    AreaDeleteView,
    ContextListView,
    ContextCreateView,
    ContextUpdateView,
    ContextDeleteView,
    # Profile
    UserProfileView,
    update_preferences,
    regenerate_api_key,
    account_delete_confirm,
)

urlpatterns = [
    # Home redirect
    path('', lambda r: __import__('django.shortcuts', fromlist=['redirect']).redirect('today'), name='home'),

    # Today — SDS 3.4
    path('today/', TodayView.as_view(), name='today'),
    path('today/more/<str:date_str>/', TodayMoreView, name='today_more'),
    path('today/action/<int:pk>/panel/', ActionSidePanelView.as_view(), name='action_side_panel'),
    path('today/action/<int:pk>/complete/', complete_action, name='complete_action'),
    path('today/action/<int:pk>/uncomplete/', uncomplete_action, name='uncomplete_action'),
    path('today/action/<int:pk>/update/', update_action_from_panel, name='update_action'),
    path('today/unscheduled/', UnscheduledTasksView.as_view(), name='unscheduled_tasks'),

    # Inbox — SDS 3.3
    path('inbox/', InboxListView.as_view(), name='inbox_list'),
    path('inbox/add/', InboxCreateView.as_view(), name='inbox_add'),
    path('inbox/quick-capture/', quick_capture, name='quick_capture'),
    path('inbox/process/', InboxProcessView, name='inbox_process'),
    path('inbox/process/<int:pk>/', InboxProcessView, name='inbox_process_item'),
    path('inbox/processed/', InboxProcessedView.as_view(), name='inbox_processed'),
    path('inbox/processed/<int:pk>/', InboxProcessedDetailView.as_view(), name='inbox_processed_detail'),
    path('inbox/<int:pk>/convert-to-action/', convert_inbox_to_action, name='convert_to_action'),
    path('inbox/<int:pk>/convert-to-project/', convert_inbox_to_project, name='convert_to_project'),
    path('inbox/<int:pk>/archive/', archive_inbox_item, name='archive_inbox_item'),
    path('inbox/<int:pk>/delete/', delete_inbox_item, name='delete_inbox_item'),

    # Work sessions — SDS 3.5
    path('work-session/start/<int:action_id>/', start_work_session, name='start_work_session'),
    path('work-session/stop/', stop_work_session, name='stop_work_session'),

    # Projects — SDS 3.6
    path('projects/', ProjectListView.as_view(), name='project_list'),
    path('projects/new/', ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/edit/', ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/panel/', ProjectSidePanelView.as_view(), name='project_side_panel'),
    path('projects/<int:pk>/panel/save/', project_panel_save, name='project_panel_save'),
    path('projects/<int:pk>/actions/', ProjectActionsView.as_view(), name='project_actions'),
    path('projects/<int:pk>/actions/add/', ProjectActionAddView.as_view(), name='project_action_add'),
    path('projects/<int:pk>/actions/reorder/', project_action_reorder, name='project_action_reorder'),
    path('project/complete/<int:pk>/', complete_project, name='complete_project'),
    path('project/abandon/<int:pk>/', abandon_project, name='abandon_project'),
    path('project/reopen/<int:pk>/', reopen_project, name='reopen_project'),

    # Configuration — SDS 3.7
    path('config/domains/', DomainListView.as_view(), name='domain_list'),
    path('config/domains/new/', DomainCreateView.as_view(), name='domain_create'),
    path('config/domains/<int:pk>/edit/', DomainUpdateView.as_view(), name='domain_update'),
    path('config/domains/<int:pk>/delete/', DomainDeleteView.as_view(), name='domain_delete'),
    path('config/areas/', AreaListView.as_view(), name='area_list'),
    path('config/areas/new/', AreaCreateView.as_view(), name='area_create'),
    path('config/areas/<int:pk>/edit/', AreaUpdateView.as_view(), name='area_update'),
    path('config/areas/<int:pk>/delete/', AreaDeleteView.as_view(), name='area_delete'),
    path('config/contexts/', ContextListView.as_view(), name='context_list'),
    path('config/contexts/new/', ContextCreateView.as_view(), name='context_create'),
    path('config/contexts/<int:pk>/edit/', ContextUpdateView.as_view(), name='context_update'),
    path('config/contexts/<int:pk>/delete/', ContextDeleteView.as_view(), name='context_delete'),

    # Time tracking — SDS 3.8
    path('time/', TimeDailyView.as_view(), name='time_daily'),
    path('time/<str:date>/', TimeDailyView.as_view(), name='time_daily_date'),
    path('time/timecards/', WorkSessionListView.as_view(), name='worksession_list'),
    path('time/timecards/new/', WorkSessionCreateView.as_view(), name='worksession_create'),
    path('time/timecards/<int:pk>/edit/', WorkSessionUpdateView.as_view(), name='worksession_update'),
    path('time/reports/', lambda r: __import__('django.shortcuts', fromlist=['redirect']).redirect('report_daily'), name='reports'),
    path('time/reports/daily/', DailyReportView.as_view(), name='report_daily'),
    path('time/reports/daily/<int:day_offset>/', DailyReportView.as_view(), name='report_daily_offset'),
    path('time/reports/weekly/', WeeklyReportView.as_view(), name='report_weekly'),
    path('time/reports/weekly/<int:week_offset>/', WeeklyReportView.as_view(), name='report_weekly_offset'),
    path('time/reports/monthly/by-day/', MonthlyByDayView.as_view(), name='report_monthly_by_day'),
    path('time/reports/monthly/by-day/<int:month_offset>/', MonthlyByDayView.as_view(), name='report_monthly_by_day_offset'),
    path('time/reports/monthly/by-project/', MonthlyByProjectView.as_view(), name='report_monthly_by_project'),
    path('time/reports/monthly/by-project/<int:month_offset>/', MonthlyByProjectView.as_view(), name='report_monthly_by_project_offset'),
    path('time/reports/monthly/by-area/', MonthlyByAreaView.as_view(), name='report_monthly_by_area'),
    path('time/reports/monthly/by-area/<int:month_offset>/', MonthlyByAreaView.as_view(), name='report_monthly_by_area_offset'),
    path('time/reports/monthly/by-action/', MonthlyByActionView.as_view(), name='report_monthly_by_action'),
    path('time/reports/monthly/by-action/<int:month_offset>/', MonthlyByActionView.as_view(), name='report_monthly_by_action_offset'),

    # Review — SDS 3.2
    path('review/', WeeklyReviewView.as_view(), name='review'),

    # Profile — SDS 3.2
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/preferences/', update_preferences, name='update_preferences'),
    path('profile/regenerate-key/', regenerate_api_key, name='regenerate_api_key'),
    path('account/delete/', account_delete_confirm, name='account_delete'),
]
