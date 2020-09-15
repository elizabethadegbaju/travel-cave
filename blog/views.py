from itertools import chain
from operator import attrgetter

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

from blog.forms import PostForm
from blog.models import Profile, Post, Location, LocationReview, Tag, \
    PostLike, Comment


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            last_login = user.last_login
            login(request, user)
            if last_login is not None:
                request.session['previous_login'] = last_login.isoformat()
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
            classify_post(form, post)
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
        image = request.FILES['image']

        user = User.objects.create_user(username=username, email=email,
                                        password=password,
                                        first_name=first_name,
                                        last_name=last_name)
        user.save()

        user_profile = Profile.objects.create(DOB=dob, user=user, image=image)
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
            classify_post(form, post)
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
    client, document = extract_document(form)
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


def classify_post(form, post):
    client, document = extract_document(form)
    response = client.classify_text(document=document)
    categories = response.categories
    tags = list()

    for category in categories:
        tag = category.name.split('/')[-1]
        tag, created = Tag.objects.get_or_create(name=tag)
        tag.save()
        tags.append(tag)
        print(u'{:<16}: {}'.format('\ntag', tag))
        print(u'{:<16}: {}'.format('category', category.name))
        print(u'{:<16}: {}'.format('confidence', category.confidence))
    post.tags.set(tags)


def extract_document(form):
    client = language.LanguageServiceClient()
    title = form.cleaned_data.get('title')
    content = form.cleaned_data.get('content')
    text = f"<p>{title}</p>{content}"
    print(text)
    document = types.Document(content=text,
                              type=enums.Document.Type.HTML)
    return client, document


def delete_post(request, pk):
    post = Post.objects.get(id=pk)
    post.delete()
    return redirect('blog:my_posts')


def view_user(request, username):
    profile = Profile.objects.get(user__username=username)
    activities = get_user_activities_sorted(username)
    newsfeed = get_newsfeed_sorted(
        profile.users_following.all()) if request.user.username == username else []
    blog_posts = Post.objects.filter(author=profile)
    reviews = LocationReview.objects.filter(post__in=blog_posts)
    highlight = Post.objects.filter(is_published=True).order_by('-created_at',
                                                                '-total_likes',
                                                                '-total_comments',
                                                                '-total_shares').first()
    # recommend users who follow the same content
    recommended_users = (Profile.objects.filter(
        users_following__in=profile.users_following.all()) | Profile.objects.filter(
        locations_following__in=profile.locations_following.all())).exclude(
        user=request.user).order_by('?')[:5]
    previous_login = parse_datetime(
        request.session.get('previous_login', now().isoformat()))
    updates = LocationReview.objects.filter(
        location__in=profile.locations_following.all(),
        post__is_published=True,
        post__created_at__gt=previous_login).values('location').annotate(
        total=Count('location')).order_by('total')
    return render(request, 'user.html',
                  {'profile': profile, 'activities': activities,
                   'reviews': reviews, 'highlight': highlight,
                   'recommended_users': recommended_users, 'updates':
                       updates, 'newsfeed': newsfeed})


def get_user_activities_sorted(username):
    user = Profile.objects.get(user__username=username)
    likes = PostLike.objects.filter(user=user)
    comments = Comment.objects.filter(user=user)
    posts = Post.objects.filter(author=user)
    result_list = sorted(chain(likes, comments, posts),
                         key=attrgetter('created_at'), reverse=True)
    return result_list


def get_newsfeed_sorted(users_following):
    likes = PostLike.objects.filter(user__in=users_following)
    comments = Comment.objects.filter(user__in=users_following)
    posts = Post.objects.filter(author__in=users_following)
    result_list = sorted(chain(likes, comments, posts),
                         key=attrgetter('created_at'), reverse=True)
    return result_list


def follow_user(request, username):
    profile = Profile.objects.get(user__username=username)
    user = request.user
    user.profile.users_following.add(profile)
    return redirect('blog:view_user', username)


def unfollow_user(request, username):
    profile = Profile.objects.get(user__username=username)
    user = request.user
    user.profile.users_following.remove(profile)
    return redirect('blog:view_user', username)


def users(request):
    return None


def view_location(request, pk):
    location = Location.objects.get(id=pk)
    reviews = LocationReview.objects.filter(location=location)
    return render(request, 'location.html',
                  {'location': location, 'reviews': reviews})


def view_tag(request, pk):
    tag = Tag.objects.get(id=pk)
    posts = tag.blog_posts.all()
    return render(request, 'tag.html',
                  {'tag': tag, 'posts': posts})
