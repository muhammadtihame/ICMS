from django.contrib import admin
from .models import User, Student, Parent


class UserAdmin(admin.ModelAdmin):
    list_display = [
        "get_full_name",
        "username",
        "email",
        "is_active",
        "is_student",
        "is_lecturer",
        "is_parent",
        "is_staff",
    ]
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "is_lecturer",
        "is_parent",
        "is_staff",
    ]

    class Meta:
        managed = True
        verbose_name = "User"
        verbose_name_plural = "Users"


class StudentAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "program",
        "level",
        "semester",
        "get_full_name",
        "get_email",
    ]
    list_filter = ["program", "level", "semester"]
    search_fields = ["student__username", "student__first_name", "student__last_name", "student__email"]
    ordering = ["student__first_name", "student__last_name"]
    
    def get_full_name(self, obj):
        return obj.student.get_full_name
    get_full_name.short_description = "Full Name"
    
    def get_email(self, obj):
        return obj.student.email
    get_email.short_description = "Email"


admin.site.register(User, UserAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Parent)
