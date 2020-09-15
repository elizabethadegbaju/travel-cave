"""travelcave URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='home'),
    path('home/', views.index, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('posts/create/', views.create_post, name="create_post"),
    path('posts/<int:pk>/edit/', views.edit_post, name="edit_post"),
    path('posts/<int:pk>/delete/', views.delete_post, name="delete_post"),
    path('posts/<int:pk>/view/', views.view_post, name="view_post"),
    path('account/posts/', views.my_posts, name='my_posts'),
    path('users/<str:username>/follow/', views.follow_user,
         name='follow_user'),
    path('users/<str:username>/unfollow/', views.unfollow_user,
         name='unfollow_user'),
    path('users/<str:username>/', views.view_user, name='view_user'),
    path('users/', views.users, name='users'),
    path('locations/<int:pk>/', views.view_location, name='view_location'),
    path('tags/<int:pk>/', views.view_tag, name='view_tag')
]
