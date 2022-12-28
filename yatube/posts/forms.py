from django import forms
from posts.models import Comment, Post


class PostForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group'].empty_label = 'Без группы'

    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': ('Текст поста'),
            'group': ('Группа'),
        }
        help_texts = {'text': 'Текст нового поста',
                      'group': 'Группа, к которой будет относиться пост'}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
