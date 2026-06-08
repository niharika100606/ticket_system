from django.db import models
from django.utils import timezone


class Theater(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    total_seats = models.IntegerField(default=100)

    def __str__(self):
        return self.name


class Booking(models.Model):
    email = models.EmailField()
    movie_name = models.CharField(max_length=100, db_index=True)
    show_time = models.CharField(max_length=100)
    seats = models.CharField(max_length=100)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    theater = models.ForeignKey(
        Theater,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings"
    )

    status = models.CharField(max_length=30, default="PENDING", db_index=True)
    amount = models.IntegerField(default=50000, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.movie_name} - {self.status}"


class PaymentEvent(models.Model):
    event_id = models.CharField(max_length=150, unique=True)
    event_type = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    processed = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)
    trailer_url = models.URLField(blank=True, null=True)


class Seat(models.Model):
    seat_number = models.CharField(max_length=10, unique=True)
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return self.seat_number


class SeatReservation(models.Model):
    STATUS_CHOICES = [
        ("LOCKED", "Locked"),
        ("CONFIRMED", "Confirmed"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    user_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="LOCKED", db_index=True)
    locked_until = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.locked_until


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=150, db_index=True)
    genres = models.ManyToManyField(Genre, related_name="movies")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="movies")
    release_date = models.DateField(null=True, blank=True, db_index=True)
    rating = models.FloatField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["rating"]),
            models.Index(fields=["release_date"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.title