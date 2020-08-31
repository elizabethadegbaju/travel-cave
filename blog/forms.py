from django import forms
from django_summernote.fields import SummernoteTextFormField

from blog.models import Post


class PostForm(forms.ModelForm):
    content = SummernoteTextFormField()

    class Meta:
        model = Post
        exclude = ('created_at', 'author')
