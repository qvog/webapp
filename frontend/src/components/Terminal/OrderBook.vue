<template>
  <div
    :class="[
      'flex flex-col h-full border rounded-lg overflow-hidden relative',
      isDark ? 'bg-black border-zinc-800' : 'bg-white border-gray-300',
    ]"
  >
    <!-- Split-screen dual book: Outcome 1 (YES) | Outcome 2 (NO) — no toggles -->
    <div
      class="flex-1 grid grid-cols-1 md:grid-cols-2 min-h-0 divide-y md:divide-y-0 md:divide-x"
      :class="isDark ? 'divide-zinc-800' : 'divide-gray-300'"
    >
      <LadderColumn
        v-for="pane in panes"
        :key="pane.team"
        :ref="(el) => setColumnRef(pane.team, el)"
        :is-dark="isDark"
        :title="pane.title"
        :ladder="pane.ladder"
        :token-id="pane.tokenId"
        :imbalance-percent="pane.imbalance"
        :max-bid-size="pane.maxBid"
        :max-ask-size="pane.maxAsk"
        :accent="pane.accent"
        @place-order="(side, price) => $emit('placeOrder', side, price, pane.team)"
      />
    </div>
    <!-- Spread recenter: Spacebar hotkey only (scrollToSpread exposed to parent) -->
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import LadderColumn from './OrderBookLadderColumn.vue'

const props = defineProps({
  isDark: Boolean,
  team1Name: String,
  team2Name: String,
  ladderYes: Array,
  ladderNo: Array,
  tokenIdYes: String,
  tokenIdNo: String,
  imbalanceYes: { type: Number, default: 50 },
  imbalanceNo: { type: Number, default: 50 },
  maxBidSizeYes: { type: Number, default: 0 },
  maxAskSizeYes: { type: Number, default: 0 },
  maxBidSizeNo: { type: Number, default: 0 },
  maxAskSizeNo: { type: Number, default: 0 },
})

defineEmits(['placeOrder'])

const columnRefs = ref({ 1: null, 2: null })

function setColumnRef(team, el) {
  columnRefs.value[team] = el
}

const panes = computed(() => [
  {
    team: 1,
    title: props.team1Name || 'YES',
    ladder: props.ladderYes,
    tokenId: props.tokenIdYes,
    imbalance: props.imbalanceYes,
    maxBid: props.maxBidSizeYes,
    maxAsk: props.maxAskSizeYes,
    accent: 'cyan',
  },
  {
    team: 2,
    title: props.team2Name || 'NO',
    ladder: props.ladderNo,
    tokenId: props.tokenIdNo,
    imbalance: props.imbalanceNo,
    maxBid: props.maxBidSizeNo,
    maxAsk: props.maxAskSizeNo,
    accent: 'indigo',
  },
])

/** Spacebar / parent: recenter both columns on their spreads */
const scrollToSpread = () => {
  columnRefs.value[1]?.scrollToSpread?.()
  columnRefs.value[2]?.scrollToSpread?.()
}

defineExpose({ scrollToSpread })
</script>
