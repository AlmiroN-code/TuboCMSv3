"""
Forms for comments app.
"""
from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    """Form for creating comments."""

    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "cols": 50,
                    "placeholder": "Напишите комментарий...",
                    "class": "form-control",
                }
            )
        }

    def __init__(self, *args, user=None, video=None, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.video = video
        self.parent = parent

    def save(self, commit=True):
        comment = super().save(commit=False)
        if self.user:
            comment.user = self.user
        if self.video:
            comment.video = self.video
        if self.parent:
            comment.parent = self.parent
        if commit:
            comment.save()
        return comment


class CommentEditForm(forms.ModelForm):
    """Form for editing comments."""

    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 3, "cols": 50, "class": "form-control"}
            )
        }


class CommentReportForm(forms.Form):
    """Form for reporting comments."""

    reason = forms.ChoiceField(
        choices=[
            ("spam", "Спам"),
            ("inappropriate", "Неподходящий контент"),
            ("harassment", "Преследование"),
            ("other", "Другое"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "cols": 50,
                "placeholder": "Опишите причину жалобы...",
                "class": "form-control",
            }
        ),
    )
