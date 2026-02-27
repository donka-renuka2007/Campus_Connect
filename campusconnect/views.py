from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import UserProfile, Announcement, BRANCH_CHOICES, YEAR_CHOICES,Goal, QuizQuestion, GoalSubmission, QuizAnswer
from django.utils import timezone
import json
from groq import Groq
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import LibraryRecord
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




# ─────────────────────────────────────────────────────────────────────────────
# GOALS HUB  (branch point: teacher vs student)
# ─────────────────────────────────────────────────────────────────────────────

def goals(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    is_faculty = profile and profile.role == 'faculty'

    if is_faculty:
        # Teacher sees all goals they created
        goals_list = Goal.objects.filter(assigned_by=request.user)
        return render(request, 'goals/teacher_goals.html', {
            'goals': goals_list,
            'user': request.user,
            'profile': profile,
        })
    else:
        # Student sees goals assigned to them
        today = timezone.now().date()
        goals_list = Goal.objects.filter(assigned_to=request.user)

        # Auto-mark overdue
        goals_list.filter(due_date__lt=today, status='active').update(status='overdue')

        # Annotate with submission status
        annotated = []
        for g in goals_list:
            sub = GoalSubmission.objects.filter(goal=g, student=request.user).first()
            annotated.append({'goal': g, 'submission': sub})

        return render(request, 'goals/student_goals.html', {
            'annotated': annotated,
            'user': request.user,
            'profile': profile,
        })


# ─────────────────────────────────────────────────────────────────────────────
# TEACHER: CREATE GOAL
# ─────────────────────────────────────────────────────────────────────────────

def create_goal(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        return redirect('goals')

    if profile.role != 'faculty':
        messages.error(request, 'Only faculty can create goals.')
        return redirect('goals')

    students = User.objects.filter(profile__role='student').select_related('profile')

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        goal_type   = request.POST.get('goal_type', 'task')
        start_date  = request.POST.get('start_date')
        due_date    = request.POST.get('due_date')
        res_link    = request.POST.get('resource_link', '').strip() or None
        res_file    = request.FILES.get('resource_file')
        student_ids = request.POST.getlist('students')  # list of user IDs

        # Validation
        if not title or not start_date or not due_date:
            messages.error(request, 'Title, start date and due date are required.')
            return render(request, 'goals/create_goal.html', {
                'students': students,
                'user': request.user,
                'profile': profile,
            })

        # Create Goal
        goal = Goal.objects.create(
            title=title,
            description=description,
            goal_type=goal_type,
            assigned_by=request.user,
            start_date=start_date,
            due_date=due_date,
            resource_link=res_link,
            resource_file=res_file if res_file else None,
        )

        # Assign students
        if student_ids:
            # Filter to valid IDs only
            valid_students = User.objects.filter(id__in=student_ids, profile__role='student')
            goal.assigned_to.set(valid_students)
        else:
            # Assign to ALL students if none selected
            goal.assigned_to.set(students)

        # If quiz: handle questions
        if goal_type == 'quiz':
            i = 1
            while True:
                q_text = request.POST.get(f'q_text_{i}', '').strip()
                if not q_text:
                    break
                qtype   = request.POST.get(f'q_type_{i}', 'mcq')
                opt_a   = request.POST.get(f'q_a_{i}', '').strip()
                opt_b   = request.POST.get(f'q_b_{i}', '').strip()
                opt_c   = request.POST.get(f'q_c_{i}', '').strip()
                opt_d   = request.POST.get(f'q_d_{i}', '').strip()
                correct = request.POST.get(f'q_correct_{i}', '').strip()
                QuizQuestion.objects.create(
                    goal=goal,
                    qtype=qtype,
                    question=q_text,
                    option_a=opt_a,
                    option_b=opt_b,
                    option_c=opt_c,
                    option_d=opt_d,
                    correct=correct.upper(),
                    order=i,
                )
                i += 1

        messages.success(request, f'Goal "{title}" created and assigned to {goal.assigned_to.count()} student(s)!')
        return redirect('goals')

    return render(request, 'goals/create_goal.html', {
        'students': students,
        'user': request.user,
        'profile': profile,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TEACHER: VIEW SUBMISSIONS FOR A GOAL
# ─────────────────────────────────────────────────────────────────────────────

def goal_submissions(request, goal_id):
    if not request.user.is_authenticated:
        return redirect('login')

    # Teacher must own this goal
    goal = get_object_or_404(Goal, id=goal_id, assigned_by=request.user)

    # Get ALL submissions for this goal with related data
    submissions = GoalSubmission.objects.filter(
        goal=goal
    ).select_related('student', 'student__profile').prefetch_related('answers')

    assigned_students = goal.assigned_to.all().select_related('profile')
    assigned_count = assigned_students.count()

    # Build a "not submitted yet" list too
    submitted_student_ids = submissions.values_list('student_id', flat=True)
    not_submitted = assigned_students.exclude(id__in=submitted_student_ids)

    return render(request, 'goals/goal_submissions.html', {
        'goal': goal,
        'submissions': submissions,
        'not_submitted': not_submitted,
        'assigned_count': assigned_count,
        'submitted_count': submissions.count(),
        'user': request.user,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TEACHER: GIVE FEEDBACK ON SUBMISSION
# ─────────────────────────────────────────────────────────────────────────────

def review_submission(request, sub_id):
    if not request.user.is_authenticated:
        return redirect('login')
    sub = get_object_or_404(GoalSubmission, id=sub_id, goal__assigned_by=request.user)

    if request.method == 'POST':
        sub.feedback = request.POST.get('feedback', '').strip()
        sub.status   = request.POST.get('status', 'reviewed')
        sub.save()
        messages.success(request, 'Feedback saved!')
        return redirect('goal_submissions', goal_id=sub.goal.id)

    return render(request, 'goals/review_submission.html', {
        'sub': sub,
        'user': request.user,
    })


# ─────────────────────────────────────────────────────────────────────────────
# STUDENT: VIEW GOAL DETAIL + SUBMIT
# ─────────────────────────────────────────────────────────────────────────────

def goal_detail(request, goal_id):
    if not request.user.is_authenticated:
        return redirect('login')

    goal = get_object_or_404(Goal, id=goal_id, assigned_to=request.user)
    existing_sub = GoalSubmission.objects.filter(goal=goal, student=request.user).first()

    if request.method == 'POST' and not existing_sub:
        note = request.POST.get('note', '').strip()
        file = request.FILES.get('submission_file')

        sub = GoalSubmission.objects.create(
            goal=goal,
            student=request.user,
            note=note,
            file=file if file else None,
        )

        # If quiz: process answers
        if goal.goal_type == 'quiz':
            questions = goal.questions.all()
            score = 0
            for q in questions:
                ans = request.POST.get(f'answer_{q.id}', '').strip()
                is_correct = None
                if q.qtype == 'mcq':
                    is_correct = ans.upper() == q.correct.upper()
                    if is_correct:
                        score += 1
                QuizAnswer.objects.create(
                    submission=sub, question=q,
                    answer=ans, is_correct=is_correct
                )
            sub.quiz_score = score
            sub.quiz_total = questions.count()
            sub.save()

        messages.success(request, 'Submitted successfully!')
        return redirect('goal_detail', goal_id=goal_id)

    return render(request, 'goals/goal_detail.html', {
        'goal': goal,
        'submission': existing_sub,
        'questions': goal.questions.all() if goal.goal_type == 'quiz' else [],
        'user': request.user,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TEACHER: DELETE GOAL
# ─────────────────────────────────────────────────────────────────────────────

def delete_goal(request, goal_id):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        goal = get_object_or_404(Goal, id=goal_id, assigned_by=request.user)
        goal.delete()
        messages.success(request, 'Goal deleted.')
    return redirect('goals')



def chatbot_api(request):
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
        history = body.get("history", [])

        if not user_message:
            return JsonResponse({"reply": "Please send a message."}, status=400)

        client = Groq(api_key=settings.GROQ_API_KEY)

        messages = [
            {
                "role": "system",
                "content": """You are Campus AI Assistant, a helpful academic bot for Campus Connect — a student platform.
You help students with academic concepts, exam prep, assignments, and study strategies.
Be concise, friendly, and encouraging. Use **bold** for key terms and numbered lists for steps."""
            }
        ]

        # Add chat history (last 10 messages for context)
        for item in history[-10:]:
            role = item.get("role")
            content = item.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # free, fast model
            messages=messages,
            max_tokens=1024,
        )

        reply = response.choices[0].message.content
        return JsonResponse({"reply": reply})

    except Exception as e:
        return JsonResponse({"reply": f"⚠️ Error: {str(e)}"}, status=500)
@login_required
def chatbot(request):
    profile = getattr(request.user, 'profile', None)
    return render(request, 'chatbot.html', {'profile': profile})





# ──────────────────────────────────────────────
# HELPER: Check if user is a teacher
# Teachers = staff users OR users in 'Teacher' group
# ──────────────────────────────────────────────
def is_teacher(user):
    profile = getattr(user, 'profile', None)
    return profile is not None and profile.role == 'faculty'


# ──────────────────────────────────────────────
# MAIN LIBRARY VIEW — routes to teacher or student
# ──────────────────────────────────────────────
@login_required
def library(request):
    profile = getattr(request.user, 'profile', None)
    if is_teacher(request.user):
        return teacher_library(request, profile)
    else:
        return student_library(request, profile)


# ──────────────────────────────────────────────
# TEACHER LIBRARY VIEW
# ──────────────────────────────────────────────
def teacher_library(request, profile):
    if request.method == 'POST':
        student_id    = request.POST.get('student_id')
        book_name     = request.POST.get('book_name', '').strip()
        book_no       = request.POST.get('book_no', '').strip()
        start_date    = request.POST.get('start_date')
        due_date      = request.POST.get('due_date')
        penalty_per_day = request.POST.get('penalty_per_day', 0)

        if not all([student_id, book_name, book_no, start_date, due_date]):
            messages.error(request, 'Please fill in all fields.')
            return redirect('library')

        student = get_object_or_404(User, id=student_id)

        LibraryRecord.objects.create(
            issued_by=request.user,
            student=student,
            book_name=book_name,
            book_no=book_no,
            start_date=start_date,
            due_date=due_date,
            penalty_per_day=penalty_per_day,
        )
        messages.success(request, f'Book "{book_name}" issued to {student.get_full_name() or student.username}.')
        return redirect('library')

    # All records issued by this teacher
    records = LibraryRecord.objects.filter(
        issued_by=request.user
    ).select_related('student')

    # Get student list — try 'Student' group first, fallback to all non-staff
    students = User.objects.filter(
    profile__role='student',
    is_active=True
      ).order_by('first_name', 'username')

    # Stats for teacher dashboard
    total      = records.count()
    overdue    = sum(1 for r in records if r.days_overdue > 0 and not r.is_returned)
    returned   = records.filter(is_returned=True).count()
    active     = total - returned

    return render(request, 'library_teacher.html', {
        'profile':  profile,
        'records':  records,
        'students': students,
        'today':    timezone.now().date(),
        'stats': {
            'total':    total,
            'active':   active,
            'overdue':  overdue,
            'returned': returned,
        }
    })


# ──────────────────────────────────────────────
# STUDENT LIBRARY VIEW
# ──────────────────────────────────────────────
def student_library(request, profile):
    records = LibraryRecord.objects.filter(
        student=request.user
    ).select_related('issued_by')

    today = timezone.now().date()

    records_data = []
    total_penalty = 0

    for r in records:
        days_overdue = 0
        if not r.is_returned and today > r.due_date:
            days_overdue = (today - r.due_date).days

        current_penalty = float(r.penalty_per_day) * days_overdue
        total_penalty += current_penalty

        records_data.append({
            'record':          r,
            'days_overdue':    days_overdue,
            'current_penalty': current_penalty,
        })

    active_count = sum(1 for rd in records_data if not rd['record'].is_returned)

    return render(request, 'library_student.html', {
        'profile':       profile,
        'records_data':  records_data,
        'today':         today,
        'total_penalty': total_penalty,
        'active_count':  active_count,
    })


# ──────────────────────────────────────────────
# AJAX: Teacher marks a book as returned/done
# POST /library/mark-returned/<id>/
# ──────────────────────────────────────────────
@login_required
@require_POST
def mark_returned(request, record_id):
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    record = get_object_or_404(LibraryRecord, id=record_id, issued_by=request.user)

    if record.is_returned:
        return JsonResponse({'error': 'Already marked as returned'}, status=400)

    record.is_returned    = True
    record.returned_date  = timezone.now().date()
    record.save()

    return JsonResponse({
        'success':       True,
        'returned_date': str(record.returned_date),
        'record_id':     record.id,
    })


# ──────────────────────────────────────────────
# AJAX: Live penalty data for student
# GET /library/penalty/<id>/
# ──────────────────────────────────────────────
@login_required
def penalty_api(request, record_id):
    record = get_object_or_404(LibraryRecord, id=record_id, student=request.user)

    today = timezone.now().date()
    days_overdue = 0

    if not record.is_returned and today > record.due_date:
        days_overdue = (today - record.due_date).days

    penalty = float(record.penalty_per_day) * days_overdue

    return JsonResponse({
        'record_id':    record.id,
        'days_overdue': days_overdue,
        'penalty':      round(penalty, 2),
        'is_returned':  record.is_returned,
        'returned_date': str(record.returned_date) if record.returned_date else None,
        'status':       record.status,
    })








import os
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from resources.models import Resource   # ← your resources app


@login_required
def self_study(request):
    """Shows all uploaded resources for student to pick one to study."""
    profile = getattr(request.user, 'profile', None)

    resources_qs = Resource.objects.all().order_by('-uploaded_at')

    resources = []
    for res in resources_qs:
        file_type = get_file_type(res.file.name)
        resources.append({
            'id':          res.id,
            'title':       res.title,
            'subject':     res.subject,
            'description': res.description,
            'file':        res.file,
            'file_type':   file_type,
            'icon':        get_file_icon(file_type),
            'file_size':   get_file_size(res.file),
            'uploaded_by': res.uploaded_by,
            'created_at':  res.uploaded_at,   # ← your field is uploaded_at
        })

    return render(request, 'self_study.html', {
        'profile':   profile,
        'resources': resources,
    })


@login_required
def self_study_workspace(request, resource_id):
    """Opens split-screen workspace for a specific resource."""
    profile  = getattr(request.user, 'profile', None)
    resource = get_object_or_404(Resource, id=resource_id)

    # Attach computed fields to the resource object
    resource.file_type = get_file_type(resource.file.name)
    resource.subject_display = dict(Resource.SUBJECT_CHOICES).get(resource.subject, resource.subject)

    return render(request, 'self_study_workspace.html', {
        'profile':  profile,
        'resource': resource,
    })


# ── Helper functions ──────────────────────────────────────

def get_file_type(filename):
    if not filename:
        return 'other'
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        return 'pdf'
    elif ext in ['.doc', '.docx']:
        return 'doc'
    elif ext in ['.ppt', '.pptx']:
        return 'ppt'
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']:
        return 'img'
    else:
        return 'other'


def get_file_icon(file_type):
    return {
        'pdf':   '📄',
        'doc':   '📝',
        'ppt':   '📊',
        'img':   '🖼',
        'other': '📎',
    }.get(file_type, '📎')


def get_file_size(file_field):
    try:
        size = file_field.size
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size // 1024} KB'
        else:
            return f'{size / (1024*1024):.1f} MB'
    except Exception:
        return '—'








import json
import re
import os
import math
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings          # ← WAS MISSING
from groq import Groq                     # ← WAS MISSING
from resources.models import Resource     # ← WAS MISSING (at top level)


# ── Helper 1: file type detector ──────────────────────────────────
def get_file_type(filename):
    if not filename:
        return 'other'
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':                                return 'pdf'
    elif ext in ['.doc', '.docx']:                   return 'doc'
    elif ext in ['.ppt', '.pptx']:                   return 'ppt'
    elif ext in ['.png','.jpg','.jpeg','.gif','.webp','.svg']: return 'img'
    return 'other'


# ── Helper 2: extract text from PDF ───────────────────────────────
def extract_text_from_pdf(file_path):
    try:
        import PyPDF2
        parts = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:20]:
                t = page.extract_text()
                if t:
                    parts.append(t)
        text = '\n'.join(parts)
        if len(text.strip()) > 100:
            return text   # normal PDF — text extracted fine

        # Fallback: scanned PDF — use OCR
        print("[PDF] Text too short, trying OCR...")
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(file_path, first_page=1, last_page=10)
        ocr_parts = [pytesseract.image_to_string(img) for img in images]
        return '\n'.join(ocr_parts)

    except Exception as e:
        print(f"[PDF] ERROR: {e}")
        return ""


# ── Helper 3: split text into overlapping chunks ──────────────────
def chunk_text(text, chunk_size=400, overlap=60):
    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# ── Helper 4: simple TF-IDF search ───────────────────────────────
def simple_tfidf_search(query, chunks, top_k=4):
    if not chunks:
        return []

    def tokenize(text):
        return re.findall(r'\b\w+\b', text.lower())

    query_tokens = set(tokenize(query))
    num_docs     = len(chunks)
    scores       = []

    for chunk in chunks:
        chunk_tokens = tokenize(chunk)
        if not chunk_tokens:
            scores.append(0)
            continue
        counts = {}
        for t in chunk_tokens:
            counts[t] = counts.get(t, 0) + 1
        score = 0
        for token in query_tokens:
            if token in counts:
                tf  = counts[token] / len(chunk_tokens)
                df  = sum(1 for c in chunks if token in tokenize(c))
                idf = math.log((num_docs + 1) / (df + 1)) + 1
                score += tf * idf
        scores.append(score)

    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    top    = [chunks[i] for i in ranked[:top_k] if scores[i] > 0]
    return top if top else chunks[:top_k]


# ── Main RAG view ─────────────────────────────────────────────────
@login_required
@csrf_exempt
def rag_chatbot_api(request, resource_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    # Parse body
    try:
        body     = json.loads(request.body)
        question = body.get("question", "").strip()
        history  = body.get("history", [])
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not question:
        return JsonResponse({"error": "No question"}, status=400)

    # Get resource
    try:
        resource = Resource.objects.get(pk=resource_id)
    except Resource.DoesNotExist:
        return JsonResponse({"error": "Resource not found"}, status=404)

    # Extract context from file
    context_text = ""
    file_type    = get_file_type(resource.file.name)

    if resource.file and file_type == "pdf":
        raw_text = extract_text_from_pdf(resource.file.path)
        if raw_text and len(raw_text.strip()) > 100:
            chunks       = chunk_text(raw_text, chunk_size=400, overlap=60)
            relevant     = simple_tfidf_search(question, chunks, top_k=4)
            context_text = "\n\n---\n\n".join(relevant)

    # Build system prompt
    if context_text:
        system_prompt = (
            "You are a helpful AI study assistant. "
            "Answer the student's question using ONLY the document context below. "
            "If the answer is not in the context, say so clearly. "
            "Be concise, clear, and educational. Use bullet points or code blocks where helpful.\n\n"
            f"=== DOCUMENT CONTEXT ===\n{context_text}\n=== END CONTEXT ==="
        )
    else:
        system_prompt = (
            f"You are a helpful AI study assistant for subject: {resource.subject}. "
            f"The student is studying '{resource.title}'. "
            "The document could not be parsed (not a PDF or text extraction failed). "
            "Answer using your general knowledge about this subject."
        )

    # Build messages
    messages_list = [{"role": "system", "content": system_prompt}]
    for turn in history[-6:]:
        role    = turn.get("role")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages_list.append({"role": role, "content": content})
    messages_list.append({"role": "user", "content": question})

    # Call Groq
    try:
        api_key = settings.GROQ_API_KEY
        if not api_key:
            return JsonResponse({"error": "GROQ_API_KEY not set in .env / settings.py"}, status=500)

        client   = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_list,
            max_tokens=1024,
            temperature=0.7,
        )
        answer = response.choices[0].message.content
        return JsonResponse({"answer": answer})

    except Exception as e:
        return JsonResponse({"error": f"LLM error: {str(e)}"}, status=500)




#complaint views

def is_teacher(user):
    try:
        return user.profile.role == 'faculty'
    except Exception:
        return False


@login_required
def complaint_portal(request):
    """Routes to student or faculty view."""
    profile = getattr(request.user, 'profile', None)
    if is_teacher(request.user):
        return redirect('complaint_faculty')
    return redirect('complaint_student')


@login_required
def complaint_student(request):
    """Student: view own complaints + submit new."""
    from .models import Complaint   # adjust app name if needed

    profile   = getattr(request.user, 'profile', None)
    teachers  = User.objects.filter(profile__role='faculty').order_by('first_name', 'last_name')
    complaints = Complaint.objects.filter(student=request.user)

    if request.method == 'POST':
        teacher_id     = request.POST.get('teacher')
        heading        = request.POST.get('heading', '').strip()
        description    = request.POST.get('description', '').strip()
        complaint_type = request.POST.get('complaint_type')
        urgency        = request.POST.get('urgency', 'normal')

        if teacher_id and heading and description and complaint_type:
            teacher = get_object_or_404(User, id=teacher_id)
            Complaint.objects.create(
                student=request.user,
                teacher=teacher,
                heading=heading,
                description=description,
                complaint_type=complaint_type,
                urgency=urgency,
            )
        return redirect('complaint_student')

    return render(request, 'complaint_student.html', {
        'profile':    profile,
        'teachers':   teachers,
        'complaints': complaints,
        'type_choices': Complaint.COMPLAINT_TYPES,
    })


@login_required
def complaint_edit(request, complaint_id):
    """Student edits their own complaint (only if pending)."""
    from .models import Complaint

    complaint = get_object_or_404(Complaint, id=complaint_id, student=request.user)

    if complaint.status != 'pending':
        return redirect('complaint_student')  # can't edit after viewed/solved

    if request.method == 'POST':
        complaint.heading        = request.POST.get('heading', complaint.heading).strip()
        complaint.description    = request.POST.get('description', complaint.description).strip()
        complaint.complaint_type = request.POST.get('complaint_type', complaint.complaint_type)
        complaint.urgency        = request.POST.get('urgency', complaint.urgency)
        teacher_id = request.POST.get('teacher')
        if teacher_id:
            complaint.teacher = get_object_or_404(User, id=teacher_id)
        complaint.save()
        return redirect('complaint_student')

    profile  = getattr(request.user, 'profile', None)
    teachers = User.objects.filter(profile__role='faculty').order_by('first_name', 'last_name')

    return render(request, 'complaint_edit.html', {
        'profile':    profile,
        'complaint':  complaint,
        'teachers':   teachers,
        'type_choices': Complaint.COMPLAINT_TYPES,
    })


@login_required
def complaint_delete(request, complaint_id):
    """Student deletes their own complaint."""
    from .models import Complaint
    complaint = get_object_or_404(Complaint, id=complaint_id, student=request.user)
    if request.method == 'POST':
        complaint.delete()
    return redirect('complaint_student')


@login_required
def complaint_faculty(request):
    from .models import Complaint

    if not is_teacher(request.user):
        return redirect('complaint_student')

    profile    = getattr(request.user, 'profile', None)
    complaints = Complaint.objects.filter(teacher=request.user)

    return render(request, 'complaint_faculty.html', {
        'profile':       profile,
        'complaints':    complaints,
        'pending_count': complaints.filter(status='pending').count(),
        'viewed_count':  complaints.filter(status='viewed').count(),
        'solved_count':  complaints.filter(status='solved').count(),
        'urgent_count':  complaints.filter(urgency='urgent', status='pending').count(),
    })


@login_required
@require_POST
def complaint_update_status(request, complaint_id):
    """Faculty marks complaint as viewed or solved via AJAX."""
    from .models import Complaint

    if not is_teacher(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    complaint = get_object_or_404(Complaint, id=complaint_id, teacher=request.user)
    data   = json.loads(request.body)
    status = data.get('status')

    if status in ('viewed', 'solved'):
        complaint.status = status
        complaint.save()
        return JsonResponse({'ok': True, 'status': status})

    return JsonResponse({'error': 'Invalid status'}, status=400)







#permission views




import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import Permission


def is_teacher(user):
    try:
        return user.profile.role == 'faculty'
    except Exception:
        return False


# ─────────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────────

@login_required
def permission_portal(request):
    """Routes to student or faculty view."""
    if is_teacher(request.user):
        return redirect('permission_faculty')
    return redirect('permission_student')


# ─────────────────────────────────────────────
#  STUDENT VIEWS
# ─────────────────────────────────────────────

@login_required
def permission_student(request):
    """Student: view own permission letters + submit new."""
    profile     = getattr(request.user, 'profile', None)
    teachers    = User.objects.filter(profile__role='faculty').order_by('first_name', 'last_name')
    permissions = Permission.objects.filter(student=request.user)

    if request.method == 'POST':
        teacher_id      = request.POST.get('teacher')
        heading         = request.POST.get('heading', '').strip()
        description     = request.POST.get('description', '').strip()
        permission_type = request.POST.get('permission_type')
        urgency         = request.POST.get('urgency', 'normal')
        start_date      = request.POST.get('start_date')
        end_date        = request.POST.get('end_date')

        if teacher_id and heading and description and permission_type:
            teacher = get_object_or_404(User, id=teacher_id)
            Permission.objects.create(
                student=request.user,
                teacher=teacher,
                heading=heading,
                description=description,
                permission_type=permission_type,
                urgency=urgency,
                start_date=start_date or None,
                end_date=end_date or None,
            )
        return redirect('permission_student')

    return render(request, 'permission_student.html', {
        'profile':      profile,
        'teachers':     teachers,
        'permissions':  permissions,
        'type_choices': Permission.PERMISSION_TYPES,
    })


@login_required
def permission_edit(request, permission_id):
    """Student edits their own permission letter (only if pending)."""
    permission = get_object_or_404(Permission, id=permission_id, student=request.user)

    if permission.status != 'pending':
        return redirect('permission_student')

    if request.method == 'POST':
        permission.heading         = request.POST.get('heading', permission.heading).strip()
        permission.description     = request.POST.get('description', permission.description).strip()
        permission.permission_type = request.POST.get('permission_type', permission.permission_type)
        permission.urgency         = request.POST.get('urgency', permission.urgency)
        permission.start_date      = request.POST.get('start_date') or permission.start_date
        permission.end_date        = request.POST.get('end_date') or permission.end_date
        teacher_id = request.POST.get('teacher')
        if teacher_id:
            permission.teacher = get_object_or_404(User, id=teacher_id)
        permission.save()
        return redirect('permission_student')

    profile  = getattr(request.user, 'profile', None)
    teachers = User.objects.filter(profile__role='faculty').order_by('first_name', 'last_name')

    return render(request, 'permission_edit.html', {
        'profile':      profile,
        'permission':   permission,
        'teachers':     teachers,
        'type_choices': Permission.PERMISSION_TYPES,
    })


@login_required
def permission_delete(request, permission_id):
    """Student deletes their own pending permission letter."""
    permission = get_object_or_404(Permission, id=permission_id, student=request.user)
    if request.method == 'POST':
        if permission.status == 'pending':
            permission.delete()
    return redirect('permission_student')


# ─────────────────────────────────────────────
#  FACULTY VIEWS
# ─────────────────────────────────────────────

@login_required
def permission_faculty(request):
    """Faculty: see all permission letters sent to them."""
    if not is_teacher(request.user):
        return redirect('permission_student')

    profile     = getattr(request.user, 'profile', None)
    permissions = Permission.objects.filter(teacher=request.user)

    return render(request, 'permission_faculty.html', {
        'profile':        profile,
        'permissions':    permissions,
        'pending_count':  permissions.filter(status='pending').count(),
        'accepted_count': permissions.filter(status='accepted').count(),
        'rejected_count': permissions.filter(status='rejected').count(),
        'urgent_count':   permissions.filter(urgency='urgent', status='pending').count(),
    })


@login_required
@require_POST
def permission_update_status(request, permission_id):
    """Faculty accepts or rejects a permission letter via AJAX."""
    if not is_teacher(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    permission = get_object_or_404(Permission, id=permission_id, teacher=request.user)

    data   = json.loads(request.body)
    status = data.get('status')
    remark = data.get('remark', '').strip()

    if status in ('accepted', 'rejected'):
        permission.status = status
        if remark:
            permission.remark = remark
        permission.save()
        return JsonResponse({'ok': True, 'status': status})

    return JsonResponse({'error': 'Invalid status'}, status=400)