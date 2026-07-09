import logging
from celery import shared_task
from .models import CustomUser
from .Trasaciton import sync_card_transactions
logger = logging.getLogger(__name__)


@shared_task
def my_background_task(user_id):
    logger.info(f"Task boshlandi. user_id={user_id}")

    try:
        user = CustomUser.objects.get(id=user_id)
        logger.info(f"User topildi. code={user.code}")

        sync_card_transactions(user.code)

        logger.info(f"Transaction sync muvaffaqiyatli tugadi. user_id={user_id}")

    except CustomUser.DoesNotExist:
        logger.error(f"User topilmadi. user_id={user_id}")

    except Exception as e:
        logger.exception(f"Taskda xatolik yuz berdi. user_id={user_id}. Xato: {e}")