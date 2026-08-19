<template>
  <div class="w-64 flex flex-col gap-3 shrink-0" tabindex="-1" ref="panelRoot">
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

      <div class="mb-4">
        <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">
          Strategy
        </label>
        <select
          :value="marketStore.activeStrategy"
          @change="onStrategyChange"
          class="w-full border border-zinc-800 rounded-lg px-3 py-2 text-sm font-bold outline-none focus:border-[#00e5ff] bg-[#050505] text-white transition-all appearance-none cursor-pointer"
        >
          <option
            v-for="opt in strategyOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
        <p class="mt-1.5 text-[9px] text-zinc-600 font-mono tracking-wide">
          F1–F3 presets · F10 flatten
        </p>
      </div>

      <div class="mb-4">
        <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">Volume (USDC)</label>
        <input
          ref="volumeInput"
          v-model="marketStore.tradeSize"
          type="number"
          class="w-full border border-zinc-800 rounded-lg px-3 py-2 text-sm font-bold outline-none focus:border-[#00e5ff] bg-[#050505] text-white transition-all"
        />
      </div>

      <!-- Custom: both TP offset + SL offset -->
      <div v-if="marketStore.activeStrategy === 'custom'" class="flex gap-2">
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

      <!-- Fix: relative TP offset only, SL disabled -->
      <div v-else-if="marketStore.activeStrategy === 'fix'" class="flex flex-col gap-1.5">
        <div>
          <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">
            TP Offset (+¢)
          </label>
          <div class="relative">
            <span
              class="absolute left-2.5 top-1/2 -translate-y-1/2 text-sm font-bold text-[#00e5ff] pointer-events-none"
            >+</span>
            <input
              v-model="marketStore.fixTpCents"
              type="number"
              min="1"
              max="98"
              step="1"
              placeholder="+¢ offset"
              class="w-full border border-zinc-800 rounded-lg pl-6 pr-2 py-2 text-sm font-bold outline-none focus:border-[#00e5ff] bg-[#050505] text-[#00e5ff] transition-all"
            />
          </div>
        </div>
        <p class="text-[9px] text-zinc-600 font-mono tracking-wide">
          Relative take-profit · capped @ 99¢ · SL disabled
        </p>
      </div>

      <div
        v-else
        class="rounded-lg border border-zinc-800/80 bg-[#050505] px-3 py-2 text-[10px] text-zinc-500 font-mono leading-relaxed"
      >
        {{ presetHint }}
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
            'relative w-full p-3 rounded-xl text-left text-[11px] font-mono leading-relaxed transition-all border pr-6',
            activeSub?.condition_id === sub.condition_id
              ? 'border-[#00e5ff] bg-[#00e5ff]/10 text-white shadow-[0_0_15px_rgba(0,229,255,0.1)]'
              : 'border-zinc-800/50 bg-[#050505] text-zinc-400 hover:bg-zinc-800',
          ]"
        >
          <div
            v-if="marketStore.subHasActiveOrder(sub)"
            class="w-2 h-2 bg-yellow-400 rounded-full shadow-[0_0_5px_rgba(250,204,21,0.8)] absolute top-1 right-1"
            title="Active order on this sub-market"
          />
          <span class="line-clamp-2">{{ sub.question }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useMarketStore } from '../../store/marketStore'

defineProps({
  event: Object,
  activeSub: Object,
})
defineEmits(['close', 'select-sub'])

const marketStore = useMarketStore()
const panelRoot = ref(null)
const volumeInput = ref(null)

const strategyOptions = [
  { value: 'custom', label: 'Custom' },
  { value: 'fix', label: 'Fix' },
  { value: 'draft_win', label: 'Draft Win (F1)' },
  { value: 'short_range', label: 'Short Range (F2)' },
  { value: 'high_range', label: 'High Range (F3)' },
]

const PRESET_HINTS = {
  fix: 'Manual +¢ TP offset · No SL · cap 99¢',
  draft_win: 'No TP · No SL — hold to resolve',
  short_range: 'TP +4¢ · SL −6¢ · 3-tick SL',
  high_range: 'TP +6¢ · SL −8¢ · 3-tick SL',
}

const presetHint = computed(
  () => PRESET_HINTS[marketStore.activeStrategy] || 'Preset — TP/SL set by backend'
)

function applyStrategy(strategy, volume = null) {
  marketStore.activeStrategy = strategy
  marketStore.activePreset = strategy
  marketStore.tradingMode = strategy === 'custom' ? 'custom' : 'presets'
  if (volume != null) marketStore.tradeSize = volume
}

function onStrategyChange(e) {
  applyStrategy(e.target.value)
}

/** Focus terminal panel after hotkey preset switch */
function focusTerminal() {
  panelRoot.value?.focus?.()
  // Prefer volume field so user can immediately adjust size
  volumeInput.value?.focus?.()
}

defineExpose({ applyStrategy, focusTerminal, panelRoot })
</script>
