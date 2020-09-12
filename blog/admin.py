from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from blog.models import *


class PostAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)


admin.site.register(Post, PostAdmin)
admin.site.register(Profile)
admin.site.register(Tag)
admin.site.register(Location)
admin.site.register(LocationReview)
admin.site.register(Comment)
admin.site.register(PostLike)
