from django.contrib import admin
from accounts.models import User, VerificationCode
from django.utils.safestring import mark_safe

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'updated_at','email_verified_at','phone_verified_at')
    list_display = ('email','phone','status','is_admin')
    list_filter = ('status','created_at','is_active')
    search_fields = ('created_at','email','phone')

    def preview_avatar_image(self, obj):
        return mark_safe(f'<img src="{obj.avatar.url}"width="150"/>')


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('code','is_used','is_expired')
    readonly_fields = ('created_at','expired_at')