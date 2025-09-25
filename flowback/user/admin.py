from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from flowback.user.models import User, Report, OnboardUser
from flowback.user.services import user_delete


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'is_staff')
    list_filter = ('is_staff',)
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('profile_image', 'banner_image', 'bio', 'website')}),
        ('Permissions', {'fields': ('is_staff',)}),
        ('Activity', {'fields': ('last_login',)}),
        ('Notifications', {'fields': ('email_notifications',)})
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

    def get_queryset(self, request):
        return User.objects.filter(is_active=True).all()

    def delete_model(self, request, obj):
        user_delete(user_id=obj.id)





@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    readonly_fields = ['created_at']

    list_display = ('user', 'title', 'created_at')
    list_filter = ('user', 'title', 'description', 'created_at')

    fieldsets = [
        (None, {'fields': ['user', 'title', 'description', 'created_at']}),
    ]

    add_fieldsets = [
        (None, {'fields': ['user', 'title', 'description']}),
    ]

    search_fields = ('user__username', 'user__email', 'title', 'description')
    ordering = ('created_at',)


@admin.register(OnboardUser)
class OnboardUserAdmin(admin.ModelAdmin):
    readonly_fields = ['verification_code', 'created_at', 'updated_at']
    
    list_display = ('email', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    
    fieldsets = [
        (None, {'fields': ['email', 'is_verified']}),
        ('System Info', {'fields': ['verification_code', 'created_at', 'updated_at']}),
    ]
    
    add_fieldsets = [
        (None, {'fields': ['email']}),
    ]
    
    search_fields = ('email',)
    ordering = ('-created_at',)
