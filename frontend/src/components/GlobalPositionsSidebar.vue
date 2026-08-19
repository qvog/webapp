<template>
  <aside
    :class="[
      'flex flex-col border-l border-zinc-900 bg-[#020202] transition-all duration-300 z-50 shrink-0 overflow-hidden',
      marketStore.isPositionsSidebarExpanded ? 'w-72' : 'w-16',
    ]"
  >
    <!-- Header -->
    <div
      :class="[
        'flex items-center border-b border-zinc-900 shrink-0 h-12',
        marketStore.isPositionsSidebarExpanded ? 'px-4 justify-between' : 'px-0 justify-center',
      ]"
    >
      <div
        v-if="marketStore.isPositionsSidebarExpanded"
        class="flex items-center gap-2 min-w-0"
      >
        <span
          class="w-2 h-2 rounded-full bg-yellow-400 shadow-[0_0_6px_rgba(250,204,21,0.8)] shrink-0"
        />
        <span class="text-[10px] font-bold uppercase tracking-widest text-zinc-400 truncate">
          Global Positions
        </span>
        <span class="text-[10px] font-mono text-zinc-600 shrink-0">
          {{ marketStore.activePositions.length }}
        </span>
      </div>
      <span
        v-else
        class="w-2 h-2 rounded-full bg-yellow-400 shadow-[0_0_6px_rgba(250,204,21,0.8)]"
        :title="marketStore.activePositions.length + ' active'"
      />
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto custom-scrollbar min-h-0">
      <!-- Empty -->
      <div
        v-if="marketStore.activePositions.length === 0"
        :class="[
          'text-center font-mono text-zinc-700 text-[9px] uppercase tracking-widest px-2',
          marketStore.isPositionsSidebarExpanded ? 'mt-10' : 'mt-6',
        ]"
      >
        <template v-if="marketStore.isPositionsSidebarExpanded">No open orders</template>
        <template v-else>—</template>
      </div>

      <!-- Collapsed: unique market icons -->
      <div
        v-else-if="!marketStore.isPositionsSidebarExpanded"
        class="flex flex-col items-center gap-2 py-3"
      >
        <button
          v-for="group in groupedByMarket"
          :key="group.eventId"
          type="button"
          @click="openGroup(group)"
          class="relative w-10 h-10 rounded-xl border border-zinc-800 bg-[#050505] hover:border-yellow-400/50 hover:bg-zinc-900 transition-colors flex items-center justify-center cursor-pointer"
          :title="group.title"
        >
          <img
            v-if="group.image"
            :src="group.image"
            alt=""
            class="w-6 h-6 rounded-full object-cover"
          />
          <span
            v-else
            class="text-[9px] font-black text-zinc-500 uppercase"
          >
            {{ initials(group.title) }}
          </span>
          <span
            class="absolute -top-1 -right-1 min-w-[14px] h-3.5 px-0.5 rounded-full bg-yellow-400 text-black text-[8px] font-black flex items-center justify-center shadow-[0_0_6px_rgba(250,204,21,0.6)]"
          >
            {{ group.positions.length }}
          </span>
        </button>
      </div>

      <!-- Expanded: full position list -->
      <div v-else class="flex flex-col gap-2 p-3">
        <button
          v-for="pos in marketStore.activePositions"
          :key="pos.order_id"
          type="button"
          @click="openPosition(pos)"
          class="w-full text-left border border-zinc-800 rounded-xl bg-[#050505] p-3 hover:border-yellow-400/40 hover:bg-zinc-900/60 transition-colors cursor-pointer"
        >
          <div class="flex items-start gap-2.5 min-w-0">
            <img
              v-if="meta(pos).image"
              :src="meta(pos).image"
              alt=""
              class="w-6 h-6 rounded-full object-cover border border-zinc-800 shrink-0"
            />
            <div
              v-else
              class="w-6 h-6 rounded-full bg-zinc-900 border border-zinc-800 shrink-0"
            />
            <div class="min-w-0 flex-1">
              <p
                class="text-[11px] font-bold text-white leading-snug line-clamp-2"
                :title="meta(pos).title || 'Unknown'"
              >
                {{ meta(pos).title || 'Unknown market' }}
              </p>
              <div class="flex items-center gap-1.5 mt-1 min-w-0">
                <span
                  class="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 shadow-[0_0_6px_#eab308] shrink-0"
                />
                <span class="text-[9px] font-mono text-yellow-400 shrink-0">
                  {{ shortId(pos.order_id) }}
                </span>
                <span class="text-[9px] text-zinc-500 uppercase truncate">
                  {{ meta(pos).teamName || '—' }}
                </span>
                <span
                  v-if="pos.status === 'PENDING'"
                  class="ml-auto shrink-0 text-[8px] px-1 py-0.5 rounded font-bold bg-yellow-500/10 text-yellow-500 border border-yellow-500/30 uppercase"
                >
                  PEND
                </span>
              </div>
              <div class="flex justify-between mt-1.5 text-[9px] font-mono text-zinc-500">
                <span>IN <b class="text-zinc-300">{{ Math.round(Number(pos.entry_price) * 100) }}¢</b></span>
                <span>SZ <b class="text-zinc-300">{{ Number(pos.size).toFixed(1) }}</b></span>
                <span class="uppercase text-zinc-600">{{ formatStrategy(pos.strategy) }}</span>
              </div>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- Footer toggle (mirrors left sidebar) -->
    <div class="flex flex-col border-t border-zinc-900 shrink-0">
      <button
        type="button"
        @click="marketStore.togglePositionsSidebar()"
        class="flex items-center px-5 h-14 text-zinc-600 hover:text-[#00e5ff] transition-colors cursor-pointer w-full focus:outline-none shrink-0"
        :title="marketStore.isPositionsSidebarExpanded ? 'Collapse' : 'Expand positions'"
      >
        <svg
          v-if="marketStore.isPositionsSidebarExpanded"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="w-6 h-6 shrink-0"
        >
          <path d="M13 5l7 7-7 7M5 5l7 7-7 7" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="w-6 h-6 shrink-0"
        >
          <path d="M11 19l-7-7 7-7M19 19l-7-7 7-7" />
        </svg>
        <span
          v-if="marketStore.isPositionsSidebarExpanded"
          class="ml-3 text-[10px] font-bold uppercase tracking-widest"
        >
          Collapse
        </span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useToast } from 'vue-toastification'
import { useMarketStore } from '../store/marketStore'

const emit = defineEmits(['open-terminal'])

const marketStore = useMarketStore()
const toast = useToast()

let pollTimer = null

onMounted(() => {
  marketStore.loadPositions()
  pollTimer = setInterval(() => marketStore.loadPositions(), 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

function meta(pos) {
  return marketStore.resolveMarketFromToken(pos?.token_id)
}

function shortId(orderId) {
  return String(orderId || '').slice(-4)
}

function formatStrategy(strategy) {
  if (!strategy) return 'CUSTOM'
  return String(strategy).toUpperCase()
}

function initials(title) {
  const parts = String(title || '?')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

/** Unique markets that currently have active orders (for collapsed icon rail). */
const groupedByMarket = computed(() => {
  const map = new Map()
  for (const pos of marketStore.activePositions) {
    const m = meta(pos)
    const eventId = m.eventId || String(pos.token_id)
    if (!map.has(eventId)) {
      map.set(eventId, {
        eventId,
        title: m.title || m.question || 'Unknown',
        image: m.image,
        match: m.match,
        tokenId: pos.token_id,
        positions: [],
      })
    }
    map.get(eventId).positions.push(pos)
  }
  return [...map.values()]
})

function openPosition(pos) {
  emit('open-terminal')
  const ok = marketStore.openMarketFromPosition(pos)
  if (!ok) {
    toast.warning('Market not in current list — open it from search/favorites first', {
      timeout: 2500,
    })
  }
}

function openGroup(group) {
  emit('open-terminal')
  if (group.match) {
    marketStore.setActiveMarket(group.match, { tokenId: group.tokenId })
    return
  }
  // Fallback: try via first position
  const first = group.positions?.[0]
  if (first) openPosition(first)
  else toast.warning('Cannot resolve market for this position')
}
</script>
