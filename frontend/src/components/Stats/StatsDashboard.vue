<template>
  <main
    class="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-gradient-to-br from-[#000000] via-[#030303] to-[#001012]"
  >
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-zinc-900 shrink-0">
      <div>
        <h1 class="text-lg font-black tracking-widest text-white uppercase">
          Statistics <span class="text-emerald-400">/ PnL</span>
        </h1>
        <p class="text-[10px] text-zinc-500 font-mono uppercase tracking-wider mt-0.5">
          Closed trades · read-only analytics
        </p>
      </div>
      <button
        @click="refresh"
        :disabled="loading"
        class="px-3 py-1.5 rounded-lg border border-zinc-800 bg-[#0a0a0a] text-[11px] font-mono font-bold uppercase tracking-wider text-[#00e5ff] hover:border-[#00e5ff]/40 hover:bg-[#00e5ff]/5 transition-colors disabled:opacity-40"
      >
        {{ loading ? '… Syncing' : '↻ Refresh' }}
      </button>
    </header>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
      <!-- Error banner -->
      <div
        v-if="error"
        class="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 font-mono"
      >
        {{ error }}
      </div>

      <!-- Top row: overall metric cards -->
      <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div class="rounded-2xl border border-zinc-800/60 bg-[#0a0a0a]/80 backdrop-blur-sm p-5 shadow-lg">
          <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Overall PnL</p>
          <p
            :class="[
              'text-3xl font-black font-mono tracking-tight',
              overallPnl > 0 ? 'text-emerald-400' : overallPnl < 0 ? 'text-red-400' : 'text-zinc-300',
            ]"
          >
            {{ formatSigned(overallPnl) }}
          </p>
          <p class="text-[10px] text-zinc-600 font-mono mt-1">shares · (exit − entry) × size</p>
        </div>

        <div class="rounded-2xl border border-zinc-800/60 bg-[#0a0a0a]/80 backdrop-blur-sm p-5 shadow-lg">
          <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Total Trades</p>
          <p class="text-3xl font-black font-mono text-white tracking-tight">
            {{ overall.total_trades ?? 0 }}
          </p>
          <p class="text-[10px] text-zinc-600 font-mono mt-1">
            {{ overall.wins ?? 0 }}W · {{ overall.losses ?? 0 }}L
          </p>
        </div>

        <div class="rounded-2xl border border-zinc-800/60 bg-[#0a0a0a]/80 backdrop-blur-sm p-5 shadow-lg">
          <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Overall Winrate</p>
          <p class="text-3xl font-black font-mono text-[#00e5ff] tracking-tight">
            {{ formatPct(overall.winrate) }}
          </p>
          <div class="mt-3 h-1.5 w-full rounded-full bg-zinc-900 overflow-hidden flex">
            <div
              class="h-full bg-emerald-500 transition-all duration-500"
              :style="{ width: clampPct(overall.winrate) + '%' }"
            />
            <div
              class="h-full bg-red-500/80 transition-all duration-500"
              :style="{ width: clampPct(100 - (overall.winrate || 0)) + '%' }"
            />
          </div>
        </div>

        <div class="rounded-2xl border border-zinc-800/60 bg-[#0a0a0a]/80 backdrop-blur-sm p-5 shadow-lg">
          <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Profit Factor</p>
          <p class="text-3xl font-black font-mono text-amber-400 tracking-tight">
            {{ formatPF(overall.profit_factor) }}
          </p>
          <p class="text-[10px] text-zinc-600 font-mono mt-1">
            GP {{ formatNum(overall.gross_profit) }} / GL {{ formatNum(overall.gross_loss) }}
          </p>
        </div>
      </section>

      <!-- Middle row: strategy winrates -->
      <section class="rounded-2xl border border-zinc-800/60 bg-[#0a0a0a]/80 backdrop-blur-sm p-5 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xs font-bold text-zinc-400 uppercase tracking-widest">Strategy Winrates</h2>
          <span class="text-[10px] text-zinc-600 font-mono">
            {{ strategyList.length }} strateg{{ strategyList.length === 1 ? 'y' : 'ies' }}
          </span>
        </div>

        <div v-if="strategyList.length === 0" class="text-center py-10 text-zinc-600 font-mono text-xs uppercase tracking-widest">
          No closed trades yet
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="row in strategyList"
            :key="row.name"
            class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4"
          >
            <div class="sm:w-36 shrink-0">
              <p class="text-sm font-bold text-white uppercase tracking-wide truncate" :title="row.name">
                {{ formatStrategy(row.name) }}
              </p>
              <p class="text-[10px] text-zinc-500 font-mono">
                {{ row.total_trades }} trades · {{ row.wins }}W / {{ row.losses }}L
              </p>
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex h-3 w-full rounded-full overflow-hidden bg-zinc-900 border border-zinc-800/80">
                <div
                  class="h-full bg-emerald-500 transition-all duration-500"
                  :style="{ width: clampPct(row.winrate) + '%' }"
                  :title="'Winrate ' + formatPct(row.winrate)"
                />
                <div
                  class="h-full bg-red-500 transition-all duration-500"
                  :style="{ width: clampPct(100 - (row.winrate || 0)) + '%' }"
                  :title="'Loss rate ' + formatPct(100 - (row.winrate || 0))"
                />
              </div>
            </div>

            <div class="flex items-center gap-4 shrink-0 sm:w-48 justify-between sm:justify-end">
              <span class="text-sm font-mono font-bold text-[#00e5ff]">{{ formatPct(row.winrate) }}</span>
              <span class="text-[11px] font-mono text-zinc-400">
                PF
                <b class="text-amber-400">{{ formatPF(row.profit_factor) }}</b>
              </span>
              <span
                :class="[
                  'text-[11px] font-mono font-bold',
                  row.total_pnl > 0 ? 'text-emerald-400' : row.total_pnl < 0 ? 'text-red-400' : 'text-zinc-400',
                ]"
              >
                {{ formatSigned(row.total_pnl) }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Bottom row: trade history table -->
      <section class="rounded-2xl border border-zinc-800/60 bg-[#0a0a0a]/80 backdrop-blur-sm shadow-lg flex flex-col min-h-0">
        <div class="flex items-center justify-between px-5 py-4 border-b border-zinc-900 shrink-0">
          <h2 class="text-xs font-bold text-zinc-400 uppercase tracking-widest">Trade History</h2>
          <span class="text-[10px] text-zinc-600 font-mono">{{ history.length }} closed</span>
        </div>

        <div class="overflow-x-auto custom-scrollbar">
          <table class="w-full text-left border-collapse min-w-[720px]">
            <thead>
              <tr class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold border-b border-zinc-900">
                <th class="px-5 py-3 font-bold">Match</th>
                <th class="px-3 py-3 font-bold">Strategy</th>
                <th class="px-3 py-3 font-bold text-right">Size</th>
                <th class="px-3 py-3 font-bold text-right">Entry</th>
                <th class="px-3 py-3 font-bold text-right">Exit</th>
                <th class="px-3 py-3 font-bold">Status</th>
                <th class="px-5 py-3 font-bold text-right">PnL</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="history.length === 0">
                <td colspan="7" class="px-5 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">
                  No closed trades in history
                </td>
              </tr>
              <tr
                v-for="trade in history"
                :key="trade.order_id"
                class="border-b border-zinc-900/80 hover:bg-white/[0.02] transition-colors"
              >
                <td class="px-5 py-3">
                  <span
                    class="text-sm font-bold text-gray-200 uppercase tracking-wide truncate block max-w-[200px]"
                    :title="matchLabel(trade.token_id)"
                  >
                    {{ matchLabel(trade.token_id) }}
                  </span>
                  <span class="text-[10px] text-zinc-600 font-mono">{{ shortId(trade.order_id) }}</span>
                </td>
                <td class="px-3 py-3">
                  <span class="text-[11px] font-mono font-bold text-zinc-300 uppercase">
                    {{ formatStrategy(trade.strategy) }}
                  </span>
                </td>
                <td class="px-3 py-3 text-right font-mono text-sm text-white">
                  {{ formatNum(trade.size) }}
                </td>
                <td class="px-3 py-3 text-right font-mono text-sm text-zinc-300">
                  {{ formatPrice(trade.entry_price) }}
                </td>
                <td class="px-3 py-3 text-right font-mono text-sm text-zinc-300">
                  {{ formatPrice(trade.exit_price) }}
                </td>
                <td class="px-3 py-3">
                  <span :class="['text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider border', statusClass(trade.status)]">
                    {{ trade.status || '—' }}
                  </span>
                </td>
                <td
                  :class="[
                    'px-5 py-3 text-right font-mono text-sm font-bold',
                    (trade.pnl || 0) > 0 ? 'text-emerald-400' : (trade.pnl || 0) < 0 ? 'text-red-400' : 'text-zinc-400',
                  ]"
                >
                  {{ formatSigned(trade.pnl) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../api/http'
import { useMarketStore } from '../../store/marketStore'

const marketStore = useMarketStore()

const loading = ref(false)
const error = ref(null)
const overall = ref({
  total_trades: 0,
  wins: 0,
  losses: 0,
  winrate: 0,
  total_pnl: 0,
  gross_profit: 0,
  gross_loss: 0,
  profit_factor: 0,
})
const strategies = ref({})
const history = ref([])

const overallPnl = computed(() => Number(overall.value?.total_pnl) || 0)

const strategyList = computed(() => {
  const entries = Object.entries(strategies.value || {})
  return entries
    .map(([name, metrics]) => ({
      name,
      total_trades: Number(metrics?.total_trades) || 0,
      wins: Number(metrics?.wins) || 0,
      losses: Number(metrics?.losses) || 0,
      winrate: Number(metrics?.winrate) || 0,
      total_pnl: Number(metrics?.total_pnl) || 0,
      profit_factor: Number(metrics?.profit_factor) || 0,
    }))
    .sort((a, b) => b.total_trades - a.total_trades)
})

function safeNum(v, fallback = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function clampPct(v) {
  const n = safeNum(v, 0)
  if (n < 0) return 0
  if (n > 100) return 100
  return n
}

function formatNum(v) {
  return safeNum(v).toFixed(2)
}

function formatSigned(v) {
  const n = safeNum(v)
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}`
}

function formatPct(v) {
  return `${safeNum(v).toFixed(2)}%`
}

function formatPF(v) {
  const n = safeNum(v)
  // Backend uses 999.0 as infinity sentinel when gross_loss == 0
  if (n >= 999) return '∞'
  return n.toFixed(2)
}

function formatPrice(v) {
  const n = safeNum(v)
  return `${Math.round(n * 100)}¢`
}

function formatStrategy(name) {
  if (!name) return 'CUSTOM'
  return String(name).replace(/_/g, ' ').toUpperCase()
}

function shortId(id) {
  if (!id) return '—'
  const s = String(id)
  return s.length > 8 ? s.slice(-6) : s
}

function matchLabel(tokenId) {
  if (!tokenId) return '—'
  const name = marketStore.getTeamNameFromToken(tokenId)
  if (!name || name === 'UNKNOWN' || !String(name).trim()) {
    const tid = String(tokenId)
    return tid.slice(0, 6) + '...'
  }
  return name
}

function statusClass(status) {
  switch (status) {
    case 'CLOSED_TP':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
    case 'CLOSED_SL':
      return 'bg-red-500/10 text-red-400 border-red-500/30'
    case 'PANIC_SELL':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30'
    case 'RESOLVED':
      return 'bg-[#00e5ff]/10 text-[#00e5ff] border-[#00e5ff]/30'
    default:
      return 'bg-zinc-800 text-zinc-400 border-zinc-700'
  }
}

async function refresh() {
  loading.value = true
  error.value = null
  try {
    const [summary, hist] = await Promise.all([
      apiFetch('/api/stats/summary'),
      apiFetch('/api/stats/history'),
    ])
    overall.value = summary?.overall || overall.value
    strategies.value = summary?.strategies || {}
    history.value = Array.isArray(hist?.trades) ? hist.trades : []
  } catch (e) {
    error.value = e?.message || 'Failed to load statistics'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
})
</script>
