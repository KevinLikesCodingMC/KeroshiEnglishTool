from django.contrib import admin
from .models import TTSJob


@admin.register(TTSJob)
class TTSJobAdmin(admin.ModelAdmin):
	list_display = ("id", "text_preview", "voice", "speed", "status", "created_at")
	list_filter = ("status", "voice", "created_at")
	search_fields = ("text", "error_message")
	readonly_fields = ("created_at", "started_at", "completed_at")
	date_hierarchy = "created_at"

	@admin.display(description = "文本")
	def text_preview(self, job):
		return job.text[:50]
