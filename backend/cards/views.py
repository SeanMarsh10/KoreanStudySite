from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Card, Deck
from .serializers import CardSerializer, DeckSerializer


class DeckViewSet(viewsets.ModelViewSet):
    serializer_class = DeckSerializer

    def get_queryset(self):
        return Deck.objects.filter(owner=self.request.user).order_by("name")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True)
    def study(self, request, pk=None):
        """Cards that are due now, in random order."""
        cards = self.get_object().cards.filter(due__lte=timezone.now()).order_by("?")
        return Response(CardSerializer(cards, many=True, context={"request": request}).data)


class CardViewSet(viewsets.ModelViewSet):
    serializer_class = CardSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Card.objects.filter(deck__owner=self.request.user).order_by("-id")
        deck, q = self.request.query_params.get("deck"), self.request.query_params.get("q")
        if deck:
            qs = qs.filter(deck_id=deck)
        if q:
            qs = qs.filter(Q(korean__icontains=q) | Q(english__icontains=q) | Q(romanization__icontains=q))
        return qs

    @action(detail=False)
    def study(self, request):
        """Due cards from every deck (the 'All cards' list)."""
        cards = self.get_queryset().filter(due__lte=timezone.now()).order_by("?")
        return Response(CardSerializer(cards, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        card = self.get_object()
        card.record_review(bool(request.data.get("correct")))
        return Response(CardSerializer(card, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or User.objects.filter(username=username).exists():
        return Response({"detail": "Choose a different username."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(password)
    except ValidationError as e:
        return Response({"detail": " ".join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(username=username, password=password)
    return Response({"token": Token.objects.create(user=user).key}, status=status.HTTP_201_CREATED)
