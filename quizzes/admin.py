from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Test, Question, Option, UserResult


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_staff', 'date_joined']
    list_filter = ['role', 'is_staff', 'date_joined']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'is_private', 'time_limit', 'is_active', 'created_at']
    list_filter = ['is_private', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    filter_horizontal = ['allowed_users']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'test', 'order']
    list_filter = ['test']
    search_fields = ['text']


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'question', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__test']
    search_fields = ['text']


@admin.register(UserResult)
class UserResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'score', 'total_questions', 'percentage', 'time_spent_display', 'completed_at']
    list_filter = ['completed_at', 'test']
    search_fields = ['user__username', 'test__title']
    readonly_fields = ['score', 'total_questions', 'percentage', 'answers', 'certificate_id']
    
    def time_spent_display(self, obj):
        """Display time spent in minutes:seconds format"""
        if obj.time_spent:
            minutes = obj.time_spent // 60
            seconds = obj.time_spent % 60
            return f"{minutes}:{seconds:02d}"
        return "—"
    time_spent_display.short_description = "Time Spent"
