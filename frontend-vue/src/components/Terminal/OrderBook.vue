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
        class="flex-1 py-2 rounded font-bold text-sm border shadow-[0_0_15px_rgba(0,229,255,0.15)] transition-all flex flex-col items-center justify-center"
        :class="isDark ? 'bg-[#00e5ff]/10 border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff]/20' : 'bg-[#00e5ff]/10 border-[#00e5ff] text-[#00b8cc] hover:bg-[#00e5ff]/20'"
      >
        <span class="text-[10px] tracking-wider uppercase">BUY (Best Ask)</span>
        <span class="text-lg">{{ bestAsk > 0 ? bestAsk + '¢' : '--' }}</span>
      </button>
    </div>

    <div :class="['grid grid-cols-3 text-[10px] font-bold text-gray-500 py-1 sticky top-0 z-20 shrink-0 border-b', isDark ? 'bg-black border-zinc-800' : 'bg-gray-100 border-gray-300']">
      <div class="text-center">BIDS (ПОКУПКА)</div>
      <div class="text-center">ЦЕНА ¢</div>
      <div class="text-center">ASKS (ПРОДАЖА)</div>
    </div>
    
    <div id="ladder-container" class="flex-1 overflow-y-auto scroll-smooth custom-scrollbar relative">
      <div 
        v-for="row in ladderRows" :key="row.price" 
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

    <button @click="scrollToSpread" class="absolute bottom-4 right-4 p-2 rounded-full shadow-lg transition-all z-30" :class="isDark ? 'bg-black border border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black' : 'bg-white border border-[#00e5ff] text-[#00b8cc] hover:bg-[#00e5ff] hover:text-white'" title="Центрировать спред">
      🎯
    </button>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  isDark: Boolean,
  activeTeam: Number,
  team1Name: String,
  team2Name: String,
  rawBidsYes: Map,
  rawAsksYes: Map,
  rawBidsNo: Map,
  rawAsksNo: Map,
  openPositions: Array,
  currentTokenId: String
})

const emit = defineEmits(['update:activeTeam', 'placeOrder'])

const ladderRows = computed(() => {
  const rows = []
  const targetBids = props.activeTeam === 1 ? props.rawBidsYes : props.rawBidsNo
  const targetAsks = props.activeTeam === 1 ? props.rawAsksYes : props.rawAsksNo
  const oppBids = props.activeTeam === 1 ? props.rawBidsNo : props.rawBidsYes
  const oppAsks = props.activeTeam === 1 ? props.rawAsksNo : props.rawAsksYes

  for (let price = 99; price >= 1; price--) {
    let bidSize = 0, askSize = 0
    let pFloat = price / 100.0
    if (targetBids.has(pFloat)) bidSize += targetBids.get(pFloat)
    if (targetAsks.has(pFloat)) askSize += targetAsks.get(pFloat)

    let impFloat = (100 - price) / 100.0
    if (oppAsks.has(impFloat)) bidSize += oppAsks.get(impFloat)
    if (oppBids.has(impFloat)) askSize += oppBids.get(impFloat)

    rows.push({ price, bidSize, askSize })
  }
  return rows
})

const bestAsk = computed(() => {
  let best = 100
  for(let r of ladderRows.value) { if(r.askSize > 0 && r.price < best) best = r.price }
  return best === 100 ? 0 : best
})

const bestBid = computed(() => {
  let best = 0
  for(let r of ladderRows.value) { if(r.bidSize > 0 && r.price > best) best = r.price }
  return best
})

const maxVolume = computed(() => {
  let max = 0
  ladderRows.value.forEach(r => {
    if (r.bidSize > max) max = r.bidSize
    if (r.askSize > max) max = r.askSize
  })
  return max < 500 ? 500 : max
})

const getVolumeBarWidth = (size) => Math.min(100, (size / maxVolume.value) * 100)

const getPriceColorClass = (row) => {
  if (row.bidSize > 0 && row.askSize === 0) return props.isDark ? 'text-green-400 bg-green-900/10' : 'text-green-600 bg-green-50'
  if (row.askSize > 0 && row.bidSize === 0) return props.isDark ? 'text-red-400 bg-red-900/10' : 'text-red-600 bg-red-50'
  if (row.bidSize > 0 && row.askSize > 0) return 'text-yellow-500 bg-yellow-500/10'
  return 'text-gray-500'
}

const isMyOrder = (price) => {
  if (!props.currentTokenId || !props.openPositions) return false
  return props.openPositions.some(pos => pos.token_id === props.currentTokenId && Math.round(pos.entry_price * 100) === price)
}

// 🎯 ИСПРАВЛЕННАЯ ЦЕНТРОВКА (Ищет математическую середину ликвидности)
const scrollToSpread = () => {
  setTimeout(() => {
    const container = document.getElementById('ladder-container')
    if (!container) return
    
    let bAsk = bestAsk.value > 0 ? bestAsk.value : 50;
    let bBid = bestBid.value > 0 ? bestBid.value : 50;
    
    let midPrice = Math.round((bAsk + bBid) / 2);
    if (midPrice === 0) midPrice = 50;
    
    let spreadIndex = 99 - midPrice; // Цена 99 это индекс 0. Цена 40 это индекс 59.

    container.scrollTo({
      top: (spreadIndex * 28) - (container.clientHeight / 2),
      behavior: 'smooth'
    })
  }, 50)
}

watch(() => props.activeTeam, scrollToSpread)
defineExpose({ scrollToSpread })
</script>