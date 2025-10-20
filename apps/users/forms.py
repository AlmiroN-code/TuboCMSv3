"""
Forms for user management.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    register_as_model = forms.BooleanField(
        required=False,
        label="Зарегистрироваться как модель",
        help_text="Отметьте, если хотите создать профиль модели для взрослого контента",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'register_as_model')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            
            # Create model profile if requested
            if self.cleaned_data.get('register_as_model'):
                from apps.models.models import Model
                Model.objects.create(
                    user=user,
                    display_name=f"{user.first_name} {user.last_name}".strip() or user.username,
                    bio="",
                    is_active=True
                )
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})


class UserProfileForm(forms.ModelForm):
    """User profile form."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'bio', 'location', 'website']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class UserSettingsForm(forms.ModelForm):
    """User settings form."""
    class Meta:
        model = UserProfile
        fields = ['theme_preference', 'language', 'notifications_enabled', 
                 'email_notifications', 'privacy_level']
        widgets = {
            'theme_preference': forms.Select(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'privacy_level': forms.Select(attrs={'class': 'form-control'}),
        }






