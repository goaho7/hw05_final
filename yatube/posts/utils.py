from django.core.paginator import Paginator
from django.conf import settings


def paginat(request, posts):
    paginator = Paginator(posts, settings.PAGINATION)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
