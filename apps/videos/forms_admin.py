"""
Admin forms for video processing.
"""
from django import forms
from .models import Video
from .models_encoding import VideoEncodingProfile
from apps.models.models import Model


class VideoAdminForm(forms.ModelForm):
    """Custom form for video admin with encoding profile selection."""
    encoding_profiles = forms.ModelMultipleChoiceField(
        queryset=VideoEncodingProfile.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Профили кодирования",
        help_text="Выберите профили для конвертации видео"
    )
    
    performers = forms.ModelMultipleChoiceField(
        queryset=Model.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Модели",
        help_text="Выберите модели, участвующие в видео"
    )
    
    class Meta:
        model = Video
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default selected profiles to all active ones
        if not self.instance.pk:  # New video
            self.fields['encoding_profiles'].initial = VideoEncodingProfile.objects.filter(is_active=True)
            
            # Set default values for fields that exist in the model
            if 'duration' in self.fields:
                self.fields['duration'].initial = 0
            if 'file_size' in self.fields:
                self.fields['file_size'].initial = 0
            if 'views_count' in self.fields:
                self.fields['views_count'].initial = 0
            if 'likes_count' in self.fields:
                self.fields['likes_count'].initial = 0
            if 'dislikes_count' in self.fields:
                self.fields['dislikes_count'].initial = 0
            if 'comments_count' in self.fields:
                self.fields['comments_count'].initial = 0
            if 'processing_status' in self.fields:
                self.fields['processing_status'].initial = 'pending'
            if 'processing_progress' in self.fields:
                self.fields['processing_progress'].initial = 0
        
        # Make some fields not required if they exist
        for field_name in ['duration', 'file_size', 'views_count', 'likes_count', 'dislikes_count', 'comments_count', 'processing_status', 'processing_progress']:
            if field_name in self.fields:
                self.fields[field_name].required = False
    
    def save(self, commit=True):
        video = super().save(commit=commit)
        
        if commit:
            # Store selected profiles for processing
            selected_profiles = self.cleaned_data.get('encoding_profiles', [])
            if selected_profiles:
                # Store selected profiles as attribute for signals
                video._selected_encoding_profiles = [p.id for p in selected_profiles]
            else:
                # If no profiles selected, use all active ones
                video._selected_encoding_profiles = list(VideoEncodingProfile.objects.filter(is_active=True).values_list('id', flat=True))
            
            # Handle selected performers
            selected_performers = self.cleaned_data.get('performers', [])
            if selected_performers:
                # Clear existing performers
                video.performers.clear()
                # Add new performers
                for performer in selected_performers:
                    from apps.models.models import ModelVideo
                    ModelVideo.objects.create(
                        model=performer,
                        video=video,
                        is_primary=(performer == selected_performers.first())
                    )
        
        return video
