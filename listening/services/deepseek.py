from django.conf import settings
from openai import OpenAI


class DeepSeekConfigurationError(Exception):
	pass


def create_completion(messages, *, max_tokens = 24000):
	if not settings.DEEPSEEK_API_KEY:
		raise DeepSeekConfigurationError("Please configure DEEPSEEK_API_KEY in .env.")
	with OpenAI(
		api_key = settings.DEEPSEEK_API_KEY,
		base_url = "https://api.deepseek.com",
		timeout = 60.0,
		max_retries = 0,
	) as client:
		return client.chat.completions.create(
			model = settings.DEEPSEEK_MODEL,
			messages = messages,
			max_tokens = max_tokens,
			extra_body = {"thinking": {"type": "disabled"}},
		)
