"""
Core views for TubeCMS.
"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.users.models import User, COUNTRY_CHOICES, GENDER_CHOICES, ORIENTATION_CHOICES
from apps.videos.models import Video

from .models import Category, Tag


def home(request):
    """Home page with featured videos."""
    from django.core.cache import cache

    from apps.videos.constants import FEATURED_VIDEOS_LIMIT, RECENT_VIDEOS_LIMIT

    # Попытка получить данные из кэша
    cache_key = "homepage_videos"
    cached_data = cache.get(cache_key)

    if cached_data:
        context = cached_data
    else:
        # Используем оптимизированный менеджер
        homepage_data = Video.objects.for_homepage(
            featured_limit=FEATURED_VIDEOS_LIMIT, recent_limit=RECENT_VIDEOS_LIMIT
        )

        context = {
            "featured_videos": homepage_data["featured"],
            "recent_videos": homepage_data["recent"],
        }

        # Кэшируем на 5 минут
        cache.set(cache_key, context, 300)

    return render(request, "core/home.html", context)


def search(request):
    """Search videos."""
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")

    # Используем оптимизированный менеджер
    videos = Video.objects.published().with_related().with_stats()

    # Применяем поиск
    if query:
        videos = videos.search(query)

    # Фильтр по категории
    if category:
        videos = videos.by_category(category)

    # Сортировка с использованием оптимизированных методов
    if sort == "popular":
        videos = videos.popular()
    elif sort == "trending":
        videos = videos.trending()
    elif sort == "oldest":
        videos = videos.order_by("created_at")
    else:  # newest
        videos = videos.recent()

    from apps.videos.constants import VIDEOS_PER_PAGE

    paginator = Paginator(videos, VIDEOS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "videos": page_obj,
        "query": query,
        "selected_category": category,
        "sort": sort,
    }
    return render(request, "videos/list.html", context)


def get_categories(request):
    """Display all categories page."""
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(video_count=Count("video", filter=Q(video__status="published")))
        .order_by("order", "name")
    )

    context = {
        "categories": categories,
    }
    return render(request, "core/categories.html", context)


@require_http_methods(["GET"])
def get_tags(request):
    """Get popular tags for HTMX requests."""
    tags = Tag.objects.all()[:20]
    return render(request, "partials/tags.html", {"tags": tags})


@require_http_methods(["GET"])
def search_dropdown(request):
    """HTMX search dropdown results with categories, tags, and users."""
    from apps.videos.constants import SEARCH_DROPDOWN_LIMIT, SEARCH_MIN_QUERY_LENGTH

    from .cache_utils import cache_search_results

    query = request.GET.get("q", "").strip()
    search_type = request.GET.get("type", "all")  # all, videos, users, categories, tags

    if len(query) < SEARCH_MIN_QUERY_LENGTH:
        return render(
            request,
            "core/htmx/search_results.html",
            {
                "videos": [],
                "users": [],
                "categories": [],
                "tags": [],
                "query": query,
                "search_type": search_type,
            },
        )

    # Use cached search results for better performance
    results = cache_search_results(
        query=query,
        search_type=search_type,
        limit=SEARCH_DROPDOWN_LIMIT,
        timeout=300,  # Cache for 5 minutes
    )

    return render(
        request,
        "core/htmx/search_results.html",
        {
            **results,
            "query": query,
            "search_type": search_type,
        },
    )


def robots_txt(request):
    """Serve robots.txt file."""
    from .utils import get_seo_settings

    seo_settings = get_seo_settings()

    if seo_settings and seo_settings.robots_txt:
        robots_content = seo_settings.robots_txt
    else:
        robots_content = """User-agent: *
Allow: /

Sitemap: http://localhost:8008/sitemap.xml"""

    from django.http import HttpResponse

    response = HttpResponse(robots_content, content_type="text/plain")
    return response


def tag_videos(request, slug):
    """Display videos by tag."""
    from django.shortcuts import get_object_or_404

    tag = get_object_or_404(Tag, slug=slug)
    videos = (
        Video.objects.filter(tags=tag, status="published")
        .select_related("created_by", "category")
        .prefetch_related("tags")
        .distinct()
        .order_by("-created_at")
    )

    # Pagination
    paginator = Paginator(videos, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "tag": tag,
        "videos": page_obj,
    }
    return render(request, "videos/tag.html", context)


@require_http_methods(["GET"])
def tag_autocomplete(request):
    """HTMX autocomplete for tags."""
    query = request.GET.get("q", "").strip()

    if len(query) < 1:
        return render(request, "core/htmx/tag_autocomplete.html", {"tags": []})

    # Поиск существующих тегов
    tags = Tag.objects.filter(name__icontains=query)[:10]

    return render(request, "core/htmx/tag_autocomplete.html", {"tags": tags})


def community_list(request):
    """Страница сообщества со списком всех пользователей."""
    # Получаем параметры фильтрации и сортировки
    sort_by = request.GET.get("sort", "date_joined")  # По умолчанию по дате регистрации
    country = request.GET.get("country", "")
    gender = request.GET.get("gender", "")
    orientation = request.GET.get("orientation", "")
    age_min = request.GET.get("age_min", "")
    age_max = request.GET.get("age_max", "")
    has_avatar = request.GET.get("has_avatar", "")
    search = request.GET.get("search", "")

    # Базовый queryset - все пользователи с аннотациями
    users = User.objects.annotate(
        videos_count_actual=Count("created_videos", distinct=True),
        subscribers_count_actual=Count("subscribers", distinct=True),
    ).select_related("profile")

    # Фильтрация по поиску
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(bio__icontains=search)
        )

    # Фильтрация по стране
    if country:
        users = users.filter(country=country)

    # Фильтрация по полу
    if gender:
        users = users.filter(gender=gender)

    # Фильтрация по ориентации
    if orientation:
        users = users.filter(orientation=orientation)

    # Фильтрация по возрасту
    if age_min:
        try:
            age_min = int(age_min)
            from django.utils import timezone

            max_birth_year = timezone.now().year - age_min
            users = users.filter(birth_date__year__lte=max_birth_year)
        except ValueError:
            pass

    if age_max:
        try:
            age_max = int(age_max)
            from django.utils import timezone

            min_birth_year = timezone.now().year - age_max
            users = users.filter(birth_date__year__gte=min_birth_year)
        except ValueError:
            pass

    # Фильтрация по наличию аватара
    if has_avatar == "yes":
        users = users.exclude(Q(avatar="") | Q(avatar__isnull=True))
    elif has_avatar == "no":
        users = users.filter(Q(avatar="") | Q(avatar__isnull=True))

    # Сортировка
    if sort_by == "date_joined":
        users = users.order_by("-date_joined")
    elif sort_by == "videos_count":
        users = users.order_by("-videos_count_actual", "-date_joined")
    elif sort_by == "subscribers_count":
        users = users.order_by("-subscribers_count_actual", "-date_joined")
    elif sort_by == "username":
        users = users.order_by("username")
    elif sort_by == "last_login":
        users = users.order_by("-last_login")
    else:
        users = users.order_by("-date_joined")

    # Пагинация
    paginator = Paginator(users, 24)  # 24 пользователя на страницу (4x6 сетка)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Получаем уникальные значения для фильтров (кэшируем)
    from django.core.cache import cache

    cache_key = "community_countries"
    country_choices = cache.get(cache_key)
    if country_choices is None:
        countries = (
            User.objects.exclude(country="")
            .values_list("country", flat=True)
            .distinct()
        )
        country_choices = [
            (code, dict(COUNTRY_CHOICES).get(code, code)) for code in countries
        ]
        cache.set(cache_key, country_choices, 3600)  # Кэш на 1 час

    context = {
        "users": page_obj,
        "sort_by": sort_by,
        "country": country,
        "gender": gender,
        "orientation": orientation,
        "age_min": age_min,
        "age_max": age_max,
        "has_avatar": has_avatar,
        "search": search,
        "country_choices": country_choices,
        "gender_choices": GENDER_CHOICES,
        "orientation_choices": ORIENTATION_CHOICES,
        "total_users": paginator.count,
    }

    return render(request, "core/community.html", context)
