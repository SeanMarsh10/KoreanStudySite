<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "./api.js";
import Study from "./Study.vue";

const authed = ref(!!localStorage.getItem("token"));
const creds = ref({ username: "", password: "" }), registering = ref(false), error = ref("");
const decks = ref([]), deck = ref(null), cards = ref([]), studying = ref(false);
const ALL = { id: null, name: "All cards", all: true }; // virtual deck: a view of every card, never a copy
const total = computed(() => decks.value.reduce((n, d) => n + d.card_count, 0));
const newDeck = ref(""), search = ref("");
const blank = () => ({ korean: "", english: "", romanization: "", example: "", notes: "", image: null });
const form = ref(blank()), fileInput = ref(null);

const guard = async (fn) => { error.value = ""; try { await fn(); } catch (e) { error.value = e.message; } };

const submitAuth = () => guard(async () => {
  const { token } = await api(registering.value ? "/register/" : "/login/", { method: "POST", body: creds.value });
  localStorage.setItem("token", token); authed.value = true; await loadDecks();
});
const logout = () => { localStorage.removeItem("token"); authed.value = false; deck.value = null; };
const loadDecks = () => guard(async () => { decks.value = await api("/decks/"); });
const addDeck = () => guard(async () => { await api("/decks/", { method: "POST", body: { name: newDeck.value } }); newDeck.value = ""; await loadDecks(); });
const delDeck = (d) => confirm(`Delete "${d.name}" and its cards?`) && guard(async () => { await api(`/decks/${d.id}/`, { method: "DELETE" }); await loadDecks(); });
const open = (d) => { deck.value = d; return loadCards(); };
const loadCards = () => guard(async () => { cards.value = await api(`/cards/?${deck.value.id ? `deck=${deck.value.id}&` : ""}q=${encodeURIComponent(search.value)}`); });
const addCard = () => guard(async () => {
  const fd = new FormData(); fd.append("deck", deck.value.id);
  for (const [k, v] of Object.entries(form.value)) if (v) fd.append(k, v);
  await api("/cards/", { method: "POST", form: fd });
  form.value = blank(); if (fileInput.value) fileInput.value.value = ""; await loadCards();
});
const delCard = (c) => guard(async () => { await api(`/cards/${c.id}/`, { method: "DELETE" }); await loadCards(); });
onMounted(() => authed.value && loadDecks());
</script>

<template>
  <main>
    <header class="bar">
      <h1>Hangul Cards</h1>
      <button v-if="authed" class="ghost" @click="logout">Log out</button>
    </header>
    <p v-if="error" class="err" role="alert">{{ error }}</p>

    <form v-if="!authed" class="grid" @submit.prevent="submitAuth">
      <input v-model="creds.username" placeholder="Username" autocomplete="username" required />
      <input v-model="creds.password" type="password" placeholder="Password" autocomplete="current-password" required />
      <button class="full">{{ registering ? "Create account" : "Log in" }}</button>
      <button type="button" class="ghost full" @click="registering = !registering">{{ registering ? "I already have an account" : "I need an account" }}</button>
    </form>

    <Study v-else-if="studying" :deck="deck" @close="studying = false; loadCards()" />

    <template v-else-if="deck">
      <div class="row" style="justify-content:space-between">
        <button class="ghost" @click="deck = null; loadDecks()">All decks</button>
        <button @click="studying = true">Study {{ deck.name }}</button>
      </div>
      <h2 v-if="!deck.all">Add a card</h2>
      <form v-if="!deck.all" class="grid" @submit.prevent="addCard">
        <input v-model="form.korean" class="ko" placeholder="Korean" required />
        <input v-model="form.english" placeholder="English" required />
        <input v-model="form.romanization" placeholder="Romanization (optional)" />
        <input ref="fileInput" type="file" accept="image/*" @change="form.image = $event.target.files[0]" aria-label="Picture (optional)" />
        <textarea v-model="form.example" class="full" rows="2" placeholder="Example sentence (optional)"></textarea>
        <textarea v-model="form.notes" class="full" rows="2" placeholder="Notes (optional)"></textarea>
        <button class="full">Add card</button>
      </form>
      <h2>Cards in {{ deck.name }}</h2>
      <input v-model="search" placeholder="Search cards" @input="loadCards" aria-label="Search cards" />
      <ul class="list">
        <li v-for="c in cards" :key="c.id">
          <span class="row"><img v-if="c.image" :src="c.image" class="thumb" alt="" /><span><strong class="ko">{{ c.korean }}</strong> <span class="muted">{{ c.english }}</span> <em v-if="deck.all" class="muted">in {{ c.deck_name }}</em></span></span>
          <button class="ghost" @click="delCard(c)">Delete</button>
        </li>
      </ul>
      <p v-if="!cards.length" class="muted">No cards yet. Add your first one above.</p>
    </template>

    <template v-else>
      <form class="row" @submit.prevent="addDeck">
        <input v-model="newDeck" placeholder="New deck name, e.g. Food" style="flex:1" required />
        <button>Create deck</button>
      </form>
      <div class="decks">
        <article v-if="decks.length" class="deck deck-all">
          <a href="#" class="deck-link" @click.prevent="open(ALL)"><strong>All cards</strong><span>{{ total }} {{ total === 1 ? "card" : "cards" }}</span></a>
        </article>
        <article v-for="d in decks" :key="d.id" class="deck">
          <a href="#" class="deck-link" @click.prevent="open(d)"><strong>{{ d.name }}</strong><span>{{ d.card_count }} {{ d.card_count === 1 ? "card" : "cards" }}</span></a>
          <button class="ghost deck-del" :aria-label="`Delete ${d.name}`" @click="delDeck(d)">Delete</button>
        </article>
      </div>
      <p v-if="!decks.length" class="muted">No decks yet. Create one to start adding cards.</p>
    </template>
  </main>
</template>
