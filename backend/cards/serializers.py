from rest_framework import serializers

from .models import Card, Deck, Playlist


class DeckSerializer(serializers.ModelSerializer):
    card_count = serializers.IntegerField(source="cards.count", read_only=True)

    class Meta:
        model = Deck
        fields = ["id", "name", "card_count"]


class CardSerializer(serializers.ModelSerializer):
    deck_name = serializers.CharField(source="deck.name", read_only=True)

    class Meta:
        model = Card
        fields = ["id", "deck", "deck_name", "korean", "english", "romanization", "example", "notes", "image", "box", "due"]
        read_only_fields = ["box", "due"]

    def validate_deck(self, deck):
        if deck.owner != self.context["request"].user:
            raise serializers.ValidationError("That deck belongs to another user.")
        return deck

    def validate(self, attrs):
        """A card (same Korean + English) can exist only once per user, across all decks."""
        get = lambda k: attrs.get(k, getattr(self.instance, k, "")).strip()
        attrs["korean"], attrs["english"] = get("korean"), get("english")
        same = Card.objects.filter(
            deck__owner=self.context["request"].user,
            korean__iexact=attrs["korean"], english__iexact=attrs["english"],
        )
        if self.instance:
            same = same.exclude(pk=self.instance.pk)
        match = same.select_related("deck").first()
        if match:
            raise serializers.ValidationError(f'"{attrs["korean"]}" is already in your cards (deck: {match.deck.name}).')
        return attrs


class PlaylistSerializer(serializers.ModelSerializer):
    decks = serializers.PrimaryKeyRelatedField(many=True, queryset=Deck.objects.all())
    deck_names = serializers.SerializerMethodField()
    card_count = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ["id", "name", "decks", "deck_names", "card_count"]

    def validate_decks(self, decks):
        if len(set(decks)) < 2:
            raise serializers.ValidationError("Choose at least two decks.")
        if any(d.owner != self.context["request"].user for d in decks):
            raise serializers.ValidationError("One of those decks belongs to another user.")
        return decks

    def get_deck_names(self, obj):
        return [d.name for d in obj.decks.all()]

    def get_card_count(self, obj):
        return Card.objects.filter(deck__in=obj.decks.all()).count()
