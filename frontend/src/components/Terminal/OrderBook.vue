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
        :class="[isDark ? 'border-zinc-800/50' : 'border-gray-200', myOrderPrices.has(row.price) ? (isDark ? 'bg-yellow-900/20' : 'bg-yellow-100') : '']"
      >
        <div @click="$emit('placeOrder', 'BUY', row.price)" class="relative flex items-center justify-end px-2 text-green-500 font-mono text-xs border-r" :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'">
          <div v-if="row.bidSize > 0" class="absolute left-0 top-0 bottom-0 bg-green-500/20 transition-all duration-200" :style="{ width: getVolumeBarWidth(row.bidSize) + '%' }"></div>
          <span v-if="row.price === bestBidCents" class="absolute left-1 text-[10px] text-green-500 animate-pulse">▶</span>
          <span class="relative z-10">{{ row.bidSize > 0 ? row.bidSize.toFixed(0) : '' }}</span>
        </div>
        
        <div :class="['flex items-center justify-center font-bold font-mono text-sm relative', getPriceColorClass(row)]">
          {{ row.price }}
          <div v-if="myOrderPrices.has(row.price)" class="absolute w-2 h-2 rounded-full bg-yellow-500 -left-3 shadow-[0_0_5px_#eab308]"></div>
        </div>
        
        <div class="relative flex items-center justify-start px-2 text-red-500 font-mono text-xs border-l" :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'">
          <div v-if="row.askSize > 0" class="absolute right-0 top-0 bottom-0 bg-red-500/20 transition-all duration-200" :style="{ width: getVolumeBarWidth(row.askSize) + '%' }"></div>
          <span v-if="row.price === bestAskCents" class="absolute right-1 text-[10px] text-red-500 animate-pulse">◀</span>
          <span class="relative z-10">{{ row.askSize > 0 ? row.askSize.toFixed(0) : '' }}</span>
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
  currentTokenId: String
})

const emit = defineEmits(['update:activeTeam', 'placeOrder'])
const orderBookContainer = ref(null)
const marketStore = useMarketStore()

const activeLadder = computed(() => props.activeTeam === 1 ? props.ladderYes : props.ladderNo)

// 🎯 ВЕРНУЛИ ВНУТРЕННИЙ ПОДСЧЕТ (Кнопки и стакан больше не зависят от Terminal.vue)
// Ищем самую высокую цену, где есть покупатели (Bids)
const bestBidCents = computed(() => {
  if (!activeLadder.value) return 0
  for (let i = 0; i < 99; i++) {
    if (activeLadder.value[i].bidSize > 0) return activeLadder.value[i].price
  }
  return 0
})

// Ищем самую низкую цену, где есть продавцы (Asks)
const bestAskCents = computed(() => {
  if (!activeLadder.value) return 0
  for (let i = 98; i >= 0; i--) {
    if (activeLadder.value[i].askSize > 0) return activeLadder.value[i].price
  }
  return 0
})

const myOrderPrices = computed(() => {
  const prices = new Set()
  marketStore.openPositions.forEach(p => {
    if (p.token_id === props.currentTokenId && p.status === 'PENDING') {
      prices.add(Math.round(p.entry_price * 100))
    }
  })
  return prices
})

const getVolumeBarWidth = (size) => {
  if (!size) return 0
  return Math.min(100, (size / 5000) * 100)
}

const getPriceColorClass = (row) => {
  if (row.price === bestBidCents.value) return 'text-green-500'
  if (row.price === bestAskCents.value) return 'text-red-500'
  return props.isDark ? 'text-gray-300' : 'text-gray-700'
}

// 🎯 ИДЕАЛЬНАЯ ЦЕНТРОВКА
const scrollToSpread = () => {
  if (!orderBookContainer.value) return
  
  // Ищем точную строку с лучшим Asks или Bids
  const targetPrice = bestAskCents.value > 0 ? bestAskCents.value : (bestBidCents.value > 0 ? bestBidCents.value : 50)
  
  // O(1) поиск нужного элемента в DOM
  const targetRow = orderBookContainer.value.querySelector(`[data-price="${targetPrice}"]`)
  
  if (targetRow) {
    const containerHeight = orderBookContainer.value.clientHeight
    const rowTop = targetRow.offsetTop
    orderBookContainer.value.scrollTo({
      top: rowTop - (containerHeight / 2),
      behavior: 'auto' 
    })
  }
}

defineExpose({ scrollToSpread })
</script>