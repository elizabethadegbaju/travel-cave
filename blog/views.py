from datetime import timedelta, datetime
from itertools import chain
from operator import attrgetter

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVector, SearchRank
from django.db.models import Count, Avg
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from google.cloud import language_v1beta2 as language
from google.cloud.language_v1beta2 import Entity, EntityMention, Document

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
    recent_posts = Post.objects.filter(is_published=True)[:12]
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    trending_locations = Location.objects.filter(
        reviews__postlike__created_at__gte=week_ago).annotate(
        likes_count=Count('reviews__postlike', distinct=True),
        average_sentiment=Avg('locationreview__sentiment',
                              distinct=True)).order_by('-likes_count')[:12]
    return render(request, 'index.html', {'recent_posts': recent_posts,
                                          'trending_locations': trending_locations})


def view_post(request, pk):
    post = Post.objects.get(id=pk)
    profile = post.author
    return render(request, 'view_post.html',
                  {'post': post, 'profile': profile})


@login_required
def publish_new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user.profile
            instance.is_published = True
            instance.save()
            post = Post.objects.get(id=instance.id)
            analyse_entity_sentiment(form, post)
            classify_post(form, post)
            return redirect('blog:view_post', post.id)
        else:
            return HttpResponse(status=400)


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
            return redirect('blog:view_post', post.id)
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
        username = request.POST['username']
        image = request.FILES['image']

        user = User.objects.create_user(username=username, email=email,
                                        password=password,
                                        first_name=first_name,
                                        last_name=last_name)
        user.save()

        user_profile = Profile.objects.create(user=user, image=image)
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
def publish_post(request, pk):
    post = Post.objects.get(id=pk)
    post.is_published = True
    post.save()
    return redirect('blog:view_post', pk)


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
        if Entity.Type(entity.type).name == 'LOCATION':
            for mention in entity.mentions:
                if EntityMention.Type(
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
    tags = list()
    try:
        response = client.classify_text(document=document)
        categories = response.categories

        for category in categories:
            tag = category.name.split('/')[-1]
            tag, created = Tag.objects.get_or_create(name=tag)
            tag.save()
            tags.append(tag)
    finally:
        post.tags.set(tags)


def extract_document(form):
    client = language.LanguageServiceClient()
    title = form.cleaned_data.get('title')
    content = form.cleaned_data.get('content')
    text = f"<p>{title}</p>{content}"
    print(text)
    document = Document(content=text, type=Document.Type.HTML)
    return client, document


@login_required
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
        user=request.user).distinct().order_by('?')[:5]
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


@login_required
def follow_user(request, username):
    profile = Profile.objects.get(user__username=username)
    user = request.user
    user.profile.users_following.add(profile)
    return redirect('blog:view_user', username)


@login_required
def unfollow_user(request, username):
    profile = Profile.objects.get(user__username=username)
    user = request.user
    user.profile.users_following.remove(profile)
    return redirect('blog:view_user', username)


@login_required
def follow_location(request, pk):
    location = Location.objects.get(id=pk)
    user = request.user
    user.profile.locations_following.add(location)
    return redirect('blog:view_location', pk)


@login_required
def unfollow_location(request, pk):
    location = Location.objects.get(id=pk)
    user = request.user
    user.profile.locations_following.remove(location)
    return redirect('blog:view_location', pk)


def users(request):
    return None


def view_location(request, pk):
    location = Location.objects.get(id=pk)
    reviews = LocationReview.objects.filter(location=location,
                                            post__is_published=True)
    return render(request, 'location.html',
                  {'location': location, 'reviews': reviews})


def view_tag(request, pk):
    tag = Tag.objects.get(id=pk)
    posts = tag.blog_posts.filter(is_published=True)
    return render(request, 'tag.html',
                  {'tag': tag, 'posts': posts})


@login_required
def like_post(request, pk):
    post = Post.objects.get(id=pk)
    post_like = PostLike.objects.create(post=post, user=request.user.profile)
    post_like.save()
    post.total_likes += 1
    post.save()
    return redirect('blog:view_post', pk)


@login_required
def unlike_post(request, pk):
    post = Post.objects.get(id=pk)
    post_like = PostLike.objects.get(post=post, user=request.user.profile)
    post_like.delete()
    post.total_likes -= 1
    post.save()
    return redirect('blog:view_post', pk)


@login_required
def comment_post(request, pk):
    message = request.POST['comment']
    post = Post.objects.get(id=pk)
    comment = Comment.objects.create(user=request.user.profile, post=post,
                                     message=message)
    comment.save()
    post.total_comments += 1
    post.save()
    return redirect('blog:view_post', pk)


@login_required
def reply_comment(request, pk):
    message = request.POST['comment']
    comment = Comment.objects.get(id=pk)
    post = comment.post
    reply = Comment.objects.create(user=request.user.profile, post=post,
                                   message=message, parent=comment)
    reply.save()
    post.total_comments += 1
    post.save()
    return redirect('blog:view_post', post.id)


@login_required
def share_post(request, pk):
    post = Post.objects.get(id=pk)
    post.total_shares += 1
    post.save()
    return redirect('blog:view_post', pk)


@login_required
def publish_post(request, pk):
    post = Post.objects.get(id=pk)
    post.is_published = True
    post.save()
    return redirect('blog:view_post', pk)


def explore(request):
    query = request.GET['query']
    if query:
        profiles = Profile.objects.annotate(rank=SearchRank(
            SearchVector('user__first_name', 'user__last_name',
                         'user__username'), query)).order_by('-rank')
        locations = Location.objects.annotate(
            rank=SearchRank(SearchVector('name'), query)).order_by('-rank')
        tags = Tag.objects.annotate(
            rank=SearchRank(SearchVector('name'), query)).order_by('-rank')
        posts = Post.objects.filter(is_published=True).annotate(
            rank=SearchRank(
                SearchVector('title', 'content', 'author__user__first_name',
                             'author__user__last_name',
                             'author__user__username'), query)).order_by(
            '-rank')
    else:
        profiles = Profile.objects.all().annotate(posts_count=Count(
            'blog_posts')).order_by('-posts_count')
        locations = Location.objects.all().order_by('name')
        tags = Tag.objects.all().order_by('name')
        posts = Post.objects.all().annotate(likes_count=Count(
            'postlike')).order_by('-likes_count')
    return render(request, 'explore.html',
                  {'profiles': profiles, 'locations': locations, 'tags': tags,
                   'posts': posts})
