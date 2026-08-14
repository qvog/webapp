<template>
  <div class="flex-1 flex flex-col overflow-hidden relative">
    <header
      class="h-14 border-b border-zinc-800/60 flex items-center px-8 shrink-0 bg-[#050505]/80 backdrop-blur-md z-10 w-full gap-4"
    >
      <!-- Left: title + count -->
      <h2
        class="text-sm font-black uppercase tracking-widest text-[#00e5ff] flex items-center gap-2 shrink-0 min-w-0 max-w-[28%]"
      >
        <span class="truncate">
          <template v-if="marketStore.activeCategory === 'most_traded'">🔥 Most Traded</template>
          <template v-else-if="marketStore.activeCategory === 'live'">🔴 Live Markets</template>
          <template v-else>
            <span class="text-zinc-600">{{ marketStore.activeCategory }} / </span>
            {{ marketStore.activeSubcategory }}
          </template>
        </span>
        <span
          class="shrink-0 text-[10px] font-mono font-bold tracking-widest text-zinc-500 border border-zinc-800 bg-zinc-900/60 px-2 py-0.5 rounded-md normal-case"
          :class="{ 'opacity-40': marketStore.isLoadingMarkets }"
        >
          {{ marketStore.filteredMatches.length }}
          <span class="text-zinc-600 font-medium">markets</span>
        </span>
      </h2>

      <!-- Center: search -->
      <div class="flex-1 flex justify-center min-w-0 relative" ref="searchWrapRef">
        <div class="w-full max-w-md relative">
          <div
            class="flex items-center gap-2 h-9 px-3 rounded-xl border bg-[#0a0a0a]/90 transition-colors"
            :class="
              searchFocused || searchQuery
                ? 'border-[#00e5ff]/40 shadow-[0_0_12px_rgba(0,229,255,0.12)]'
                : 'border-zinc-800 hover:border-zinc-700'
            "
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              class="w-3.5 h-3.5 text-zinc-500 shrink-0"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
            <input
              v-model="searchQuery"
              type="search"
              autocomplete="off"
              spellcheck="false"
              placeholder="Search markets & categories…"
              class="flex-1 bg-transparent text-xs text-gray-200 placeholder:text-zinc-600 outline-none font-medium tracking-wide min-w-0"
              @focus="searchFocused = true"
              @keydown.escape="closeSearch"
              @keydown.enter.prevent="selectFirstResult"
            />
            <button
              v-if="searchQuery"
              type="button"
              class="text-zinc-600 hover:text-zinc-300 text-[10px] font-mono uppercase tracking-widest shrink-0"
              @click="clearSearch"
            >
              ESC
            </button>
          </div>

          <!-- Dropdown -->
          <div
            v-if="showDropdown"
            class="absolute left-0 right-0 top-[calc(100%+6px)] z-50 rounded-xl border border-zinc-800 bg-[#0a0a0a]/98 backdrop-blur-xl shadow-[0_16px_48px_rgba(0,0,0,0.75)] overflow-hidden max-h-[min(420px,70vh)] overflow-y-auto custom-scrollbar"
          >
            <div v-if="isSearching" class="px-4 py-3 text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
              Searching…
            </div>

            <template v-else>
              <!-- Categories first -->
              <div v-if="categoryHits.length">
                <div
                  class="px-3 pt-2.5 pb-1 text-[9px] font-black uppercase tracking-[0.2em] text-zinc-600"
                >
                  Categories
                </div>
                <button
                  v-for="cat in categoryHits"
                  :key="`c-${cat.category}-${cat.subcategory}`"
                  type="button"
                  class="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-[#00e5ff]/8 transition-colors group"
                  @click="onSelectCategory(cat)"
                >
                  <span
                    class="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0 overflow-hidden group-hover:border-[#00e5ff]/30"
                  >
                    <img
                      v-if="categoryIcon(cat).type === 'image'"
                      :src="categoryIcon(cat).url"
                      :alt="cat.label"
                      class="w-full h-full object-cover"
                      loading="lazy"
                      decoding="async"
                    />
                    <span
                      v-else
                      v-html="categoryIcon(cat).html"
                      class="flex items-center justify-center"
                    />
                  </span>
                  <div class="min-w-0 flex-1">
                    <div class="text-xs font-bold text-gray-200 truncate group-hover:text-[#00e5ff]">
                      {{ cat.label }}
                    </div>
                    <div class="text-[10px] font-mono text-zinc-600 truncate uppercase tracking-wider">
                      {{ cat.path }}
                    </div>
                  </div>
                  <span class="text-[9px] font-mono text-zinc-700 uppercase tracking-widest shrink-0">
                    category
                  </span>
                </button>
              </div>

              <!-- Then markets -->
              <div v-if="marketHits.length">
                <div
                  class="px-3 pt-2.5 pb-1 text-[9px] font-black uppercase tracking-[0.2em] text-zinc-600 border-t border-zinc-900/80"
                  :class="{ 'border-t-0': !categoryHits.length }"
                >
                  Markets
                </div>
                <button
                  v-for="m in marketHits"
                  :key="`m-${m.event_id}`"
                  type="button"
                  class="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-[#00e5ff]/8 transition-colors group"
                  @click="onSelectMarket(m)"
                >
                  <img
                    v-if="m.image"
                    :src="m.image"
                    class="w-7 h-7 rounded-full object-cover border border-zinc-800 shrink-0"
                    alt=""
                  />
                  <span
                    v-else
                    class="w-7 h-7 rounded-full bg-zinc-900 border border-zinc-800 shrink-0"
                  />
                  <div class="min-w-0 flex-1">
                    <div class="text-xs font-bold text-gray-200 truncate group-hover:text-white">
                      {{ m.title }}
                    </div>
                    <div class="text-[10px] font-mono text-zinc-600 truncate">
                      Vol ${{ formatVolume(m.total_volume) }}
                      <span v-if="m.sub_markets?.[0]" class="text-zinc-500">
                        · {{ Math.round((m.sub_markets[0].price_yes || 0) * 100) }}¢
                      </span>
                    </div>
                  </div>
                  <span class="text-[9px] font-mono text-[#00e5ff]/70 uppercase tracking-widest shrink-0">
                    trade
                  </span>
                </button>
              </div>

              <div
                v-if="!categoryHits.length && !marketHits.length"
                class="px-4 py-6 text-center text-[11px] font-mono text-zinc-600 uppercase tracking-widest"
              >
                No results for “{{ searchQuery }}”
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Right: refresh + sort -->
      <div class="flex items-center gap-2 border-zinc-800/60 shrink-0">
        <button
          type="button"
          @click="refreshMarkets"
          :disabled="marketStore.isLoadingMarkets"
          class="text-[10px] font-mono font-bold uppercase tracking-widest px-2.5 py-1 rounded-md border transition-colors disabled:opacity-40
            border-zinc-800 text-zinc-400 hover:text-[#00e5ff] hover:border-[#00e5ff]/40 bg-zinc-900/40"
          title="Refresh markets for current category"
        >
          ↻ Refresh
        </button>
        <span class="text-[9px] font-mono text-zinc-600 uppercase tracking-widest mr-1">Sort by:</span>
        <button @click="marketStore.sortBy = 'volume'" :class="sortBtnClass('volume')">VOL</button>
        <button @click="marketStore.sortBy = 'date'" :class="sortBtnClass('date')">DATE</button>
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useMarketStore } from '../../store/marketStore'
import { tradeApi } from '../../api/tradeService'
import {
  formatMarketDate,
  formatVolume,
  searchCategories,
  getSubcategoryIconInfo,
} from '../../constants/categories'

function categoryIcon(cat) {
  const id = cat?.subcategory === 'all' ? cat.category : cat?.subcategory
  return getSubcategoryIconInfo(id)
}

const emit = defineEmits(['open'])
const marketStore = useMarketStore()

const searchQuery = ref('')
const searchFocused = ref(false)
const isSearching = ref(false)
const marketHits = ref([])
const searchWrapRef = ref(null)
let searchTimer = null
let searchSeq = 0

const categoryHits = computed(() => searchCategories(searchQuery.value, 8))

const showDropdown = computed(
  () => searchFocused.value && searchQuery.value.trim().length > 0
)

function sortBtnClass(key) {
  const active = marketStore.sortBy === key
  return [
    'px-3 py-1.5 rounded-md text-[9px] font-black uppercase tracking-widest transition-colors',
    active
      ? 'text-[#00e5ff] bg-[#00e5ff]/10 border border-[#00e5ff]/30 shadow-[0_0_10px_rgba(0,229,255,0.2)]'
      : 'text-zinc-500 border border-transparent hover:text-zinc-300',
  ]
}

/** Pull latest active markets for the selected category/subcategory */
function refreshMarkets() {
  marketStore.loadMatches()
}

function closeSearch() {
  searchFocused.value = false
}

function clearSearch() {
  searchQuery.value = ''
  marketHits.value = []
  searchFocused.value = false
}

function onSelectCategory(cat) {
  marketStore.navigateToCategory(cat.category, cat.subcategory)
  clearSearch()
}

function onSelectMarket(match) {
  emit('open', match)
  clearSearch()
}

function selectFirstResult() {
  if (categoryHits.value.length) {
    onSelectCategory(categoryHits.value[0])
    return
  }
  if (marketHits.value.length) {
    onSelectMarket(marketHits.value[0])
  }
}

async function runMarketSearch(q) {
  const seq = ++searchSeq
  const query = q.trim()
  if (!query) {
    marketHits.value = []
    isSearching.value = false
    return
  }

  // Instant local hits from current list + favorites
  const localPool = [...marketStore.matches, ...marketStore.favorites]
  const seen = new Set()
  const local = []
  const ql = query.toLowerCase()
  for (const m of localPool) {
    if (!m?.title || !String(m.title).toLowerCase().includes(ql)) continue
    const id = String(m.event_id)
    if (seen.has(id)) continue
    seen.add(id)
    local.push(m)
  }

  isSearching.value = true
  try {
    const data = await tradeApi.searchMarkets(query)
    if (seq !== searchSeq) return
    const remote = Array.isArray(data?.markets) ? data.markets : []
    for (const m of remote) {
      const id = String(m.event_id)
      if (seen.has(id)) continue
      seen.add(id)
      local.push(m)
    }
    marketHits.value = local.slice(0, 15)
  } catch {
    if (seq === searchSeq) marketHits.value = local.slice(0, 15)
  } finally {
    if (seq === searchSeq) isSearching.value = false
  }
}

watch(searchQuery, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q.trim()) {
    marketHits.value = []
    isSearching.value = false
    return
  }
  searchTimer = setTimeout(() => runMarketSearch(q), 220)
})

function onDocClick(e) {
  if (!searchWrapRef.value) return
  if (!searchWrapRef.value.contains(e.target)) {
    searchFocused.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onDocClick)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onDocClick)
  if (searchTimer) clearTimeout(searchTimer)
  marketStore._stopLiveWindowPoll()
})
</script>
