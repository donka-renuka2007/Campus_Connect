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