"""
Admin forms for video processing.
"""
from django import forms

from apps.core.models import Tag
from apps.models.models import Model

from .models import Video
from .models_encoding import VideoEncodingProfile


class VideoAdminForm(forms.ModelForm):
    """Custom form for video admin with encoding profile selection."""

    encoding_profiles = forms.ModelMultipleChoiceField(
        queryset=VideoEncodingProfile.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Профили кодирования",
        help_text="Выберите профили для конвертации видео",
    )

    performers = forms.ModelMultipleChoiceField(
        queryset=Model.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Модели",
        help_text="Выберите модели, участвующие в видео",
    )

    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "vTextField",
                "id": "tags-input",
                "placeholder": "Введите теги через запятую или выберите из списка",
                "style": "width: 100%; padding: 8px;",
            }
        ),
        label="Теги (ввод через запятую)",
        help_text="Введите теги через запятую или используйте стандартный виджет ниже для выбора существующих",
    )

    class Meta:
        model = Video
        fields = "__all__"

    class Media:
        js = (
            'js/admin-tags-autocomplete.js',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default selected profiles to all active ones
        if not self.instance.pk:  # New video
            self.fields[
                "encoding_profiles"
            ].initial = VideoEncodingProfile.objects.filter(is_active=True)

            # Set default values for fields that exist in the model
            if "duration" in self.fields:
                self.fields["duration"].initial = 0
            if "views_count" in self.fields:
                self.fields["views_count"].initial = 0
            if "processing_status" in self.fields:
                self.fields["processing_status"].initial = "pending"
            if "processing_progress" in self.fields:
                self.fields["processing_progress"].initial = 0

        # Если редактируем существующее видео, заполняем tags_input
        if self.instance and self.instance.pk:
            tag_names = ", ".join([tag.name for tag in self.instance.tags.all()])
            self.fields["tags_input"].initial = tag_names

        # Make some fields not required if they exist
        for field_name in [
            "duration",
            "views_count",
            "processing_status",
            "processing_progress",
        ]:
            if field_name in self.fields:
                self.fields[field_name].required = False

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

    def save(self, commit=True):
        video = super().save(commit=commit)

        if commit:
            # Store selected profiles for processing
            selected_profiles = self.cleaned_data.get("encoding_profiles", [])
            if selected_profiles:
                # Store selected profiles as attribute for signals
                video._selected_encoding_profiles = [p.id for p in selected_profiles]
            else:
                # If no profiles selected, use all active ones
                video._selected_encoding_profiles = list(
                    VideoEncodingProfile.objects.filter(is_active=True).values_list(
                        "id", flat=True
                    )
                )

            # Handle selected performers
            selected_performers = self.cleaned_data.get("performers", [])
            if selected_performers:
                # Clear existing performers
                video.performers.clear()
                # Add new performers
                for performer in selected_performers:
                    from apps.models.models import ModelVideo

                    ModelVideo.objects.create(
                        model=performer,
                        video=video,
                        is_primary=(performer == selected_performers.first()),
                    )

            # Обрабатываем теги из tags_input (если заполнено, объединяем с выбранными через виджет)
            tags_input = self.cleaned_data.get("tags_input", [])
            if tags_input:
                # Объединяем теги из tags_input с выбранными через стандартный виджет
                existing_tags = list(video.tags.all())
                # Создаем словарь для удаления дубликатов по pk
                all_tags_dict = {}
                for tag in existing_tags:
                    all_tags_dict[tag.pk] = tag
                for tag in tags_input:
                    all_tags_dict[tag.pk] = tag
                # Устанавливаем объединенный список тегов
                video.tags.set(list(all_tags_dict.values()))
            # Если tags_input не заполнен, используем стандартное сохранение через save_m2m

        return video
