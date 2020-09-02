from django import forms
from django_summernote.widgets import SummernoteInplaceWidget, SummernoteWidget

from blog.models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ('created_at', 'author')
        widgets = {
            'content': SummernoteWidget(attrs={
                'width': '50%', 'height': '400px'
            })}
