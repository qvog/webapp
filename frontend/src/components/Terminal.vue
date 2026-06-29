<template>
  <div :class="['h-screen w-full font-sans flex flex-col overflow-hidden transition-colors duration-300', marketStore.isDark ? 'bg-black text-gray-200' : 'bg-gray-100 text-gray-900']">
    
    <header :class="['h-14 shrink-0 px-4 flex justify-between items-center z-10 border-b', marketStore.isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300']">
      <div class="flex items-center gap-4">
        <button v-if="currentEvent" @click="closeTerminal" :class="['px-3 py-1 rounded text-xs font-bold border transition-colors', marketStore.isDark ? 'border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black' : 'border-[#00e5ff] text-[#00b8cc] hover:bg-[#00e5ff] hover:text-white']">
          ← BACK
        </button>
        <h1 class="text-lg font-bold">{{ currentEvent ? currentEvent.title : 'qScalp' }}</h1>
      </div>
      
      <button @click="marketStore.isDark = !marketStore.isDark" :class="['px-4 py-1.5 rounded-full text-xs font-bold border transition-colors flex gap-2 items-center', marketStore.isDark ? 'border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff]/10' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50 shadow-sm']">
        <span v-if="marketStore.isDark">🌙 Dark Mode</span>
        <span v-else>☀️ Light Mode</span>
      </button>
    </header>

    <div v-if="currentEvent" class="flex-1 flex overflow-hidden p-2 gap-2">
      
      <div class="w-64 flex flex-col gap-2 shrink-0">
        <div :class="['border rounded p-3 shrink-0', marketStore.isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300 shadow-sm']">
          <div class="flex justify-between items-center mb-3">
            <h3 class="font-bold text-gray-500 text-[10px] tracking-wider">Options</h3>
            <div :class="['flex rounded border p-0.5', marketStore.isDark ? 'bg-black border-zinc-800' : 'bg-gray-100 border-gray-300']">
              <button @click="marketStore.tradingMode = 'custom'" :class="['px-2 py-1 text-[10px] font-bold rounded transition-colors', marketStore.tradingMode === 'custom' ? (marketStore.isDark ? 'bg-[#00e5ff] text-black' : 'bg-[#00e5ff] text-white') : 'text-gray-500']">Custom</button>
              <button @click="marketStore.tradingMode = 'presets'" :class="['px-2 py-1 text-[10px] font-bold rounded transition-colors', marketStore.tradingMode === 'presets' ? (marketStore.isDark ? 'bg-[#00e5ff] text-black' : 'bg-[#00e5ff] text-white') : 'text-gray-500']">Presets</button>
            </div>
          </div>

          <div class="mb-3">
            <label class="block text-[10px] text-gray-500 mb-1">Value (USDC)</label>
            <input v-model="marketStore.tradeSize" type="number" :class="['w-full border rounded px-2 py-1.5 text-sm font-bold outline-none focus:border-[#00e5ff]', marketStore.isDark ? 'bg-black border-zinc-800 text-white' : 'bg-white border-gray-300 text-black']" />
          </div>

          <div v-if="marketStore.tradingMode === 'custom'" class="flex gap-2">
            <div class="flex-1">
              <label class="block text-[10px] text-gray-500 mb-1">Take Profit</label>
              <input v-model="marketStore.tpOffset" type="number" :class="['w-full border rounded px-2 py-1.5 text-sm font-bold outline-none text-green-500', marketStore.isDark ? 'bg-black border-zinc-800' : 'bg-white border-gray-300']" />
            </div>
            <div class="flex-1">
              <label class="block text-[10px] text-gray-500 mb-1">Stop Loss</label>
              <input v-model="marketStore.slOffset" type="number" :class="['w-full border rounded px-2 py-1.5 text-sm font-bold outline-none text-red-500', marketStore.isDark ? 'bg-black border-zinc-800' : 'bg-white border-gray-300']" />
            </div>
          </div>

          <div v-if="marketStore.tradingMode === 'presets'" class="grid grid-cols-2 gap-2">
            <button @click="marketStore.activePreset = '4c'" :class="['p-2 rounded text-xs font-bold border transition-colors', marketStore.activePreset === '4c' ? (marketStore.isDark ? 'bg-[#00e5ff] border-[#00e5ff] text-black' : 'bg-[#00e5ff] border-[#00e5ff] text-white') : (marketStore.isDark ? 'bg-black border-zinc-800 text-gray-500' : 'bg-gray-50 border-gray-300 text-gray-600')]">4c</button>
            <button @click="marketStore.activePreset = '8c'" :class="['p-2 rounded text-xs font-bold border transition-colors', marketStore.activePreset === '8c' ? (marketStore.isDark ? 'bg-[#00e5ff] border-[#00e5ff] text-black' : 'bg-[#00e5ff] border-[#00e5ff] text-white') : (marketStore.isDark ? 'bg-black border-zinc-800 text-gray-500' : 'bg-gray-50 border-gray-300 text-gray-600')]">8c</button>
          </div>
        </div>

        <div :class="['border rounded p-3 flex-1 overflow-y-auto custom-scrollbar', marketStore.isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300 shadow-sm']">
          <h3 class="font-bold text-gray-500 text-[10px] mb-2 tracking-wider">Lines ({{ currentEvent.sub_markets.length }})</h3>
          <div class="flex flex-col gap-2">
            <button 
              v-for="sub in currentEvent.sub_markets" :key="sub.condition_id"
              @click="openSubMarket(sub)"
              :class="['w-full p-2 rounded text-left text-xs transition-colors border', activeSubMarket?.condition_id === sub.condition_id ? (marketStore.isDark ? 'border-[#00e5ff] bg-[#00e5ff]/10 text-white' : 'border-[#00e5ff] bg-cyan-50 text-black font-bold') : (marketStore.isDark ? 'border-transparent bg-black text-gray-400 hover:bg-zinc-900' : 'border-gray-200 bg-gray-50 text-gray-600 hover:bg-gray-100')]"
            >
              <span class="block whitespace-normal break-words leading-snug">
                {{ sub.question }}
              </span>
            </button>
          </div>
        </div>
      </div>

      <div class="flex-1 relative flex flex-col min-w-[350px]">
        <div v-if="isConnecting" class="absolute inset-0 z-50 flex items-center justify-center backdrop-blur-sm rounded-lg" :class="marketStore.isDark ? 'bg-black/80' : 'bg-white/80'">
          <span class="text-[#00e5ff] text-sm font-bold animate-pulse">CONNECTION...</span>
        </div>
        
        <div v-if="activeSubMarket" class="mb-2 flex items-center justify-between border-b pb-2" :class="marketStore.isDark ? 'border-gray-800' : 'border-gray-200'">
          <h2 class="text-sm font-bold truncate pr-4" :class="marketStore.isDark ? 'text-gray-200' : 'text-gray-800'" :title="activeSubMarket.question">
            {{ activeSubMarket.question }}
          </h2>
          <div :class="['px-2 py-0.5 rounded text-[11px] font-mono font-bold border transition-colors whitespace-nowrap', spreadBadgeClass]">
            SPREAD: {{ activeSpreadCents }}¢
          </div>
        </div>

        <OrderBook 
          ref="orderBookRef"
          v-if="activeSubMarket"
          :isDark="marketStore.isDark"
          v-model:activeTeam="activeTeam"
          :team1Name="activeSubMarket.out1"
          :team2Name="activeSubMarket.out2"
          :ladderYes="ladderYes"
          :ladderNo="ladderNo"
          :bestBid="activeTeam === 1 ? bestBidYes : bestBidNo" 
          :bestAsk="activeTeam === 1 ? bestAskYes : bestAskNo"
          :currentTokenId="activeTeam === 1 ? activeSubMarket.token_id_yes : activeSubMarket.token_id_no"
          @placeOrder="handlePlaceOrder"
        />
      </div>

      <div :class="['w-64 border rounded p-3 flex flex-col shrink-0', marketStore.isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300 shadow-sm']">
        <div class="flex justify-between items-center mb-2"> 
          <h3 class="font-bold text-gray-500 text-[10px] tracking-wider">Open Orders</h3>
          <button @click="marketStore.loadPositions()" class="text-[10px] text-[#00e5ff] hover:underline transition-colors">↻RESET</button>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scrollbar space-y-2 pr-1">
          <div v-if="livePositions.length === 0" class="text-center text-gray-500 text-xs mt-10">Empty</div>
          
          <div v-for="pos in livePositions" :key="pos.order_id" :class="['border p-2 rounded flex flex-col gap-1.5 transition-colors', marketStore.isDark ? 'bg-black border-zinc-800 hover:border-zinc-700' : 'bg-gray-50 border-gray-200 hover:border-gray-300']">
            
            <div class="flex justify-between items-center">
              <span class="font-bold text-xs truncate max-w-[120px]" :title="marketStore.getTeamNameFromToken(pos.token_id)">
                {{ marketStore.getTeamNameFromToken(pos.token_id) }}
              </span>
              
              <div class="flex items-center">
                <span v-if="pos.status === 'PENDING'" class="text-[9px] px-1.5 py-0.5 rounded font-bold bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 animate-pulse uppercase tracking-wider">
                  ⏳ In order book
                </span>
                <span v-else :class="['font-bold text-xs transition-colors', pos.liveDiff >= 0 ? 'text-green-500' : 'text-red-500']">
                  {{ pos.liveDiff > 0 ? '+' : '' }}{{ pos.liveDiff }}¢
                </span>
              </div>
            </div>
            
            <div class="text-[10px] flex flex-col gap-1" :class="marketStore.isDark ? 'text-gray-400' : 'text-gray-500'">
              <div class="flex justify-between px-1.5 py-1 rounded" :class="marketStore.isDark ? 'bg-[#161b22]' : 'bg-white shadow-sm border border-gray-100'">
                <span>BUY: <b :class="marketStore.isDark ? 'text-white' : 'text-black'">{{ Math.round(pos.entry_price * 100) }}¢</b></span>
                <span>VOL: <b :class="marketStore.isDark ? 'text-white' : 'text-black'">{{ pos.size.toFixed(1) }}</b></span>
              </div>
              
              <div class="flex justify-between px-1.5 font-mono">
                <span :class="marketStore.isDark ? 'text-green-400' : 'text-green-600'">
                  TP: <b>{{ pos.tp_price ? Math.round(pos.tp_price * 100) + '¢' : '--' }}</b>
                </span>
                <span :class="marketStore.isDark ? 'text-red-400' : 'text-red-600'">
                  SL: <b>{{ pos.sl_trigger_price ? Math.round(pos.sl_trigger_price * 100) + '¢' : '--' }}</b>
                </span>
              </div>
            </div>
            
            <button @click="executePanicSell(pos.order_id)" class="w-full mt-1 bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white text-[10px] py-1 rounded transition-colors font-bold border border-red-500/30">
              {{ pos.status === 'PENDING' ? 'CANCEL ORDER' : 'MARKET DUMP' }}
            </button>
          </div>
          
        </div>
      </div>
    </div>

    <div v-else class="flex-1 overflow-y-auto p-6">
      <div class="max-w-6xl mx-auto">
        <h2 class="text-2xl font-bold mb-6">Dota 2</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="match in marketStore.matches" :key="match.event_id" :class="['border p-4 rounded-lg flex flex-col justify-between h-40 transition-colors', marketStore.isDark ? 'bg-[#0a0a0a] border-zinc-800 hover:border-zinc-600' : 'bg-white border-gray-300 hover:border-gray-400 shadow-sm']">
            <div>
              <span class="text-[10px] text-gray-500">{{ new Date(match.start_date).toLocaleDateString() }}</span>
              <h3 class="font-bold text-sm mt-1 line-clamp-2" :class="marketStore.isDark ? 'text-white' : 'text-black'">{{ match.title }}</h3>
            </div>
            <div class="flex justify-between items-end mt-2">
              <div class="text-xs text-gray-500">Vol: <span class="font-bold" :class="marketStore.isDark ? 'text-white' : 'text-black'">${{ formatVolume(match.total_volume) }}</span></div>
              <button @click="openEvent(match)" :class="['px-3 py-1.5 rounded text-xs font-bold transition-colors', marketStore.isDark ? 'bg-[#00e5ff] text-black hover:bg-[#00b8cc]' : 'bg-[#00e5ff] text-white hover:bg-[#00b8cc] shadow-md']">
                GO
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useToast } from 'vue-toastification'
import OrderBook from './Terminal/OrderBook.vue'

import { useMarketStore } from '../store/marketStore'
import { useOrderBook } from '../composables/useOrderBook'
import { tradeApi } from '../api/tradeService'

const toast = useToast()
const marketStore = useMarketStore()

// 1. СНАЧАЛА инициализируем переменные стакана
const { 
  ladderYes, ladderNo, 
  spreadYes, spreadNo, 
  bestBidYes, bestBidNo, 
  isConnecting, connectToMarket, disconnect 
} = useOrderBook()

// 2. ЗАТЕМ объявляем локальные переменные
const currentEvent = ref(null)
const activeSubMarket = ref(null)
const activeTeam = ref(1)
const orderBookRef = ref(null)

// 3. И ТОЛЬКО ПОТОМ используем их в Computed (чтобы не было ошибок загрузки)
const activeSpreadCents = computed(() => {
  const sp = activeTeam.value === 1 ? spreadYes.value : spreadNo.value
  return Math.round(sp * 100)
})

const spreadBadgeClass = computed(() => {
  const cents = activeSpreadCents.value
  if (cents <= 2) return 'bg-green-500/20 text-green-500 border-green-500/50'
  if (cents <= 5) return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/50'
  return 'bg-red-500/20 text-red-500 border-red-500/50'
})

// 🎯 ЖИВОЙ PnL (Связан с позициями и стаканом)
const livePositions = computed(() => {
  return marketStore.openPositions.map(pos => {
    // Если позиция закрыта, берем финальный профит
    if (pos.status === 'CLOSED_TP' || pos.status === 'CLOSED_SL' || pos.status === 'RESOLVED') {
      const exitP = pos.exit_price || pos.entry_price;
      const profitCents = Math.round((exitP - pos.entry_price) * 100);
      return { ...pos, liveDiff: profitCents };
    }

    // Если открыта — считаем по живому стакану
    let currentMarketPrice = 0;
    
    if (activeSubMarket.value) {
      if (pos.token_id === activeSubMarket.value.token_id_yes) {
        currentMarketPrice = bestBidYes.value;
      } else if (pos.token_id === activeSubMarket.value.token_id_no) {
        currentMarketPrice = bestBidNo.value;
      }
    }
    
    if (!currentMarketPrice) currentMarketPrice = pos.entry_price;

    const profitCents = Math.round((currentMarketPrice - pos.entry_price) * 100);
    return { ...pos, liveDiff: profitCents, currentMarketPrice };
  });
});

const handleKeydown = (e) => {
  if (e.code === 'Space' && currentEvent.value && e.target.tagName !== 'INPUT') {
    e.preventDefault()
    orderBookRef.value?.scrollToSpread()
  }
}

const formatVolume = (val) => val >= 1000 ? (val / 1000).toFixed(1) + 'K' : Math.round(val)

const closeTerminal = () => {
  disconnect()
  currentEvent.value = null
  activeSubMarket.value = null
}

const openEvent = (match) => {
  currentEvent.value = match
  if (match.sub_markets.length > 0) openSubMarket(match.sub_markets[0])
}

const openSubMarket = (sub) => {
  activeSubMarket.value = sub
  connectToMarket(sub, () => {
    nextTick(() => orderBookRef.value?.scrollToSpread())
  })
}

const handlePlaceOrder = async (side, priceCents) => {
  if (side === 'SELL') return
  const targetToken = activeTeam.value === 1 ? activeSubMarket.value.token_id_yes : activeSubMarket.value.token_id_no
  
  let finalTpCents = null
  let finalSlCents = null  
  let finalStrategy = 'custom'

  if (marketStore.tradingMode === 'custom') {
    finalTpCents = marketStore.tpOffset > 0 ? priceCents + marketStore.tpOffset : null
    finalSlCents = marketStore.slOffset > 0 ? priceCents - marketStore.slOffset : null
  } else {
    finalStrategy = marketStore.activePreset
    if (marketStore.activePreset === '4c') {
      finalTpCents = priceCents + 4
      finalSlCents = priceCents - 12
    }
    if (marketStore.activePreset === '8c') {
      finalTpCents = priceCents + 8
      finalSlCents = priceCents - 12
    }
  }

  const reqBody = {
    token_id: targetToken,
    condition_id: activeSubMarket.value.condition_id,
    price: priceCents / 100.0,
    side: "BUY", 
    bankroll: marketStore.tradeSize, 
    risk_percent: 100, 
    is_custom_limit: true,
    take_profit_price: finalTpCents ? Math.min(0.99, finalTpCents / 100.0) : null,
    stop_loss_price: finalSlCents ? Math.max(0.01, finalSlCents / 100.0) : null,
    strategy: finalStrategy
  }
  
  try {
    toast.info(`Order Submission: ${priceCents}¢...`)
    const data = await tradeApi.placeOrder(reqBody)
    if (data.success) {
      toast.success(`✅ Success! BUY ${priceCents}¢`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ Exchange Rejection: ${data.error}`)
    }
  } catch (e) {
    toast.error("❌ Network Error: Server Not Responding")
  }
}

const executePanicSell = async (orderId) => {
  try {
    toast.warning("⚡ Market Dump Initiation...")
    const data = await tradeApi.panicSell(orderId)
    if (data.success) {
      toast.success(`✅ ${data.message}`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ Error Dump: ${data.error}`)
    }
  } catch(e) {
    toast.error("❌ Network Error With Dump")
  }
}

onMounted(() => { 
  window.addEventListener('keydown', handleKeydown)
  marketStore.loadMatches()
  marketStore.loadPositions()
  setInterval(() => { marketStore.loadPositions() }, 3000) 
})

onUnmounted(() => { 
  window.removeEventListener('keydown', handleKeydown)
  disconnect()
})
</script>