<script setup>
import { ref, computed, watch, onMounted, nextTick } from "vue";
import { api } from "./api.js";

const props = defineProps({ deck: Object }); // a deck, the "All cards" view, or a playlist
const emit = defineEmits(["close"]);

const tilt = ref({ x: 0, y: 0 });
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
function onMove(e) {
  if (calm) return;
  const r = e.currentTarget.getBoundingClientRect();
  tilt.value = { x: -((e.clientY - r.top) / r.height - 0.5) * 12, y: ((e.clientX - r.left) / r.width - 0.5) * 16 };
}
const onLeave = () => { tilt.value = { x: 0, y: 0 }; };

// "from-to": what shows on the front, then what shows after flipping.
const MODES = { "ko-en": "Korean → English", "en-ko": "English → Korean", "pic-ko": "Picture → Korean", "pic-en": "Picture → English" };
const cards = ref([]), i = ref(0), flipped = ref(false), mode = ref("ko-en");
const typed = ref(false), guess = ref(""), result = ref(null), guessEl = ref(null);

const endpoint = props.deck.all ? "/cards/study/" : props.deck.playlist ? `/playlists/${props.deck.id}/study/` : `/decks/${props.deck.id}/study/`;
onMounted(async () => { cards.value = await api(endpoint); });

const reset = () => { flipped.value = false; result.value = null; guess.value = ""; };
const focusGuess = async () => { await nextTick(); guessEl.value?.focus(); };
watch(mode, () => { i.value = 0; reset(); });
watch(typed, () => { reset(); focusGuess(); });

const canType = computed(() => mode.value.endsWith("-en")); // typing is for English answers
const isTyping = computed(() => typed.value && canType.value);
const usable = computed(() => (mode.value.startsWith("pic") ? cards.value.filter((c) => c.image) : cards.value));
const card = computed(() => usable.value[i.value]);
const layers = computed(() => Math.max(0, Math.min(2, usable.value.length - i.value - 1)));
const view = (key) => (key === "pic" ? { img: card.value.image } : { text: key === "ko" ? card.value.korean : card.value.english, ko: key === "ko" });
const front = computed(() => card.value && view(mode.value.split("-")[0]));
const back = computed(() => card.value && view(mode.value.split("-")[1]));

// Ignore case, punctuation and (bracketed notes); accept the whole answer or any one meaning in it.
const norm = (s) => s.normalize("NFKC").toLowerCase().replace(/\(.*?\)/g, " ").replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
const accepted = (c) => [c.english, ...c.english.split(/[;,/]/)].map(norm).filter(Boolean);
function check(giveUp = false) {
  if (result.value) return;
  const g = norm(guess.value);
  result.value = { ok: !giveUp && g !== "" && accepted(card.value).includes(g) };
  flipped.value = true;
}

async function mark(correct) {
  await api(`/cards/${card.value.id}/review/`, { method: "POST", body: { correct } });
  reset();
  i.value += 1;
  if (isTyping.value) focusGuess();
}
</script>

<template>
  <div class="row" style="justify-content:space-between">
    <button class="ghost" @click="emit('close')">Back</button>
    <div class="row">
      <label class="row" :title="canType ? '' : 'Typing is available when the answer is English'">
        <input v-model="typed" type="checkbox" :disabled="!canType" style="width:auto" /> Type the answer
      </label>
      <select v-model="mode" style="width:auto" aria-label="Card style">
        <option v-for="(label, key) in MODES" :key="key" :value="key">{{ label }}</option>
      </select>
    </div>
  </div>

  <p v-if="!usable.length" class="muted">
    {{ mode.startsWith("pic") ? "No due cards with pictures here. Add a picture to a card, or switch card style." : "Nothing due here. Come back later, or add more cards." }}
  </p>
  <p v-else-if="!card" class="muted">Session complete. You reviewed {{ usable.length }} cards.</p>
  <template v-else>
    <p class="muted">{{ deck.name }}: card {{ i + 1 }} of {{ usable.length }}</p>
    <div class="scene" :data-layers="layers">
      <div class="tilt" :style="{ transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }" @pointermove="onMove" @pointerleave="onLeave">
        <div
          class="card" :class="{ flipped }"
          :role="isTyping ? undefined : 'button'" :tabindex="isTyping ? undefined : 0"
          @click="!isTyping && (flipped = !flipped)" @keydown.enter.space.prevent="!isTyping && (flipped = !flipped)"
        >
          <div class="face front"><img v-if="front.img" :src="front.img" alt="" /><span v-else :class="{ ko: front.ko }">{{ front.text }}</span></div>
          <div class="face back">
            <img v-if="back.img" :src="back.img" alt="" /><span v-else :class="{ ko: back.ko }">{{ back.text }}</span>
            <small v-if="card.romanization">{{ card.romanization }}</small>
            <small v-if="card.example">{{ card.example }}</small>
          </div>
        </div>
      </div>
    </div>

    <template v-if="isTyping">
      <form v-if="!result" class="row" @submit.prevent="check()">
        <input ref="guessEl" v-model="guess" style="flex:1" placeholder="Type the English" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Your answer" />
        <button>Check</button>
        <button type="button" class="ghost" @click="check(true)">Show answer</button>
      </form>
      <template v-else>
        <p :class="result.ok ? 'ok' : 'err'" role="status">{{ result.ok ? "Correct!" : guess.trim() ? `Not quite. You typed "${guess.trim()}".` : "Here is the answer." }}</p>
        <div class="row">
          <button @click="mark(result.ok)">Next</button>
          <button v-if="!result.ok" class="ghost" @click="mark(true)">Count it as correct</button>
        </div>
      </template>
    </template>
    <template v-else>
      <div v-if="flipped" class="row">
        <button class="miss" @click="mark(false)">Still learning</button>
        <button class="hit" @click="mark(true)">Knew it</button>
      </div>
      <p v-else class="muted">Select the card to flip it.</p>
    </template>
  </template>
</template>
