from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from .models import User, Room, Topic, Message, Course, Post, CourseMessage, ContactMessage
from .forms import RoomForm, UserForm, PostForm, MyUserCreationForm, UserCreationForm, ApplyTeacherForm, ApplyStudentForm
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.contrib.auth.models import Group
from django.forms.utils import ErrorList
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from agora_token_builder import RtcTokenBuilder
import random
import time
from datetime import datetime
from datetime import timedelta
from django.utils import timezone

def getToken(request):
    appId = '770b21a50e5c43f7afee0b043509cdbb'
    appCertificate = '1e44bf1ba1fd49018795989293a7382c'
    channelName = request.GET.get('channel')
    uid = random.randint(1, 230)
    expirationTimeInSeconds = 3600*24
    currentTimeStamp = time.time()
    privilegeExpiredTs = currentTimeStamp + expirationTimeInSeconds
    role = 1

    token = RtcTokenBuilder.buildTokenWithUid(appId, appCertificate, channelName, uid, role, privilegeExpiredTs)

    return JsonResponse({'token': token, 'uid': uid}, safe=False)


def check_user_exists_in_group(username):
    try:
        user = User.objects.get(username=username)
        if user.groups.exists():
            return True
        else:
            return False
    except User.DoesNotExist:
        return False


def check_user_group(username):
    try:
        user = User.objects.get(username=username)
        if user.groups.exists():
            user_groups = user.groups.all()
            return True, user_groups
        else:
            return False, []
    except User.DoesNotExist:
        return False, []


def change_user_group(user, new_group_name):
    try:
        new_group = Group.objects.get(name=new_group_name)
        user.groups.set([new_group])
        user.save()
        return True
    except Group.DoesNotExist:
        return False


def home(request):
    return render(request, 'website/widget.html')


def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        message = request.POST.get('message')
        ContactMessage.objects.create(email=email, phone_number=phone_number, message=message)
    return render(request, 'website/widget.html')


def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=email)
        except:
            messages.error(request, "Podany użytkownik nie istnieje.")

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Nazwa użytkownika lub hasło nie istnieje.")

    context = {'page': page}
    return render(request, 'website/login_register.html', context)

def logoutUser(request):
    logout(request)
    return redirect('dashboard')

def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')

            if check_user_exists_in_group(username):
                messages.error(request, 'Użytkownik już istnieje w grupie.')
                return redirect('registerPage')

            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            user.groups.add(Group.objects.get(name='Writers'))
            login(request, user)
            return redirect('dashboard')

        else:
            # Wyświetlanie komunikatów o błędach formularza
            errors = form.errors.as_data()
            for field, field_errors in errors.items():
                for error in field_errors:
                    messages.error(request, f"{field}: {error.message}")

            # Dodanie błędów formularza do kontekstu
            form._errors = ErrorList()

    context = {'form': form}
    return render(request, 'website/login_register.html', context)

def dashboard(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description__icontains=q)
    )

    topics = Topic.objects.all()[0:28]
    room_count = rooms.count()
    room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))[0:7]
    context = {'rooms': rooms, 'topics': topics, 'room_count': room_count,
               'room_messages': room_messages}
    return render(request, 'website/dashboard.html', context)


def room(request, pk):
    room = Room.objects.get(id=pk)
    room_messages = room.message_set.all().order_by('-created')
    participants = room.participants.all()

    if request.method == 'POST':
        message = Message.objects.create(
            user=request.user,
            room=room,
            body=request.POST.get('body'),
            image=request.FILES.get('image')
        )
        room.participants.add(request.user)

        message.save()
        return redirect('room', pk=room.id)

    context = {'room': room, 'room_messages': room_messages, 'participants': participants}
    return render(request, 'website/room.html', context)


def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    topics = Topic.objects.all()
    context = {'user': user, 'rooms': rooms, 'room_messages': room_messages, 'topics': topics}
    return render(request, 'website/profile.html', context)


@login_required(login_url='login')
def createRoom(request):
    form = RoomForm(request.POST, request.FILES)
    topics = Topic.objects.all()
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic = get_object_or_404(Topic, id=topic_name)

        room = Room(
            host=request.user,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            topic=topic,
        )

        if 'image' in request.FILES:
            image_file = request.FILES['image']
            room.image.save(image_file.name, ContentFile(image_file.read()))

        room.save()
        return redirect('dashboard')

    context = {'form': form, 'topics': topics}
    return render(request, 'website/room_form.html', context)


@login_required(login_url='login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()

    if request.user != room.host:
        return HttpResponse('Operacja wzbroniona.')

    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            form.save()
            return redirect('dashboard')

    context = {'form': form, 'topics': topics}
    return render(request, 'website/room_form.html', context)


@login_required(login_url='login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HttpResponse('Operacja wzbroniona.')

    if request.method == 'POST':
        room.delete()
        return redirect('dashboard')
    return render(request, 'website/delete.html', {'obj': room})


@login_required(login_url='login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse('Operacja wzbroniona.')

    if request.method == 'POST':
        message.delete()
        return redirect('dashboard')
    return render(request, 'website/delete.html', {'obj': message})


@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            redirect('user-profile', pk=user.id)
    return render(request, 'website/update-user.html', {'form': form})


def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    topics = Topic.objects.filter(name__icontains=q)
    return render(request, 'website/topics.html', {'topics': topics})


def activityPage(request):
    room_messages = Message.objects.all()
    return render(request, 'website/activity.html', {'room_messages':room_messages})


def lessonsLogin(request):
    page = 'lessonsLogin'

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except:
            messages.error(request, 'Użytkownik nie istnieje')

        user = authenticate(request, username=username, password=password)

        if user is not None and (user.groups.filter(name='Students').exists() or
                                 user.groups.filter(name='Teachers').exists() or
                                 user.groups.filter(name='NONE').exists() or
                                 user.groups.filter(name='Writers').exists() or
                                 user.groups.filter(name='Migrates').exists()):
            if user.groups.filter(name='Teachers').exists():
                login(request, user)
                return redirect('teacherPage')
            elif user.groups.filter(name='Students').exists():
                if user.lessons > 0:
                    login(request, user)
                    return redirect('studentPage')
                else:
                    return redirect('noLessons')
            elif user.groups.filter(name='NONE').exists():
                return redirect('coursesLoader')
            elif user.groups.filter(name='Migrates').exists():
                return redirect('coursesLoader')
            elif user.groups.filter(name='Writers').exists():
                change_user_group(user, 'Migrates')
                return redirect('coursesLoader')
        else:
            messages.error(request, 'Nazwa użytkownika lub hasło nie istnieje')

    context = {'page': page}
    return render(request, 'website/login_register_lessons.html', context)


def lessonsRegister(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            user.groups.add(Group.objects.get(name='NONE'))
            return redirect('lessonsLogin')
        else:
            messages.error(request, 'Wystąpił błąd podczas próby rejestracji.')

    context = {'form': form}
    return render(request, 'website/login_register_lessons.html', context)


def lessonsLogout(request):
    logout(request)
    return redirect('lessons-home')


def coursesLoader(request):
    return render(request, 'website/userCreator.html')

def noLessons(request):
    return render(request, 'website/noLessons.html')


@login_required(login_url='lessonsLogin')
def teacherPage(request):
    now = datetime.now()
    time_difference = timedelta(minutes=50)
    time_threshold = now - time_difference
    a = 0
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    teacher = request.user
    courses = Course.objects.filter(teacher=teacher)
    students = User.objects.filter(groups__name='Students', courses_enrolled__in=courses)
    all_courses = Course.objects.all()
    lessons = Post.objects.filter(
        Q(course__in=courses) & (Q(course__teacher__in=students) | Q(course__name__icontains=q) | Q(title__icontains=q))
    )

    post_count = lessons.count()
    lesson_messages = CourseMessage.objects.filter(room__in=lessons)

    context = {'lessons': lessons, 'courses': courses, 'post_count': post_count, 'lesson_messages': lesson_messages, 'all_courses': all_courses, 'now':now, 'time_threshold': time_threshold, 'a':a}
    return render(request, 'website/teacherPage.html', context)


@login_required(login_url='lessonsLogin')
def studentPage(request):
    now = datetime.now()
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    student = request.user
    courses = Course.objects.filter(students=student)
    teachers = User.objects.filter(groups__name='Teachers', courses_taught__in=courses)
    other_students = User.objects.filter(groups__name='Students', courses_enrolled__in=courses).exclude(id=student.id)
    all_courses = Course.objects.all()
    lessons = Post.objects.filter(
        Q(course__in=courses) & (Q(course__teacher__in=teachers) | Q(host__in=other_students)) & (Q(course__name__icontains=q) | Q(title__icontains=q))
    )

    post_count = lessons.count()
    lesson_messages = CourseMessage.objects.filter(Q(room__in=lessons) & (Q(user__in=teachers) | Q(user__in=other_students)))

    context = {'lessons': lessons, 'courses': courses, 'post_count': post_count, 'lesson_messages': lesson_messages, 'all_courses': all_courses, 'now': now}
    return render(request, 'website/studentPage.html', context)


def lessonsHome(request):
    user = request.user

    if user.groups.filter(name='Teachers').exists():
        return redirect('teacherPage')  # Replace 'teachers-page' with your actual URL name for the teachers' page
    elif user.groups.filter(name='Students').exists():
        return redirect('studentPage')  # Replace 'students-page' with your actual URL name for the students' page

    return render(request, 'website/lessonsHome.html')


def lesson(request, pk):
    lesson = Post.objects.get(id=pk)
    lesson_messages = lesson.coursemessage_set.all()
    participants = lesson.participants.all()

    if request.method == 'POST':
        message = CourseMessage.objects.create(
            user=request.user,
            room=lesson,
            body=request.POST.get('body')
        )
        return redirect('lesson', pk=lesson.id)

    lesson.participants.add(request.user)

    user = request.user
    if user.groups.filter(name='Teachers').exists():
        navbar_template = 'navbarTeacher.html'
        back_link = reverse('teacherPage')  # Replace 'teacher-page' with your actual URL name for the teacher page
    elif user.groups.filter(name='Students').exists():
        navbar_template = 'navbarStudent.html'
        back_link = reverse('studentPage')

    user = request.user
    if user.groups.filter(name='Teachers').exists():
        navbar_template = 'navbarTeacher.html'
    elif user.groups.filter(name='Students').exists():
        navbar_template = 'navbarStudent.html'

    context = {
        'lesson': lesson,
        'lesson_messages': lesson_messages,
        'participants': participants,
        'navbar_template': navbar_template,
        'back_link': back_link
    }
    return render(request, 'website/lesson.html', context)


@login_required(login_url='lessonsLogin')
def userStudentsProfile(request, pk):
    user = User.objects.get(id=pk)
    lessons = user.post_set.all()
    lesson_messages = user.coursemessage_set.all()

    student = request.user
    courses = Course.objects.filter(students=student)

    if student.groups.filter(name='Teachers').exists():
        navbar_template = 'navbarTeacher.html'
        courses_component = 'website/courses_component_teachers.html'
    elif student.groups.filter(name='Students').exists():
        navbar_template = 'navbarStudent.html'
        courses_component = 'website/courses_component_students.html'

    context = {
        'user': user,
        'lessons': lessons,
        'lesson_messages': lesson_messages,
        'courses': courses,
        'navbar_template': navbar_template,
        'courses_component': courses_component
    }

    return render(request, 'website/profile_students.html', context)


@login_required(login_url='lessonsLogin')
def userTeachersProfile(request, pk):
    user = User.objects.get(id=pk)
    lessons = user.post_set.all()
    lesson_messages = user.coursemessage_set.all()

    teacher = request.user
    courses = Course.objects.filter(teacher=teacher)

    if teacher.groups.filter(name='Teachers').exists():
        navbar_template = 'navbarTeacher.html'
        courses_component = 'website/courses_component_teachers.html'

    elif teacher.groups.filter(name='Students').exists():
        navbar_template = 'navbarStudent.html'
        courses_component = 'website/courses_component_students.html'

    context = {
        'user': user,
        'lessons': lessons,
        'lesson_messages': lesson_messages,
        'courses': courses,
        'navbar_template': navbar_template,
        'courses_component': courses_component
    }

    return render(request, 'website/profile_teachers.html', context)


@login_required(login_url='lessonsLogin')
def createLesson(request):
    form = PostForm()
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.host = request.user
            post.save()
            return redirect('teacherPage')

    context = {'form': form}
    return render(request, 'website/createPost.html', context)


@login_required(login_url='lessonsLogin')
def updateLesson(request, pk):
    post = Post.objects.get(id=pk)
    form = PostForm(instance=post)

    if request.user != post.host:
        return HttpResponse('Brak dostępu')

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('teacherPage')

    context = {'form': form}
    return render(request, 'website/createPost.html', context)


@login_required(login_url='lessonsLogin')
def deleteLesson(request, pk):
    post = Post.objects.get(id=pk)

    if request.method == 'POST':
        post.delete()
        return redirect('teacherPage')

    user = request.user

    if user.groups.filter(name='Teachers').exists():
        navbar_template = 'navbarTeacher.html'
        back_link = reverse('teacherPage')

    elif user.groups.filter(name='Students').exists():
        navbar_template = 'navbarStudent.html'
        back_link = reverse('studentPage')

    context = {'obj': post, 'navbar_template': navbar_template, 'back_link': back_link}
    return render(request, 'website/deleteLessons.html', context)


@login_required(login_url='lessonsLogin')
def deleteLessonMessage(request, pk):
    message = CourseMessage.objects.get(id=pk)
    if request.user != message.user:
        return HttpResponse('Brak dostępu')
    if request.method == 'POST':
        message.delete()
        return redirect('teacherPage')

    user = request.user

    if user.groups.filter(name='Teachers').exists():
        navbar_template = 'navbarTeacher.html'

    elif user.groups.filter(name='Students').exists():
        navbar_template = 'navbarStudent.html'

    context = {'obj': message, 'navbar_template': navbar_template}
    return render(request, 'website/deleteLessons.html', context)


def applyTeacher(request):
    if request.method == 'POST':
        form = ApplyTeacherForm(request.POST)
        if form.is_valid():
            user = form.save()
            group = Group.objects.get(name='NewTeachers')
            user.groups.add(group)
            return redirect('lessonsLogin')  # Redirect to a success page after registration
    else:
        form = ApplyTeacherForm()
    return render(request, 'website/applyTeacher.html', {'form': form})


def applyStudent(request):
    if request.method == 'POST':
        form = ApplyStudentForm(request.POST)
        if form.is_valid():
            user = form.save()
            group = Group.objects.get(name='NewStudents')
            user.groups.add(group)
            return redirect('lessonsLogin')  # Redirect to a success page after registration
    else:
        form = ApplyStudentForm()
    return render(request, 'website/applyStudents.html', {'form': form})


@login_required(login_url='lessonsLogin')
def updateUserStudents(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('students-profile', pk=user.id)

    navbar_template = 'navbarStudent.html'

    context = {'navbar_template': navbar_template,'form': form}

    return render(request, 'website/update-user-students.html', context)


@login_required(login_url='lessonsLogin')
def updateUserTeachers(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('teachers-profile', pk=user.id)

    navbar_template = 'navbarTeacher.html'

    context = {'navbar_template': navbar_template, 'form': form}

    return render(request, 'website/update-user-teachers.html', context)


def FAQ(request):
    return render(request, 'website/FAQ.html')


def ContactInfo(request):
    return render(request, 'website/contact.html')


@login_required(login_url='lessonsLogin')
def Lobby(request):
    return render(request, 'website/lobby1.html')


@login_required(login_url='lessonsLogin')
def converse(request):
    user = request.user
    user.lessons = user.lessons - 1
    user.save()
    return render(request, 'website/lesson_converse1.html')


@receiver(pre_delete, sender=User)
def user_pre_delete(sender, instance, **kwargs):
    Room.objects.filter(host=instance).update(host=None)
