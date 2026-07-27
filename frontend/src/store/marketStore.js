import { defineStore } from 'pinia'
import { tradeApi } from '../api/tradeService'

const FAV_KEY = 'qscalp_fav_v2'

export const useMarketStore = defineStore('market', {
  state: () => ({
    matches: [],
    openPositions: [],
    tradingMode: 'custom',
    tradeSize: 10,
    tpOffset: 5,
    slOffset: 15,
    activePreset: '4c',

    isLoadingMarkets: false,
    activeCategory: 'most_traded',
    activeSubcategory: 'all',

    favorites: JSON.parse(localStorage.getItem(FAV_KEY) || '[]'),
    isSidebarExpanded: false,
    sortBy: 'volume',

    _fetchId: 0,
  }),

  getters: {
    filteredMatches(state) {
      let result =
        state.activeCategory === 'favorites' ? [...state.favorites] : [...state.matches]

      if (['sports', 'esports'].includes(state.activeCategory)) {
        if (state.activeSubcategory === 'live') {
          result = result.filter((m) => m.is_live)
        } else if (state.activeSubcategory === 'starting soon') {
          const now = Date.now()
          result = result.filter(
            (m) => !m.is_live && m.start_date && new Date(m.start_date).getTime() > now
          )
        }
      }

      result.sort((a, b) => {
        if (state.sortBy === 'date') {
          const now = Date.now()
          const tA = new Date(a.start_date).getTime() || 0
          const tB = new Date(b.start_date).getTime() || 0

          if (a.is_live && !b.is_live) return -1
          if (!a.is_live && b.is_live) return 1

          if (tA && tB) {
            const diffA = tA - now
            const diffB = tB - now
            const isFutureA = diffA > 0
            const isFutureB = diffB > 0

            if (isFutureA && isFutureB) return diffA - diffB
            if (!isFutureA && !isFutureB) return diffB - diffA
            if (isFutureA && !isFutureB) return -1
            if (!isFutureA && isFutureB) return 1
          }
        }
        return (b.total_volume || 0) - (a.total_volume || 0)
      })

      return result
    },
  },

  actions: {
    async loadMatches() {
      if (this.activeCategory === 'favorites') return

      const fetchCategory = this.activeCategory
      const fetchSub = this.activeSubcategory
      const currentId = ++this._fetchId

      this.isLoadingMarkets = true
      try {
        const data = await tradeApi.getMarkets(fetchCategory, fetchSub)
        if (this._fetchId === currentId) {
          this.matches = Array.isArray(data) ? data : []
        }
      } catch {
        if (this._fetchId === currentId) this.matches = []
      } finally {
        if (this._fetchId === currentId) this.isLoadingMarkets = false
      }
    },

    setCategory(cat) {
      if (this.activeCategory === cat) return
      this.activeCategory = cat
      this.activeSubcategory = 'all'
      this.loadMatches()
    },

    setSubcategory(sub) {
      if (this.activeSubcategory === sub) return
      this.activeSubcategory = sub
      this.loadMatches()
    },

    toggleFavorite(match) {
      const idx = this.favorites.findIndex((f) => f.event_id === match.event_id)
      if (idx === -1) this.favorites.push(match)
      else this.favorites.splice(idx, 1)
      localStorage.setItem(FAV_KEY, JSON.stringify(this.favorites))
    },

    isFavorite(eventId) {
      return this.favorites.some((f) => f.event_id === eventId)
    },

    async loadPositions() {
      try {
        const data = await tradeApi.getPositions()
        if (data && data.success) this.openPositions = data.positions || []
      } catch {
        /* keep last known positions on transient errors */
      }
    },

    getTeamNameFromToken(tokenId) {
      const allMarkets = [...this.matches, ...this.favorites]
      for (const match of allMarkets) {
        for (const sub of match.sub_markets || []) {
          if (sub.token_id_yes === tokenId) return sub.out1 || 'YES'
          if (sub.token_id_no === tokenId) return sub.out2 || 'NO'
        }
      }
      return 'UNKNOWN'
    },
  },
})
