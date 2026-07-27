<template>
  <div
    class="w-64 border border-zinc-800/60 rounded-2xl bg-[#0a0a0a]/80 backdrop-blur-sm p-4 flex flex-col shrink-0 shadow-lg"
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
        class="border border-zinc-800 rounded-xl bg-[#050505] p-3 flex flex-col gap-2 transition-colors hover:border-zinc-600"
      >
        <div class="flex justify-between items-center">
          <span
            class="font-bold text-[11px] truncate max-w-[110px] text-gray-200 uppercase tracking-wide"
            :title="marketStore.getTeamNameFromToken(pos.token_id)"
          >
            {{ marketStore.getTeamNameFromToken(pos.token_id) }}
          </span>

          <div class="flex items-center">
            <span
              v-if="pos.status === 'PENDING'"
              class="text-[9px] px-1.5 py-0.5 rounded font-bold bg-yellow-500/10 text-yellow-500 border border-yellow-500/30 animate-pulse uppercase tracking-widest"
            >
              PENDING
            </span>
            <span
              v-else
              :class="['font-mono font-bold text-xs', pos.liveDiff >= 0 ? 'text-[#00e5ff]' : 'text-indigo-400']"
            >
              {{ pos.liveDiff > 0 ? '+' : '' }}{{ pos.liveDiff }}¢
            </span>
          </div>
        </div>

        <div class="text-[10px] flex flex-col gap-1.5 text-zinc-500 font-mono">
          <div class="flex justify-between px-2 py-1.5 rounded-lg bg-[#0a0a0a]">
            <span>IN: <b class="text-white">{{ Math.round(pos.entry_price * 100) }}¢</b></span>
            <span>SZ: <b class="text-white">{{ pos.size.toFixed(1) }}</b></span>
          </div>
          <div class="flex justify-between px-1.5 mt-0.5">
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
          class="w-full mt-1 bg-indigo-500/10 hover:bg-[#312E81] text-indigo-400 hover:text-white text-[10px] py-1.5 rounded-lg transition-all font-bold uppercase tracking-widest border border-indigo-500/30"
        >
          {{ pos.status === 'PENDING' ? 'CANCEL' : 'MARKET DUMP' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useMarketStore } from '../../store/marketStore'

defineProps({
  positions: { type: Array, default: () => [] },
})
defineEmits(['panic'])

const marketStore = useMarketStore()
</script>
