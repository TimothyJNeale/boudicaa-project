# SDS 9.3 — Error handling middleware
import logging
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger('gtd')


class ErrorLoggingMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        logger.error(
            f"Unhandled exception: {exception}",
            exc_info=True,
            extra={
                'user_id': request.user.id if request.user.is_authenticated else None,
                'request_path': request.path,
                'request_method': request.method,
            }
        )
        return None
