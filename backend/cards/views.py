import csv
import io

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Card, Deck, Playlist
from .serializers import CardSerializer, DeckSerializer, PlaylistSerializer


CSV_FIELDS = ["deck", "korean", "english", "romanization", "example", "notes"]


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


class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistSerializer

    def get_queryset(self):
        return Playlist.objects.filter(owner=self.request.user).prefetch_related("decks").order_by("name")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True)
    def study(self, request, pk=None):
        """Due cards from every deck in the playlist."""
        decks = self.get_object().decks.all()
        cards = Card.objects.filter(deck__in=decks, due__lte=timezone.now()).order_by("?")
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

    @action(detail=False)
    def export(self, request):
        """CSV of the cards in view (one deck with ?deck=ID, otherwise all). Pictures are not included."""
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="hangul-cards.csv"'
        resp.write("\ufeff")  # BOM so Excel reads Hangul correctly
        w = csv.writer(resp)
        w.writerow(CSV_FIELDS)
        for c in self.get_queryset().select_related("deck").order_by("deck__name", "id"):
            w.writerow([c.deck.name, c.korean, c.english, c.romanization, c.example, c.notes])
        return resp

    @action(detail=False, methods=["post"], url_path="import")
    def import_csv(self, request):
        """Needs 'korean' and 'english' columns. A 'deck' column sends each row to that deck (created if new);
        rows without one go to the deck chosen in the request. Duplicates are skipped."""
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Choose a CSV file."}, status=status.HTTP_400_BAD_REQUEST)
        raw = upload.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp949", errors="replace")  # Korean Excel often saves CSV this way
        reader = csv.DictReader(io.StringIO(text))
        reader.fieldnames = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
        if not {"korean", "english"} <= set(reader.fieldnames):
            return Response({"detail": "The file needs 'korean' and 'english' columns."}, status=status.HTTP_400_BAD_REQUEST)

        decks = {d.name: d for d in Deck.objects.filter(owner=request.user)}
        target = Deck.objects.filter(owner=request.user, pk=request.data.get("deck") or 0).first()
        seen = {(k.lower(), e.lower()) for k, e in Card.objects.filter(deck__owner=request.user).values_list("korean", "english")}
        created = skipped = invalid = 0
        with transaction.atomic():
            for row in reader:
                get = lambda k: (row.get(k) or "").strip()
                ko, en, rom, name = get("korean"), get("english"), get("romanization"), get("deck")
                deck = decks.get(name) if name else target
                if name and deck is None:
                    deck = decks[name] = Deck.objects.create(owner=request.user, name=name[:100])
                if not ko or not en or deck is None or max(len(ko), len(en), len(rom)) > 200:
                    invalid += 1
                    continue
                if (ko.lower(), en.lower()) in seen:
                    skipped += 1
                    continue
                seen.add((ko.lower(), en.lower()))
                Card.objects.create(deck=deck, korean=ko, english=en, romanization=rom, example=get("example"), notes=get("notes"))
                created += 1
        return Response({"created": created, "skipped": skipped, "invalid": invalid})

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
