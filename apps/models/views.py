"""
Views for models app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Model, ModelVideo, ModelSubscription, ModelLike
from apps.videos.models import Video


class ModelListView(ListView):
    """List view for models."""
    model = Model
    template_name = 'models/list.html'
    context_object_name = 'models'
    paginate_by = 24
    
    def get_queryset(self):
        queryset = Model.objects.filter(is_active=True).select_related('user').prefetch_related('model_videos')
        
        # Filter by gender
        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)
        
        # Filter by country
        country = self.request.GET.get('country')
        if country:
            queryset = queryset.filter(country__icontains=country)
        
        # Filter by hair color
        hair_color = self.request.GET.get('hair_color')
        if hair_color:
            queryset = queryset.filter(hair_color=hair_color)
        
        # Filter by eye color
        eye_color = self.request.GET.get('eye_color')
        if eye_color:
            queryset = queryset.filter(eye_color=eye_color)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(display_name__icontains=search) |
                Q(bio__icontains=search) |
                Q(country__icontains=search) |
                Q(ethnicity__icontains=search)
            )
        
        # Ordering
        sort = self.request.GET.get('sort', 'newest')
        if sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort == 'popular':
            queryset = queryset.order_by('-views_count')
        elif sort == 'subscribers':
            queryset = queryset.order_by('-subscribers_count')
        elif sort == 'videos':
            queryset = queryset.order_by('-videos_count')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genders'] = Model.GENDER_CHOICES
        context['hair_colors'] = Model.HAIR_COLOR_CHOICES
        context['eye_colors'] = Model.EYE_COLOR_CHOICES
        context['countries'] = Model.objects.values_list('country', flat=True).distinct().exclude(country='')
        return context


class ModelDetailView(DetailView):
    """Detail view for a model."""
    model = Model
    template_name = 'models/detail.html'
    context_object_name = 'model'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Model.objects.filter(is_active=True).select_related('user').prefetch_related('model_videos__video')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.get_object()
        
        # Increment view count
        model.views_count += 1
        model.save(update_fields=['views_count'])
        
        # Get model's videos
        model_videos = ModelVideo.objects.filter(model=model).select_related('video').order_by('-created_at')
        paginator = Paginator(model_videos, 12)
        page = self.request.GET.get('page')
        context['model_videos'] = paginator.get_page(page)
        
        # Check if user is subscribed
        if self.request.user.is_authenticated:
            context['is_subscribed'] = ModelSubscription.objects.filter(
                user=self.request.user, 
                model=model
            ).exists()
            context['is_liked'] = ModelLike.objects.filter(
                user=self.request.user, 
                model=model
            ).exists()
        else:
            context['is_subscribed'] = False
            context['is_liked'] = False
        
        return context


class ModelCreateView(LoginRequiredMixin, CreateView):
    """Create view for a model."""
    model = Model
    template_name = 'models/create.html'
    fields = [
        'display_name', 'bio', 'avatar', 'cover_photo',
        'gender', 'age', 'birth_date', 'country', 'ethnicity', 'career_start', 'zodiac_sign',
        'hair_color', 'eye_color', 'has_tattoos', 'tattoos_description', 
        'has_piercings', 'piercings_description', 'breast_size', 'measurements', 
        'height', 'weight'
    ]
    success_url = reverse_lazy('models:list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ModelUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for a model."""
    model = Model
    template_name = 'models/update.html'
    fields = [
        'display_name', 'bio', 'avatar', 'cover_photo',
        'gender', 'age', 'birth_date', 'country', 'ethnicity', 'career_start', 'zodiac_sign',
        'hair_color', 'eye_color', 'has_tattoos', 'tattoos_description', 
        'has_piercings', 'piercings_description', 'breast_size', 'measurements', 
        'height', 'weight'
    ]
    success_url = reverse_lazy('models:list')
    
    def get_queryset(self):
        return Model.objects.filter(user=self.request.user)


@login_required
def model_subscribe(request, slug):
    """Subscribe to a model."""
    model = get_object_or_404(Model, slug=slug, is_active=True)
    
    if request.method == 'POST':
        subscription, created = ModelSubscription.objects.get_or_create(
            user=request.user,
            model=model
        )
        if created:
            model.subscribers_count += 1
            model.save(update_fields=['subscribers_count'])
    
    return redirect('models:detail', slug=slug)


@login_required
def model_unsubscribe(request, slug):
    """Unsubscribe from a model."""
    model = get_object_or_404(Model, slug=slug, is_active=True)
    
    if request.method == 'POST':
        subscription = ModelSubscription.objects.filter(
            user=request.user,
            model=model
        ).first()
        if subscription:
            subscription.delete()
            if model.subscribers_count > 0:
                model.subscribers_count -= 1
                model.save(update_fields=['subscribers_count'])
    
    return redirect('models:detail', slug=slug)


@login_required
def model_like(request, slug):
    """Like a model."""
    model = get_object_or_404(Model, slug=slug, is_active=True)
    
    if request.method == 'POST':
        like, created = ModelLike.objects.get_or_create(
            user=request.user,
            model=model
        )
        if created:
            model.likes_count += 1
            model.save(update_fields=['likes_count'])
    
    return redirect('models:detail', slug=slug)


@login_required
def model_unlike(request, slug):
    """Unlike a model."""
    model = get_object_or_404(Model, slug=slug, is_active=True)
    
    if request.method == 'POST':
        like = ModelLike.objects.filter(
            user=request.user,
            model=model
        ).first()
        if like:
            like.delete()
            if model.likes_count > 0:
                model.likes_count -= 1
                model.save(update_fields=['likes_count'])
    
    return redirect('models:detail', slug=slug)
