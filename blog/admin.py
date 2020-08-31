from django.contrib import admin
# Register your models here.
from django_summernote.admin import SummernoteModelAdmin

from blog.models import Post, Profile


class PostAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)


admin.site.register(Post, PostAdmin)
admin.site.register(Profile)
