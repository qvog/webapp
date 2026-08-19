<template>
  <div class="flex flex-1 min-w-0 h-full overflow-hidden" ref="terminalRoot">
    <SubcategoryNav v-if="!currentEvent" />

    <main class="flex-1 flex flex-col min-w-0 bg-gradient-to-br from-[#000000] via-[#030303] to-[#001012]">
      <FavoritesBar :active-event-id="currentEvent?.event_id" @open="openEvent" />

      <div v-if="currentEvent" class="flex-1 flex overflow-hidden p-3 gap-3">
        <TradingPanel
          ref="tradingPanelRef"
          :event="currentEvent"
          :active-sub="activeSubMarket"
          @close="closeTerminal"
          @select-sub="openSubMarket"
        />


        <div class="flex-1 relative flex flex-col min-w-[520px]">
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
            <div class="flex items-center gap-2 flex-wrap justify-end">
              <div
                :class="[
                  'px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border transition-colors whitespace-nowrap',
                  strategyBadgeClass,
                ]"
              >
                {{ strategyLabel }}
              </div>
              <div
                class="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border whitespace-nowrap bg-[#00e5ff]/10 text-[#00e5ff] border-[#00e5ff]/30"
                :title="(activeSubMarket.out1 || 'YES') + ' spread'"
              >
                {{ activeSubMarket.out1 || 'YES' }}: {{ spreadYesCents }}¢
              </div>
              <div
                class="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border whitespace-nowrap bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
                :title="(activeSubMarket.out2 || 'NO') + ' spread'"
              >
                {{ activeSubMarket.out2 || 'NO' }}: {{ spreadNoCents }}¢
              </div>
            </div>
          </div>

          <OrderBook
            ref="orderBookRef"
            v-if="activeSubMarket"
            :isDark="true"
            :team1Name="activeSubMarket.out1"
            :team2Name="activeSubMarket.out2"
            :ladderYes="ladderYes"
            :ladderNo="ladderNo"
            :tokenIdYes="activeSubMarket.token_id_yes"
            :tokenIdNo="activeSubMarket.token_id_no"
            :imbalanceYes="imbalanceYes"
            :imbalanceNo="imbalanceNo"
            :maxBidSizeYes="maxBidSizeYes"
            :maxAskSizeYes="maxAskSizeYes"
            :maxBidSizeNo="maxBidSizeNo"
            :maxAskSizeNo="maxAskSizeNo"
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
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { useToast } from 'vue-toastification'

import OrderBook from './Terminal/OrderBook.vue'
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
  bestBidNo,
  bestAskYes,
  bestAskNo,
  imbalanceYes,
  imbalanceNo,
  maxBidSizeYes,
  maxAskSizeYes,
  maxBidSizeNo,
  maxAskSizeNo,
  isConnecting,
  connectToMarket,
  disconnect,
} = useOrderBook()

/** Open terminal event — sourced from Pinia so logo / global sidebar can navigate. */
const currentEvent = computed(() => marketStore.activeEvent)
const activeSubMarket = ref(null)
const activeTeam = ref(1)
const orderBookRef = ref(null)
const tradingPanelRef = ref(null)
const terminalRoot = ref(null)
let positionsTimer = null

const STRATEGY_LABELS = {
  custom: 'CUSTOM',
  fix: 'FIX',
  draft_win: 'DRAFT WIN',
  short_range: 'SHORT RANGE',
  high_range: 'HIGH RANGE',
}

const strategyLabel = computed(
  () => STRATEGY_LABELS[marketStore.activeStrategy] || marketStore.activeStrategy?.toUpperCase()
)

const strategyBadgeClass = computed(() => {
  if (marketStore.activeStrategy === 'custom') {
    return 'bg-zinc-800/60 text-zinc-400 border-zinc-700'
  }
  return 'bg-[#00e5ff]/10 text-[#00e5ff] border-[#00e5ff]/30'
})

const spreadYesCents = computed(() => Math.round(spreadYes.value * 100))
const spreadNoCents = computed(() => Math.round(spreadNo.value * 100))

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

const activeTokenId = computed(() => {
  if (!activeSubMarket.value) return null
  return activeTeam.value === 1
    ? activeSubMarket.value.token_id_yes
    : activeSubMarket.value.token_id_no
})

const currentMarketPrice = computed(() => {
  // Prefer best ask for market-like entry buys
  const ask = activeTeam.value === 1 ? bestAskYes.value : bestAskNo.value
  const bid = activeTeam.value === 1 ? bestBidYes.value : bestBidNo.value
  const p = Number(ask) > 0 && Number(ask) < 1 ? Number(ask) : Number(bid)
  return Math.round(p * 100) / 100
})

function focusTerminal() {
  tradingPanelRef.value?.focusTerminal?.()
  terminalRoot.value?.focus?.()
}

function applyHotkeyPreset(strategy, volume) {
  marketStore.activeStrategy = strategy
  marketStore.activePreset = strategy
  marketStore.tradingMode = 'presets'
  marketStore.tradeSize = volume
  tradingPanelRef.value?.applyStrategy?.(strategy, volume)
  focusTerminal()
  toast.info(`${STRATEGY_LABELS[strategy] || strategy} · vol $${volume}`, { timeout: 1500 })
}

/**
 * Build POST /api/order payload.
 * For presets, TP/SL are left null — backend resolves levels.
 * Fix: sends relative +¢ offset in dollars (e.g. 0.12); backend does entry + offset, cap 0.99.
 * All orders are strict limit at the provided price.
 */
function buildOrderPayload(priceDollars, strategyOverride = null) {
  const strategy = strategyOverride || marketStore.activeStrategy || 'custom'
  const targetToken = activeTokenId.value
  const price = Math.round(Number(priceDollars) * 100) / 100

  let takeProfit = null
  let stopLoss = null

  if (strategy === 'custom') {
    const priceCents = Math.round(price * 100)
    const tpOff = Number(marketStore.tpOffset)
    const slOff = Number(marketStore.slOffset)
    if (tpOff > 0) takeProfit = Math.min(0.99, Math.round((priceCents + tpOff)) / 100)
    if (slOff > 0) stopLoss = Math.max(0.01, Math.round((priceCents - slOff)) / 100)
  } else if (strategy === 'fix') {
    // Relative offset in dollars for backend: input 12 → 0.12 (+12¢)
    const tpOffCents = Number(marketStore.fixTpCents)
    if (tpOffCents > 0 && tpOffCents < 100) {
      takeProfit = Math.round(tpOffCents) / 100
    }
    stopLoss = null
  }

  return {
    token_id: targetToken,
    condition_id: activeSubMarket.value.condition_id,
    price,
    side: 'BUY',
    bankroll: Number(marketStore.tradeSize),
    risk_percent: 100,
    is_custom_limit: true,
    take_profit_price: takeProfit,
    stop_loss_price: stopLoss,
    strategy,
  }
}

const handleKeydown = (e) => {
  // Ctrl+Z / Meta+Z → undo last placed order (panic_sell)
  if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z') && !e.shiftKey) {
    // Don't hijack undo inside text fields
    const tag = (e.target && e.target.tagName) || ''
    if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target?.isContentEditable) {
      return
    }
    e.preventDefault()
    e.stopPropagation()
    executeUndoLastOrder()
    return
  }

  // Space → scroll to spread (existing)
  if (
    e.code === 'Space' &&
    currentEvent.value &&
    e.target.tagName !== 'INPUT' &&
    e.target.tagName !== 'SELECT' &&
    e.target.tagName !== 'TEXTAREA'
  ) {
    e.preventDefault()
    orderBookRef.value?.scrollToSpread()
    return
  }

  // Global trading hotkeys — F1–F3 presets, F10 flatten
  const key = e.key
  const isTradeHotkey = ['F1', 'F2', 'F3', 'F10'].includes(key)
  if (!isTradeHotkey) return

  e.preventDefault()
  e.stopPropagation()

  if (key === 'F1') {
    applyHotkeyPreset('draft_win', 10)
    return
  }
  if (key === 'F2') {
    applyHotkeyPreset('short_range', 20)
    return
  }
  if (key === 'F3') {
    applyHotkeyPreset('high_range', 20)
    return
  }
  if (key === 'F10') {
    executeFlatten()
  }
}

const closeTerminal = () => {
  disconnect()
  activeSubMarket.value = null
  marketStore.closeActiveMarket()
}

const openEvent = (match) => {
  if (!match) return
  marketStore.setActiveMarket(match)
}

/**
 * Pick sub-market (and YES/NO side) for a focus token, else first sub.
 * @returns {{ sub: object|null, team: 1|2 }}
 */
function resolveFocusForEvent(match, focusTokenId) {
  const subs = match?.sub_markets || []
  if (!subs.length) return { sub: null, team: 1 }
  if (focusTokenId) {
    const tid = String(focusTokenId)
    for (const sub of subs) {
      const yes = sub.token_id_yes != null ? String(sub.token_id_yes) : ''
      const no = sub.token_id_no != null ? String(sub.token_id_no) : ''
      if (yes === tid) return { sub, team: 1 }
      if (no === tid) return { sub, team: 2 }
    }
  }
  return { sub: subs[0], team: 1 }
}

const openSubMarket = (sub, team = null) => {
  if (!sub) {
    activeSubMarket.value = null
    disconnect()
    return
  }
  activeSubMarket.value = sub
  if (team === 1 || team === 2) activeTeam.value = team
  connectToMarket(sub, () => {
    nextTick(() => orderBookRef.value?.scrollToSpread())
  })
}

/** Sync local orderbook whenever Pinia opens/refocuses a market. */
watch(
  () => [marketStore.activeEvent, marketStore.focusRequestId],
  ([match]) => {
    if (!match) {
      disconnect()
      activeSubMarket.value = null
      return
    }
    const focusToken = marketStore.consumePendingFocusTokenId()
    const { sub, team } = resolveFocusForEvent(match, focusToken)
    openSubMarket(sub, team)
  },
  { immediate: true }
)

const handlePlaceOrder = async (side, priceCents, team = null) => {
  if (side === 'SELL') return
  if (!activeSubMarket.value) return

  // Dual book: clicking a column selects that outcome for this order / flatten
  if (team === 1 || team === 2) activeTeam.value = team

  const price = Math.round(Number(priceCents)) / 100.0
  if (!price || price < 0.01 || price > 0.99) {
    toast.error('Invalid limit price')
    return
  }

  // Fix strategy requires a relative +¢ TP offset before placing
  if (marketStore.activeStrategy === 'fix') {
    const tpCents = Number(marketStore.fixTpCents)
    if (!tpCents || tpCents < 1 || tpCents > 98) {
      toast.warning('Fix strategy: set TP Offset (+¢) first')
      return
    }
  }

  const reqBody = buildOrderPayload(price)

  try {
    toast.info('Transmitting order...')
    const data = await tradeApi.placeOrder(reqBody)
    if (data.success) {
      if (data.order_id) marketStore.setLastPlacedOrderId(data.order_id)
      toast.success(`✅ LIMIT ${Math.round(price * 100)}¢ · ${reqBody.strategy}`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ REJECTED: ${data.error}`)
    }
  } catch (e) {
    toast.error(`❌ ${e.message || 'TIMEOUT: Node Unreachable'}`)
  }
}

const executeUndoLastOrder = async () => {
  if (!marketStore.lastPlacedOrderId) {
    toast.info('No last order to undo', { timeout: 1200 })
    return
  }
  try {
    toast.warning('↩ Undo last order...')
    const data = await marketStore.undoLastOrder()
    if (data.success) {
      toast.success('Last order canceled')
    } else if (!data.skipped) {
      toast.error(`❌ Undo: ${data.error}`)
    }
  } catch (e) {
    toast.error(`❌ ${e.message || 'Undo failed'}`)
  }
}

const executeFlatten = async () => {
  const tokenId = activeTokenId.value
  if (!tokenId) {
    toast.warning('No active token for Flatten (F10)')
    return
  }
  try {
    toast.warning('⚡ FLATTEN — closing all OPEN on token...')
    const data = await tradeApi.flatten(tokenId)
    if (data.success) {
      toast.success(`✅ ${data.message || 'Flatten done'}`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ FLATTEN: ${data.error}`)
    }
  } catch (e) {
    toast.error(`❌ ${e.message || 'TIMEOUT: Node Unreachable'}`)
  }
}

const executePanicSell = async (orderId) => {
  try {
    toast.warning('⚡ Market Dump Initiation...')
    const data = await tradeApi.panicSell(orderId)
    if (data.success) {
      if (marketStore.lastPlacedOrderId === orderId) {
        marketStore.clearLastPlacedOrderId()
      }
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
  // Capture phase so F-keys win over browser chrome where possible
  window.addEventListener('keydown', handleKeydown, true)
  marketStore.loadMatches()
  // Positions are also polled by GlobalPositionsSidebar; keep a local sync for live PnL
  marketStore.loadPositions()
  positionsTimer = setInterval(() => marketStore.loadPositions(), 3000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown, true)
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
