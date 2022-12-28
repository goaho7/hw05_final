from django.core.paginator import Paginator
from yatube.settings import PAGINATION


def paginat(request, posts):
    paginator = Paginator(posts, PAGINATION)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
