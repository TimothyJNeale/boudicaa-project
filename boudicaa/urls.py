# SDS 3.1 — Root URL configuration
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public pages — SDS 3.1
    path('', views.public_home, name='public_home'),
    path('signup/', views.signupuser, name='signupuser'),
    path('login/', views.loginuser, name='loginuser'),
    path('logout/', views.logoutuser, name='logoutuser'),
    path('verification-sent/', views.verification_sent, name='verification_sent'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # Django auth (password change/reset)
    path('accounts/', include('django.contrib.auth.urls')),

    # GTD application — SDS 3.2–3.8
    path('gtd/', include('gtd.urls')),

    # REST API — SDS 3.9
    path('api/v1/', include('gtd.api.urls')),

    # API documentation — SDS 3.1
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='api_docs'),
]
