from django.contrib import admin
from django.urls import path,include
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
    path('resources/', include('resources.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)