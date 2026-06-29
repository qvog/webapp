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
        @click="$emit('placeOrder', 'SELL', bestBid)"
        class="flex-1 py-2 rounded font-bold text-sm border transition-colors flex flex-col items-center justify-center opacity-80 hover:opacity-100"
        :class="isDark ? 'bg-red-950/20 border-red-900 text-red-500' : 'bg-red-50 border-red-200 text-red-500'"
      >
        <span class="text-[10px] tracking-wider uppercase">SELL (Best Bid)</span>
        <span class="text-lg">{{ bestBid > 0 ? bestBid + '¢' : '--' }}</span>
      </button>

      <button 
        @click="$emit('placeOrder', 'BUY', bestAsk)"
        class="flex-1 py-2 rounded font-bold text-sm border shadow-[0_0_15px_rgba(34,197,94,0.15)] transition-all flex flex-col items-center justify-center"
        :class="isDark ? 'bg-green-500/10 border-green-500 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_20px_rgba(34,197,94,0.3)]' : 'bg-green-50 border-green-400 text-green-600 hover:bg-green-100'"
      >
        <span class="text-[10px] tracking-wider uppercase">BUY (Best Ask)</span>
        <span class="text-lg">{{ bestAsk > 0 ? bestAsk + '¢' : '--' }}</span>
      </button>
    </div>

    <div :class="['grid grid-cols-3 text-[10px] font-bold text-gray-500 py-1 sticky top-0 z-20 shrink-0 border-b', isDark ? 'bg-black border-zinc-800' : 'bg-gray-100 border-gray-300']">
      <div class="text-center">BIDS (BUY)</div>
      <div class="text-center">PRICE ¢</div>
      <div class="text-center">ASKS (SELL)</div>
    </div>
    
    <div id="ladder-container" class="flex-1 overflow-y-auto scroll-smooth custom-scrollbar relative">
      <div 
        v-for="row in activeLadder" :key="row.price" 
        class="grid grid-cols-3 border-b hover:bg-[#00e5ff]/10 transition-colors group cursor-crosshair h-7 relative"
        :class="[isDark ? 'border-zinc-800/50' : 'border-gray-200', isMyOrder(row.price) ? (isDark ? 'bg-yellow-900/20' : 'bg-yellow-100') : '']"
      >
        <div @click="$emit('placeOrder', 'BUY', row.price)" class="relative flex items-center justify-end px-2 text-green-500 font-mono text-xs border-r" :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'">
          <div v-if="row.bidSize > 0" class="absolute left-0 top-0 bottom-0 bg-green-500/20 transition-all duration-200" :style="{ width: getVolumeBarWidth(row.bidSize) + '%' }"></div>
          <span v-if="row.price === bestBid" class="absolute left-1 text-[10px] text-green-500 animate-pulse">▶</span>
          <span class="relative z-10">{{ row.bidSize > 0 ? row.bidSize.toFixed(0) : '' }}</span>
        </div>
        
        <div :class="['flex items-center justify-center font-bold font-mono text-sm relative', getPriceColorClass(row)]">
          {{ row.price }}
          <div v-if="isMyOrder(row.price)" class="absolute w-2 h-2 rounded-full bg-yellow-500 -left-3 shadow-[0_0_5px_#eab308]"></div>
        </div>
        
        <div class="relative flex items-center justify-start px-2 text-red-500 font-mono text-xs border-l" :class="isDark ? 'border-zinc-800/30' : 'border-gray-200'">
          <div v-if="row.askSize > 0" class="absolute right-0 top-0 bottom-0 bg-red-500/20 transition-all duration-200" :style="{ width: getVolumeBarWidth(row.askSize) + '%' }"></div>
          <span v-if="row.price === bestAsk" class="absolute right-1 text-[10px] text-red-500 animate-pulse">◀</span>
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

// 🎯 ВЕРНУЛИ: Ищем лучшую цену покупки для подсветки спреда
const bestBid = computed(() => {
  if (!activeLadder.value) return 0
  for (let i = 0; i < 99; i++) {
    if (activeLadder.value[i].bidSize > 0) return activeLadder.value[i].price
  }
  return 0
})

// 🎯 ВЕРНУЛИ: Ищем лучшую цену продажи для подсветки спреда
const bestAsk = computed(() => {
  if (!activeLadder.value) return 100
  for (let i = 98; i >= 0; i--) {
    if (activeLadder.value[i].askSize > 0) return activeLadder.value[i].price
  }
  return 100
})

// 🎯 ВЕРНУЛИ: Проверяем, есть ли на этой цене наш ордер (подсветка синим)
const isMyOrder = (price) => {
  return marketStore.openPositions.some(p => 
    p.token_id === props.currentTokenId && 
    p.status === 'PENDING' && 
    Math.round(p.entry_price * 100) === price
  )
}

const setTeam = (teamId) => { emit('update:activeTeam', teamId) }

const onRowClick = (side, priceCents) => {
  emit('placeOrder', side, priceCents)
}

const scrollToSpread = () => {
  if (!orderBookContainer.value) return
  
  const container = orderBookContainer.value
  const rows = container.querySelectorAll('.price-row')
  
  let targetRow = null
  for (const row of rows) {
    const askSize = parseFloat(row.dataset.ask || 0)
    const bidSize = parseFloat(row.dataset.bid || 0)
    if (askSize > 0 || bidSize > 0) {
      targetRow = row
      break
    }
  }

  if (targetRow) {
    const containerHeight = container.clientHeight
    const rowTop = targetRow.offsetTop
    container.scrollTo({
      top: rowTop - (containerHeight / 2),
      behavior: 'smooth'
    })
  }
}

defineExpose({ scrollToSpread })
</script>