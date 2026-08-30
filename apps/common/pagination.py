from rest_framework.pagination import PageNumberPagination


class ClientListPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = None
    max_page_size = 12
