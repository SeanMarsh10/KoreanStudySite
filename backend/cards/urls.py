from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("decks", views.DeckViewSet, basename="deck")
router.register("cards", views.CardViewSet, basename="card")
router.register("playlists", views.PlaylistViewSet, basename="playlist")

urlpatterns = [
    path("register/", views.register),
    path("login/", obtain_auth_token),
    path("", include(router.urls)),
]
