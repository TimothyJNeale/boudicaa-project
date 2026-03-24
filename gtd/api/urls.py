# SDS 7.5 — API URL configuration
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'inbox', views.InboxViewSet, basename='api-inbox')
router.register(r'actions', views.ActionViewSet, basename='api-actions')
router.register(r'projects', views.ProjectViewSet, basename='api-projects')
router.register(r'sessions', views.WorkSessionViewSet, basename='api-sessions')
router.register(r'domains', views.DomainViewSet, basename='api-domains')
router.register(r'areas', views.AreaViewSet, basename='api-areas')
router.register(r'contexts', views.ContextViewSet, basename='api-contexts')
router.register(r'priorities', views.PriorityViewSet, basename='api-priorities')
router.register(r'statuses', views.StatusViewSet, basename='api-statuses')

urlpatterns = [
    path('', include(router.urls)),
    path('user/profile/', views.UserProfileView.as_view(), name='api_user_profile'),
    path('user/api-key/regenerate/', views.regenerate_api_key, name='api_regenerate_key'),
    path('review/generate/', views.GenerateReviewView.as_view(), name='api_generate_review'),
]
