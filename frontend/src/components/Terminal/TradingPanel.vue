<template>
  <div class="w-64 flex flex-col gap-3 shrink-0">
    <div class="border border-zinc-800/60 rounded-2xl bg-[#0a0a0a]/80 backdrop-blur-sm p-4 shrink-0 shadow-lg">
      <div class="flex items-center gap-3 mb-5">
        <button @click="$emit('close')" class="text-zinc-500 hover:text-[#00e5ff] transition-colors">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-5 h-5">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <h3 class="font-bold text-gray-300 text-[11px] tracking-widest uppercase truncate">
          {{ event?.title }}
        </h3>
      </div>

      <div class="flex justify-between items-center mb-4">
        <span class="font-bold text-zinc-500 text-[10px] uppercase tracking-widest">Strategy</span>
        <div class="flex rounded border border-zinc-800 bg-[#050505] p-0.5">
          <button
            @click="marketStore.tradingMode = 'custom'"
            :class="modeBtnClass('custom')"
          >
            Cust
          </button>
          <button
            @click="marketStore.tradingMode = 'presets'"
            :class="modeBtnClass('presets')"
          >
            Fast
          </button>
        </div>
      </div>

      <div class="mb-4">
        <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">Volume (USDC)</label>
        <input
          v-model="marketStore.tradeSize"
          type="number"
          class="w-full border border-zinc-800 rounded-lg px-3 py-2 text-sm font-bold outline-none focus:border-[#00e5ff] bg-[#050505] text-white transition-all"
        />
      </div>

      <div v-if="marketStore.tradingMode === 'custom'" class="flex gap-2">
        <div class="flex-1">
          <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">TP (¢)</label>
          <input
            v-model="marketStore.tpOffset"
            type="number"
            class="w-full border border-zinc-800 rounded-lg px-2 py-2 text-sm font-bold outline-none focus:border-[#00e5ff] bg-[#050505] text-[#00e5ff] transition-all"
          />
        </div>
        <div class="flex-1">
          <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">SL (¢)</label>
          <input
            v-model="marketStore.slOffset"
            type="number"
            class="w-full border border-zinc-800 rounded-lg px-2 py-2 text-sm font-bold outline-none focus:border-indigo-400 bg-[#050505] text-indigo-400 transition-all"
          />
        </div>
      </div>
    </div>

    <div
      class="border border-zinc-800/60 rounded-2xl bg-[#0a0a0a]/80 backdrop-blur-sm p-4 flex-1 overflow-y-auto custom-scrollbar shadow-lg"
    >
      <h3 class="font-bold text-zinc-500 text-[10px] mb-3 tracking-widest uppercase">Orderbooks</h3>
      <div class="flex flex-col gap-2">
        <button
          v-for="sub in event?.sub_markets || []"
          :key="sub.condition_id"
          @click="$emit('select-sub', sub)"
          :class="[
            'w-full p-3 rounded-xl text-left text-[11px] font-mono leading-relaxed transition-all border',
            activeSub?.condition_id === sub.condition_id
              ? 'border-[#00e5ff] bg-[#00e5ff]/10 text-white shadow-[0_0_15px_rgba(0,229,255,0.1)]'
              : 'border-zinc-800/50 bg-[#050505] text-zinc-400 hover:bg-zinc-800',
          ]"
        >
          {{ sub.question }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useMarketStore } from '../../store/marketStore'

defineProps({
  event: Object,
  activeSub: Object,
})
defineEmits(['close', 'select-sub'])

const marketStore = useMarketStore()

function modeBtnClass(mode) {
  const on = marketStore.tradingMode === mode
  return [
    'px-2.5 py-1 text-[10px] font-bold rounded transition-colors uppercase tracking-wider',
    on
      ? 'bg-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.3)]'
      : 'text-zinc-500 hover:text-zinc-300',
  ]
}
</script>
