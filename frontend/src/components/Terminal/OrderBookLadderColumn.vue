<template>
  <div class="flex flex-col min-h-0 min-w-0 h-full">
    <!-- Outcome name anchored at top of column -->
    <div
      class="shrink-0 px-2 py-1.5 text-center text-xs font-bold tracking-wider uppercase border-b truncate"
      :class="headerClass"
      :title="title"
    >
      {{ title }}
    </div>

    <!-- Imbalance bar -->
    <div
      class="shrink-0 h-1.5 w-full flex overflow-hidden border-b"
      :class="isDark ? 'border-zinc-800 bg-[#050505]' : 'border-gray-200 bg-gray-100'"
      :title="`Imbalance ${imbalanceClamped.toFixed(1)}% bids`"
    >
      <div
        class="h-full bg-emerald-500 transition-[width] duration-150 ease-out"
        :style="{ width: imbalanceClamped + '%' }"
      />
      <div
        class="h-full bg-red-500 transition-[width] duration-150 ease-out"
        :style="{ width: 100 - imbalanceClamped + '%' }"
      />
    </div>
    <div
      class="flex justify-between px-2 py-0.5 text-[8px] font-mono font-bold tracking-wider shrink-0 border-b"
      :class="isDark ? 'bg-[#0a0a0a] border-zinc-800 text-zinc-500' : 'bg-gray-50 border-gray-200 text-gray-400'"
    >
      <span class="text-emerald-500">BID {{ imbalanceClamped.toFixed(0) }}%</span>
      <span class="text-zinc-600">IMB</span>
      <span class="text-red-500">ASK {{ (100 - imbalanceClamped).toFixed(0) }}%</span>
    </div>

    <div
      class="grid grid-cols-3 text-[9px] font-bold text-gray-500 py-1 sticky top-0 z-20 shrink-0 border-b"
      :class="isDark ? 'bg-black border-zinc-800' : 'bg-gray-100 border-gray-300'"
    >
      <div class="text-center">BIDS</div>
      <div class="text-center">¢</div>
      <div class="text-center">ASKS</div>
    </div>

    <div ref="containerRef" class="flex-1 overflow-y-auto custom-scrollbar relative min-h-0">
      <div
        v-for="row in ladder"
        :key="row.price"
        :data-price="row.price"
        class="price-row grid grid-cols-3 border-b hover:bg-[#00e5ff]/10 transition-colors group cursor-crosshair h-6 relative"
        :class="rowClass(row)"
        :style="spreadRowStyle(row)"
      >
        <div
          @click="$emit('placeOrder', 'BUY', row.price)"
          class="relative flex items-center justify-end px-1.5 text-green-400 font-mono text-[11px] border-r"
          :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'"
          :style="bidHeatStyle(row.bidSize)"
        >
          <span
            v-if="row.price === bestBidCents"
            class="absolute left-0.5 text-[9px] text-green-400 animate-pulse z-10"
          >▶</span>
          <span class="relative z-10 drop-shadow-[0_0_2px_rgba(0,0,0,0.9)]">
            {{ row.bidSize > 0 ? row.bidSize.toFixed(0) : '' }}
          </span>
        </div>

        <div
          :class="[
            'flex items-center justify-center font-bold font-mono text-xs relative gap-0.5',
            getPriceColorClass(row),
          ]"
        >
          <span
            v-if="positionAtPrice(row.price)"
            class="absolute left-0 flex items-center gap-0.5 text-yellow-400 font-bold text-[8px] leading-none tracking-tight whitespace-nowrap z-10"
            :title="'Position ' + positionAtPrice(row.price)"
          >
            <span class="inline-block w-1 h-1 rounded-full bg-yellow-400 shadow-[0_0_6px_#eab308]" />
            {{ positionAtPrice(row.price) }}
          </span>
          {{ row.price }}
        </div>

        <div
          class="relative flex items-center justify-start px-1.5 text-red-400 font-mono text-[11px] border-l"
          :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'"
          :style="askHeatStyle(row.askSize)"
        >
          <span
            v-if="row.price === bestAskCents"
            class="absolute right-0.5 text-[9px] text-red-400 animate-pulse z-10"
          >◀</span>
          <span class="relative z-10 drop-shadow-[0_0_2px_rgba(0,0,0,0.9)]">
            {{ row.askSize > 0 ? row.askSize.toFixed(0) : '' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useMarketStore } from '../../store/marketStore'

const props = defineProps({
  isDark: Boolean,
  title: String,
  ladder: Array,
  tokenId: String,
  imbalancePercent: { type: Number, default: 50 },
  maxBidSize: { type: Number, default: 0 },
  maxAskSize: { type: Number, default: 0 },
  accent: { type: String, default: 'cyan' },
})

defineEmits(['placeOrder'])

const containerRef = ref(null)
const marketStore = useMarketStore()

const imbalanceClamped = computed(() => {
  const v = Number(props.imbalancePercent)
  if (!Number.isFinite(v)) return 50
  return Math.max(0, Math.min(100, v))
})

const headerClass = computed(() => {
  if (props.accent === 'indigo') {
    return props.isDark
      ? 'bg-indigo-950/40 border-zinc-800 text-indigo-300'
      : 'bg-indigo-50 border-gray-200 text-indigo-700'
  }
  return props.isDark
    ? 'bg-cyan-950/40 border-zinc-800 text-[#00e5ff]'
    : 'bg-cyan-50 border-gray-200 text-cyan-700'
})

const bestBidCents = computed(() => {
  const ladder = props.ladder
  if (!ladder) return 0
  for (let i = 0; i < 99; i++) {
    if (ladder[i]?.bidSize > 0) return ladder[i].price
  }
  return 0
})

const bestAskCents = computed(() => {
  const ladder = props.ladder
  if (!ladder) return 0
  for (let i = 98; i >= 0; i--) {
    if (ladder[i]?.askSize > 0) return ladder[i].price
  }
  return 0
})

const localMax = computed(() => {
  const ladder = props.ladder
  let maxBid = 0
  let maxAsk = 0
  if (!ladder) return { maxBid, maxAsk }
  for (let i = 0; i < 99; i++) {
    const bid = ladder[i]?.bidSize || 0
    const ask = ladder[i]?.askSize || 0
    if (bid > maxBid) maxBid = bid
    if (ask > maxAsk) maxAsk = ask
  }
  return { maxBid, maxAsk }
})

const effectiveMaxBid = computed(() =>
  props.maxBidSize > 0 ? props.maxBidSize : localMax.value.maxBid
)
const effectiveMaxAsk = computed(() =>
  props.maxAskSize > 0 ? props.maxAskSize : localMax.value.maxAsk
)

const positionsByPrice = computed(() => {
  const map = new Map()
  const tid = props.tokenId != null ? String(props.tokenId) : ''
  if (!tid) return map
  for (const p of marketStore.openPositions) {
    if (String(p.token_id) !== tid) continue
    if (!['PENDING', 'OPEN'].includes(p.status)) continue
    if (p.entry_price == null) continue
    const cents = Math.round(Number(p.entry_price) * 100)
    const shortId = String(p.order_id || '').slice(-4)
    if (!shortId) continue
    if (!map.has(cents)) map.set(cents, shortId)
  }
  return map
})

function positionAtPrice(priceCents) {
  return positionsByPrice.value.get(priceCents) || null
}

function bidHeatStyle(size) {
  if (!size || size <= 0) return {}
  const max = effectiveMaxBid.value || 1
  const intensity = Math.min(1, size / max)
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

function rowClass(row) {
  const classes = [props.isDark ? 'border-zinc-800/50' : 'border-gray-200']
  if (positionAtPrice(row.price)) {
    classes.push(props.isDark ? 'bg-yellow-900/10' : 'bg-yellow-50')
  }
  return classes
}

function spreadRowStyle(row) {
  const style = {}
  if (row.price === bestBidCents.value) style.borderBottom = '1px solid #00e5ff'
  if (row.price === bestAskCents.value) style.borderTop = '1px solid #00e5ff'
  return style
}

function getPriceColorClass(row) {
  if (row.price === bestBidCents.value) return 'text-green-400'
  if (row.price === bestAskCents.value) return 'text-red-400'
  return props.isDark ? 'text-gray-300' : 'text-gray-700'
}

const scrollToSpread = () => {
  if (!containerRef.value) return
  const targetPrice =
    bestAskCents.value > 0
      ? bestAskCents.value
      : bestBidCents.value > 0
        ? bestBidCents.value
        : 50
  const targetRow = containerRef.value.querySelector(`[data-price="${targetPrice}"]`)
  if (targetRow) {
    const containerHeight = containerRef.value.clientHeight
    containerRef.value.scrollTo({
      top: targetRow.offsetTop - containerHeight / 2,
      behavior: 'auto',
    })
  }
}

defineExpose({ scrollToSpread })
</script>
