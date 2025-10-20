"""
Forms for comments app.
"""
from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    """Form for creating comments."""
    
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'cols': 50,
                'placeholder': 'Напишите комментарий...',
                'class': 'form-control'
            })
        }


class CommentEditForm(forms.ModelForm):
    """Form for editing comments."""
    
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'cols': 50,
                'class': 'form-control'
            })
        }


class CommentReportForm(forms.Form):
    """Form for reporting comments."""
    reason = forms.ChoiceField(
        choices=[
            ('spam', 'Спам'),
            ('inappropriate', 'Неподходящий контент'),
            ('harassment', 'Преследование'),
            ('other', 'Другое')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'cols': 50,
            'placeholder': 'Опишите причину жалобы...',
            'class': 'form-control'
        })
    )