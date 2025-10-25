from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.db import models


class SettingsModel(models.Model):
    """
    Dummy model for settings admin.
    """
    
    class Meta:
        verbose_name = 'Настройки'
        verbose_name_plural = 'Настройки'
        app_label = 'admin_settings'


class SettingsAdmin(admin.ModelAdmin):
    """
    Custom admin class for settings with multiple tabs.
    """
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('basic/', self.admin_site.admin_view(self.basic_settings_view), name='admin_settings_basic'),
            path('seo/', self.admin_site.admin_view(self.seo_settings_view), name='admin_settings_seo'),
            path('optimization/', self.admin_site.admin_view(self.optimization_settings_view), name='admin_settings_optimization'),
        ]
        return custom_urls + urls
    
    def basic_settings_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title='Основные настройки',
        )
        return render(request, 'admin/settings/basic.html', context)
    
    def seo_settings_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title='SEO и аналитика',
        )
        return render(request, 'admin/settings/seo.html', context)
    
    def optimization_settings_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title='Оптимизация',
        )
        return render(request, 'admin/settings/optimization.html', context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return True


# Register the settings admin
admin.site.register(SettingsModel, SettingsAdmin)