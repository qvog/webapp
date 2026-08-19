<template>
  <aside
    v-if="items.length > 0"
    class="w-56 border-r border-zinc-900 bg-[#050505] flex flex-col shrink-0 z-40"
  >
    <div class="h-14 flex items-center px-5 border-b border-zinc-900 shrink-0">
      <span class="font-bold text-[10px] uppercase tracking-widest text-zinc-500">
        {{ category }} Markets
      </span>
    </div>
    <div class="flex flex-col p-3 gap-1 overflow-y-auto custom-scrollbar">
      <button
        v-for="sub in items"
        :key="sub.id"
        @click="marketStore.setSubcategory(sub.id)"
        :class="[
          'flex items-center gap-3 text-left px-3 py-2.5 text-[11px] font-bold uppercase tracking-widest rounded-lg transition-all',
          marketStore.activeSubcategory === sub.id
            ? 'text-[#00e5ff] bg-[#00e5ff]/10 shadow-[0_0_10px_rgba(0,229,255,0.1)]'
            : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/50',
        ]"
      >
        <!-- Polymarket-style brand / league icon -->
        <img
          v-if="iconInfo(sub.id).type === 'image'"
          :src="iconInfo(sub.id).url"
          :alt="sub.label"
          class="w-5 h-5 rounded object-cover shrink-0 bg-zinc-900 border border-zinc-800/80"
          loading="lazy"
          decoding="async"
          @error="onIconError($event)"
        />
        <span
          v-else
          v-html="iconInfo(sub.id).html"
          class="shrink-0 flex items-center justify-center w-5 h-5"
        />
        <span class="truncate">{{ sub.label }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useMarketStore } from '../../store/marketStore'
import { SUBCATEGORIES, getSubcategoryIconInfo } from '../../constants/categories'

const marketStore = useMarketStore()

const category = computed(() => marketStore.activeCategory)
const items = computed(() => SUBCATEGORIES[marketStore.activeCategory] || [])

function iconInfo(id) {
  return getSubcategoryIconInfo(id)
}

function onIconError(e) {
  // Hide broken remote icons cleanly
  if (e?.target) e.target.style.visibility = 'hidden'
}
</script>
