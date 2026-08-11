<template>
  <main
    class="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-gradient-to-br from-[#000000] via-[#030303] to-[#001012]"
  >
    <!-- Header -->
    <header class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between px-6 py-4 border-b border-zinc-900 shrink-0">
      <div>
        <h1 class="text-lg font-black tracking-widest text-white uppercase">
          Statistics <span class="text-emerald-400">/ PnL</span>
        </h1>
        <p class="text-[10px] text-zinc-500 font-mono uppercase tracking-wider mt-0.5">
          Closed trades · read-only analytics · {{ periodLabel }}
        </p>
      </div>

      <div class="flex items-center gap-3 flex-wrap">
        <!-- Time range filter -->
        <div class="flex items-center gap-1 p-1 rounded-xl border border-zinc-800 bg-[#0a0a0a]">
          <button
            v-for="opt in periodOptions"
            :key="opt.id"
            type="button"
            @click="setPeriod(opt.id)"
            :class="[
              'px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-colors',
              period === opt.id
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                : 'text-zinc-500 hover:text-zinc-300 border border-transparent',
            ]"
          >
            {{ opt.label }}
          </button>
        </div>

        <button
          @click="refresh"
          :disabled="loading"
          class="px-3 py-1.5 rounded-lg border border-zinc-800 bg-[#0a0a0a] text-[11px] font-mono font-bold uppercase tracking-wider text-[#00e5ff] hover:border-[#00e5ff]/40 hover:bg-[#00e5ff]/5 transition-colors disabled:opacity-40"
        >
          {{ loading ? '… Syncing' : '↻ Refresh' }}
        </button>
      </div>
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
          <p class="text-[10px] text-zinc-600 font-mono mt-1">{{ periodLabel }} · (exit − entry) × size</p>
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
          No closed trades in this period
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
          <span class="text-[10px] text-zinc-600 font-mono">{{ sortedHistory.length }} closed · {{ periodLabel }}</span>
        </div>

        <div class="overflow-x-auto custom-scrollbar">
          <table class="w-full text-left border-collapse min-w-[900px]">
            <thead>
              <tr class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold border-b border-zinc-900">
                <th class="px-5 py-3 font-bold">Match</th>
                <th class="px-3 py-3 font-bold whitespace-nowrap">Date / Time</th>
                <th class="px-3 py-3 font-bold">Strategy</th>
                <th class="px-3 py-3 font-bold text-right">Size</th>
                <th class="px-3 py-3 font-bold text-right">Entry</th>
                <th class="px-3 py-3 font-bold text-right">Exit</th>
                <th class="px-3 py-3 font-bold">Status</th>
                <th class="px-5 py-3 font-bold text-right">PnL</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="sortedHistory.length === 0">
                <td colspan="8" class="px-5 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">
                  No closed trades in this period
                </td>
              </tr>
              <tr
                v-for="trade in sortedHistory"
                :key="trade.order_id || trade.id"
                class="border-b border-zinc-900/80 hover:bg-white/[0.02] transition-colors"
              >
                <td class="px-5 py-3">
                  <div class="flex items-center gap-2.5 min-w-0 max-w-[320px]">
                    <img
                      v-if="matchImage(trade)"
                      :src="matchImage(trade)"
                      alt=""
                      class="w-5 h-5 rounded-full object-cover border border-zinc-800 shrink-0 bg-zinc-900"
                      @error="onImageError($event)"
                    />
                    <div
                      v-else
                      class="w-5 h-5 rounded-full bg-zinc-900 border border-zinc-800 shrink-0"
                    />
                    <div class="min-w-0 flex-1">
                      <span
                        class="text-sm font-bold text-gray-200 tracking-wide truncate block"
                        :title="matchLabel(trade)"
                      >
                        {{ matchLabel(trade) }}
                      </span>
                      <span
                        v-if="matchSubtitle(trade)"
                        class="text-[10px] text-zinc-500 truncate block"
                        :title="matchSubtitle(trade)"
                      >
                        {{ matchSubtitle(trade) }}
                      </span>
                    </div>
                  </div>
                </td>
                <td class="px-3 py-3 whitespace-nowrap">
                  <div class="flex flex-col">
                    <span class="text-[12px] font-mono font-bold text-zinc-200">
                      {{ formatDate(trade) }}
                    </span>
                    <span class="text-[10px] font-mono text-zinc-500">
                      {{ formatTime(trade) }}
                    </span>
                  </div>
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
import { ref, computed, onMounted, watch } from 'vue'
import { apiFetch } from '../../api/http'
import { useMarketStore } from '../../store/marketStore'

const marketStore = useMarketStore()

const periodOptions = [
  { id: '24h', label: '24H' },
  { id: '7d', label: 'Week' },
  { id: '30d', label: 'Month' },
  { id: '90d', label: '3M' },
  { id: '1y', label: 'Year' },
  { id: 'all', label: 'All' },
]

const period = ref('30d')
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

const periodLabel = computed(() => {
  const hit = periodOptions.find((p) => p.id === period.value)
  return hit ? hit.label : period.value
})

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

/** Newest trades first — timestamp → updated_at → created_at → id. */
const sortedHistory = computed(() => {
  const list = Array.isArray(history.value) ? [...history.value] : []
  return list.sort((a, b) => tradeSortMs(b) - tradeSortMs(a))
})

function setPeriod(id) {
  if (period.value === id) return
  period.value = id
}

function tradeSortMs(trade) {
  if (!trade) return 0
  const raw = trade.timestamp || trade.updated_at || trade.created_at || null
  if (raw) {
    const ms = Date.parse(raw)
    if (Number.isFinite(ms)) return ms
  }
  const id = Number(trade.id)
  return Number.isFinite(id) ? id : 0
}

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

function truncateToken(tokenId) {
  const tid = String(tokenId || '')
  if (!tid) return '—'
  return tid.slice(0, 6) + '...'
}

/**
 * Primary label: team/outcome if known, else match title/question, else truncated token.
 * Prefer backend enrichment (works for closed historical markets).
 */
function matchLabel(trade) {
  if (!trade) return '—'

  const storeMeta = marketStore.resolveMarketFromToken(trade.token_id)
  const outcome =
    (trade.outcome && String(trade.outcome).trim()) ||
    (storeMeta.teamName && storeMeta.teamName !== 'UNKNOWN' ? storeMeta.teamName : '') ||
    ''
  const title =
    (trade.match_title && String(trade.match_title).trim()) ||
    (trade.question && String(trade.question).trim()) ||
    (storeMeta.title && String(storeMeta.title).trim()) ||
    (storeMeta.question && String(storeMeta.question).trim()) ||
    ''

  // Prefer "TEAM — Match" when both exist
  if (outcome && title && outcome.toUpperCase() !== title.toUpperCase()) {
    return `${outcome} — ${title}`
  }
  if (outcome) return outcome
  if (title) return title
  return truncateToken(trade.token_id)
}

function matchSubtitle(trade) {
  if (!trade) return ''
  // When primary already includes full title, no subtitle needed
  const label = matchLabel(trade)
  const storeMeta = marketStore.resolveMarketFromToken(trade.token_id)
  const question =
    (trade.question && String(trade.question).trim()) ||
    (storeMeta.question && String(storeMeta.question).trim()) ||
    ''
  if (!question) return ''
  if (label.toUpperCase().includes(question.toUpperCase())) return ''
  return question
}

function matchImage(trade) {
  if (!trade) return null
  if (trade.image) return trade.image
  return marketStore.getImageFromToken(trade.token_id)
}

function onImageError(e) {
  if (e?.target) {
    e.target.style.display = 'none'
  }
}

function tradeDate(trade) {
  const raw = trade?.timestamp || trade?.updated_at || trade?.created_at
  if (!raw) return null
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? null : d
}

function formatDate(trade) {
  const d = tradeDate(trade)
  if (!d) return trade?.id != null ? `#${trade.id}` : '—'
  try {
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    })
  } catch {
    return d.toISOString().slice(0, 10)
  }
}

function formatTime(trade) {
  const d = tradeDate(trade)
  if (!d) return ''
  try {
    return d.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return d.toISOString().slice(11, 19)
  }
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
    const q = new URLSearchParams({ period: period.value })
    const [summary, hist] = await Promise.all([
      apiFetch(`/api/stats/summary?${q}`),
      apiFetch(`/api/stats/history?${q}`),
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

watch(period, () => {
  refresh()
})

onMounted(() => {
  refresh()
})
</script>
