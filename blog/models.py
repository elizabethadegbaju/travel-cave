from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    DOB = models.DateField()
    about = models.TextField()
    twitter = models.CharField(max_length=50, null=True, blank=True)
    instagram = models.CharField(max_length=50, null=True, blank=True)
    facebook = models.CharField(max_length=50, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    users_following = models.ManyToManyField(to='self', symmetrical=False,
                                             related_name='following')
    locations_following = models.ManyToManyField(to='Location',
                                                 related_name='locations_following')
    image = models.ImageField(null=True)

    def __str__(self):
        return self.user.username


class Tag(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=100)


class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    slug = models.SlugField(max_length=200, unique=True)
    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(Profile, on_delete=models.CASCADE,
                               blank=True, related_name='blog_posts')
    locations = models.ManyToManyField(to=Location, related_name='reviews',
                                       through='LocationReview')
    tags = models.ManyToManyField(to=Tag, related_name='blog_posts')

    class Meta:
        ordering = ['-created_on']

    def __str__(self):
        return f'{self.title} by {str(self.author)}'


class LocationReview(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    sentiment = models.FloatField()
    magnitude = models.FloatField()

    def __str__(self):
        return f'{str(self.location)} in {str(self.post)}'
