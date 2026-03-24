# SDS — Django admin registration
from django.contrib import admin

from .models import (
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

admin.site.register(Domain)
admin.site.register(Area)
admin.site.register(Status)
admin.site.register(Priority)
admin.site.register(Context)
admin.site.register(Project)
admin.site.register(Action)
admin.site.register(InboxItem)
admin.site.register(WorkSession)
admin.site.register(UserProfile)
