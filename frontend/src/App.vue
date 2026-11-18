<script setup>
import { ref, computed, onMounted } from "vue";
import { api, download } from "./api.js";
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
const loadDecks = () => guard(async () => { decks.value = await api("/decks/"); playlists.value = await api("/playlists/"); });
const addDeck = () => guard(async () => { await api("/decks/", { method: "POST", body: { name: newDeck.value } }); newDeck.value = ""; await loadDecks(); });
const delDeck = (d) => confirm(`Delete "${d.name}" and its cards?`) && guard(async () => { await api(`/decks/${d.id}/`, { method: "DELETE" }); await loadDecks(); });
const open = (d) => { deck.value = d; notice.value = ""; resetForm(); return loadCards(); };
const closeDeck = () => { deck.value = null; notice.value = ""; resetForm(); loadDecks(); };
const loadCards = () => guard(async () => { cards.value = await api(`/cards/?${deck.value.id ? `deck=${deck.value.id}&` : ""}q=${encodeURIComponent(search.value)}`); });
const editing = ref(null), notice = ref(""), csvInput = ref(null);
const resetForm = () => { form.value = blank(); editing.value = null; if (fileInput.value) fileInput.value.value = ""; };
const saveCard = () => guard(async () => {
  const fd = new FormData();
  if (!editing.value) fd.append("deck", deck.value.id);
  for (const [k, v] of Object.entries(form.value)) {
    if (k === "image") { if (v) fd.append(k, v); }          // no file chosen: keep the current picture
    else if (editing.value || v) fd.append(k, v);            // when editing, send empty text too so it can be cleared
  }
  await api(editing.value ? `/cards/${editing.value.id}/` : "/cards/", { method: editing.value ? "PATCH" : "POST", form: fd });
  resetForm(); await loadCards();
});
const startEdit = (c) => {
  editing.value = c;
  form.value = { korean: c.korean, english: c.english, romanization: c.romanization, example: c.example, notes: c.notes, image: null };
  if (fileInput.value) fileInput.value.value = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
};
const exportCsv = () => guard(() => download(deck.value.id ? `/cards/export/?deck=${deck.value.id}` : "/cards/export/", `${deck.value.name}.csv`));
const importCsv = (e) => guard(async () => {
  const input = e.target, file = input.files[0];
  if (!file) return;
  const fd = new FormData(); fd.append("file", file); if (deck.value.id) fd.append("deck", deck.value.id);
  try {
    const r = await api("/cards/import/", { method: "POST", form: fd });
    const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
    notice.value = [`Imported ${plural(r.created, "card")}.`, r.skipped && `Skipped ${plural(r.skipped, "duplicate")}.`, r.invalid && `${plural(r.invalid, "row")} had no Korean, English or deck, or was too long.`].filter(Boolean).join(" ");
    await loadCards();
  } finally { input.value = ""; }
});
const delCard = (c) => guard(async () => { await api(`/cards/${c.id}/`, { method: "DELETE" }); await loadCards(); });
const playlists = ref([]), playlist = ref(null), making = ref(false), plName = ref(""), plDecks = ref([]);
const addPlaylist = () => guard(async () => {
  await api("/playlists/", { method: "POST", body: { name: plName.value, decks: plDecks.value } });
  plName.value = ""; plDecks.value = []; making.value = false; await loadDecks();
});
const delPlaylist = (p) => confirm(`Delete the playlist "${p.name}"? Its decks and cards stay.`) && guard(async () => { await api(`/playlists/${p.id}/`, { method: "DELETE" }); await loadDecks(); });
const studyPlaylist = (p) => { playlist.value = { ...p, playlist: true }; studying.value = true; };
const closeStudy = () => { studying.value = false; playlist.value = null; if (deck.value) loadCards(); };
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

    <Study v-else-if="studying" :deck="playlist || deck" @close="closeStudy" />

    <template v-else-if="deck">
      <div class="row" style="justify-content:space-between">
        <button class="ghost" @click="closeDeck">All decks</button>
        <button @click="studying = true">Study {{ deck.name }}</button>
      </div>
      <div class="row" style="margin-top:12px">
        <button class="ghost" @click="exportCsv">Export CSV</button>
        <button class="ghost" @click="csvInput.click()">Import CSV</button>
        <input ref="csvInput" type="file" accept=".csv,text/csv" hidden @change="importCsv" />
      </div>
      <p v-if="notice" class="muted" role="status">{{ notice }}</p>
      <h2 v-if="!deck.all || editing">{{ editing ? "Edit card" : "Add a card" }}</h2>
      <form v-if="!deck.all || editing" class="grid" @submit.prevent="saveCard">
        <input v-model="form.korean" class="ko" placeholder="Korean" required />
        <input v-model="form.english" placeholder="English" required />
        <input v-model="form.romanization" placeholder="Romanization (optional)" />
        <input ref="fileInput" type="file" accept="image/*" @change="form.image = $event.target.files[0]" aria-label="Picture (optional)" />
        <p v-if="editing && editing.image" class="muted full">Choose a new picture to replace the current one, or leave it empty to keep it.</p>
        <textarea v-model="form.example" class="full" rows="2" placeholder="Example sentence (optional)"></textarea>
        <textarea v-model="form.notes" class="full" rows="2" placeholder="Notes (optional)"></textarea>
        <button class="full">{{ editing ? "Save changes" : "Add card" }}</button>
        <button v-if="editing" type="button" class="ghost full" @click="resetForm">Cancel</button>
      </form>
      <h2>Cards in {{ deck.name }}</h2>
      <input v-model="search" placeholder="Search cards" @input="loadCards" aria-label="Search cards" />
      <ul class="list">
        <li v-for="c in cards" :key="c.id">
          <span class="row"><img v-if="c.image" :src="c.image" class="thumb" alt="" /><span><strong class="ko">{{ c.korean }}</strong> <span class="muted">{{ c.english }}</span> <em v-if="deck.all" class="muted">in {{ c.deck_name }}</em></span></span>
          <span class="row"><button class="ghost" @click="startEdit(c)">Edit</button><button class="ghost" @click="delCard(c)">Delete</button></span>
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

      <template v-if="decks.length > 1 || playlists.length">
        <div class="row" style="justify-content:space-between; margin-top:32px">
          <h2 style="margin:0">Playlists</h2>
          <button v-if="decks.length > 1" class="ghost" @click="making = !making">{{ making ? "Cancel" : "New playlist" }}</button>
        </div>
        <form v-if="making" class="grid" style="margin-top:12px" @submit.prevent="addPlaylist">
          <input v-model="plName" class="full" placeholder="Playlist name, e.g. Week 3 review" required />
          <label v-for="d in decks" :key="d.id" class="row"><input v-model="plDecks" type="checkbox" :value="d.id" style="width:auto" /> {{ d.name }} <span class="muted">{{ d.card_count }}</span></label>
          <button class="full" :disabled="plDecks.length < 2">Create playlist</button>
          <p v-if="plDecks.length < 2" class="muted full">Choose at least two decks.</p>
        </form>
        <div class="decks">
          <article v-for="p in playlists" :key="p.id" class="deck playlist">
            <a href="#" class="deck-link" @click.prevent="studyPlaylist(p)"><strong>{{ p.name }}</strong><span>{{ p.deck_names.join(", ") }} ({{ p.card_count }} cards)</span></a>
            <button class="ghost deck-del" :aria-label="`Delete playlist ${p.name}`" @click="delPlaylist(p)">Delete</button>
          </article>
        </div>
      </template>
    </template>
  </main>
</template>
