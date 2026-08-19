<template>
  <div :class="['flex flex-col h-full border rounded-lg overflow-hidden relative', isDark ? 'bg-black border-zinc-800' : 'bg-white border-gray-300']">
    
    <div :class="['flex p-1 shrink-0 border-b', isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-gray-50 border-gray-200']">
      <button 
        @click="$emit('update:activeTeam', 1)" 
        :class="['flex-1 py-2 text-sm font-bold transition-colors rounded-l', activeTeam === 1 ? (isDark ? 'bg-[#00e5ff] text-black' : 'bg-[#00e5ff] text-white') : 'text-gray-500 hover:text-gray-400']"
      >
        {{ team1Name }}
      </button>
      <button 
        @click="$emit('update:activeTeam', 2)" 
        :class="['flex-1 py-2 text-sm font-bold transition-colors rounded-r', activeTeam === 2 ? (isDark ? 'bg-[#00e5ff] text-black' : 'bg-[#00e5ff] text-white') : 'text-gray-500 hover:text-gray-400']"
      >
        {{ team2Name }}
      </button>
    </div>

    <!-- 4.1 Imbalance bar: green (bids) | red (asks) -->
    <div
      class="shrink-0 h-2 w-full flex overflow-hidden border-b"
      :class="isDark ? 'border-zinc-800 bg-[#050505]' : 'border-gray-200 bg-gray-100'"
      :title="`Imbalance ${imbalancePercent.toFixed(1)}% bids`"
    >
      <div
        class="h-full bg-emerald-500 transition-[width] duration-150 ease-out"
        :style="{ width: imbalancePercent + '%' }"
      />
      <div
        class="h-full bg-red-500 transition-[width] duration-150 ease-out"
        :style="{ width: (100 - imbalancePercent) + '%' }"
      />
    </div>
    <div
      class="flex justify-between px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider shrink-0 border-b"
      :class="isDark ? 'bg-[#0a0a0a] border-zinc-800 text-zinc-500' : 'bg-gray-50 border-gray-200 text-gray-400'"
    >
      <span class="text-emerald-500">BID {{ imbalancePercent.toFixed(0) }}%</span>
      <span class="text-zinc-600">IMBALANCE</span>
      <span class="text-red-500">ASK {{ (100 - imbalancePercent).toFixed(0) }}%</span>
    </div>

    <div :class="['flex gap-2 p-2 border-b shrink-0', isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-200']">
      <button 
        @click="$emit('placeOrder', 'SELL', bestBidCents)"
        class="flex-1 py-2 rounded font-bold text-sm border transition-colors flex flex-col items-center justify-center opacity-80 hover:opacity-100"
        :class="isDark ? 'bg-red-950/20 border-red-900 text-red-500' : 'bg-red-50 border-red-200 text-red-500'"
      >
        <span class="text-[10px] tracking-wider uppercase">SELL (Best Bid)</span>
        <span class="text-lg">{{ bestBidCents > 0 ? bestBidCents + '¢' : '--' }}</span>
      </button>

      <button 
        @click="$emit('placeOrder', 'BUY', bestAskCents)"
        class="flex-1 py-2 rounded font-bold text-sm border shadow-[0_0_15px_rgba(34,197,94,0.15)] transition-all flex flex-col items-center justify-center"
        :class="isDark ? 'bg-green-500/10 border-green-500 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_20px_rgba(34,197,94,0.3)]' : 'bg-green-50 border-green-400 text-green-600 hover:bg-green-100'"
      >
        <span class="text-[10px] tracking-wider uppercase">BUY (Best Ask)</span>
        <span class="text-lg">{{ bestAskCents > 0 ? bestAskCents + '¢' : '--' }}</span>
      </button>
    </div>

    <div :class="['grid grid-cols-3 text-[10px] font-bold text-gray-500 py-1 sticky top-0 z-20 shrink-0 border-b', isDark ? 'bg-black border-zinc-800' : 'bg-gray-100 border-gray-300']">
      <div class="text-center">BIDS (BUY)</div>
      <div class="text-center">PRICE ¢</div>
      <div class="text-center">ASKS (SELL)</div>
    </div>
    
    <div ref="orderBookContainer" class="flex-1 overflow-y-auto custom-scrollbar relative">
      <div 
        v-for="row in activeLadder" :key="row.price" 
        :data-price="row.price"
        class="price-row grid grid-cols-3 border-b hover:bg-[#00e5ff]/10 transition-colors group cursor-crosshair h-7 relative"
        :class="rowClass(row)"
        :style="spreadRowStyle(row)"
      >
        <!-- Bid cell + heatmap -->
        <div
          @click="$emit('placeOrder', 'BUY', row.price)"
          class="relative flex items-center justify-end px-2 text-green-400 font-mono text-xs border-r"
          :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'"
          :style="bidHeatStyle(row.bidSize)"
        >
          <span v-if="row.price === bestBidCents" class="absolute left-1 text-[10px] text-green-400 animate-pulse z-10">▶</span>
          <span class="relative z-10 drop-shadow-[0_0_2px_rgba(0,0,0,0.9)]">{{ row.bidSize > 0 ? row.bidSize.toFixed(0) : '' }}</span>
        </div>
        
        <!-- Price + position marker -->
        <div :class="['flex items-center justify-center font-bold font-mono text-sm relative gap-1', getPriceColorClass(row)]">
          <span
            v-if="positionAtPrice(row.price)"
            class="absolute left-0.5 flex items-center gap-0.5 text-yellow-400 font-bold text-[9px] leading-none tracking-tight whitespace-nowrap z-10"
            :title="'Position ' + positionAtPrice(row.price)"
          >
            <span class="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 shadow-[0_0_6px_#eab308]" />
            {{ positionAtPrice(row.price) }}
          </span>
          {{ row.price }}
        </div>
        
        <!-- Ask cell + heatmap -->
        <div
          class="relative flex items-center justify-start px-2 text-red-400 font-mono text-xs border-l"
          :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'"
          :style="askHeatStyle(row.askSize)"
        >
          <span v-if="row.price === bestAskCents" class="absolute right-1 text-[10px] text-red-400 animate-pulse z-10">◀</span>
          <span class="relative z-10 drop-shadow-[0_0_2px_rgba(0,0,0,0.9)]">{{ row.askSize > 0 ? row.askSize.toFixed(0) : '' }}</span>
        </div>
      </div>
    </div>

    <button @click="scrollToSpread" class="absolute bottom-4 right-4 p-2 rounded-full shadow-lg transition-all z-30" :class="isDark ? 'bg-black border border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black' : 'bg-white border border-[#00e5ff] text-[#00b8cc] hover:bg-[#00e5ff] hover:text-white'" title="Center Spread">
      🎯
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMarketStore } from '../../store/marketStore'

const props = defineProps({
  isDark: Boolean,
  activeTeam: Number,
  team1Name: String,
  team2Name: String,
  ladderYes: Array,
  ladderNo: Array,
  currentTokenId: String,
  /** Top-3 imbalance % (bids share). Optional — falls back to local calc. */
  imbalancePercent: { type: Number, default: null },
  maxBidSize: { type: Number, default: 0 },
  maxAskSize: { type: Number, default: 0 },
})

const emit = defineEmits(['update:activeTeam', 'placeOrder'])
const orderBookContainer = ref(null)
const marketStore = useMarketStore()

const activeLadder = computed(() => props.activeTeam === 1 ? props.ladderYes : props.ladderNo)

const bestBidCents = computed(() => {
  if (!activeLadder.value) return 0
  for (let i = 0; i < 99; i++) {
    if (activeLadder.value[i].bidSize > 0) return activeLadder.value[i].price
  }
  return 0
})

const bestAskCents = computed(() => {
  if (!activeLadder.value) return 0
  for (let i = 98; i >= 0; i--) {
    if (activeLadder.value[i].askSize > 0) return activeLadder.value[i].price
  }
  return 0
})

/** Local fallback metrics if parent hasn't wired imbalance props yet */
const localMetrics = computed(() => {
  const ladder = activeLadder.value
  if (!ladder) {
    return { imbalancePercent: 50, maxBidSize: 0, maxAskSize: 0 }
  }
  let maxBid = 0
  let maxAsk = 0
  const topBids = []
  const topAsks = []
  for (let i = 0; i < 99; i++) {
    const bid = ladder[i].bidSize || 0
    const ask = ladder[i].askSize || 0
    if (bid > maxBid) maxBid = bid
    if (ask > maxAsk) maxAsk = ask
  }
  for (let i = 0; i < 99 && topBids.length < 3; i++) {
    if (ladder[i].bidSize > 0) topBids.push(ladder[i].bidSize)
  }
  for (let i = 98; i >= 0 && topAsks.length < 3; i--) {
    if (ladder[i].askSize > 0) topAsks.push(ladder[i].askSize)
  }
  const sumBids = topBids.reduce((a, b) => a + b, 0)
  const sumAsks = topAsks.reduce((a, b) => a + b, 0)
  const total = sumBids + sumAsks
  return {
    imbalancePercent: total > 0 ? (sumBids / total) * 100 : 50,
    maxBidSize: maxBid,
    maxAskSize: maxAsk,
  }
})

const imbalancePercent = computed(() => {
  if (props.imbalancePercent != null && !Number.isNaN(props.imbalancePercent)) {
    return Math.max(0, Math.min(100, props.imbalancePercent))
  }
  return localMetrics.value.imbalancePercent
})

const effectiveMaxBid = computed(() =>
  props.maxBidSize > 0 ? props.maxBidSize : localMetrics.value.maxBidSize
)
const effectiveMaxAsk = computed(() =>
  props.maxAskSize > 0 ? props.maxAskSize : localMetrics.value.maxAskSize
)

/**
 * Map price-cents → last-4 of order_id for OPEN/PENDING positions on this token.
 * entry_price is matched via Math.round(price * 100).
 */
const positionsByPrice = computed(() => {
  const map = new Map()
  for (const p of marketStore.openPositions) {
    if (p.token_id !== props.currentTokenId) continue
    if (!['PENDING', 'OPEN'].includes(p.status)) continue
    if (p.entry_price == null) continue
    const cents = Math.round(Number(p.entry_price) * 100)
    const shortId = String(p.order_id || '').slice(-4)
    if (!shortId) continue
    // Prefer first position at this price for the label
    if (!map.has(cents)) map.set(cents, shortId)
  }
  return map
})

function positionAtPrice(priceCents) {
  return positionsByPrice.value.get(priceCents) || null
}

/** 4.2 Heatmap: intensity = size / max_*_size */
function bidHeatStyle(size) {
  if (!size || size <= 0) return {}
  const max = effectiveMaxBid.value || 1
  const intensity = Math.min(1, size / max)
  // Keep text readable: soft green wash, not solid fill
  const alpha = 0.08 + intensity * 0.42
  return { background: `rgba(34, 197, 94, ${alpha.toFixed(3)})` }
}

function askHeatStyle(size) {
  if (!size || size <= 0) return {}
  const max = effectiveMaxAsk.value || 1
  const intensity = Math.min(1, size / max)
  const alpha = 0.08 + intensity * 0.42
  return { background: `rgba(239, 68, 68, ${alpha.toFixed(3)})` }
}

/** 4.3 Cyan border on best bid / best ask rows (spread gap) */
function rowClass(row) {
  const classes = [props.isDark ? 'border-zinc-800/50' : 'border-gray-200']
  if (positionAtPrice(row.price)) {
    classes.push(props.isDark ? 'bg-yellow-900/10' : 'bg-yellow-50')
  }
  return classes
}

function spreadRowStyle(row) {
  const style = {}
  // Best bid: cyan bottom edge; best ask: cyan top edge → visual spread channel
  if (row.price === bestBidCents.value) {
    style.borderBottom = '1px solid #00e5ff'
  }
  if (row.price === bestAskCents.value) {
    style.borderTop = '1px solid #00e5ff'
  }
  return style
}

const getPriceColorClass = (row) => {
  if (row.price === bestBidCents.value) return 'text-green-400'
  if (row.price === bestAskCents.value) return 'text-red-400'
  return props.isDark ? 'text-gray-300' : 'text-gray-700'
}

const scrollToSpread = () => {
  if (!orderBookContainer.value) return
  const targetPrice = bestAskCents.value > 0
    ? bestAskCents.value
    : (bestBidCents.value > 0 ? bestBidCents.value : 50)
  const targetRow = orderBookContainer.value.querySelector(`[data-price="${targetPrice}"]`)
  if (targetRow) {
    const containerHeight = orderBookContainer.value.clientHeight
    const rowTop = targetRow.offsetTop
    orderBookContainer.value.scrollTo({
      top: rowTop - (containerHeight / 2),
      behavior: 'auto',
    })
  }
}

defineExpose({ scrollToSpread })
</script>
