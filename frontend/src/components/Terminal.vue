<template>
  <div class="flex h-screen w-full bg-[#000000] text-gray-200 font-sans overflow-hidden">
    <Sidebar @home="closeTerminal" />

    <SubcategoryNav v-if="!currentEvent" />

    <main class="flex-1 flex flex-col min-w-0 bg-gradient-to-br from-[#000000] via-[#030303] to-[#001012]">
      <FavoritesBar :active-event-id="currentEvent?.event_id" @open="openEvent" />

      <div v-if="currentEvent" class="flex-1 flex overflow-hidden p-3 gap-3">
        <TradingPanel
          :event="currentEvent"
          :active-sub="activeSubMarket"
          @close="closeTerminal"
          @select-sub="openSubMarket"
          @run-preset="handleRunPreset"
        />

        <div class="flex-1 relative flex flex-col min-w-[350px]">
          <div
            v-if="isConnecting"
            class="absolute inset-0 z-50 flex items-center justify-center backdrop-blur-sm bg-[#050505]/80 rounded-2xl border border-zinc-800"
          >
            <span class="text-[#00e5ff] text-sm font-bold font-mono animate-pulse tracking-widest uppercase">
              Connecting to L2 Stream...
            </span>
          </div>

          <div
            v-if="activeSubMarket"
            class="mb-3 flex items-center justify-between border-b border-zinc-800/60 pb-3 px-2"
          >
            <h2
              class="text-base font-bold truncate pr-4 text-gray-100 tracking-tight"
              :title="activeSubMarket.question"
            >
              {{ activeSubMarket.question }}
            </h2>
            <div class="flex items-center gap-2 shrink-0">
              <div
                class="px-2 py-1 rounded-md text-[10px] font-mono font-bold border border-zinc-700 text-zinc-400"
                title="Book update velocity"
              >
                {{ velocity }}/s
              </div>
              <div
                :class="[
                  'px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border transition-colors whitespace-nowrap',
                  spreadBadgeClass,
                ]"
              >
                SPREAD: {{ activeSpreadCents }}¢
              </div>
            </div>
          </div>

          <OrderBook
            ref="orderBookRef"
            v-if="activeSubMarket"
            :isDark="true"
            v-model:activeTeam="activeTeam"
            :team1Name="activeSubMarket.out1"
            :team2Name="activeSubMarket.out2"
            :ladderYes="ladderYes"
            :ladderNo="ladderNo"
            :currentTokenId="activeTeam === 1 ? activeSubMarket.token_id_yes : activeSubMarket.token_id_no"
            :midPrice="activeTeam === 1 ? midYes : midNo"
            :imbalance="activeTeam === 1 ? imbalanceYes : imbalanceNo"
            :tape="activeTeam === 1 ? tapeYes : tapeNo"
            :velocity="velocity"
            @placeOrder="handlePlaceOrder"
          />
        </div>

        <PositionsPanel :positions="livePositions" @panic="executePanicSell" />
      </div>

      <MarketGrid v-else @open="openEvent" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useToast } from 'vue-toastification'

import OrderBook from './Terminal/OrderBook.vue'
import Sidebar from './Terminal/Sidebar.vue'
import SubcategoryNav from './Terminal/SubcategoryNav.vue'
import FavoritesBar from './Terminal/FavoritesBar.vue'
import MarketGrid from './Terminal/MarketGrid.vue'
import TradingPanel from './Terminal/TradingPanel.vue'
import PositionsPanel from './Terminal/PositionsPanel.vue'

import { useMarketStore } from '../store/marketStore'
import { useOrderBook } from '../composables/useOrderBook'
import { tradeApi } from '../api/tradeService'

const toast = useToast()
const marketStore = useMarketStore()

const {
  ladderYes,
  ladderNo,
  spreadYes,
  spreadNo,
  bestBidYes,
  bestAskYes,
  bestBidNo,
  bestAskNo,
  midYes,
  midNo,
  imbalanceYes,
  imbalanceNo,
  tapeYes,
  tapeNo,
  velocity,
  isConnecting,
  connectToMarket,
  disconnect,
} = useOrderBook()

const currentEvent = ref(null)
const activeSubMarket = ref(null)
const activeTeam = ref(1)
const orderBookRef = ref(null)
let positionsTimer = null

const activeSpreadCents = computed(() => {
  const sp = activeTeam.value === 1 ? spreadYes.value : spreadNo.value
  return Math.round(sp * 100)
})

const spreadBadgeClass = computed(() => {
  const cents = activeSpreadCents.value
  if (cents <= 2) return 'bg-[#00e5ff]/10 text-[#00e5ff] border-[#00e5ff]/30'
  if (cents <= 5) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
  return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
})

const livePositions = computed(() =>
  marketStore.openPositions.map((pos) => {
    if (['CLOSED_TP', 'CLOSED_SL', 'RESOLVED'].includes(pos.status)) {
      const exitP = pos.exit_price || pos.entry_price
      return { ...pos, liveDiff: Math.round((exitP - pos.entry_price) * 100) }
    }
    let currentMarketPrice = pos.entry_price
    if (activeSubMarket.value) {
      if (pos.token_id === activeSubMarket.value.token_id_yes) {
        currentMarketPrice = bestBidYes.value
      } else if (pos.token_id === activeSubMarket.value.token_id_no) {
        currentMarketPrice = bestBidNo.value
      }
    }
    return {
      ...pos,
      liveDiff: Math.round((currentMarketPrice - pos.entry_price) * 100),
      currentMarketPrice,
    }
  })
)

const currentBestAskCents = () => {
  const ask = activeTeam.value === 1 ? bestAskYes.value : bestAskNo.value
  if (!ask || ask <= 0) return 0
  return Math.round(ask * 100)
}

const handleKeydown = (e) => {
  if (e.code === 'Space' && currentEvent.value && e.target.tagName !== 'INPUT') {
    e.preventDefault()
    orderBookRef.value?.scrollToSpread()
  }
}

const closeTerminal = () => {
  disconnect()
  currentEvent.value = null
  activeSubMarket.value = null
}

const openEvent = (match) => {
  currentEvent.value = match
  if (match.sub_markets?.length) openSubMarket(match.sub_markets[0])
}

const openSubMarket = (sub) => {
  activeSubMarket.value = sub
  connectToMarket(sub, () => {
    nextTick(() => orderBookRef.value?.scrollToSpread())
  })
}

/**
 * Build and POST /order. Shared by ladder clicks and Fast presets.
 */
const submitBuyOrder = async ({
  priceCents,
  strategy,
  riskPercent,
  takeProfitPrice,
  stopLossPrice,
  bankroll,
}) => {
  if (!activeSubMarket.value) return
  if (!priceCents || priceCents < 1 || priceCents > 99) {
    toast.error('❌ No valid ask price')
    return
  }

  const targetToken =
    activeTeam.value === 1
      ? activeSubMarket.value.token_id_yes
      : activeSubMarket.value.token_id_no

  const reqBody = {
    token_id: targetToken,
    condition_id: activeSubMarket.value.condition_id,
    price: priceCents / 100.0,
    side: 'BUY',
    bankroll: Number(bankroll),
    risk_percent: Number(riskPercent),
    is_custom_limit: true,
    take_profit_price: takeProfitPrice,
    stop_loss_price: stopLossPrice,
    strategy,
  }

  try {
    toast.info('Transmitting order...')
    const data = await tradeApi.placeOrder(reqBody)
    if (data.success) {
      toast.success(`✅ FILLED ${priceCents}¢ · ${strategy}`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ REJECTED: ${data.error}`)
    }
  } catch (e) {
    toast.error(`❌ ${e.message || 'TIMEOUT: Node Unreachable'}`)
  }
}

const handlePlaceOrder = async (side, priceCents) => {
  if (side === 'SELL') return

  let finalTpCents = null
  let finalSlCents = null
  let finalStrategy = 'custom'
  let riskPercent = 100
  let bankroll = Number(marketStore.tradeSize)

  if (marketStore.tradingMode === 'custom') {
    finalTpCents = marketStore.tpOffset > 0 ? priceCents + Number(marketStore.tpOffset) : null
    finalSlCents = marketStore.slOffset > 0 ? priceCents - Number(marketStore.slOffset) : null
  } else {
    // Fast mode ladder click uses last active preset (defaults to rebound-like offsets)
    const preset = marketStore.activePreset || 'rebound'
    finalStrategy = preset
    if (preset === 'rebound') {
      riskPercent = 40
      finalTpCents = priceCents + 3
      finalSlCents = priceCents - 5
    } else if (preset === 'partial') {
      riskPercent = 100
      finalTpCents = priceCents + 3 // backend expands to dual TP
      finalSlCents = priceCents - 4
    } else if (preset === 'result') {
      riskPercent = 100
      bankroll = Math.max(Number(marketStore.tradeSize) * 0.05, 5)
      finalTpCents = null
      finalSlCents = Math.round(priceCents * 0.5) // entry * 0.5 in cents
    } else if (preset === 'momentum') {
      riskPercent = 60
      finalTpCents = priceCents + 6
      finalSlCents = priceCents - 3
    } else {
      // legacy 4c / 8c
      finalTpCents = priceCents + (preset === '4c' ? 4 : 8)
      finalSlCents = priceCents - 12
    }
  }

  await submitBuyOrder({
    priceCents,
    strategy: finalStrategy,
    riskPercent,
    bankroll,
    takeProfitPrice: finalTpCents != null ? Math.min(0.99, finalTpCents / 100.0) : null,
    stopLossPrice: finalSlCents != null ? Math.max(0.01, finalSlCents / 100.0) : null,
  })
}

/** One-tap preset from TradingPanel — override fields already applied; fire at best ask. */
const handleRunPreset = async (cfg) => {
  const priceCents = currentBestAskCents()
  if (!priceCents) {
    toast.error('❌ Wait for book (no best ask)')
    return
  }

  let bankroll = Number(marketStore.tradeSize)
  let riskPercent = cfg.riskPercent != null ? cfg.riskPercent : 100
  let takeProfitPrice = null
  let stopLossPrice = null

  if (cfg.resultHold || cfg.strategy === 'result') {
    // Size = max(5% of bankroll, $5)
    bankroll = Math.max(Number(marketStore.tradeSize) * 0.05, 5)
    riskPercent = 100
    takeProfitPrice = null
    stopLossPrice = Math.max(0.01, Math.round((priceCents / 100.0) * 0.5 * 100) / 100)
  } else {
    if (cfg.tpOffsetCents != null) {
      takeProfitPrice = Math.min(0.99, (priceCents + Number(cfg.tpOffsetCents)) / 100.0)
    }
    if (cfg.slOffsetCents != null) {
      stopLossPrice = Math.max(0.01, (priceCents - Number(cfg.slOffsetCents)) / 100.0)
    }
  }

  await submitBuyOrder({
    priceCents,
    strategy: cfg.strategy,
    riskPercent,
    bankroll,
    takeProfitPrice,
    stopLossPrice,
  })
}

const executePanicSell = async (orderId) => {
  try {
    toast.warning('⚡ Market Dump Initiation...')
    const data = await tradeApi.panicSell(orderId)
    if (data.success) {
      toast.success(`✅ ${data.message}`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ ERROR: ${data.error}`)
    }
  } catch (e) {
    toast.error(`❌ ${e.message || 'TIMEOUT: Node Unreachable'}`)
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  marketStore.loadMatches()
  marketStore.loadPositions()
  positionsTimer = setInterval(() => marketStore.loadPositions(), 3000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (positionsTimer) clearInterval(positionsTimer)
  disconnect()
})
</script>

<style>
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
