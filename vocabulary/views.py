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
	try:
		return JsonResponse({"questions": choose_meaning_questions()})
	except DictionaryError:
		return JsonResponse({"error": "The dictionary could not be read. Check the dictionary file and try again."}, status = 503)


@require_GET
def index(request):
	return redirect("vocabulary:meaning")
