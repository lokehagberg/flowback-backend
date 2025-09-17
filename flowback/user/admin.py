from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from flowback.user.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'is_staff')
    list_filter = ('is_staff',)
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('profile_image', 'banner_image', 'bio', 'website')}),
        ('Permissions', {'fields': ('is_staff',)}),
        ('Activity', {'fields': ('last_login',)})
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()
