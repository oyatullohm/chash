import logging

from django.core.cache import cache
from django.utils import timezone

from .tasks import my_background_task

logger = logging.getLogger(__name__)


class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            key = f"user_active:{request.user.id}"

            if cache.add(key, True, timeout=60 * 60 * 24):
                task = my_background_task.delay(request.user.id)

                logger.info(
                    f"[{timezone.now()}] Celery task queuega yuborildi. "
                    f"user_id={request.user.id}, task_id={task.id}"
                )
            else:
                logger.info(
                    f"[{timezone.now()}] Celery task yuborilmadi. "
                    f"user_id={request.user.id} (24 soat ichida allaqachon ishlagan)"
                )

        return self.get_response(request)