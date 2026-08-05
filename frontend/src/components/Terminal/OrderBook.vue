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

    <!-- Microstructure strip: imbalance + mid + velocity -->
    <div :class="['px-2 pt-2 pb-1 shrink-0 border-b space-y-1.5', isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-200']">
      <div class="flex items-center justify-between text-[9px] font-mono uppercase tracking-wider text-zinc-500">
        <span>Imbalance {{ imbalancePct }}</span>
        <span class="text-[#00e5ff]">MID {{ midPriceCents > 0 ? midPriceCents + '¢' : '--' }}</span>
        <span>Vel {{ velocity }}/s</span>
      </div>
      <!-- Imbalance bar: green = bid-heavy, red = ask-heavy -->
      <div class="h-1.5 w-full rounded-full overflow-hidden bg-zinc-800/80 relative">
        <div class="absolute inset-y-0 left-0 right-1/2 flex justify-end">
          <div
            class="h-full bg-gradient-to-l from-green-500 to-green-500/40 transition-all duration-200"
            :style="{ width: bidImbalanceWidth }"
          />
        </div>
        <div class="absolute inset-y-0 left-1/2 right-0 flex justify-start">
          <div
            class="h-full bg-gradient-to-r from-red-500 to-red-500/40 transition-all duration-200"
            :style="{ width: askImbalanceWidth }"
          />
        </div>
        <div class="absolute left-1/2 top-0 bottom-0 w-px bg-zinc-500/80 -translate-x-px" />
      </div>
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

    <!-- Book + Tape side-by-side -->
    <div class="flex-1 flex min-h-0">
      <div class="flex-1 flex flex-col min-w-0">
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
            :class="[
              isDark ? 'border-zinc-800/50' : 'border-gray-200',
              myOrderPrices.has(row.price) ? (isDark ? 'bg-yellow-900/20' : 'bg-yellow-100') : '',
              myTpPrices.has(row.price) ? (isDark ? 'ring-1 ring-inset ring-cyan-400/50' : 'ring-1 ring-inset ring-cyan-500/40') : '',
            ]"
          >
            <!-- Heatmap layers -->
            <div
              v-if="row.bidSize > 0"
              class="absolute inset-y-0 left-0 w-1/2 pointer-events-none transition-opacity duration-150"
              :style="bidHeatStyle(row.bidSize)"
            />
            <div
              v-if="row.askSize > 0"
              class="absolute inset-y-0 right-0 w-1/2 pointer-events-none transition-opacity duration-150"
              :style="askHeatStyle(row.askSize)"
            />

            <!-- Mid-price horizontal marker -->
            <div
              v-if="row.price === midPriceCents"
              class="absolute inset-x-0 top-1/2 h-px z-20 pointer-events-none"
              :class="isDark ? 'bg-[#00e5ff] shadow-[0_0_6px_#00e5ff]' : 'bg-cyan-500'"
            />

            <div @click="$emit('placeOrder', 'BUY', row.price)" class="relative flex items-center justify-end px-2 text-green-500 font-mono text-xs border-r z-10" :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'">
              <div v-if="row.bidSize > 0" class="absolute left-0 top-0 bottom-0 bg-green-500/20 transition-all duration-200" :style="{ width: getVolumeBarWidth(row.bidSize) + '%' }"></div>
              <span v-if="row.price === bestBidCents" class="absolute left-1 text-[10px] text-green-500 animate-pulse">▶</span>
              <span class="relative z-10">{{ row.bidSize > 0 ? row.bidSize.toFixed(0) : '' }}</span>
            </div>
            
            <div :class="['flex items-center justify-center font-bold font-mono text-sm relative z-10', getPriceColorClass(row)]">
              {{ row.price }}
              <div v-if="myOrderPrices.has(row.price)" class="absolute w-2 h-2 rounded-full bg-yellow-500 -left-3 shadow-[0_0_5px_#eab308]" title="Pending entry"></div>
              <div v-if="myTpPrices.has(row.price)" class="absolute w-2 h-2 rounded-full bg-cyan-400 -right-3 shadow-[0_0_5px_#22d3ee]" title="Take Profit"></div>
            </div>
            
            <div class="relative flex items-center justify-start px-2 text-red-500 font-mono text-xs border-l z-10" :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'">
              <div v-if="row.askSize > 0" class="absolute right-0 top-0 bottom-0 bg-red-500/20 transition-all duration-200" :style="{ width: getVolumeBarWidth(row.askSize) + '%' }"></div>
              <span v-if="row.price === bestAskCents" class="absolute right-1 text-[10px] text-red-500 animate-pulse">◀</span>
              <span class="relative z-10">{{ row.askSize > 0 ? row.askSize.toFixed(0) : '' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tape (Time & Sales) -->
      <div
        :class="[
          'w-[88px] shrink-0 border-l flex flex-col',
          isDark ? 'bg-[#050505] border-zinc-800' : 'bg-gray-50 border-gray-200',
        ]"
      >
        <div
          :class="[
            'text-[9px] font-bold tracking-widest uppercase text-center py-1 border-b shrink-0',
            isDark ? 'text-zinc-500 border-zinc-800' : 'text-gray-500 border-gray-200',
          ]"
        >
          Tape
        </div>
        <div class="flex-1 overflow-y-auto custom-scrollbar text-[10px] font-mono">
          <div
            v-for="(print, i) in activeTape"
            :key="i + '-' + print.ts"
            class="flex justify-between px-1.5 py-0.5 border-b"
            :class="[
              isDark ? 'border-zinc-900' : 'border-gray-100',
              print.side === 'BUY' ? 'text-green-400' : 'text-red-400',
            ]"
          >
            <span>{{ print.price }}</span>
            <span class="opacity-80">{{ formatTapeSize(print.size) }}</span>
          </div>
          <div v-if="!activeTape.length" class="text-zinc-600 text-center mt-4 text-[9px] px-1">
            waiting…
          </div>
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
  midPrice: { type: Number, default: 0 },
  imbalance: { type: Number, default: 0 },
  tape: { type: Array, default: () => [] },
  velocity: { type: Number, default: 0 },
})

const emit = defineEmits(['update:activeTeam', 'placeOrder'])
const orderBookContainer = ref(null)
const marketStore = useMarketStore()

const activeLadder = computed(() => (props.activeTeam === 1 ? props.ladderYes : props.ladderNo))
const activeTape = computed(() => props.tape || [])

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

const midPriceCents = computed(() => {
  if (props.midPrice > 0) return Math.round(props.midPrice * 100)
  if (bestBidCents.value > 0 && bestAskCents.value > 0) {
    return Math.round((bestBidCents.value + bestAskCents.value) / 2)
  }
  return bestBidCents.value || bestAskCents.value || 0
})

const imbalancePct = computed(() => {
  const v = props.imbalance || 0
  const pct = Math.round(v * 100)
  return (pct > 0 ? '+' : '') + pct + '%'
})

const bidImbalanceWidth = computed(() => {
  const v = props.imbalance || 0
  if (v <= 0) return '0%'
  return Math.min(100, Math.round(v * 100)) + '%'
})

const askImbalanceWidth = computed(() => {
  const v = props.imbalance || 0
  if (v >= 0) return '0%'
  return Math.min(100, Math.round(-v * 100)) + '%'
})

/** Pending entry limits on this token. */
const myOrderPrices = computed(() => {
  const prices = new Set()
  marketStore.openPositions.forEach((p) => {
    if (p.token_id === props.currentTokenId && p.status === 'PENDING') {
      prices.add(Math.round(p.entry_price * 100))
    }
  })
  return prices
})

/** Take-profit limit levels for open/pending positions on this token. */
const myTpPrices = computed(() => {
  const prices = new Set()
  marketStore.openPositions.forEach((p) => {
    if (p.token_id !== props.currentTokenId) return
    if (!['OPEN', 'PENDING'].includes(p.status)) return

    if (p.strategy === 'partial') {
      // Dual TPs placed by backend at entry+0.03 / entry+0.06
      prices.add(Math.round((p.entry_price + 0.03) * 100))
      prices.add(Math.round((p.entry_price + 0.06) * 100))
    } else if (p.tp_price != null) {
      prices.add(Math.round(Number(p.tp_price) * 100))
    }
  })
  return prices
})

/** Median of visible non-zero sizes for heatmap intensity scaling. */
const medianVisibleSize = computed(() => {
  const sizes = []
  if (!activeLadder.value) return 1
  for (const row of activeLadder.value) {
    if (row.bidSize > 0) sizes.push(row.bidSize)
    if (row.askSize > 0) sizes.push(row.askSize)
  }
  if (!sizes.length) return 1
  sizes.sort((a, b) => a - b)
  const mid = Math.floor(sizes.length / 2)
  return sizes.length % 2 ? sizes[mid] : (sizes[mid - 1] + sizes[mid]) / 2 || 1
})

const heatIntensity = (size) => {
  if (!size || size <= 0) return 0
  const ratio = size / medianVisibleSize.value
  // Cap opacity contribution
  return Math.min(0.55, Math.max(0.05, ratio * 0.22))
}

const bidHeatStyle = (size) => {
  const a = heatIntensity(size)
  return {
    background: `linear-gradient(90deg, rgba(34,197,94,${a}) 0%, transparent 100%)`,
  }
}

const askHeatStyle = (size) => {
  const a = heatIntensity(size)
  return {
    background: `linear-gradient(270deg, rgba(239,68,68,${a}) 0%, transparent 100%)`,
  }
}

const getVolumeBarWidth = (size) => {
  if (!size) return 0
  return Math.min(100, (size / 5000) * 100)
}

const getPriceColorClass = (row) => {
  if (row.price === midPriceCents.value) return 'text-[#00e5ff]'
  if (row.price === bestBidCents.value) return 'text-green-500'
  if (row.price === bestAskCents.value) return 'text-red-500'
  if (myTpPrices.value.has(row.price)) return 'text-cyan-300'
  return props.isDark ? 'text-gray-300' : 'text-gray-700'
}

const formatTapeSize = (size) => {
  if (size >= 1000) return (size / 1000).toFixed(1) + 'k'
  return size >= 10 ? size.toFixed(0) : size.toFixed(1)
}

const scrollToSpread = () => {
  if (!orderBookContainer.value) return
  const targetPrice =
    bestAskCents.value > 0
      ? bestAskCents.value
      : bestBidCents.value > 0
        ? bestBidCents.value
        : 50
  const targetRow = orderBookContainer.value.querySelector(`[data-price="${targetPrice}"]`)
  if (targetRow) {
    const containerHeight = orderBookContainer.value.clientHeight
    const rowTop = targetRow.offsetTop
    orderBookContainer.value.scrollTo({
      top: rowTop - containerHeight / 2,
      behavior: 'auto',
    })
  }
}

defineExpose({ scrollToSpread })
</script>
