from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import UserProfile, Announcement, BRANCH_CHOICES, YEAR_CHOICES


def home(request):
    return render(request, 'home.html')


def login_page(request):
    if request.user.is_authenticated:
        return redirect('announcements')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('announcements')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def signup_page(request):
    if request.user.is_authenticated:
        return redirect('announcements')
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        phone      = request.POST.get('phone', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')
        role       = request.POST.get('role', 'student')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html')
        if len(password1) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'signup.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'signup.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'signup.html')

        user = User.objects.create_user(
            username=username, email=email, password=password1,
            first_name=first_name, last_name=last_name
        )
        UserProfile.objects.create(user=user, role=role, phone=phone)
        messages.success(request, 'Account created! Please log in.')
        return redirect('login')
    return render(request, 'signup.html')


def logout_page(request):
    auth_logout(request)
    return redirect('home')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect('announcements')


# ── STUDY ──

def study(request):
    if not request.user.is_authenticated:
        return redirect('login')
    # FIX: Specific exception instead of bare except
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None
    return render(request, 'study.html', {
        'user': request.user,
        'profile': profile,
    })


# ── ANNOUNCEMENTS ──

def announcements(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # FIX: Specific exception instead of bare except
    try:
        profile    = request.user.profile
        is_faculty = profile.role == 'faculty'
    except UserProfile.DoesNotExist:
        profile    = None
        is_faculty = False

    qs = Announcement.objects.all()

    search   = request.GET.get('search', '').strip()
    f_year   = request.GET.get('year', '')
    f_stream = request.GET.get('stream', '')
    f_branch = request.GET.get('branch', '')
    f_prio   = request.GET.get('priority', '')

    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(body__icontains=search))
    if f_year:
        qs = qs.filter(Q(target_year='all') | Q(target_year=f_year))
    if f_stream:
        qs = qs.filter(Q(target_stream='all') | Q(target_stream=f_stream))
    if f_branch:
        qs = qs.filter(Q(target_branch='all') | Q(target_branch=f_branch))
    if f_prio:
        qs = qs.filter(priority=f_prio)

    pinned  = qs.filter(is_pinned=True)
    regular = qs.filter(is_pinned=False)

    return render(request, 'announcements.html', {
        'pinned':     pinned,
        'regular':    regular,
        # FIX: total now reflects filtered count, not all announcements
        'total':      pinned.count() + regular.count(),
        'is_faculty': is_faculty,
        'user':       request.user,
        'profile':    profile,
        'search':     search,
        'f_year':     f_year,
        'f_stream':   f_stream,
        'f_branch':   f_branch,
        'f_prio':     f_prio,
    })


def post_announcement(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # FIX: Specific exception instead of bare except
    try:
        is_faculty = request.user.profile.role == 'faculty'
    except UserProfile.DoesNotExist:
        is_faculty = False

    # Only faculty/teachers can post
    if not is_faculty:
        messages.error(request, 'Only faculty can post announcements.')
        return redirect('announcements')

    if request.method == 'POST':
        title         = request.POST.get('title', '').strip()
        body          = request.POST.get('body', '').strip()
        priority      = request.POST.get('priority', 'normal')
        is_pinned     = request.POST.get('is_pinned') == 'on'
        target_year   = request.POST.get('target_year', 'all')
        target_stream = request.POST.get('target_stream', 'all')
        target_branch = request.POST.get('target_branch', 'all')
        image         = request.FILES.get('image')

        if not title or not body:
            messages.error(request, 'Title and body are required.')
            return render(request, 'post_announcement.html')

        Announcement.objects.create(
            title=title, body=body, priority=priority, is_pinned=is_pinned,
            image=image, target_year=target_year, target_stream=target_stream,
            target_branch=target_branch, author=request.user,
        )
        messages.success(request, 'Announcement posted!')
        return redirect('announcements')

    return render(request, 'post_announcement.html')


def edit_announcement(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')

    # FIX: Was checking request.user.is_staff (Django admin flag) which is
    # unrelated to our faculty role. Now correctly checks profile.role.
    # This means faculty users can actually edit — before they got blocked.
    try:
        is_faculty = request.user.profile.role == 'faculty'
    except UserProfile.DoesNotExist:
        is_faculty = False

    if not is_faculty:
        messages.error(request, 'Only faculty can edit announcements.')
        return redirect('announcements')

    ann = get_object_or_404(Announcement, pk=pk)

    if request.method == 'POST':
        ann.title         = request.POST.get('title', '').strip()
        ann.body          = request.POST.get('body', '').strip()
        ann.priority      = request.POST.get('priority')
        ann.is_pinned     = request.POST.get('is_pinned') == 'on'
        ann.target_year   = request.POST.get('target_year')
        ann.target_stream = request.POST.get('target_stream')
        ann.target_branch = request.POST.get('target_branch')

        if request.FILES.get('image'):
            ann.image = request.FILES['image']

        ann.save()
        messages.success(request, 'Announcement updated successfully!')
        return redirect('announcements')

    return render(request, 'edit_announcement.html', {
        'announcement': ann
    })


def delete_announcement(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')

    # FIX: Was a GET request — anyone visiting the URL could delete an announcement.
    # Now requires POST (submitted from the form with CSRF token in the template).
    # FIX: Was checking is_staff (Django admin flag). Now checks profile.role == faculty.
    if request.method == 'POST':
        ann = get_object_or_404(Announcement, pk=pk)
        try:
            is_faculty = request.user.profile.role == 'faculty'
        except UserProfile.DoesNotExist:
            is_faculty = False

        if is_faculty:
            ann.delete()
            messages.success(request, 'Announcement deleted.')
        else:
            messages.error(request, 'Only faculty can delete announcements.')

    return redirect('announcements')


# ── PROFILE ──

def profile_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    # FIX: Specific exception instead of bare except
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    return render(request, 'profile.html', {
        'user': request.user, 'profile': profile,
    })


def edit_profile(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        # Shared fields
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name  = request.POST.get('last_name', '').strip()
        request.user.email      = request.POST.get('email', '').strip()
        request.user.save()

        profile.phone = request.POST.get('phone', '').strip()
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']

        if profile.role == 'faculty':
            # Faculty-only fields
            profile.teacher_id        = request.POST.get('teacher_id', '').strip()
            profile.department        = request.POST.get('department', '')
            exp = request.POST.get('experience', '').strip()
            profile.experience        = int(exp) if exp.isdigit() else None
            profile.subjects_teaching = request.POST.get('subjects_teaching', '').strip()
            profile.linkedin          = request.POST.get('linkedin', '').strip() or None
        else:
            # Student-only fields
            profile.roll_no  = request.POST.get('roll_no', '').strip()
            profile.year     = request.POST.get('year', '')
            profile.branch   = request.POST.get('branch', '')
            profile.linkedin = request.POST.get('linkedin', '').strip() or None
            profile.codechef = request.POST.get('codechef', '').strip()
            profile.leetcode = request.POST.get('leetcode', '').strip()

        profile.save()
        messages.success(request, 'Profile updated!')
        return redirect('profile')

    return render(request, 'edit_profile.html', {
        'user':     request.user,
        'profile':  profile,
        'branches': BRANCH_CHOICES,
        'years':    YEAR_CHOICES,
    })
    from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def compiler(request):
    profile = None
    try:
        profile = request.user.profile
    except Exception:
        pass

    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'compiler.html', context)