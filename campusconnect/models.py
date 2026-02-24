from django.db import models
from django.contrib.auth.models import User

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