<template>
  <div :class="['h-screen w-full font-sans flex flex-col overflow-hidden transition-colors duration-300', isDark ? 'bg-black text-gray-200' : 'bg-gray-100 text-gray-900']">
    
    <header :class="['h-14 shrink-0 px-4 flex justify-between items-center z-10 border-b', isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300']">
      <div class="flex items-center gap-4">
        <button v-if="currentEvent" @click="closeTerminal" :class="['px-3 py-1 rounded text-xs font-bold border transition-colors', isDark ? 'border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black' : 'border-[#00e5ff] text-[#00b8cc] hover:bg-[#00e5ff] hover:text-white']">
          ← НАЗАД
        </button>
        <h1 class="text-lg font-bold">{{ currentEvent ? currentEvent.title : 'HFT TERMINAL' }}</h1>
      </div>
      
      <button @click="isDark = !isDark" :class="['px-4 py-1.5 rounded-full text-xs font-bold border transition-colors flex gap-2 items-center', isDark ? 'border-[#00e5ff] text-[#00e5ff] hover:bg-[#00e5ff]/10' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50 shadow-sm']">
        <span v-if="isDark">🌙 Dark Mode</span>
        <span v-else>☀️ Light Mode</span>
      </button>
    </header>

    <div v-if="currentEvent" class="flex-1 flex overflow-hidden p-2 gap-2">
      
      <div class="w-64 flex flex-col gap-2 shrink-0">
        <div :class="['border rounded p-3 shrink-0', isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300 shadow-sm']">
          <div class="flex justify-between items-center mb-3">
            <h3 class="font-bold text-gray-500 text-[10px] tracking-wider">НАСТРОЙКИ</h3>
            <div :class="['flex rounded border p-0.5', isDark ? 'bg-black border-zinc-800' : 'bg-gray-100 border-gray-300']">
              <button @click="tradingMode = 'custom'" :class="['px-2 py-1 text-[10px] font-bold rounded transition-colors', tradingMode === 'custom' ? (isDark ? 'bg-[#00e5ff] text-black' : 'bg-[#00e5ff] text-white') : 'text-gray-500']">РУЧНОЙ</button>
              <button @click="tradingMode = 'presets'" :class="['px-2 py-1 text-[10px] font-bold rounded transition-colors', tradingMode === 'presets' ? (isDark ? 'bg-[#00e5ff] text-black' : 'bg-[#00e5ff] text-white') : 'text-gray-500']">ПРЕСЕТЫ</button>
            </div>
          </div>

          <div class="mb-3">
            <label class="block text-[10px] text-gray-500 mb-1">Объем (USDC)</label>
            <input v-model="tradeSize" type="number" :class="['w-full border rounded px-2 py-1.5 text-sm font-bold outline-none focus:border-[#00e5ff]', isDark ? 'bg-black border-zinc-800 text-white' : 'bg-white border-gray-300 text-black']" />
          </div>

          <div v-if="tradingMode === 'custom'" class="flex gap-2">
            <div class="flex-1">
              <label class="block text-[10px] text-gray-500 mb-1">Авто-ТП (Тики)</label>
              <input v-model="tpOffset" type="number" :class="['w-full border rounded px-2 py-1.5 text-sm font-bold outline-none text-green-500', isDark ? 'bg-black border-zinc-800' : 'bg-white border-gray-300']" />
            </div>
            <div class="flex-1">
              <label class="block text-[10px] text-gray-500 mb-1">Стоп (Тики)</label>
              <input v-model="slOffset" type="number" :class="['w-full border rounded px-2 py-1.5 text-sm font-bold outline-none text-red-500', isDark ? 'bg-black border-zinc-800' : 'bg-white border-gray-300']" />
            </div>
          </div>

          <div v-if="tradingMode === 'presets'" class="grid grid-cols-2 gap-2">
            <button @click="activePreset = '4c'" :class="['p-2 rounded text-xs font-bold border transition-colors', activePreset === '4c' ? (isDark ? 'bg-[#00e5ff] border-[#00e5ff] text-black' : 'bg-[#00e5ff] border-[#00e5ff] text-white') : (isDark ? 'bg-black border-zinc-800 text-gray-500' : 'bg-gray-50 border-gray-300 text-gray-600')]">4 ЦЕНТА</button>
            <button @click="activePreset = '8c'" :class="['p-2 rounded text-xs font-bold border transition-colors', activePreset === '8c' ? (isDark ? 'bg-[#00e5ff] border-[#00e5ff] text-black' : 'bg-[#00e5ff] border-[#00e5ff] text-white') : (isDark ? 'bg-black border-zinc-800 text-gray-500' : 'bg-gray-50 border-gray-300 text-gray-600')]">8 ЦЕНТОВ</button>
          </div>
        </div>

        <div :class="['border rounded p-3 flex-1 overflow-y-auto custom-scrollbar', isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300 shadow-sm']">
          <h3 class="font-bold text-gray-500 text-[10px] mb-2 tracking-wider">ЛИНИИ ({{ currentEvent.sub_markets.length }})</h3>
          <div class="flex flex-col gap-1">
            <button 
              v-for="sub in currentEvent.sub_markets" :key="sub.condition_id"
              @click="connectToMarket(sub)"
              :class="['p-2 rounded text-left text-xs transition-colors border', activeSubMarket?.condition_id === sub.condition_id ? (isDark ? 'border-[#00e5ff] bg-[#00e5ff]/10 text-white' : 'border-[#00e5ff] bg-cyan-50 text-black font-bold') : (isDark ? 'border-transparent bg-black text-gray-400' : 'border-gray-200 bg-gray-50 text-gray-600')]"
            >
              <div class="whitespace-normal leading-tight break-words">{{ sub.question.replace('Winner of the match', 'Исход матча') }}</div>
            </button>
          </div>
        </div>
      </div>

      <div class="flex-1 relative flex flex-col min-w-[350px]">
        <div v-if="isConnecting" class="absolute inset-0 z-50 flex items-center justify-center backdrop-blur-sm rounded-lg" :class="isDark ? 'bg-black/80' : 'bg-white/80'">
          <span class="text-[#00e5ff] text-sm font-bold animate-pulse">СИНХРОНИЗАЦИЯ...</span>
        </div>
        <div v-if="!isConnecting" class="absolute top-10 right-4 z-50 text-[10px] text-gray-500 pointer-events-none opacity-50">Нажми [Space] для центровки</div>

        <OrderBook 
          ref="orderBookRef"
          v-if="activeSubMarket"
          :isDark="isDark"
          v-model:activeTeam="activeTeam"
          :team1Name="activeSubMarket.out1"
          :team2Name="activeSubMarket.out2"
          :rawBidsYes="rawBidsYes"
          :rawAsksYes="rawAsksYes"
          :rawBidsNo="rawBidsNo"
          :rawAsksNo="rawAsksNo"
          :openPositions="openPositions"
          :currentTokenId="activeTeam === 1 ? activeSubMarket.token_id_yes : activeSubMarket.token_id_no"
          @placeOrder="handlePlaceOrder"
        />
      </div>

      <div :class="['w-64 border rounded p-3 flex flex-col shrink-0', isDark ? 'bg-[#0a0a0a] border-zinc-800' : 'bg-white border-gray-300 shadow-sm']">
        <div class="flex justify-between items-center mb-2">
          <h3 class="font-bold text-gray-500 text-[10px] tracking-wider">ОТКРЫТЫЕ СДЕЛКИ</h3>
          <button @click="loadPositions" class="text-[10px] text-[#00e5ff] hover:underline">↻ Обновить</button>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scrollbar space-y-2 pr-1">
          <div v-if="openPositions.length === 0" class="text-center text-gray-500 text-xs mt-10">Нет сделок</div>
          <div v-for="pos in openPositions" :key="pos.order_id" :class="['border p-2 rounded', isDark ? 'bg-black border-zinc-800' : 'bg-gray-50 border-gray-200']">
            <div class="flex justify-between items-center mb-1">
              <span class="font-bold text-xs truncate max-w-[120px]">{{ getTeamNameFromToken(pos.token_id) }}</span>
              <span :class="['font-bold text-xs', pos.currentPnL >= 0 ? 'text-green-500' : 'text-red-500']">
                {{ pos.currentPnL > 0 ? '+' : '' }}${{ pos.currentPnL.toFixed(2) }}
              </span>
            </div>
            <div class="text-[10px] text-gray-500 flex justify-between mb-2">
              <span>Вход: {{ Math.round(pos.entry_price * 100) }}¢ ({{ pos.size.toFixed(1) }}шт)</span>
            </div>
            <button @click="panicSell(pos.order_id)" class="w-full bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white text-[10px] py-1 rounded transition-colors font-bold border border-red-500/30">
              СБРОС ПО РЫНКУ
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex-1 overflow-y-auto p-6">
      <div class="max-w-6xl mx-auto">
        <h2 class="text-2xl font-bold mb-6">Активные турниры</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="match in matches" :key="match.event_id" :class="['border p-4 rounded-lg flex flex-col justify-between h-40 transition-colors', isDark ? 'bg-[#0a0a0a] border-zinc-800 hover:border-zinc-600' : 'bg-white border-gray-300 hover:border-gray-400 shadow-sm']">
            <div>
              <span class="text-[10px] text-gray-500">{{ new Date(match.start_date).toLocaleDateString() }}</span>
              <h3 class="font-bold text-sm mt-1 line-clamp-2" :class="isDark ? 'text-white' : 'text-black'">{{ match.title }}</h3>
            </div>
            <div class="flex justify-between items-end mt-2">
              <div class="text-xs text-gray-500">Vol: <span class="font-bold" :class="isDark ? 'text-white' : 'text-black'">${{ formatVolume(match.total_volume) }}</span></div>
              <button @click="openEvent(match)" :class="['px-3 py-1.5 rounded text-xs font-bold transition-colors', isDark ? 'bg-[#00e5ff] text-black hover:bg-[#00b8cc]' : 'bg-[#00e5ff] text-white hover:bg-[#00b8cc] shadow-md']">
                ТОРГОВАТЬ
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import OrderBook from './Terminal/OrderBook.vue'

// --- STATE ---
const isDark = ref(true) // По умолчанию Грок-стиль
const matches = ref([])
const currentEvent = ref(null)
const activeSubMarket = ref(null)
const activeTeam = ref(1)
const isConnecting = ref(false)

const tradeSize = ref(5)
const tradingMode = ref('custom')
const tpOffset = ref(4)
const slOffset = ref(12)
const activePreset = ref('4c')

const openPositions = ref([])
const rawBidsYes = ref(new Map())
const rawAsksYes = ref(new Map())
const rawBidsNo = ref(new Map())
const rawAsksNo = ref(new Map())

const orderBookRef = ref(null)
let ws = null

const handleKeydown = (e) => {
  if (e.code === 'Space' && currentEvent.value && e.target.tagName !== 'INPUT') {
    e.preventDefault()
    orderBookRef.value?.scrollToSpread()
  }
}

const formatVolume = (val) => val >= 1000 ? (val / 1000).toFixed(1) + 'K' : Math.round(val)

const loadMarkets = async () => {
  const res = await fetch('/api/markets?game=Dota 2')
  const data = await res.json()
  // 🎯 ИСПРАВЛЕНИЕ: Сортировка по объему
  if (data.matches) matches.value = data.matches.sort((a, b) => b.total_volume - a.total_volume)
}

const loadPositions = async () => {
  const res = await fetch('/api/positions')
  const data = await res.json()
  if (data.success) {
    openPositions.value = data.positions.map(pos => {
      let diff = Math.round(pos.entry_price * 100) - Math.round(pos.entry_price * 100)
      return { ...pos, currentPnL: (diff / 100) * pos.size }
    })
  }
}

const getTeamNameFromToken = (tokenId) => {
  for (let match of matches.value) {
    for (let sub of match.sub_markets) {
      if (sub.token_id_yes === tokenId) return sub.out1
      if (sub.token_id_no === tokenId) return sub.out2
    }
  }
  return "Ордер"
}

const closeTerminal = () => {
  if (ws) { ws.close(); ws = null }
  currentEvent.value = null
  activeSubMarket.value = null
}

const openEvent = (match) => {
  currentEvent.value = match
  if (match.sub_markets.length > 0) connectToMarket(match.sub_markets[0])
}

const connectToMarket = (sub) => {
  activeSubMarket.value = sub
  if (ws) { ws.close(); ws = null }
  isConnecting.value = true
  const tokenYes = sub.token_id_yes.toLowerCase()
  const tokenNo = sub.token_id_no ? sub.token_id_no.toLowerCase() : null
  
  rawBidsYes.value.clear(); rawAsksYes.value.clear()
  rawBidsNo.value.clear(); rawAsksNo.value.clear()

  Promise.all([
    fetch(`https://clob.polymarket.com/book?token_id=${tokenYes}`).then(r=>r.json()),
    tokenNo ? fetch(`https://clob.polymarket.com/book?token_id=${tokenNo}`).then(r=>r.json()) : Promise.resolve({bids:[], asks:[]})
  ]).then(([dataYes, dataNo]) => {
    (dataYes.bids||[]).forEach(b => rawBidsYes.value.set(parseFloat(b.price), parseFloat(b.size)));
    (dataYes.asks||[]).forEach(a => rawAsksYes.value.set(parseFloat(a.price), parseFloat(a.size)));
    (dataNo.bids||[]).forEach(b => rawBidsNo.value.set(parseFloat(b.price), parseFloat(b.size)));
    (dataNo.asks||[]).forEach(a => rawAsksNo.value.set(parseFloat(a.price), parseFloat(a.size)));
    isConnecting.value = false
    nextTick(() => orderBookRef.value?.scrollToSpread())
  }).catch(() => { isConnecting.value = false })

  ws = new WebSocket(`wss://ws-subscriptions-clob.polymarket.com/ws/market`)
  ws.onopen = () => {
    let assets = [tokenYes]; if (tokenNo) assets.push(tokenNo)
    ws.send(JSON.stringify({ assets_ids: assets, type: "market" }))
  }
  ws.onmessage = (event) => {
    if (event.data === "PONG") return
    const data = JSON.parse(event.data)
    const events = Array.isArray(data) ? data : [data]

    events.forEach(ev => {
      const evToken = ev.asset_id ? ev.asset_id.toLowerCase() : null
      let bBook = evToken === tokenYes ? rawBidsYes.value : rawBidsNo.value
      let aBook = evToken === tokenYes ? rawAsksYes.value : rawAsksNo.value
      if (!bBook) return

      if (ev.event_type === "book") {
        bBook.clear(); aBook.clear();
        (ev.bids||[]).forEach(b => bBook.set(parseFloat(b.price), parseFloat(b.size)));
        (ev.asks||[]).forEach(a => aBook.set(parseFloat(a.price), parseFloat(a.size)));
      } else if (ev.event_type === "price_change") {
        const process = (arr, isBid) => {
          arr.forEach(i => {
            const p = parseFloat(i.price), s = parseFloat(i.size)
            if (s === 0) (isBid ? bBook : aBook).delete(p); else (isBid ? bBook : aBook).set(p, s)
          })
        }
        if (ev.changes) {
          process(ev.changes.filter(c=>c.side==="BUY"), true)
          process(ev.changes.filter(c=>c.side==="SELL"), false)
        } else {
          if (ev.bids) process(ev.bids, true)
          if (ev.asks) process(ev.asks, false)
        }
      }
    })
    rawBidsYes.value = new Map(rawBidsYes.value); rawAsksYes.value = new Map(rawAsksYes.value)
    rawBidsNo.value = new Map(rawBidsNo.value); rawAsksNo.value = new Map(rawAsksNo.value)
  }
  let pingInt = setInterval(() => { if (ws?.readyState === WebSocket.OPEN) ws.send("PING"); else clearInterval(pingInt) }, 10000)
  ws.onclose = () => clearInterval(pingInt)
}

const handlePlaceOrder = async (side, priceCents) => {
  if (side === 'SELL') return
  const targetToken = activeTeam.value === 1 ? activeSubMarket.value.token_id_yes : activeSubMarket.value.token_id_no
  
  let finalTpCents = null
  let finalStrategy = 'custom'

  if (tradingMode.value === 'custom') {
    finalTpCents = tpOffset.value > 0 ? priceCents + tpOffset.value : null
  } else {
    finalStrategy = activePreset.value
    if (activePreset.value === '4c') finalTpCents = priceCents + 4
    if (activePreset.value === '8c') finalTpCents = priceCents + 8
  }

  const reqBody = {
    token_id: targetToken,
    condition_id: activeSubMarket.value.condition_id,
    price: priceCents / 100.0,
    side: "BUY", 
    bankroll: tradeSize.value, 
    risk_percent: 100, 
    is_custom_limit: true,
    take_profit_price: finalTpCents ? Math.min(0.99, finalTpCents / 100.0) : null,
    strategy: finalStrategy
  }
  
  try {
    const res = await fetch('/api/trade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(reqBody) })
    if ((await res.json()).success) loadPositions()
  } catch (e) {}
}

const panicSell = async (orderId) => {
  try {
    const res = await fetch('/api/panic_sell', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: orderId }) })
    if ((await res.json()).success) loadPositions()
  } catch(e) {}
}

onMounted(() => { 
  window.addEventListener('keydown', handleKeydown)
  loadMarkets(); loadPositions(); setInterval(loadPositions, 3000) 
})
onUnmounted(() => { 
  window.removeEventListener('keydown', handleKeydown)
  if (ws) ws.close() 
})
</script>