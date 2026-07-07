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
    activeCategory: 'most_traded',
    activeSubcategory: 'all',
    
    favorites: JSON.parse(localStorage.getItem('qscalp_fav_v2') || '[]'),
    isSidebarExpanded: false,
    sortBy: 'volume',
    
    _fetchId: 0
  }),
  
  getters: {
    filteredMatches(state) {
      let result = state.activeCategory === 'favorites' ? [...state.favorites] : [...state.matches];

      if (['sports', 'esports'].includes(state.activeCategory)) {
        if (state.activeSubcategory === 'live') {
          result = result.filter(m => m.is_live);
        } else if (state.activeSubcategory === 'starting soon') {
          const now = Date.now();
          result = result.filter(m => !m.is_live && m.start_date && (new Date(m.start_date).getTime() > now));
        }
      }

      result.sort((a, b) => {
        if (state.sortBy === 'date') {
          const now = Date.now();
          const tA = new Date(a.start_date).getTime() || 0;
          const tB = new Date(b.start_date).getTime() || 0;
          
          if (a.is_live && !b.is_live) return -1;
          if (!a.is_live && b.is_live) return 1;

          if (tA && tB) {
              const diffA = tA - now;
              const diffB = tB - now;
              const isFutureA = diffA > 0;
              const isFutureB = diffB > 0;

              if (isFutureA && isFutureB) return diffA - diffB;
              if (!isFutureA && !isFutureB) return diffB - diffA;
              if (isFutureA && !isFutureB) return -1;
              if (!isFutureA && isFutureB) return 1;
          }
        }
        return b.total_volume - a.total_volume;
      });

      return result;
    }
  },

  actions: {
    async loadMatches() {
      if (this.activeCategory === 'favorites') return

      const fetchCategory = this.activeCategory 
      const fetchSub = this.activeSubcategory
      
      const currentId = ++this._fetchId; 

      this.isLoadingMarkets = true
      try {
        // 🎯 ИСПРАВЛЕНО: Используем относительный путь для работы через Vite Proxy
        const res = await fetch(`/api/markets?category=${fetchCategory}&subcategory=${fetchSub}`)
        const data = await res.json()
        
        if (this._fetchId === currentId) {
            this.matches = data || []
        }
      } catch (e) {
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
      const idx = this.favorites.findIndex(f => f.event_id === match.event_id)
      if (idx === -1) this.favorites.push(match)
      else this.favorites.splice(idx, 1)
      localStorage.setItem('qscalp_fav_v2', JSON.stringify(this.favorites))
    },

    async loadPositions() {
      try {
        // 🎯 ИСПРАВЛЕНО: Относительный путь
        const res = await fetch('/api/positions')
        const data = await res.json()
        if (data && data.success) this.openPositions = data.positions || []
      } catch (e) {}
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