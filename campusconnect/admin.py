from django.contrib import admin
from .models import UserProfile, Announcement


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'branch', 'year', 'phone', 'created_at')
    list_filter   = ('role', 'branch', 'year')
    search_fields = ('user__username', 'user__email', 'roll_no', 'phone')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display  = ('title', 'author', 'priority', 'target_year', 'target_branch', 'is_pinned', 'created_at')
    list_filter   = ('priority', 'is_pinned', 'target_year', 'target_branch', 'target_stream')
    search_fields = ('title', 'body', 'author__username')
    ordering      = ('-created_at',)