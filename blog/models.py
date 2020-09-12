from autoslug import AutoSlugField
from django.contrib.auth.models import User
from django.db import models


# Create your models here.

def profile_image(instance, filename):
    """
    This function generates the path where a profile image should be saved to.
    :param instance: Instance of User Profile to be saved
    :param filename: Name of file to be uploaded
    :return: Path of file
    """
    ext = filename.split('.')[-1]
    return 'image/user_{0}.{1}'.format(instance.user.id, ext)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    DOB = models.DateField()
    about = models.TextField()
    twitter = models.CharField(max_length=50, null=True, blank=True)
    instagram = models.CharField(max_length=50, null=True, blank=True)
    facebook = models.CharField(max_length=50, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    users_following = models.ManyToManyField(to='self', symmetrical=False,
                                             related_name='followers',
                                             blank=True)
    locations_following = models.ManyToManyField(to='Location', blank=True,
                                                 related_name='followers')
    image = models.ImageField(null=True, blank=True, upload_to=profile_image)

    def __str__(self):
        return self.user.username


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    slug = AutoSlugField(populate_from='title')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(Profile, on_delete=models.CASCADE,
                               blank=True, related_name='blog_posts')
    locations = models.ManyToManyField(to=Location, related_name='reviews',
                                       through='LocationReview')
    tags = models.ManyToManyField(to=Tag, related_name='blog_posts')
    total_likes = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_shares = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} by {str(self.author)}'


class PostLike(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.DO_NOTHING)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{str(self.user)} liked {str(self.post)} on {self.created_at}'


class Comment(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.DO_NOTHING)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    parent = models.ForeignKey('Comment', on_delete=models.DO_NOTHING,
                               null=True, blank=True, related_name='replies')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{str(self.user)} commented on {str(self.post)} on {self.created_at}'


class LocationReview(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    sentiment = models.FloatField()
    magnitude = models.FloatField()

    def __str__(self):
        return f'{str(self.location)} in {str(self.post)}'
