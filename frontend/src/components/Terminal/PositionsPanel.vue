<template>
  <div
    class="w-72 border border-zinc-800/60 rounded-2xl bg-[#0a0a0a]/80 backdrop-blur-sm p-4 flex flex-col shrink-0 shadow-lg"
  >
    <div class="flex justify-between items-center mb-4">
      <h3 class="font-bold text-zinc-500 text-[10px] tracking-widest uppercase">Live Positions</h3>
      <button
        @click="marketStore.loadPositions()"
        class="text-[10px] text-[#00e5ff] hover:text-white transition-colors uppercase font-mono tracking-wider"
      >
        ↻ Sync
      </button>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar space-y-3 pr-1">
      <div
        v-if="positions.length === 0"
        class="text-center font-mono text-zinc-600 text-[10px] mt-10 uppercase tracking-widest"
      >
        No Open Orders
      </div>

      <div
        v-for="pos in positions"
        :key="pos.order_id"
        class="border border-zinc-800 rounded-2xl bg-[#050505] p-4 flex flex-col gap-3 transition-colors hover:border-zinc-600 min-h-[168px]"
      >
        <!-- Market / event title -->
        <div class="flex items-start gap-2.5 min-w-0">
          <img
            v-if="marketImage(pos)"
            :src="marketImage(pos)"
            alt=""
            class="w-7 h-7 rounded-full object-cover border border-zinc-800 shrink-0 bg-zinc-900 mt-0.5"
          />
          <div
            v-else
            class="w-7 h-7 rounded-full bg-zinc-900 border border-zinc-800 shrink-0 mt-0.5"
          />
          <div class="min-w-0 flex-1">
            <h4
              class="text-[12px] font-bold text-white leading-snug line-clamp-2 tracking-wide"
              :title="marketTitle(pos)"
            >
              {{ marketTitle(pos) }}
            </h4>
            <div class="flex items-center gap-1.5 mt-1 min-w-0">
              <span
                class="flex items-center gap-0.5 shrink-0 text-yellow-400 font-bold text-[10px] font-mono leading-none tracking-tight"
                :title="pos.order_id"
              >
                <span class="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 shadow-[0_0_6px_#eab308]" />
                {{ shortOrderId(pos.order_id) }}
              </span>
              <span
                class="text-[10px] font-bold text-zinc-400 uppercase truncate"
                :title="marketStore.getTeamNameFromToken(pos.token_id)"
              >
                {{ marketStore.getTeamNameFromToken(pos.token_id) }}
              </span>
              <span
                class="shrink-0 text-[8px] px-1.5 py-0.5 rounded font-bold font-mono uppercase tracking-wider bg-zinc-800/80 text-zinc-400 border border-zinc-700/60"
                :title="'Strategy: ' + formatStrategy(pos.strategy)"
              >
                {{ formatStrategy(pos.strategy) }}
              </span>
            </div>
          </div>

          <div class="flex items-center shrink-0 pl-1">
            <span
              v-if="pos.status === 'PENDING'"
              class="text-[9px] px-1.5 py-0.5 rounded font-bold bg-yellow-500/10 text-yellow-500 border border-yellow-500/30 animate-pulse uppercase tracking-widest"
            >
              PENDING
            </span>
            <span
              v-else
              :class="['font-mono font-bold text-sm', pos.liveDiff >= 0 ? 'text-[#00e5ff]' : 'text-indigo-400']"
            >
              {{ pos.liveDiff > 0 ? '+' : '' }}{{ pos.liveDiff }}¢
            </span>
          </div>
        </div>

        <!-- Stats -->
        <div class="text-[10px] flex flex-col gap-1.5 text-zinc-500 font-mono">
          <div class="flex justify-between px-2.5 py-2 rounded-lg bg-[#0a0a0a]">
            <span>IN: <b class="text-white">{{ Math.round(pos.entry_price * 100) }}¢</b></span>
            <span>SZ: <b class="text-white">{{ Number(pos.size).toFixed(1) }}</b></span>
          </div>
          <div class="flex justify-between px-1.5">
            <span class="text-[#00e5ff]/70">
              TP:
              <b class="text-[#00e5ff]">{{ pos.tp_price ? Math.round(pos.tp_price * 100) + '¢' : '--' }}</b>
            </span>
            <span class="text-indigo-400/70">
              SL:
              <b class="text-indigo-400">
                {{ pos.sl_trigger_price ? Math.round(pos.sl_trigger_price * 100) + '¢' : '--' }}
              </b>
            </span>
          </div>
        </div>

        <button
          @click="$emit('panic', pos.order_id)"
          class="w-full bg-indigo-500/10 hover:bg-[#312E81] text-indigo-400 hover:text-white text-[10px] py-2 rounded-lg transition-all font-bold uppercase tracking-widest border border-indigo-500/30"
        >
          {{ pos.status === 'PENDING' ? 'CANCEL' : 'MARKET DUMP' }}
        </button>

        <!-- Manual resolve for stuck / ended matches -->
        <div class="grid grid-cols-3 gap-1">
          <button
            type="button"
            :disabled="resolvingId === pos.order_id"
            @click="resolvePosition(pos, 1.0)"
            class="text-[8px] py-1.5 rounded-md font-bold uppercase tracking-wider border transition-all disabled:opacity-40
              bg-emerald-500/10 hover:bg-emerald-500/25 text-emerald-400 border-emerald-500/30"
            title="Resolve as win @ 100¢"
          >
            Win 100¢
          </button>
          <button
            type="button"
            :disabled="resolvingId === pos.order_id"
            @click="resolvePosition(pos, 0.0)"
            class="text-[8px] py-1.5 rounded-md font-bold uppercase tracking-wider border transition-all disabled:opacity-40
              bg-red-500/10 hover:bg-red-500/25 text-red-400 border-red-500/30"
            title="Resolve as loss @ 0¢"
          >
            Loss 0¢
          </button>
          <button
            type="button"
            :disabled="resolvingId === pos.order_id"
            @click="resolvePosition(pos, pos.entry_price)"
            class="text-[8px] py-1.5 rounded-md font-bold uppercase tracking-wider border transition-all disabled:opacity-40
              bg-zinc-800/60 hover:bg-zinc-700 text-zinc-400 border-zinc-700"
            title="Drop / hide — resolve @ entry (0 PnL)"
          >
            Drop
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useToast } from 'vue-toastification'
import { useMarketStore } from '../../store/marketStore'
import { tradeApi } from '../../api/tradeService'

defineProps({
  positions: { type: Array, default: () => [] },
})
defineEmits(['panic'])

const marketStore = useMarketStore()
const toast = useToast()
const resolvingId = ref(null)

/** Last 4 chars of order_id — matches OrderBook yellow marker label */
function shortOrderId(orderId) {
  return String(orderId || '').slice(-4)
}

/** Clean uppercase strategy label for the badge (e.g. SHORT_RANGE, FIX) */
function formatStrategy(strategy) {
  if (!strategy) return 'CUSTOM'
  return String(strategy).toUpperCase()
}

function marketTitle(pos) {
  const meta = marketStore.resolveMarketFromToken(pos?.token_id)
  return meta.title || meta.question || marketStore.getTeamNameFromToken(pos?.token_id) || 'Unknown market'
}

function marketImage(pos) {
  return marketStore.getImageFromToken(pos?.token_id)
}

/**
 * Manual resolve: Win 100¢ / Loss 0¢ / Drop @ entry (0 PnL).
 * Hits the stats dashboard via RESOLVED + exit_price.
 */
async function resolvePosition(pos, exitPrice) {
  if (!pos?.order_id || resolvingId.value) return
  resolvingId.value = pos.order_id
  try {
    const data = await tradeApi.resolvePosition(pos.order_id, exitPrice)
    if (data.success) {
      const cents = Math.round(Number(exitPrice) * 100)
      toast.success(`Resolved @ ${cents}¢`)
      await marketStore.loadPositions()
    } else {
      toast.error(data.error || 'Resolve failed')
    }
  } catch (e) {
    toast.error(e.message || 'Resolve failed')
  } finally {
    resolvingId.value = null
  }
}
</script>
