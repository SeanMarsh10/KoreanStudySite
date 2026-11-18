<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { api } from "./api.js";

const props = defineProps({ deck: Object });
const emit = defineEmits(["close"]);

// "from-to": what shows on the front, then what shows after flipping.
const MODES = { "ko-en": "Korean → English", "en-ko": "English → Korean", "pic-ko": "Picture → Korean", "pic-en": "Picture → English" };
const tilt = ref({ x: 0, y: 0 });
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
function onMove(e) {
  if (calm) return;
  const r = e.currentTarget.getBoundingClientRect();
  tilt.value = { x: -((e.clientY - r.top) / r.height - 0.5) * 12, y: ((e.clientX - r.left) / r.width - 0.5) * 16 };
}
const onLeave = () => { tilt.value = { x: 0, y: 0 }; };
const cards = ref([]), i = ref(0), flipped = ref(false), mode = ref("ko-en"), done = ref(false);

onMounted(async () => { cards.value = await api(props.deck.all ? "/cards/study/" : `/decks/${props.deck.id}/study/`); });
watch(mode, () => { i.value = 0; flipped.value = false; });

const usable = computed(() => (mode.value.startsWith("pic") ? cards.value.filter((c) => c.image) : cards.value));
const card = computed(() => usable.value[i.value]);
const layers = computed(() => Math.max(0, Math.min(2, usable.value.length - i.value - 1)));
const view = (key) => (key === "pic" ? { img: card.value.image } : { text: key === "ko" ? card.value.korean : card.value.english, ko: key === "ko" });
const front = computed(() => card.value && view(mode.value.split("-")[0]));
const back = computed(() => card.value && view(mode.value.split("-")[1]));

async function mark(correct) {
  await api(`/cards/${card.value.id}/review/`, { method: "POST", body: { correct } });
  flipped.value = false;
  i.value += 1;
}
</script>

<template>
  <div class="row" style="justify-content:space-between">
    <button class="ghost" @click="emit('close')">Back to decks</button>
    <select v-model="mode" style="width:auto" aria-label="Card style">
      <option v-for="(label, key) in MODES" :key="key" :value="key">{{ label }}</option>
    </select>
  </div>

  <p v-if="!usable.length" class="muted">
    {{ mode.startsWith("pic") ? "No due cards with pictures in this deck. Add a picture to a card, or switch card style." : "Nothing due in this deck. Come back later, or add more cards." }}
  </p>
  <p v-else-if="!card" class="muted">Session complete. You reviewed {{ usable.length }} cards.</p>
  <template v-else>
    <p class="muted">Card {{ i + 1 }} of {{ usable.length }}</p>
    <div class="scene" :data-layers="layers">
      <div class="tilt" :style="{ transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }" @pointermove="onMove" @pointerleave="onLeave">
      <div class="card" :class="{ flipped }" role="button" tabindex="0" @click="flipped = !flipped" @keydown.enter.space.prevent="flipped = !flipped">
        <div class="face front"><img v-if="front.img" :src="front.img" alt="" /><span v-else :class="{ ko: front.ko }">{{ front.text }}</span></div>
        <div class="face back">
          <img v-if="back.img" :src="back.img" alt="" /><span v-else :class="{ ko: back.ko }">{{ back.text }}</span>
          <small v-if="card.romanization">{{ card.romanization }}</small>
          <small v-if="card.example">{{ card.example }}</small>
        </div>
      </div>
      </div>
    </div>
    <div class="row" v-if="flipped">
      <button class="miss" @click="mark(false)">Still learning</button>
      <button class="hit" @click="mark(true)">Knew it</button>
    </div>
    <p v-else class="muted">Select the card to flip it.</p>
  </template>
</template>
