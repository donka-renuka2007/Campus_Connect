from django.db import models
from django.contrib.auth.models import User

class Resource(models.Model):
    SUBJECT_CHOICES = [
        ('OOPS', 'OOPs Through Java'),
        ('ADS', 'ADS'),
        ('DMGT', 'DM & GT'),
        ('UHV', 'UHV'),
        ('AI', 'AI'),
        ('Python', 'Python'),
    ]
    
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, choices=SUBJECT_CHOICES)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='resources/')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title