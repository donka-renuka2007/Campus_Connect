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

COMPUTING_BRANCHES = ['aiml', 'cse', 'csd', 'cst', 'it']
NON_COMPUTING_BRANCHES = ['ece', 'eee', 'ce', 'me']

YEAR_CHOICES = [
    ('1', '1st Year'),
    ('2', '2nd Year'),
    ('3', '3rd Year'),
    ('4', '4th Year'),
]


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
    ]
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone       = models.CharField(max_length=15, blank=True, null=True)
    roll_no     = models.CharField(max_length=20, blank=True, null=True)
    year        = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)
    branch      = models.CharField(max_length=10, choices=BRANCH_CHOICES, blank=True, null=True)
    linkedin    = models.URLField(blank=True, null=True)
    codechef    = models.CharField(max_length=100, blank=True, null=True)
    leetcode    = models.CharField(max_length=100, blank=True, null=True)
    avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

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
        ('all',          'All Streams'),
        ('computing',    'Computing'),
        ('non-computing','Non-Computing'),
    ]
    TARGET_BRANCH_CHOICES = [('all', 'All Branches')] + BRANCH_CHOICES

    title         = models.CharField(max_length=200)
    body          = models.TextField()
    image         = models.ImageField(upload_to='announcements/', blank=True, null=True)
    author        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    priority      = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    is_pinned     = models.BooleanField(default=False)
    target_year   = models.CharField(max_length=5, choices=TARGET_YEAR_CHOICES, default='all')
    target_stream = models.CharField(max_length=15, choices=TARGET_STREAM_CHOICES, default='all')
    target_branch = models.CharField(max_length=10, choices=TARGET_BRANCH_CHOICES, default='all')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title