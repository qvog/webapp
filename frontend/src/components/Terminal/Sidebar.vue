<template>
  <aside
    :class="[
      'flex flex-col justify-between border-r border-zinc-900 bg-[#020202] transition-all duration-300 z-50 shrink-0 overflow-hidden whitespace-nowrap',
      marketStore.isSidebarExpanded ? 'w-56' : 'w-16',
    ]"
  >
    <div class="flex flex-col gap-1 py-4">
      <div class="flex items-center px-4 mb-6 cursor-pointer" @click="$emit('home')">
        <div
          class="w-8 h-8 rounded shrink-0 flex items-center justify-center font-black text-black bg-[#00e5ff] tracking-tighter shadow-[0_0_15px_rgba(0,229,255,0.3)]"
        >
          qS
        </div>
        <span
          :class="[
            'font-black text-lg tracking-widest text-white transition-opacity duration-300',
            marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0',
          ]"
        >
          QSCALP
        </span>
      </div>

      <NavItem
        v-for="item in navItems"
        :key="item.id"
        :active="marketStore.activeCategory === item.id"
        :active-class="item.activeClass || 'text-[#00e5ff]'"
        :bar-class="item.barClass || 'bg-[#00e5ff] shadow-[0_0_10px_rgba(0,229,255,0.5)]'"
        :expanded="marketStore.isSidebarExpanded"
        :label="item.label"
        @click="marketStore.setCategory(item.id)"
      >
        <template #icon>
          <span v-html="item.icon" />
        </template>
      </NavItem>

      <div class="h-px bg-zinc-900 mx-4 my-2 shrink-0" />

      <NavItem
        :active="marketStore.activeCategory === 'live'"
        active-class="text-red-500"
        bar-class="bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]"
        :expanded="marketStore.isSidebarExpanded"
        label="Live Markets"
        @click="marketStore.setCategory('live')"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0">
            <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-14a6 6 0 1 0 6 6 6 6 0 0 0-6-6zm0 10a4 4 0 1 1 4-4 4 4 0 0 1-4 4z" />
          </svg>
        </template>
      </NavItem>

      <NavItem
        :active="marketStore.activeCategory === 'favorites'"
        active-class="text-yellow-500"
        bar-class="bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]"
        :expanded="marketStore.isSidebarExpanded"
        label="Favorites"
        @click="marketStore.setCategory('favorites')"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </template>
      </NavItem>
    </div>

    <div class="flex flex-col border-t border-zinc-900">
      <button
        @click="marketStore.isSidebarExpanded = !marketStore.isSidebarExpanded"
        class="flex items-center px-5 h-14 text-zinc-600 hover:text-[#00e5ff] transition-colors cursor-pointer w-full focus:outline-none shrink-0"
      >
        <svg v-if="!marketStore.isSidebarExpanded" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0">
          <path d="M13 5l7 7-7 7M5 5l7 7-7 7" />
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0">
          <path d="M11 19l-7-7 7-7M19 19l-7-7 7-7" />
        </svg>
      </button>

      <button
        class="flex items-center px-5 h-16 w-full text-zinc-500 hover:text-[#00e5ff] transition-colors border-t border-zinc-900 shrink-0 bg-[#050505]"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <div
          :class="[
            'flex flex-col text-left transition-opacity duration-300',
            marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0',
          ]"
        >
          <span class="font-bold text-xs text-white uppercase tracking-widest">Profile</span>
          <span class="text-[10px] font-medium opacity-70">Connect Wallet</span>
        </div>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { useMarketStore } from '../../store/marketStore'
import NavItem from './NavItem.vue'

defineEmits(['home'])

const marketStore = useMarketStore()

const iconClass = 'w-6 h-6 shrink-0'
const navItems = [
  {
    id: 'most_traded',
    label: 'Most Traded',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="${iconClass}"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`,
  },
  {
    id: 'sports',
    label: 'Sports',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="${iconClass}"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>`,
  },
  {
    id: 'esports',
    label: 'Esports',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="${iconClass}"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 12h4M8 10v4M15 13h.01M18 11h.01"/></svg>`,
  },
  {
    id: 'crypto',
    label: 'Crypto',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="${iconClass}"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
  },
  {
    id: 'others',
    label: 'Others',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="${iconClass}"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`,
  },
]
</script>
