<template>
  <header
    class="h-12 flex items-center border-b border-zinc-900 shrink-0 bg-[#020202] overflow-x-auto hide-scrollbar z-20 w-full flex-nowrap"
  >
    <div
      v-if="marketStore.favorites.length === 0"
      class="text-zinc-700 font-mono text-[10px] uppercase tracking-widest px-6 whitespace-nowrap"
    >
      No pinned markets
    </div>
    <div
      v-for="fav in marketStore.favorites"
      :key="fav.event_id"
      @click="$emit('open', fav)"
      :class="[
        'relative h-full flex items-center px-4 gap-2.5 border-r border-zinc-900/50 cursor-pointer transition-all group shrink-0 min-w-[140px] max-w-[200px]',
        activeEventId === fav.event_id ? 'bg-[#0a0a0a]' : 'hover:bg-zinc-900/30',
      ]"
    >
      <div
        v-if="activeEventId === fav.event_id"
        class="absolute bottom-0 left-0 w-full h-[2px] bg-[#00e5ff] shadow-[0_0_8px_rgba(0,229,255,0.8)]"
      />
      <!-- Active order indicator -->
      <div
        v-if="marketStore.eventHasActiveOrder(fav)"
        class="w-2 h-2 bg-yellow-400 rounded-full shadow-[0_0_5px_rgba(250,204,21,0.8)] absolute top-1 right-1 z-10"
        title="Active order on this market"
      />
      <img
        v-if="fav.image"
        :src="fav.image"
        class="w-4 h-4 rounded-full object-cover border border-zinc-800 shrink-0"
      />
      <div v-else class="w-4 h-4 rounded-full bg-zinc-800 shrink-0" />
      <span
        :class="[
          'text-[10px] font-bold uppercase tracking-widest truncate flex-1',
          activeEventId === fav.event_id ? 'text-[#00e5ff]' : 'text-zinc-500 group-hover:text-zinc-300',
        ]"
        :title="fav.title"
      >
        {{ fav.title }}
      </span>
      <button
        @click.stop="marketStore.toggleFavorite(fav)"
        class="text-zinc-700 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 shrink-0 p-1"
      >
        <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  </header>
</template>

<script setup>
import { useMarketStore } from '../../store/marketStore'

defineProps({
  activeEventId: [String, Number],
})
defineEmits(['open'])

const marketStore = useMarketStore()
</script>
