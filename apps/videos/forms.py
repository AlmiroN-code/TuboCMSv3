"""
Forms for video management.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Video, VideoReport
from apps.core.models import Tag


class VideoUploadForm(forms.ModelForm):
    """Video upload form."""
    class Meta:
        model = Video
        fields = ['title', 'description', 'category', 'tags', 'is_premium']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название видео'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Описание видео'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'is_premium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tags'].queryset = Tag.objects.all()
        self.fields['tags'].required = False

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise ValidationError('Название должно содержать минимум 5 символов')
        return title

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) > 5000:
            raise ValidationError('Описание не должно превышать 5000 символов')
        return description


class VideoEditForm(forms.ModelForm):
    """Video edit form."""
    class Meta:
        model = Video
        fields = ['title', 'description', 'category', 'tags', 'is_premium', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'is_premium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tags'].queryset = Tag.objects.all()
        self.fields['tags'].required = False


class VideoSearchForm(forms.Form):
    """Video search form."""
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск видео...'
        })
    )
    category = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.HiddenInput()
    )
    sort = forms.ChoiceField(
        choices=[
            ('newest', 'Новые'),
            ('oldest', 'Старые'),
            ('popular', 'Популярные'),
            ('trending', 'Тренды'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class VideoReportForm(forms.ModelForm):
    """Video report form."""
    class Meta:
        model = VideoReport
        fields = ['report_type', 'description']
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите проблему...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False










