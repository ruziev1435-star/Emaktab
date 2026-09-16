from django.db import models


class Article(models.Model):
    """Aggregated (not authored) news/articles from official sources."""

    class Category(models.TextChoices):
        UZ_NEWS = "uz_news", "Uzbekistan current events"
        MENTAL_HEALTH = "mental_health", "Teen mental health"
        DIGITAL_WORLD = "digital_world", "Teens & the digital world"

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices)
    source_name = models.CharField(max_length=150)
    source_url = models.URLField()
    summary = models.TextField(blank=True)
    published_at = models.DateField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title
