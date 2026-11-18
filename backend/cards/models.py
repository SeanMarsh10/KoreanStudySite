from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

# Leitner boxes: days to wait before a card in that box is due again.
INTERVAL_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 21}


class Deck(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="decks")
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Card(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="cards")
    korean = models.CharField(max_length=200)
    english = models.CharField(max_length=200)
    romanization = models.CharField(max_length=200, blank=True)
    example = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    image = models.ImageField(upload_to="cards/", blank=True, null=True)
    box = models.PositiveSmallIntegerField(default=1)
    due = models.DateTimeField(default=timezone.now)

    def record_review(self, correct):
        self.box = min(self.box + 1, 5) if correct else 1
        self.due = timezone.now() + timedelta(days=INTERVAL_DAYS[self.box])
        self.save()
        Review.objects.create(card=self, correct=correct)


class Review(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="reviews")
    correct = models.BooleanField()
    at = models.DateTimeField(auto_now_add=True)
