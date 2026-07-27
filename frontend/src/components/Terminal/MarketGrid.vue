<template>
  <div class="flex-1 flex flex-col overflow-hidden relative">
    <header
      class="h-14 border-b border-zinc-800/60 flex items-center px-8 shrink-0 bg-[#050505]/80 backdrop-blur-md z-10 w-full justify-between"
    >
      <h2 class="text-sm font-black uppercase tracking-widest text-[#00e5ff] flex items-center gap-2">
        <template v-if="marketStore.activeCategory === 'most_traded'">🔥 Most Traded Markets</template>
        <template v-else-if="marketStore.activeCategory === 'live'">🔴 Live Markets</template>
        <template v-else>
          <span class="text-zinc-600">{{ marketStore.activeCategory }} / </span>
          {{ marketStore.activeSubcategory }}
        </template>
      </h2>

      <div class="flex items-center gap-2 border-zinc-800/60 shrink-0">
        <span class="text-[9px] font-mono text-zinc-600 uppercase tracking-widest mr-1">Sort by:</span>
        <button
          @click="marketStore.sortBy = 'volume'"
          :class="sortBtnClass('volume')"
        >
          VOL
        </button>
        <button
          @click="marketStore.sortBy = 'date'"
          :class="sortBtnClass('date')"
        >
          DATE
        </button>
      </div>
    </header>

    <div class="flex-1 overflow-y-auto p-8 relative custom-scrollbar">
      <div
        v-if="marketStore.isLoadingMarkets"
        class="absolute inset-0 flex items-center justify-center z-10 bg-[#0a0a0a]/60 backdrop-blur-sm"
      >
        <span class="text-[#00e5ff] font-mono animate-pulse font-bold text-sm uppercase tracking-widest">
          Scanning Blockchain...
        </span>
      </div>

      <div class="max-w-[1600px] mx-auto">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-5">
          <div
            v-for="match in marketStore.filteredMatches"
            :key="match.event_id"
            class="relative bg-[#0a0a0a]/90 backdrop-blur-sm border border-zinc-900 rounded-2xl flex flex-col h-[230px] transition-all duration-300 hover:border-zinc-700 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)] hover:-translate-y-1 group overflow-hidden"
          >
            <div class="flex justify-between items-start p-5 shrink-0">
              <span class="text-[10px] font-medium font-mono text-zinc-500 uppercase tracking-widest">
                {{ formatMarketDate(match.start_date) }}
              </span>
              <div class="flex items-center gap-2">
                <span
                  v-if="match.is_live"
                  class="bg-red-500/10 border border-red-500/30 text-red-500 text-[9px] font-black px-1.5 py-0.5 rounded animate-pulse uppercase tracking-widest"
                >
                  LIVE
                </span>
                <button
                  @click.stop="marketStore.toggleFavorite(match)"
                  class="text-zinc-600 hover:text-yellow-500 transition-colors"
                >
                  <svg
                    viewBox="0 0 24 24"
                    :fill="marketStore.isFavorite(match.event_id) ? 'currentColor' : 'none'"
                    stroke="currentColor"
                    stroke-width="2"
                    class="w-4 h-4"
                    :class="{
                      'text-yellow-500 drop-shadow-[0_0_5px_rgba(234,179,8,0.5)]':
                        marketStore.isFavorite(match.event_id),
                    }"
                  >
                    <polygon
                      points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"
                    />
                  </svg>
                </button>
              </div>
            </div>

            <div class="px-5 flex-1 overflow-hidden flex gap-4 items-start">
              <img
                v-if="match.image"
                :src="match.image"
                class="w-10 h-10 rounded-full shrink-0 object-cover border-2 border-zinc-800 group-hover:border-[#00e5ff]/50 transition-colors"
              />
              <h3
                class="font-bold text-base text-gray-200 line-clamp-3 leading-snug tracking-tight group-hover:text-white transition-colors"
                :title="match.title"
              >
                {{ match.title }}
              </h3>
            </div>

            <div class="p-2 border-t border-zinc-900 bg-[#050505]/50 shrink-0 flex flex-col gap-3">
              <div v-if="match.sub_markets?.length" class="flex flex-col gap-2">
                <div class="flex justify-between items-center font-mono">
                  <div class="flex flex-col">
                    <span
                      class="text-[9px] uppercase tracking-widest text-zinc-500 truncate max-w-[80px]"
                      :title="match.sub_markets[0].out1"
                    >
                      {{ match.sub_markets[0].out1 || 'YES' }}
                    </span>
                    <span class="font-bold text-[#00e5ff] text-xs">
                      {{ Math.round(match.sub_markets[0].price_yes * 100) }}%
                    </span>
                  </div>
                  <div class="flex flex-col text-right">
                    <span
                      class="text-[9px] uppercase tracking-widest text-zinc-500 truncate max-w-[80px]"
                      :title="match.sub_markets[0].out2"
                    >
                      {{ match.sub_markets[0].out2 || 'NO' }}
                    </span>
                    <span class="font-bold text-indigo-400 text-xs">
                      {{ Math.round(match.sub_markets[0].price_no * 100) }}%
                    </span>
                  </div>
                </div>

                <div class="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden flex">
                  <div
                    class="h-full bg-[#00e5ff] transition-all duration-500"
                    :style="{ width: Math.round(match.sub_markets[0].price_yes * 100) + '%' }"
                  />
                  <div
                    class="h-full bg-[#312E81] transition-all duration-500"
                    :style="{ width: Math.round(match.sub_markets[0].price_no * 100) + '%' }"
                  />
                </div>
              </div>

              <div class="flex justify-between items-end mt-1">
                <div class="text-[9px] text-zinc-600 font-mono uppercase tracking-widest">
                  Vol:
                  <span class="text-zinc-300 font-medium">${{ formatVolume(match.total_volume) }}</span>
                </div>
                <button
                  @click="$emit('open', match)"
                  class="px-5 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all border border-[#00e5ff]/30 bg-[#00e5ff]/10 text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black hover:shadow-[0_0_15px_rgba(0,229,255,0.4)]"
                >
                  TRADE
                </button>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="!marketStore.isLoadingMarkets && marketStore.filteredMatches.length === 0"
          class="flex flex-col items-center justify-center h-64 opacity-50"
        >
          <span class="text-sm font-mono uppercase tracking-widest text-zinc-600">Zero Markets Found</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useMarketStore } from '../../store/marketStore'
import { formatMarketDate, formatVolume } from '../../constants/categories'

defineEmits(['open'])

const marketStore = useMarketStore()

function sortBtnClass(key) {
  const active = marketStore.sortBy === key
  return [
    'px-3 py-1.5 rounded-md text-[9px] font-black uppercase tracking-widest transition-colors',
    active
      ? 'text-[#00e5ff] bg-[#00e5ff]/10 border border-[#00e5ff]/30 shadow-[0_0_10px_rgba(0,229,255,0.2)]'
      : 'text-zinc-500 border border-transparent hover:text-zinc-300',
  ]
}
</script>
