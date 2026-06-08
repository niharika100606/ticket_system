import logging
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import SeatReservation

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_ticket_email(self, email, context):
    try:
        html_content = render_to_string("ticket_confirmation.html", context)

        send_mail(
            subject="🎟 Ticket Confirmation",
            message="Your ticket is confirmed.",
            from_email="your_email@gmail.com",
            recipient_list=[email],
            fail_silently=False,
            html_message=html_content,
        )

        logger.info(f"Ticket email sent successfully to {email}")
        return "Email Sent"

    except Exception as exc:
        logger.error(f"Ticket email failed for {email}: {exc}")
        raise self.retry(exc=exc, countdown=5)


@shared_task
def release_expired_seat_reservations():
    expired_reservations = SeatReservation.objects.filter(
        status="LOCKED",
        locked_until__lt=timezone.now()
    )

    count = expired_reservations.update(status="EXPIRED")

    logger.info(f"Released {count} expired seat reservations")
    return f"Released {count} expired reservations"