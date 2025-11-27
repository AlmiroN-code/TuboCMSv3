"""
Forms for video management.
"""
from django import forms
from django.core.exceptions import ValidationError

from apps.core.models import Tag

from .models import Video, VideoReport


class VideoUploadForm(forms.ModelForm):
    """Video upload form."""

    video_file = forms.FileField(
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "video/*"}),
        help_text="Выберите видеофайл для загрузки",
    )

    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "tags-input",
                "placeholder": "Введите теги через запятую или выберите из списка",
            }
        ),
        help_text="Введите теги через запятую или используйте автокомплит",
    )

    class Meta:
        model = Video
        fields = ["title", "description", "category", "tags", "performers"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Название видео"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Описание видео",
                }
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "tags": forms.SelectMultiple(
                attrs={
                    "class": "form-control",
                    "id": "id_tags",
                    "style": "display: none;",  # Скрываем стандартный select
                }
            ),
            "is_premium": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].queryset = Tag.objects.all()
        self.fields["tags"].required = False
        self.fields["tags"].widget.attrs[
            "style"
        ] = "display: none;"  # Скрываем стандартный select

        # Добавляем поле для выбора моделей
        from apps.models.models import Model

        self.fields["performers"] = forms.ModelMultipleChoiceField(
            queryset=Model.objects.filter(is_active=True),
            required=False,
            widget=forms.SelectMultiple(
                attrs={
                    "class": "form-control select2-multiple",
                    "data-placeholder": "Выберите модели...",
                    "multiple": "multiple",
                    "size": "10",
                }
            ),
            label="Модели",
            help_text="Выберите модели, участвующие в видео",
        )

        # Если редактируем существующее видео, заполняем tags_input и performers
        if self.instance and self.instance.pk:
            tag_names = ", ".join([tag.name for tag in self.instance.tags.all()])
            self.fields["tags_input"].initial = tag_names
            # Устанавливаем начальные значения для моделей
            self.fields["performers"].initial = self.instance.performers.all()

        # Применяем настройки сайта
        from apps.core.utils import get_site_settings

        site_settings = get_site_settings()
        if site_settings:
            # Устанавливаем максимальный размер файла
            max_size = (
                site_settings.max_video_size * 1024 * 1024
            )  # Конвертируем MB в байты
            self.fields["video_file"].widget.attrs["data-max-size"] = max_size

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if len(title) < 5:
            raise ValidationError("Название должно содержать минимум 5 символов")
        return title

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if description and len(description) > 5000:
            raise ValidationError("Описание не должно превышать 5000 символов")
        return description

    def clean_tags_input(self):
        """Преобразует строку тегов в список объектов Tag."""
        tags_input = self.cleaned_data.get("tags_input", "")
        if not tags_input:
            return []

        # Разбиваем строку по запятым и очищаем
        tag_names = [name.strip() for name in tags_input.split(",") if name.strip()]
        tag_objects = []

        for tag_name in tag_names:
            # Ищем существующий тег или создаем новый
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={"slug": None},  # Slug сгенерируется автоматически в save()
            )
            tag_objects.append(tag)

        return tag_objects

    def clean_video_file(self):
        video_file = self.cleaned_data.get("video_file")
        if video_file:
            from apps.core.utils import get_site_settings

            site_settings = get_site_settings()

            if site_settings:
                # Проверяем размер файла
                max_size = site_settings.max_video_size * 1024 * 1024  # MB в байты
                if video_file.size > max_size:
                    raise ValidationError(
                        f"Размер файла не должен превышать {site_settings.max_video_size} MB"
                    )

                # Проверяем формат файла
                allowed_formats = site_settings.allowed_video_formats.split(",")
                file_extension = video_file.name.split(".")[-1].lower()
                if file_extension not in [
                    fmt.strip().lower() for fmt in allowed_formats
                ]:
                    raise ValidationError(
                        f"Разрешенные форматы: {site_settings.allowed_video_formats}"
                    )

        return video_file


class VideoEditForm(forms.ModelForm):
    """Video edit form."""

    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "tags-input",
                "placeholder": "Введите теги через запятую или выберите из списка",
            }
        ),
        help_text="Введите теги через запятую или используйте автокомплит",
    )

    class Meta:
        model = Video
        fields = ["title", "description", "category", "tags", "performers", "status"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "tags": forms.SelectMultiple(
                attrs={
                    "class": "form-control",
                    "style": "display: none;",  # Скрываем стандартный select
                }
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].queryset = Tag.objects.all()
        self.fields["tags"].required = False
        self.fields["tags"].widget.attrs["style"] = "display: none;"

        # Добавляем поле для выбора моделей
        from apps.models.models import Model

        self.fields["performers"] = forms.ModelMultipleChoiceField(
            queryset=Model.objects.filter(is_active=True),
            required=False,
            widget=forms.SelectMultiple(
                attrs={
                    "class": "form-control select2-multiple",
                    "data-placeholder": "Выберите модели...",
                    "multiple": "multiple",
                    "size": "10",
                }
            ),
            label="Модели",
            help_text="Выберите модели, участвующие в видео",
        )

        # Если редактируем существующее видео, заполняем tags_input и performers
        if self.instance and self.instance.pk:
            tag_names = ", ".join([tag.name for tag in self.instance.tags.all()])
            self.fields["tags_input"].initial = tag_names
            # Устанавливаем начальные значения для моделей
            self.fields["performers"].initial = self.instance.performers.all()

    def clean_tags_input(self):
        """Преобразует строку тегов в список объектов Tag."""
        tags_input = self.cleaned_data.get("tags_input", "")
        if not tags_input:
            return []

        # Разбиваем строку по запятым и очищаем
        tag_names = [name.strip() for name in tags_input.split(",") if name.strip()]
        tag_objects = []

        for tag_name in tag_names:
            # Ищем существующий тег или создаем новый
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={"slug": None},  # Slug сгенерируется автоматически в save()
            )
            tag_objects.append(tag)

        return tag_objects


class VideoSearchForm(forms.Form):
    """Video search form."""

    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Поиск видео..."}
        ),
    )
    category = forms.CharField(
        max_length=50, required=False, widget=forms.HiddenInput()
    )
    sort = forms.ChoiceField(
        choices=[
            ("newest", "Новые"),
            ("oldest", "Старые"),
            ("popular", "Популярные"),
            ("trending", "Тренды"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class VideoReportForm(forms.ModelForm):
    """Video report form."""

    class Meta:
        model = VideoReport
        fields = ["report_type", "description"]
        widgets = {
            "report_type": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Опишите проблему...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
