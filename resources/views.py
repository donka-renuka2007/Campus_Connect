from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Resource
from .forms import ResourceForm

@login_required
def resource_access(request):
    subjects = [
        ('OOPS',   'Through Java'),
        ('ADS',    'Algorithm Design'),
        ('DMGT',   'Discrete Math & GT'),
        ('UHV',    'Universal Human Values'),
        ('AI',     'Artificial Intelligence'),
        ('Python', 'Python Programming'),
    ]
    subjects_with_counts = []
    for code, name in subjects:
        count = Resource.objects.filter(subject=code).count()
        subjects_with_counts.append((code, name, count))

    return render(request, 'resource_access.html', {
        'subjects': subjects_with_counts,
    })

@login_required
def resource_upload(request):
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.uploaded_by = request.user
            resource.save()
            return redirect('resource_access')
        else:
            print("FORM ERRORS:", form.errors)
    else:
        form = ResourceForm()
    return render(request, 'resource_upload.html', {'form': form})

@login_required
def resource_subject(request, subject):
    resources = Resource.objects.filter(subject=subject).order_by('-uploaded_at')
    return render(request, 'resource_subject.html', {
        'resources': resources,
        'subject': subject,
    })