"""
Forms for user management.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import COUNTRY_CHOICES, UserProfile

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
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
            "register_as_model",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control"})
        self.fields["email"].widget.attrs.update({"class": "form-control"})
        self.fields["first_name"].widget.attrs.update({"class": "form-control"})
        self.fields["last_name"].widget.attrs.update({"class": "form-control"})
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(user=user)

            # Create model profile if requested
            if self.cleaned_data.get("register_as_model"):
                from apps.models.models import Model

                Model.objects.create(
                    user=user,
                    display_name=f"{user.first_name} {user.last_name}".strip()
                    or user.username,
                    bio="",
                    is_active=True,
                )
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control"})
        self.fields["password"].widget.attrs.update({"class": "form-control"})


class UserProfileForm(forms.ModelForm):
    """User profile form."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "bio", "location", "website"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
        }


class ProfileEditForm(forms.ModelForm):
    """Profile edit form for /members/{username}/edit/."""

    username = forms.CharField(
        max_length=150,
        required=True,
        label="Имя пользователя",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "avatar",
            "birth_date",
            "gender",
            "country",
            "location",
            "marital_status",
            "orientation",
            "website",
            "education",
            "bio",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Имя"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Фамилия"}
            ),
            "avatar": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-control"}),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Город"}
            ),
            "marital_status": forms.Select(attrs={"class": "form-control"}),
            "orientation": forms.Select(attrs={"class": "form-control"}),
            "website": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://example.com"}
            ),
            "education": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Образование"}
            ),
            "bio": forms.Textarea(
                attrs={"class": "form-control", "rows": 5, "placeholder": "О себе"}
            ),
        }
        labels = {
            "username": "Имя пользователя",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "avatar": "Аватар",
            "birth_date": "Дата рождения",
            "gender": "Пол",
            "country": "Страна",
            "location": "Город",
            "marital_status": "Семейное положение",
            "orientation": "Сексуальная ориентация",
            "website": "Веб-сайт",
            "education": "Образование",
            "bio": "Обо мне",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["username"].initial = self.instance.username

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            # Проверяем уникальность username, исключая текущего пользователя
            existing_user = (
                User.objects.filter(username=username)
                .exclude(pk=self.instance.pk)
                .first()
            )
            if existing_user:
                raise forms.ValidationError(
                    "Пользователь с таким именем уже существует."
                )
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        username = self.cleaned_data.get("username")
        if username and username != user.username:
            user.username = username
        if commit:
            user.save()
        return user


class PasswordChangeForm(forms.Form):
    """Password change form."""

    old_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=True,
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=True,
        min_length=8,
    )
    new_password2 = forms.CharField(
        label="Подтверждение нового пароля",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=True,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Неверный текущий пароль.")
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают.")
        return password2

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class UserSettingsForm(forms.ModelForm):
    """User settings form."""

    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=False,
        label="Страна",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = UserProfile
        fields = [
            "theme_preference",
            "language",
            "notifications_enabled",
            "email_notifications",
            "privacy_level",
            "show_videos_publicly",
            "show_favorites_publicly",
            "show_watch_later_publicly",
            "show_friends_publicly",
        ]
        widgets = {
            "theme_preference": forms.Select(attrs={"class": "form-control"}),
            "language": forms.Select(attrs={"class": "form-control"}),
            "notifications_enabled": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "email_notifications": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "privacy_level": forms.Select(attrs={"class": "form-control"}),
            "show_videos_publicly": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "show_favorites_publicly": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "show_watch_later_publicly": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "show_friends_publicly": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "show_videos_publicly": "Show Videos to others",
            "show_favorites_publicly": "Show Favorites to others",
            "show_watch_later_publicly": "Show Watch Later to others",
            "show_friends_publicly": "Show Friends to others",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Set translated choices based on user language
        user_language = 'en'
        if self.user and hasattr(self.user, 'profile'):
            try:
                user_language = self.user.profile.language
            except:
                pass
        
        # Set translated choices for theme
        if user_language == 'ru':
            self.fields['theme_preference'].choices = [
                ('light', 'Светлая'),
                ('dark', 'Тёмная'),
            ]
            self.fields['privacy_level'].choices = [
                ('public', 'Публичный'),
                ('private', 'Приватный'),
            ]
        
        if self.user:
            self.fields["country"].initial = self.user.country

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            self.user.country = self.cleaned_data.get("country", "")
            self.user.save()
        if commit:
            instance.save()
        return instance
