from django import forms
from django_summernote.widgets import SummernoteWidget, SummernoteInplaceWidget

from blog.models import Post


class FormFromSomeModel(forms.ModelForm):
    class Meta:
        model = Post
        widgets = {
            'foo': SummernoteWidget(),
            'bar': SummernoteInplaceWidget(),
        }
