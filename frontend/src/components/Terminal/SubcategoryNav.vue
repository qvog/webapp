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
        <span v-html="getSubcategoryIcon(sub.id)" class="shrink-0 flex items-center justify-center" />
        <span class="truncate">{{ sub.label }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useMarketStore } from '../../store/marketStore'
import { SUBCATEGORIES, getSubcategoryIcon } from '../../constants/categories'

const marketStore = useMarketStore()

const category = computed(() => marketStore.activeCategory)
const items = computed(() => SUBCATEGORIES[marketStore.activeCategory] || [])
</script>
