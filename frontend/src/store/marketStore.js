import { defineStore } from 'pinia'

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
    activeCategory: 'sports',    
    activeSubcategory: 'all',
    
    favorites: JSON.parse(localStorage.getItem('qscalp_fav_v2') || '[]'),
    isSidebarExpanded: false,
    sortBy: 'volume' 
  }),
  
  getters: {
    filteredMatches(state) {
      let result = []
      
      if (state.activeCategory === 'favorites') {
        result = [...state.favorites]
      } else {
        result = [...state.matches]
        if (state.activeCategory === 'live') {
          result = result.filter(m => m.is_live)
        }
      }

      // 🎯 ПРАВИЛЬНАЯ СОРТИРОВКА (d2 - d1 выводит ближайшие/новые сверху)
      if (state.sortBy === 'volume') {
        result.sort((a, b) => b.total_volume - a.total_volume)
      } else if (state.sortBy === 'date') {
        result.sort((a, b) => {
          const d1 = new Date(a.start_date).getTime() || 0
          const d2 = new Date(b.start_date).getTime() || 0
          return d2 - d1 
        })
      }

      return result
    }
  },

  actions: {
    async loadMatches() {
      if (this.activeCategory === 'favorites') return

      const fetchCategory = this.activeCategory === 'live' ? 'sports' : this.activeCategory
      const fetchSub = this.activeSubcategory

      this.isLoadingMarkets = true
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/markets?category=${fetchCategory}&subcategory=${fetchSub}`)
        this.matches = await res.json() || []
      } catch (e) {
        console.error("Fetch markets error:", e)
        this.matches = []
      } finally {
        this.isLoadingMarkets = false
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
      const idx = this.favorites.findIndex(f => f.event_id === match.event_id)
      if (idx === -1) {
        this.favorites.push(match)
      } else {
        this.favorites.splice(idx, 1)
      }
      localStorage.setItem('qscalp_fav_v2', JSON.stringify(this.favorites))
    },

    async loadPositions() {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/positions')
        const data = await res.json()
        if (data && data.success) {
          this.openPositions = data.positions || []
        }
      } catch (e) {
        console.error("Fetch positions error:", e)
      }
    },
    
    getTeamNameFromToken(tokenId) {
      const allMarkets = [...this.matches, ...this.favorites]
      for (const match of allMarkets) {
        for (const sub of match.sub_markets) {
          if (sub.token_id_yes === tokenId) return sub.out1 || "YES"
          if (sub.token_id_no === tokenId) return sub.out2 || "NO"
        }
      }
      return "UNKNOWN"
    }
  }
})