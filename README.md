# Ticket Booking System

A Django-based movie ticket booking platform with secure booking, seat reservation, payment workflow, admin analytics, movie filtering, trailer embedding, and automated email confirmation.

## Features

### Automated Ticket Email Confirmation

* Background email processing using Celery.
* Retry mechanism for failed emails.
* HTML email templates.

### Payment Gateway Workflow

* Payment order creation.
* Payment verification.
* Duplicate payment prevention using idempotency logic.

### Seat Reservation System

* Seat locking for 2 minutes.
* Double-booking prevention.
* Atomic database transactions.

### Movie Filtering

* Filter by genre and language.
* Pagination and sorting.
* Optimized queries.

### Admin Analytics Dashboard

* Revenue analytics.
* Popular movies.
* Peak booking hours.
* Cancellation rate.

### Secure YouTube Trailer Embedding

* Trailer URL validation.
* XSS protection.
* Lazy loading support.

## Technologies Used

* Python
* Django
* SQLite
* Celery
* Redis
* HTML
* CSS

## Admin Credentials

Username: admin
Password: admin123

## Project Status

All internship tasks implemented successfully.
