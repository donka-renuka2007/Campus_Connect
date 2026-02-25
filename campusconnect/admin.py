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










from django.utils import timezone
from .models import LibraryRecord


@admin.register(LibraryRecord)
class LibraryRecordAdmin(admin.ModelAdmin):

    # ── List view columns ──────────────────────────────────
    list_display = (
        'book_name',
        'book_no',
        'student_name',
        'issued_by_name',
        'start_date',
        'due_date',
        'penalty_per_day',
        'days_overdue_display',
        'penalty_display',
        'status_badge',
    )

    # ── Filters on the right sidebar ──────────────────────
    list_filter = (
        'is_returned',
        'start_date',
        'due_date',
        'issued_by',
    )

    # ── Search bar ────────────────────────────────────────
    search_fields = (
        'book_name',
        'book_no',
        'student__username',
        'student__first_name',
        'student__last_name',
        'issued_by__username',
        'issued_by__first_name',
    )

    # ── Default ordering ──────────────────────────────────
    ordering = ('-created_at',)

    # ── Date hierarchy navigation ─────────────────────────
    date_hierarchy = 'start_date'

    # ── Read-only fields ──────────────────────────────────
    readonly_fields = ('created_at', 'updated_at', 'days_overdue_display', 'penalty_display')

    # ── Fieldsets for the detail/edit form ────────────────
    fieldsets = (
        ('📖 Book Details', {
            'fields': ('book_name', 'book_no')
        }),
        ('👥 People', {
            'fields': ('issued_by', 'student')
        }),
        ('📅 Dates', {
            'fields': ('start_date', 'due_date')
        }),
        ('💰 Penalty', {
            'fields': ('penalty_per_day', 'days_overdue_display', 'penalty_display')
        }),
        ('✅ Return Status', {
            'fields': ('is_returned', 'returned_date')
        }),
        ('🕒 Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Bulk actions ──────────────────────────────────────
    actions = ['mark_as_returned', 'mark_as_not_returned']

    # ── Custom column: Student full name ──────────────────
    @admin.display(description='Student', ordering='student__first_name')
    def student_name(self, obj):
        name = obj.student.get_full_name() or obj.student.username
        return format_html('<strong>{}</strong>', name)

    # ── Custom column: Issued by ──────────────────────────
    @admin.display(description='Issued By', ordering='issued_by__first_name')
    def issued_by_name(self, obj):
        return obj.issued_by.get_full_name() or obj.issued_by.username

    # ── Custom column: Days overdue ───────────────────────
    @admin.display(description='Days Overdue')
    def days_overdue_display(self, obj):
        days = obj.days_overdue
        if obj.is_returned:
            return format_html('<span style="color:#aaa;">—</span>')
        elif days > 0:
            return format_html(
                '<span style="color:#ff6b6b;font-weight:bold;">⚠️ {} day{}</span>',
                days, 's' if days != 1 else ''
            )
        else:
            return format_html('<span style="color:#00e676;">✔ On time</span>')

    # ── Custom column: Current penalty ───────────────────
    @admin.display(description='Penalty Due')
    def penalty_display(self, obj):
        penalty = obj.current_penalty
        if obj.is_returned:
            return format_html('<span style="color:#aaa;">—</span>')
        elif penalty > 0:
            return format_html(
                '<span style="color:#ff6b6b;font-weight:bold;">₹{}</span>',
                penalty
            )
        else:
            return format_html('<span style="color:#aaa;">₹0</span>')

    # ── Custom column: Status badge ───────────────────────
    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.is_returned:
            return format_html(
                '<span style="background:#0a2e1a;color:#00e676;padding:3px 10px;border-radius:20px;font-size:0.78rem;">✅ Returned</span>'
            )
        elif obj.days_overdue > 0:
            return format_html(
                '<span style="background:#2e0a0a;color:#ff6b6b;padding:3px 10px;border-radius:20px;font-size:0.78rem;">⚠️ Overdue</span>'
            )
        else:
            return format_html(
                '<span style="background:#0a1a2e;color:#64b5f6;padding:3px 10px;border-radius:20px;font-size:0.78rem;">📖 Active</span>'
            )

    # ── Bulk action: Mark selected as returned ────────────
    @admin.action(description='✅ Mark selected books as returned')
    def mark_as_returned(self, request, queryset):
        today = timezone.now().date()
        updated = queryset.filter(is_returned=False).update(
            is_returned=True,
            returned_date=today,
        )
        self.message_user(request, f'{updated} book(s) marked as returned.')

    # ── Bulk action: Unmark returned ──────────────────────
    @admin.action(description='↩️ Unmark selected books as returned')
    def mark_as_not_returned(self, request, queryset):
        updated = queryset.filter(is_returned=True).update(
            is_returned=False,
            returned_date=None,
        )
        self.message_user(request, f'{updated} book(s) unmarked.')
