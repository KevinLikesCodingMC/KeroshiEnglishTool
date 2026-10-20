from django.db import models


class Question(models.Model):
	question = models.TextField("题目")
	analysis = models.TextField("解析", blank =  True)
	created_at = models.DateTimeField("记录时间", auto_now_add = True)
	source = models.CharField("来源", max_length = 255)

	class Meta:
		ordering = ["-created_at", "id"]
		verbose_name = "翻译题目"
		verbose_name_plural = "翻译题目"

	def __str__(self):
		return self.question[:50]
