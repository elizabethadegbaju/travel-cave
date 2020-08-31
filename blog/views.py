from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from blog.forms import PostForm
from blog.models import Profile


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('blog:home')
        else:
            # Return an 'invalid login' error message.
            ...
    elif request.method == 'GET':
        return render(request, 'login.html')


def index(request):
    return render(request, 'index.html')


def view_post(request, pk):
    return render(request, '')


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        print(form)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user.profile
            instance.save()
            return redirect('blog:home')
        else:
            return HttpResponse(status=400)
    elif request.method == 'GET':
        form = PostForm()
    return render(request, 'create_post.html', {'form': form})


def register(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    elif request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        password = request.POST['password']
        dob = request.POST['dob']
        username = request.POST['username']

        user = User.objects.create_user(username=username, email=email,
                                        password=password,
                                        first_name=first_name,
                                        last_name=last_name)
        user.save()

        user_profile = Profile.objects.create(DOB=dob, user=user)
        user_profile.save()

        return redirect('blog:home')


def logout_view(request):
    logout(request)
    return redirect('blog:home')
