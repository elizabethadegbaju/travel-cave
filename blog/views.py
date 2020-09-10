from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

from blog.forms import PostForm
from blog.models import Profile, Post, Location, LocationReview


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
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user.profile
            instance.save()
            post = Post.objects.get(id=instance.id)
            analyse_entity_sentiment(form, post)
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


@login_required
def my_posts(request):
    posts = request.user.profile.blog_posts.all()
    return render(request, 'posts.html', {'posts': posts})


@login_required
def edit_post(request, pk):
    if request.method == 'POST':
        post = Post.objects.get(id=pk)
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            analyse_entity_sentiment(form, post)
            instance = form.save(commit=False)
            instance.author = request.user.profile
            instance.save()
            return redirect('blog:home')
        else:
            return HttpResponse(status=400)
    elif request.method == 'GET':
        post = Post.objects.get(id=pk)
        form = PostForm(instance=post)
    return render(request, 'edit_post.html', {'form': form})


def analyse_entity_sentiment(form, post):
    client = language.LanguageServiceClient()
    title = form.cleaned_data.get('title')
    content = form.cleaned_data.get('content')
    text = f"<p>{title}</p>{content}"
    print(text)
    document = types.Document(content=text,
                              type=enums.Document.Type.HTML)
    response = client.analyze_entity_sentiment(document=document)
    for entity in response.entities:
        if enums.Entity.Type(entity.type).name == 'LOCATION':
            for mention in entity.mentions:
                if enums.EntityMention.Type(
                        mention.type).name == 'PROPER':
                    print(f'\nDetected Location: {entity.name}')
                    print(f'Salience score: {entity.salience}')
                    sentiment = entity.sentiment
                    print(f'Entity sentiment score: {sentiment.score}')
                    print(
                        f'Entity sentiment magnitude: {sentiment.magnitude}')
                    location, created = Location.objects.get_or_create(
                        name=entity.name.lower())
                    location.save()
                    review, created = LocationReview.objects.update_or_create(
                        post=post, location=location,
                        defaults={'sentiment': sentiment.score,
                                  'magnitude': sentiment.magnitude})
                    review.save()


def delete_post(request, pk):
    post = Post.objects.get(id=pk)
    post.delete()
    return redirect('blog:my_posts')
