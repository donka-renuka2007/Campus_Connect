from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from campusconnect import views

urlpatterns = [
    path('admin/',                              admin.site.urls),
    path('',                                    views.home,               name='home'),
    path('login/',                              views.login_page,         name='login'),
    path('signup/',                             views.signup_page,        name='signup'),
    path('logout/',                             views.logout_page,        name='logout'),
    path('dashboard/',                          views.dashboard,          name='dashboard'),
    path('study/',                              views.study,              name='study'),
    path('announcements/',                      views.announcements,      name='announcements'),
    path('announcements/post/',                 views.post_announcement,  name='post_announcement'),
    path('announcements/edit/<int:pk>/',        views.edit_announcement,  name='edit_announcement'),
    path('announcements/delete/<int:pk>/',      views.delete_announcement,name='delete_announcement'),
    path('profile/',                            views.profile_view,       name='profile'),
    path('profile/edit/',                       views.edit_profile,       name='edit_profile'),
    path('study/compiler/',                     views.compiler,           name='compiler'),
    path('study/goals/',                        views.goals,              name='goals'),
    path('study/goals/create/',                 views.create_goal,        name='create_goal'),
    path('study/goals/<int:goal_id>/',          views.goal_detail,        name='goal_detail'),
    path('study/goals/<int:goal_id>/submissions/', views.goal_submissions, name='goal_submissions'),
    path('study/goals/submission/<int:sub_id>/review/', views.review_submission, name='review_submission'),
    path('study/goals/<int:goal_id>/delete/',   views.delete_goal,        name='delete_goal'),
    path('study/chatbot/',                      views.chatbot,            name='chatbot'),
    path('study/chatbot/api/',                  views.chatbot_api,        name='chatbot_api'),
    path('resources/',                          include('resources.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)