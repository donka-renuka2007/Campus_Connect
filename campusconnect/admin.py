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




from .models import Goal, QuizQuestion, GoalSubmission, QuizAnswer


# ── Inline: Quiz Questions inside Goal ───────────────────────────────────────
class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    fields = ('order', 'qtype', 'question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct')


# ── Inline: Submissions inside Goal ──────────────────────────────────────────
class GoalSubmissionInline(admin.TabularInline):
    model = GoalSubmission
    extra = 0
    readonly_fields = ('student', 'submitted_at', 'quiz_score', 'quiz_total', 'status')
    fields = ('student', 'status', 'quiz_score', 'quiz_total', 'submitted_at')
    can_delete = False


# ── Inline: Quiz Answers inside Submission ────────────────────────────────────
class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    readonly_fields = ('question', 'answer', 'is_correct')
    can_delete = False


# ── Goal Admin ────────────────────────────────────────────────────────────────
@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display  = ('title', 'goal_type', 'assigned_by', 'start_date', 'due_date', 'status', 'student_count', 'submission_count')
    list_filter   = ('goal_type', 'status')
    search_fields = ('title', 'description', 'assigned_by__username')
    date_hierarchy = 'due_date'
    filter_horizontal = ('assigned_to',)
    inlines       = [QuizQuestionInline, GoalSubmissionInline]
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'goal_type', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'due_date', 'created_at')
        }),
        ('Assignment', {
            'fields': ('assigned_by', 'assigned_to')
        }),
        ('Resources', {
            'fields': ('resource_link', 'resource_file'),
            'classes': ('collapse',)
        }),
    )

    def student_count(self, obj):
        return obj.assigned_to.count()
    student_count.short_description = 'Students'

    def submission_count(self, obj):
        return obj.submissions.count()
    submission_count.short_description = 'Submissions'


# ── Quiz Question Admin ───────────────────────────────────────────────────────
@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display  = ('goal', 'order', 'qtype', 'question_short', 'correct')
    list_filter   = ('qtype', 'goal')
    search_fields = ('question', 'goal__title')
    ordering      = ('goal', 'order')

    def question_short(self, obj):
        return obj.question[:60] + ('...' if len(obj.question) > 60 else '')
    question_short.short_description = 'Question'


# ── Goal Submission Admin ─────────────────────────────────────────────────────
@admin.register(GoalSubmission)
class GoalSubmissionAdmin(admin.ModelAdmin):
    list_display  = ('student', 'goal', 'status', 'quiz_score', 'quiz_total', 'submitted_at')
    list_filter   = ('status',)
    search_fields = ('student__username', 'goal__title')
    readonly_fields = ('submitted_at', 'quiz_score', 'quiz_total')
    inlines       = [QuizAnswerInline]

    fieldsets = (
        ('Submission', {
            'fields': ('goal', 'student', 'file', 'note', 'submitted_at')
        }),
        ('Quiz Result', {
            'fields': ('quiz_score', 'quiz_total'),
            'classes': ('collapse',)
        }),
        ('Review', {
            'fields': ('status', 'feedback')
        }),
    )


# ── Quiz Answer Admin ─────────────────────────────────────────────────────────
@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display  = ('submission', 'question', 'answer', 'is_correct')
    list_filter   = ('is_correct',)
    search_fields = ('submission__student__username', 'question__question')
    readonly_fields = ('submission', 'question', 'answer', 'is_correct')