from django.db import models


def normalize_word(value: str) -> str:
	return value.strip().replace("’", "'").casefold()


class SourceDocument(models.Model):
	source_id = models.CharField("来源标识", max_length = 255, unique = True)
	imported_at = models.DateTimeField("首次导入时间", auto_now_add = True)
	updated_at = models.DateTimeField("最后更新时间", auto_now = True)

	class Meta:
		ordering = ["source_id"]
		verbose_name = "来源文档"
		verbose_name_plural = "来源文档"

	def __str__(self):
		return self.source_id


class Word(models.Model):
	text = models.CharField("单词", max_length = 100)
	normalized = models.CharField(
		"标准化单词",
		max_length = 100,
		unique = True,
		editable = False,
	)
	created_at = models.DateTimeField("创建时间", auto_now_add = True)

	class Meta:
		ordering = ["normalized"]
		verbose_name = "单词"
		verbose_name_plural = "单词"

	def save(self, *args, **kwargs):
		self.normalized = normalize_word(self.text)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.text
