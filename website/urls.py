from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name="home"),
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),
    path('contact/', views.contact_view, name='contact'),

    path('dashboard/', views.dashboard, name="dashboard"),
    path('room/<str:pk>/', views.room, name="room"),
    path('profile/<str:pk>/', views.userProfile, name="user-profile"),

    path('create-room/', views.createRoom, name="create-room"),
    path('update-room/<str:pk>/', views.updateRoom, name="update-room"),
    path('delete-room/<str:pk>/', views.deleteRoom, name="delete-room"),
    path('delete-message/<str:pk>/', views.deleteMessage, name="delete-message"),

    path('update-user/', views.updateUser, name="update-user"),

    path('topics/', views.topicsPage, name="topics"),
    path('activity/', views.activityPage, name="activity"),

    path('lessons-login/', views.lessonsLogin, name="lessonsLogin"),
    path('lessons-logout/', views.lessonsLogout, name="lessonsLogout"),
    path('lessons-register/', views.lessonsRegister, name="lessonsRegister"),

    path('lessons/', views.lessonsHome, name="lessons-home"),
    path('lesson/<str:pk>/', views.lesson, name="lesson"),
    path('profile-teachers/<str:pk>/', views.userTeachersProfile, name="teachers-profile"),
    path('profile-students/<str:pk>/', views.userStudentsProfile, name="students-profile"),

    path('student-page/', views.studentPage, name="studentPage"),
    path('teacher-page/', views.teacherPage, name="teacherPage"),
    path('create-loader/', views.coursesLoader, name="coursesLoader"),
    path('no-lessons/', views.noLessons, name="noLessons"),

    path('create-lesson/', views.createLesson, name='createLesson'),
    path('update-lesson/<str:pk>/', views.updateLesson, name='updateLesson'),
    path('delete-lesson/<str:pk>/', views.deleteLesson, name='deleteLesson'),
    path('delete-lesson-message/<str:pk>/', views.deleteLessonMessage, name='deleteLessonMessage'),

    path('apply-teacher/', views.applyTeacher, name="applyTeacher"),
    path('apply-student/', views.applyStudent, name="applyStudent"),

    path('update-user-students/', views.updateUserStudents, name="update-user-students"),
    path('update-user-teachers/', views.updateUserTeachers, name="update-user-teachers"),

    path('faq/', views.FAQ, name="faq"),
    path('contact-info/', views.ContactInfo, name="contact-info"),

    path('lobby/', views.Lobby, name='lobby'),
    path('converse/', views.converse),
    path('get_token/', views.getToken),
]
