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
            <div class="flex items-center gap-2">
              <div
                :class="[
                  'px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border transition-colors whitespace-nowrap',
                  strategyBadgeClass,
                ]"
              >
                {{ strategyLabel }}
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
            :imbalancePercent="activeImbalance"
            :maxBidSize="activeMaxBidSize"
            :maxAskSize="activeMaxAskSize"
            @placeOrder="handlePlaceOrder"
          />
        </div>

        <PositionsPanel :positions="livePositions" @panic="executePanicSell" />
      </div>

      <MarketGrid v-else @open="openEvent" />
    </main>

    <!-- F5 All-In Half confirmation modal -->
    <div
      v-if="showAllInModal"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm"
      @keydown.esc="cancelAllIn"
    >
      <div
        class="max-w-md w-full mx-4 border border-indigo-500/40 rounded-2xl bg-[#0a0a0a] p-6 shadow-[0_0_40px_rgba(99,102,241,0.25)]"
        role="dialog"
        aria-modal="true"
      >
        <p class="text-sm text-gray-200 leading-relaxed font-medium mb-6">
          Ты уверен что это не эмоция и это тот самый момент и выбор да или нет?
        </p>
        <div class="flex gap-3">
          <button
            @click="confirmAllIn"
            :disabled="allInBusy"
            class="flex-1 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-black font-bold text-sm uppercase tracking-wider transition-colors disabled:opacity-50"
          >
            Да
          </button>
          <button
            @click="cancelAllIn"
            :disabled="allInBusy"
            class="flex-1 py-2.5 rounded-xl border border-zinc-700 text-zinc-300 hover:bg-zinc-900 font-bold text-sm uppercase tracking-wider transition-colors disabled:opacity-50"
          >
            Нет
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
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

const currentEvent = ref(null)
const activeSubMarket = ref(null)
const activeTeam = ref(1)
const orderBookRef = ref(null)
const tradingPanelRef = ref(null)
const terminalRoot = ref(null)
const showAllInModal = ref(false)
const allInBusy = ref(false)
let positionsTimer = null

const STRATEGY_LABELS = {
  custom: 'CUSTOM',
  draft_early: 'DRAFT EARLY',
  draft_win: 'DRAFT WIN',
  short_range: 'SHORT RANGE',
  high_range: 'HIGH RANGE',
  all_in_half: 'ALL IN HALF',
}

const strategyLabel = computed(
  () => STRATEGY_LABELS[marketStore.activeStrategy] || marketStore.activeStrategy?.toUpperCase()
)

const strategyBadgeClass = computed(() => {
  if (marketStore.activeStrategy === 'all_in_half') {
    return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/40'
  }
  if (marketStore.activeStrategy === 'custom') {
    return 'bg-zinc-800/60 text-zinc-400 border-zinc-700'
  }
  return 'bg-[#00e5ff]/10 text-[#00e5ff] border-[#00e5ff]/30'
})

const activeSpreadCents = computed(() => {
  const sp = activeTeam.value === 1 ? spreadYes.value : spreadNo.value
  return Math.round(sp * 100)
})

const activeImbalance = computed(() =>
  activeTeam.value === 1 ? imbalanceYes.value : imbalanceNo.value
)
const activeMaxBidSize = computed(() =>
  activeTeam.value === 1 ? maxBidSizeYes.value : maxBidSizeNo.value
)
const activeMaxAskSize = computed(() =>
  activeTeam.value === 1 ? maxAskSizeYes.value : maxAskSizeNo.value
)

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
  if (e.code === 'Space' && currentEvent.value && e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT' && e.target.tagName !== 'TEXTAREA') {
    e.preventDefault()
    orderBookRef.value?.scrollToSpread()
    return
  }

  // Global trading hotkeys — always prevent browser default for F1–F5 / F10
  const key = e.key
  const isTradeHotkey = ['F1', 'F2', 'F3', 'F4', 'F5', 'F10'].includes(key)
  if (!isTradeHotkey) return

  e.preventDefault()
  e.stopPropagation()

  // Modal open: only Esc / buttons (handled elsewhere)
  if (showAllInModal.value) return

  if (key === 'F1') {
    applyHotkeyPreset('draft_early', 10)
    return
  }
  if (key === 'F2') {
    applyHotkeyPreset('draft_win', 10)
    return
  }
  if (key === 'F3') {
    applyHotkeyPreset('short_range', 20)
    return
  }
  if (key === 'F4') {
    applyHotkeyPreset('high_range', 20)
    return
  }
  if (key === 'F5') {
    // Immediate confirmation modal for all-in half
    if (!currentEvent.value || !activeSubMarket.value) {
      toast.warning('Открой рынок перед All In Half')
      return
    }
    marketStore.activeStrategy = 'all_in_half'
    marketStore.activePreset = 'all_in_half'
    marketStore.tradingMode = 'presets'
    showAllInModal.value = true
    return
  }
  if (key === 'F10') {
    executeFlatten()
  }
}

const closeTerminal = () => {
  disconnect()
  currentEvent.value = null
  activeSubMarket.value = null
  showAllInModal.value = false
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

const handlePlaceOrder = async (side, priceCents) => {
  if (side === 'SELL') return
  if (!activeSubMarket.value) return

  // F5 path uses modal; if user clicks book with all_in_half selected, still confirm
  if (marketStore.activeStrategy === 'all_in_half') {
    showAllInModal.value = true
    return
  }

  const price = priceCents / 100.0
  const reqBody = buildOrderPayload(price)

  try {
    toast.info('Transmitting order...')
    const data = await tradeApi.placeOrder(reqBody)
    if (data.success) {
      if (data.order_id) marketStore.setLastPlacedOrderId(data.order_id)
      toast.success(`✅ FILLED ${priceCents}¢ · ${reqBody.strategy}`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ REJECTED: ${data.error}`)
    }
  } catch (e) {
    toast.error(`❌ ${e.message || 'TIMEOUT: Node Unreachable'}`)
  }
}

const confirmAllIn = async () => {
  if (allInBusy.value) return
  if (!activeSubMarket.value) {
    toast.error('Нет активного маркета')
    showAllInModal.value = false
    return
  }

  const price = currentMarketPrice.value
  if (!price || price < 0.01 || price > 0.99) {
    toast.error('Нет валидной рыночной цены')
    return
  }

  allInBusy.value = true
  try {
    toast.warning('⚡ ALL IN HALF — transmitting...')
    const reqBody = buildOrderPayload(price, 'all_in_half')
    // Ensure bankroll is current volume; backend takes 50%
    const data = await tradeApi.placeOrder(reqBody)
    if (data.success) {
      if (data.order_id) marketStore.setLastPlacedOrderId(data.order_id)
      toast.success(`✅ ALL IN HALF @ ${Math.round(price * 100)}¢`)
      marketStore.loadPositions()
      showAllInModal.value = false
    } else {
      toast.error(`❌ REJECTED: ${data.error}`)
    }
  } catch (e) {
    toast.error(`❌ ${e.message || 'TIMEOUT: Node Unreachable'}`)
  } finally {
    allInBusy.value = false
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

const cancelAllIn = () => {
  if (allInBusy.value) return
  showAllInModal.value = false
}

const executeFlatten = async () => {
  const tokenId = activeTokenId.value
  if (!tokenId) {
    toast.warning('Нет активного токена для Flatten (F10)')
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
