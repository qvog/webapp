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
        <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">Bankroll (USDC)</label>
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

      <!-- 4 HFT presets: override fields + fire /order at best ask -->
      <div v-else class="flex flex-col gap-2">
        <p class="text-[9px] text-zinc-600 uppercase tracking-wider mb-0.5">
          One-tap → best ask
        </p>
        <button
          v-for="p in PRESETS"
          :key="p.id"
          type="button"
          @click="firePreset(p)"
          :disabled="!activeSub || submitting === p.id"
          :class="[
            'w-full text-left px-3 py-2 rounded-xl border transition-all',
            marketStore.activePreset === p.id
              ? 'border-[#00e5ff]/60 bg-[#00e5ff]/10 shadow-[0_0_12px_rgba(0,229,255,0.12)]'
              : 'border-zinc-800/70 bg-[#050505] hover:border-zinc-600',
            (!activeSub || submitting) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
          ]"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-[11px] font-bold text-gray-200 tracking-wide">{{ p.label }}</span>
            <span class="text-[9px] font-mono text-zinc-500">{{ p.sizeHint }}</span>
          </div>
          <div class="mt-0.5 text-[9px] font-mono text-zinc-500">
            <span class="text-[#00e5ff]">{{ p.tpHint }}</span>
            <span class="mx-1 text-zinc-700">·</span>
            <span class="text-indigo-400">{{ p.slHint }}</span>
          </div>
        </button>
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
import { ref } from 'vue'
import { useMarketStore } from '../../store/marketStore'

const props = defineProps({
  event: Object,
  activeSub: Object,
})
const emit = defineEmits(['close', 'select-sub', 'run-preset'])

const marketStore = useMarketStore()
const submitting = ref(null)

const PRESETS = [
  {
    id: 'rebound',
    label: 'Rebound Scalp',
    sizeHint: '40%',
    tpHint: 'TP +3¢',
    slHint: 'SL −5¢',
    riskPercent: 40,
    tpOffsetCents: 3,
    slOffsetCents: 5,
    strategy: 'rebound',
  },
  {
    id: 'partial',
    label: 'Partial TP',
    sizeHint: '100%',
    tpHint: 'TP dual',
    slHint: 'SL −4¢',
    riskPercent: 100,
    tpOffsetCents: 3, // display; backend places +3 and +6
    slOffsetCents: 4,
    strategy: 'partial',
  },
  {
    id: 'result',
    label: 'Result Hold',
    sizeHint: '≥$5 / 5%',
    tpHint: 'TP none',
    slHint: 'SL 50%',
    riskPercent: null, // special sizing
    tpOffsetCents: null,
    slOffsetCents: null, // SL = entry * 0.5
    strategy: 'result',
  },
  {
    id: 'momentum',
    label: 'Momentum',
    sizeHint: '60%',
    tpHint: 'TP +6¢',
    slHint: 'SL −3¢',
    riskPercent: 60,
    tpOffsetCents: 6,
    slOffsetCents: 3,
    strategy: 'momentum',
  },
]

function modeBtnClass(mode) {
  const on = marketStore.tradingMode === mode
  return [
    'px-2.5 py-1 text-[10px] font-bold rounded transition-colors uppercase tracking-wider',
    on
      ? 'bg-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.3)]'
      : 'text-zinc-500 hover:text-zinc-300',
  ]
}

/**
 * Override store fields for visibility, then ask Terminal to submit /order.
 */
function firePreset(preset) {
  if (!props.activeSub || submitting.value) return

  marketStore.tradingMode = 'presets'
  marketStore.activePreset = preset.id

  // Mirror offsets into custom fields so the panel stays consistent
  if (preset.tpOffsetCents != null) marketStore.tpOffset = preset.tpOffsetCents
  if (preset.slOffsetCents != null) marketStore.slOffset = preset.slOffsetCents

  submitting.value = preset.id
  emit('run-preset', {
    strategy: preset.strategy,
    riskPercent: preset.riskPercent,
    tpOffsetCents: preset.tpOffsetCents,
    slOffsetCents: preset.slOffsetCents,
    // Result Hold: size = max(5% bankroll, $5)
    resultHold: preset.strategy === 'result',
  })
  // Parent clears busy state via next tick order completion; local unlock shortly
  setTimeout(() => {
    if (submitting.value === preset.id) submitting.value = null
  }, 2500)
}
</script>
