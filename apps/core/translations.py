"""
Manual translations for TubeCMS.
Used when gettext is not available.
"""

TRANSLATIONS = {
    'ru': {
        'Settings': 'Настройки',
        'Account Settings': 'Настройки аккаунта',
        'Appearance': 'Внешний вид',
        'Theme': 'Тема',
        'Language': 'Язык',
        'Profile': 'Профиль',
        'Country': 'Страна',
        'Notifications': 'Уведомления',
        'Enable notifications': 'Включить уведомления',
        'Email notifications': 'Email уведомления',
        'Privacy': 'Приватность',
        'Privacy Level': 'Уровень приватности',
        'Save Settings': 'Сохранить настройки',
        'Cancel': 'Отмена',
        'Search...': 'Поиск...',
        'Upload video': 'Загрузить видео',
        'Upload': 'Загрузить',
        'Notifications': 'Уведомления',
        'Toggle theme': 'Переключить тему',
        'Profile': 'Профиль',
        'My Profile': 'Мой профиль',
        'Edit Profile': 'Редактировать профиль',
        'Playlists': 'Плейлисты',
        'Favorites': 'Избранное',
        'Watch Later': 'Смотреть позже',
        'Subscriptions': 'Подписки',
        'Admin Panel': 'Панель администратора',
        'Logout': 'Выход',
        'Login': 'Вход',
        'Register': 'Регистрация',
        'Home': 'Главная',
        'Videos': 'Видео',
        'Categories': 'Категории',
        'Pornstars': 'Порнозвёзды',
        'Popular': 'Популярное',
        'Trends': 'Тренды',
        'About Us': 'О нас',
        'About Company': 'О компании',
        'Press': 'Пресса',
        'Careers': 'Карьера',
        'Contact': 'Контакты',
        'For Creators': 'Для авторов',
        'TubeCMS for Authors': 'TubeCMS для авторов',
        'Monetization': 'Монетизация',
        'Partner Program': 'Партнёрская программа',
        'Creative Studios': 'Творческие студии',
        'Help': 'Помощь',
        'Support Center': 'Центр поддержки',
        'Community': 'Сообщество',
        'Rules': 'Правила',
        'Security': 'Безопасность',
        'Follow Us': 'Подписывайтесь',
        'All rights reserved.': 'Все права защищены.',
        'Light': 'Светлая',
        'Dark': 'Тёмная',
        'Public': 'Публичный',
        'Private': 'Приватный',
        'Change Language': 'Изменить язык',
    },
    'en': {
        # English is default, no translations needed
    }
}

def get_translation(text, language='en'):
    """Get translation for text in specified language."""
    if language in TRANSLATIONS and text in TRANSLATIONS[language]:
        return TRANSLATIONS[language][text]
    return text