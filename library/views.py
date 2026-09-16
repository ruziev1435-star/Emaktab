from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Article


@login_required
def article_list(request):
    category = request.GET.get("category", "")
    articles = Article.objects.all()
    if category:
        articles = articles.filter(category=category)
    return render(
        request,
        "library/article_list.html",
        {"articles": articles, "categories": Article.Category.choices, "selected": category},
    )
