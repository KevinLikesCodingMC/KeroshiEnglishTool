from django.contrib import admin

from .models import SourceDocument, Word


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
	list_display = ("source_id", "imported_at", "updated_at")
	search_fields = ("source_id",)
	readonly_fields = ("imported_at", "updated_at")


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
	list_display = ("text", "normalized", "created_at")
	search_fields = ("text", "normalized")
	readonly_fields = ("normalized", "created_at")
