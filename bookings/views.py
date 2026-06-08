import json
import logging
from urllib.parse import urlparse, parse_qs

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour, TruncDay, TruncMonth, TruncWeek
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Booking,
    PaymentEvent,
    Seat,
    SeatReservation,
    Movie,
    Genre,
    Language,
    Theater,
)

logger = logging.getLogger(__name__)


def create_payment_order(request):
    booking = Booking.objects.create(
        email="test@gmail.com",
        movie_name="Avengers",
        show_time="2026-05-24 18:00",
        seats="A1,A2",
        amount=50000,
        status="PAYMENT_PENDING",
    )

    fake_order_id = f"order_test_{booking.id}"
    booking.razorpay_order_id = fake_order_id
    booking.save()

    return JsonResponse({
        "message": "Payment order created in test/mock mode",
        "booking_id": booking.id,
        "razorpay_order_id": booking.razorpay_order_id,
        "amount": booking.amount,
        "currency": "INR",
        "status": booking.status,
    })


@csrf_exempt
def reserve_seats(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    data = json.loads(request.body)

    user_email = data.get("email", "test@gmail.com")
    seat_numbers = data.get("seats", [])

    if not seat_numbers:
        return JsonResponse({"message": "No seats selected"}, status=400)

    locked_until = timezone.now() + timezone.timedelta(minutes=2)

    try:
        with transaction.atomic():
            seats = list(
                Seat.objects.select_for_update().filter(
                    seat_number__in=seat_numbers
                )
            )

            if len(seats) != len(seat_numbers):
                return JsonResponse({"message": "Some seats do not exist"}, status=400)

            for seat in seats:
                if seat.is_booked:
                    return JsonResponse({
                        "message": f"Seat {seat.seat_number} already booked"
                    }, status=409)

                active_lock = SeatReservation.objects.filter(
                    seat=seat,
                    status="LOCKED",
                    locked_until__gt=timezone.now()
                ).exists()

                if active_lock:
                    return JsonResponse({
                        "message": f"Seat {seat.seat_number} already locked"
                    }, status=409)

            reservations = []

            for seat in seats:
                reservation = SeatReservation.objects.create(
                    seat=seat,
                    user_email=user_email,
                    status="LOCKED",
                    locked_until=locked_until
                )
                reservations.append(reservation.id)

        return JsonResponse({
            "message": "Seats locked for 2 minutes",
            "reservation_ids": reservations,
            "locked_until": locked_until,
        })

    except Exception as exc:
        logger.error(f"Seat reservation failed: {exc}")
        return JsonResponse({"message": "Seat reservation failed"}, status=500)


@csrf_exempt
def verify_payment(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    data = json.loads(request.body)

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")

    try:
        booking = Booking.objects.get(razorpay_order_id=razorpay_order_id)

        if booking.status == "PAID":
            return JsonResponse({"message": "Duplicate payment ignored"})

        booking.payment_id = razorpay_payment_id
        booking.status = "PAID"
        booking.save()

        logger.info(f"Payment verified successfully for booking {booking.id}")

        return JsonResponse({"message": "Payment verified successfully"})

    except Exception as exc:
        logger.error(f"Payment verification failed: {exc}")
        return JsonResponse({"message": "Payment verification failed"}, status=400)


@csrf_exempt
def razorpay_webhook(request):
    payload = json.loads(request.body)

    event_id = payload.get("id")
    event_type = payload.get("event")

    if PaymentEvent.objects.filter(event_id=event_id).exists():
        return JsonResponse({"message": "Duplicate webhook ignored"})

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")

    PaymentEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        razorpay_payment_id=payment_id,
        razorpay_order_id=order_id,
        processed=True,
    )

    try:
        booking = Booking.objects.get(razorpay_order_id=order_id)

        if event_type == "payment.captured":
            booking.status = "PAID"
            booking.payment_id = payment_id

        elif event_type == "payment.failed":
            booking.status = "FAILED"

        booking.save()

        logger.info(f"Webhook processed successfully for booking {booking.id}")

    except Booking.DoesNotExist:
        logger.error(f"No booking found for order_id {order_id}")

    return JsonResponse({"message": "Webhook processed successfully"})


def movie_filter_api(request):
    genres = request.GET.getlist("genre")
    languages = request.GET.getlist("language")
    sort_by = request.GET.get("sort", "title")
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))

    allowed_sorting = {
        "title": "title",
        "-title": "-title",
        "rating": "rating",
        "-rating": "-rating",
        "release_date": "release_date",
        "-release_date": "-release_date",
    }

    sort_field = allowed_sorting.get(sort_by, "title")

    movies = (
        Movie.objects
        .filter(is_active=True)
        .select_related("language")
        .prefetch_related("genres")
    )

    if genres:
        movies = movies.filter(genres__name__in=genres)

    if languages:
        movies = movies.filter(language__name__in=languages)

    movies = movies.distinct().order_by(sort_field)

    paginator = Paginator(movies, page_size)
    current_page = paginator.get_page(page)

    movie_data = []

    for movie in current_page:
        movie_data.append({
            "id": movie.id,
            "title": movie.title,
            "language": movie.language.name,
            "genres": [genre.name for genre in movie.genres.all()],
            "rating": movie.rating,
            "release_date": movie.release_date,
        })

    genre_count_query = Movie.objects.filter(is_active=True)

    if languages:
        genre_count_query = genre_count_query.filter(language__name__in=languages)

    genre_counts = Genre.objects.annotate(
        movie_count=Count(
            "movies",
            filter=Q(movies__in=genre_count_query),
            distinct=True
        )
    ).values("name", "movie_count")

    language_count_query = Movie.objects.filter(is_active=True)

    if genres:
        language_count_query = language_count_query.filter(genres__name__in=genres)

    language_counts = Language.objects.annotate(
        movie_count=Count(
            "movies",
            filter=Q(movies__in=language_count_query),
            distinct=True
        )
    ).values("name", "movie_count")

    return JsonResponse({
        "movies": movie_data,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "total_movies": paginator.count,
        },
        "filters": {
            "genre_counts": list(genre_counts),
            "language_counts": list(language_counts),
        }
    })


@staff_member_required
def admin_analytics_dashboard(request):
    cache_key = "admin_analytics_dashboard"
    cached_data = cache.get(cache_key)

    if cached_data:
        return JsonResponse(cached_data)

    paid_bookings = Booking.objects.filter(status="PAID")

    daily_revenue = list(
        paid_bookings
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(total_revenue=Sum("amount"))
        .order_by("-day")[:7]
    )

    weekly_revenue = list(
        paid_bookings
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(total_revenue=Sum("amount"))
        .order_by("-week")[:4]
    )

    monthly_revenue = list(
        paid_bookings
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total_revenue=Sum("amount"))
        .order_by("-month")[:6]
    )

    popular_movies = list(
        Booking.objects
        .values("movie_name")
        .annotate(total_bookings=Count("id"))
        .order_by("-total_bookings")[:5]
    )

    busiest_theaters = []

    theaters = Theater.objects.annotate(
        occupied_bookings=Count(
            "bookings",
            filter=Q(bookings__status="PAID")
        )
    ).order_by("-occupied_bookings")[:5]

    for theater in theaters:
        occupancy_rate = 0

        if theater.total_seats > 0:
            occupancy_rate = round(
                (theater.occupied_bookings / theater.total_seats) * 100,
                2
            )

        busiest_theaters.append({
            "theater_name": theater.name,
            "total_seats": theater.total_seats,
            "occupied_bookings": theater.occupied_bookings,
            "occupancy_rate": occupancy_rate,
        })

    peak_booking_hours = list(
        Booking.objects
        .annotate(hour=ExtractHour("created_at"))
        .values("hour")
        .annotate(total_bookings=Count("id"))
        .order_by("-total_bookings")[:5]
    )

    total_bookings = Booking.objects.count()
    cancelled_bookings = Booking.objects.filter(status="CANCELLED").count()

    cancellation_rate = 0

    if total_bookings > 0:
        cancellation_rate = round(
            (cancelled_bookings / total_bookings) * 100,
            2
        )

    data = {
        "daily_revenue": daily_revenue,
        "weekly_revenue": weekly_revenue,
        "monthly_revenue": monthly_revenue,
        "popular_movies": popular_movies,
        "busiest_theaters": busiest_theaters,
        "peak_booking_hours": peak_booking_hours,
        "cancellation_rate": cancellation_rate,
    }

    cache.set(cache_key, data, 60)

    return JsonResponse(data)


def get_youtube_video_id(url):
    if not url:
        return None

    parsed_url = urlparse(url)

    allowed_domains = [
        "www.youtube.com",
        "youtube.com",
        "youtu.be",
    ]

    if parsed_url.netloc not in allowed_domains:
        return None

    if parsed_url.netloc == "youtu.be":
        return parsed_url.path.strip("/")

    query_params = parse_qs(parsed_url.query)
    video_id = query_params.get("v", [None])[0]

    return video_id


def movie_detail(request, movie_id):
    movie = get_object_or_404(
        Movie,
        id=movie_id,
        is_active=True
    )

    trailer_url = getattr(movie, "trailer_url", None)

    video_id = get_youtube_video_id(trailer_url)

    embed_url = None

    if video_id:
        embed_url = f"https://www.youtube.com/embed/{video_id}"

    return render(
        request,
        "movie_detail.html",
        {
            "movie": movie,
            "embed_url": embed_url,
        }
    )
def home_page(request):
    return render(request, "home.html")


def movie_list_page(request):
    movies = (
        Movie.objects
        .filter(is_active=True)
        .select_related("language")
        .prefetch_related("genres")
        .order_by("-rating")
    )

    return render(
        request,
        "movies.html",
        {"movies": movies}
    )