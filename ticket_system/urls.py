from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

from bookings.views import (
    home_page,
    movie_list_page,
    create_payment_order,
    verify_payment,
    razorpay_webhook,
    reserve_seats,
    movie_filter_api,
    admin_analytics_dashboard,
    movie_detail,
)

urlpatterns = [
    path("", home_page),

    path("admin/analytics/", admin_analytics_dashboard),

    path("payment/create-order/", create_payment_order),
    path("payment/verify/", verify_payment),
    path("payment/webhook/", razorpay_webhook),

    path("seats/reserve/", reserve_seats),

    path("movies/", movie_list_page),
    path("api/movies/", movie_filter_api),
    path("movies/<int:movie_id>/", movie_detail),

    path("admin/", admin.site.urls),
]