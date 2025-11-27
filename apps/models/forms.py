"""
Forms for models app.
"""
from django import forms
from django.contrib.auth import get_user_model

from .models import Model, ModelVideo

User = get_user_model()


class ModelForm(forms.ModelForm):
    """Form for creating/updating a model."""

    # Add user selection field
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by("username"),
        empty_label="Выберите пользователя или создайте нового",
        required=True,
        label="Пользователь",
        help_text="Выберите существующего пользователя или создайте нового",
    )

    class Meta:
        model = Model
        fields = [
            "user",
            "display_name",
            "bio",
            "avatar",
            "cover_photo",
            "gender",
            "age",
            "birth_date",
            "country",
            "ethnicity",
            "career_start",
            "zodiac_sign",
            "hair_color",
            "eye_color",
            "has_tattoos",
            "tattoos_description",
            "has_piercings",
            "piercings_description",
            "breast_size",
            "measurements",
            "height",
            "weight",
            "is_verified",
            "is_active",
            "is_premium",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "cols": 50}),
            "tattoos_description": forms.Textarea(attrs={"rows": 3, "cols": 50}),
            "piercings_description": forms.Textarea(attrs={"rows": 3, "cols": 50}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "career_start": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter users who don't already have a model profile
        existing_model_users = Model.objects.values_list("user_id", flat=True)
        self.fields["user"].queryset = User.objects.exclude(
            id__in=existing_model_users
        ).order_by("username")

        # Make some fields optional
        self.fields["bio"].required = False
        self.fields["avatar"].required = False
        self.fields["cover_photo"].required = False
        self.fields["age"].required = False
        self.fields["birth_date"].required = False
        self.fields["country"].required = False
        self.fields["ethnicity"].required = False
        self.fields["career_start"].required = False
        self.fields["zodiac_sign"].required = False
        self.fields["hair_color"].required = False
        self.fields["eye_color"].required = False
        self.fields["breast_size"].required = False
        self.fields["measurements"].required = False
        self.fields["height"].required = False
        self.fields["weight"].required = False

        # If editing existing model, don't allow changing user
        if self.instance and self.instance.pk:
            self.fields["user"].disabled = True
            self.fields[
                "user"
            ].help_text = "Пользователь не может быть изменен для существующей модели"


class ModelVideoForm(forms.ModelForm):
    """Form for adding models to videos."""

    class Meta:
        model = ModelVideo
        fields = ["model", "is_primary"]
        widgets = {
            "model": forms.Select(attrs={"class": "form-control"}),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to only active models
        self.fields["model"].queryset = Model.objects.filter(is_active=True).order_by(
            "display_name"
        )
