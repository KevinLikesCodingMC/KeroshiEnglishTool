from django.contrib import admin
from .models import Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
	list_display = ("question", "source", "created_at")
	list_filter = ("source", "created_at")
	search_fields = ("question", "analysis", "source")
	date_hierarchy = "created_at"
