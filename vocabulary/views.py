from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .dictionary import DictionaryError
from .practice import choose_meaning_questions


@require_GET
def meaning(request):
	return render(request, "vocabulary/meaning.html")


@never_cache
@require_GET
def questions(request):
	words: list[str] | None = (
		request.GET.getlist("word") if "word" in request.GET else None
	)
	if words is not None:
		if len(words) > 50 or any(
			not word.isascii()
			or not word.isalpha()
			or not 2 <= len(word) <= 30
			for word in words
		):
			return JsonResponse({"error": "Invalid review words."}, status = 400)

	try:
		questions = choose_meaning_questions(
			batch_size = 50 if words is not None else 10,
			words = set(words) if words is not None else None,
		)
		return JsonResponse({"questions": questions})
	except DictionaryError:
		return JsonResponse(
			{"error": "The dictionary could not be read. "
				"Check the dictionary file and try again."},
			status = 503,
		)


@require_GET
def index(request):
	return redirect("vocabulary:meaning")
