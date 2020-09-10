from django import forms
from django_summernote.widgets import SummernoteInplaceWidget

from blog.models import Post


class PostForm(forms.ModelForm):
    content = forms.CharField(widget=SummernoteInplaceWidget())

    class Meta:
        model = Post
        exclude = ('slug', 'author', 'is_published', 'locations', 'tags')
