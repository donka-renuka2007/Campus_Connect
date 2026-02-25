from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
BRANCH_CHOICES = [
    # Computing
    ('aiml', 'AI & ML'),
    ('cse',  'CSE'),
    ('csd',  'CSD'),
    ('cst',  'CST'),
    ('it',   'IT'),
    # Non-Computing
    ('ece',  'ECE'),
    ('eee',  'EEE'),
    ('ce',   'Civil Engineering'),
    ('me',   'Mechanical'),
]

COMPUTING_BRANCHES     = ['aiml', 'cse', 'csd', 'cst', 'it']
NON_COMPUTING_BRANCHES = ['ece', 'eee', 'ce', 'me']

YEAR_CHOICES = [
    ('1', '1st Year'),
    ('2', '2nd Year'),
    ('3', '3rd Year'),
    ('4', '4th Year'),
]

# NEW: department choices for faculty
DEPARTMENT_CHOICES = [
    ('cse',  'Computer Science & Engineering'),
    ('ece',  'Electronics & Communication'),
    ('eee',  'Electrical & Electronics'),
    ('ce',   'Civil Engineering'),
    ('me',   'Mechanical Engineering'),
    ('maths','Mathematics'),
    ('phy',  'Physics'),
    ('chem', 'Chemistry'),
    ('eng',  'English'),
    ('other','Other'),
]


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
    ]

    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone      = models.CharField(max_length=15, blank=True, null=True)
    avatar     = models.ImageField(upload_to='avatars/', blank=True, null=True)
    linkedin   = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Student-only fields ──
    roll_no  = models.CharField(max_length=20, blank=True, null=True)
    year     = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)
    branch   = models.CharField(max_length=10, choices=BRANCH_CHOICES, blank=True, null=True)
    codechef = models.CharField(max_length=100, blank=True, null=True)
    leetcode = models.CharField(max_length=100, blank=True, null=True)

    # ── Faculty-only fields ── (NEW)
    teacher_id         = models.CharField(max_length=30, blank=True, null=True)
    department         = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    experience         = models.PositiveIntegerField(blank=True, null=True, help_text='Years of experience')
    subjects_teaching  = models.TextField(blank=True, null=True, help_text='Comma-separated list of subjects')

    @property
    def is_computing(self):
        return self.branch in COMPUTING_BRANCHES

    @property
    def stream(self):
        if self.branch in COMPUTING_BRANCHES:
            return 'computing'
        elif self.branch in NON_COMPUTING_BRANCHES:
            return 'non-computing'
        return 'unknown'

    def get_branch_display_name(self):
        for code, name in BRANCH_CHOICES:
            if code == self.branch:
                return name
        return self.branch or '—'

    def get_subjects_list(self):
        """Returns subjects_teaching as a clean list."""
        if self.subjects_teaching:
            return [s.strip() for s in self.subjects_teaching.split(',') if s.strip()]
        return []

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('normal',    'Normal'),
        ('important', 'Important'),
        ('urgent',    'Urgent'),
    ]
    TARGET_YEAR_CHOICES = [
        ('all', 'All Years'),
        ('1',   '1st Year'),
        ('2',   '2nd Year'),
        ('3',   '3rd Year'),
        ('4',   '4th Year'),
    ]
    TARGET_STREAM_CHOICES = [
        ('all',           'All Streams'),
        ('computing',     'Computing'),
        ('non-computing', 'Non-Computing'),
    ]
    TARGET_BRANCH_CHOICES = [('all', 'All Branches')] + BRANCH_CHOICES

    title         = models.CharField(max_length=200)
    body          = models.TextField()
    image         = models.ImageField(upload_to='announcements/', blank=True, null=True)
    author        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    priority      = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    is_pinned     = models.BooleanField(default=False)
    target_year   = models.CharField(max_length=5,  choices=TARGET_YEAR_CHOICES,   default='all')
    target_stream = models.CharField(max_length=15, choices=TARGET_STREAM_CHOICES, default='all')
    target_branch = models.CharField(max_length=10, choices=TARGET_BRANCH_CHOICES, default='all')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class Goal(models.Model):
    GOAL_TYPE = [
        ('task',  'Task'),
        ('quiz',  'Quiz'),
    ]
    STATUS = [
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('overdue',   'Overdue'),
    ]

    title           = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    goal_type       = models.CharField(max_length=10, choices=GOAL_TYPE, default='task')
    assigned_by     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals_created')
    assigned_to     = models.ManyToManyField(User, related_name='goals_assigned', blank=True)
    start_date      = models.DateField()
    due_date        = models.DateField()
    resource_link   = models.URLField(blank=True, null=True)
    resource_file   = models.FileField(upload_to='goal_resources/', blank=True, null=True)
    status          = models.CharField(max_length=20, choices=STATUS, default='active')
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    QTYPE = [
        ('mcq',   'Multiple Choice'),
        ('short', 'Short Answer'),
    ]
    goal     = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='questions')
    qtype    = models.CharField(max_length=10, choices=QTYPE, default='mcq')
    question = models.TextField()
    option_a = models.CharField(max_length=300, blank=True)
    option_b = models.CharField(max_length=300, blank=True)
    option_c = models.CharField(max_length=300, blank=True)
    option_d = models.CharField(max_length=300, blank=True)
    correct  = models.CharField(max_length=1, blank=True, help_text="A/B/C/D for MCQ")
    order    = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.question[:50]}"


class GoalSubmission(models.Model):
    STATUS = [
        ('submitted', 'Submitted'),
        ('reviewed',  'Reviewed'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]
    goal        = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='submissions')
    student     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goal_submissions')
    file        = models.FileField(upload_to='goal_submissions/', blank=True, null=True)
    note        = models.TextField(blank=True)
    quiz_score  = models.FloatField(null=True, blank=True)
    quiz_total  = models.IntegerField(null=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS, default='submitted')
    feedback    = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('goal', 'student')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} → {self.goal.title}"


class QuizAnswer(models.Model):
    submission = models.ForeignKey(GoalSubmission, on_delete=models.CASCADE, related_name='answers')
    question   = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    answer     = models.TextField()
    is_correct = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.submission.student.username} - Q{self.question.order}"




class LibraryRecord(models.Model):
    # Teacher who issued the book
    issued_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='issued_books'
    )
    # Student who borrowed the book
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='borrowed_books'
    )

    book_name = models.CharField(max_length=255)
    book_no = models.CharField(max_length=100)
    start_date = models.DateField()
    due_date = models.DateField()
    penalty_per_day = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Teacher marks as returned/done
    is_returned = models.BooleanField(default=False)
    returned_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Library Record'
        verbose_name_plural = 'Library Records'

    def __str__(self):
        return f"{self.book_name} → {self.student.get_full_name() or self.student.username}"

    @property
    def days_overdue(self):
        if self.is_returned:
            return 0
        today = timezone.now().date()
        if today > self.due_date:
            return (today - self.due_date).days
        return 0

    @property
    def current_penalty(self):
        return Decimal(self.days_overdue) * self.penalty_per_day

    @property
    def status(self):
        if self.is_returned:
            return 'returned'
        elif self.days_overdue > 0:
            return 'overdue'
        else:
            return 'active'
