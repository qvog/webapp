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
    sortBy: 'volume',
    
    // 🎯 ЗАЩИТА ОТ RACE CONDITION
    _fetchId: 0
  }),
  
  getters: {
    filteredMatches(state) {
      let result = state.activeCategory === 'favorites' ? [...state.favorites] : [...state.matches];

      // 🎯 БРОНЕБОЙНАЯ СОРТИРОВКА
      result.sort((a, b) => {
        if (state.sortBy === 'date') {
          const now = Date.now();
          const tA = new Date(a.start_date).getTime() || 0;
          const tB = new Date(b.start_date).getTime() || 0;
          
          // 1. LIVE матчи абсолютно всегда наверху
          if (a.is_live && !b.is_live) return -1;
          if (!a.is_live && b.is_live) return 1;

          // 2. Если у обоих есть даты, вычисляем дистанцию до текущего момента
          if (tA && tB) {
              const diffA = tA - now;
              const diffB = tB - now;

              const isFutureA = diffA > 0;
              const isFutureB = diffB > 0;

              if (isFutureA && isFutureB) {
                // Оба в будущем: Ближайший матч (меньшая разница) выше
                const res = diffA - diffB;
                if (res !== 0) return res;
              } else if (!isFutureA && !isFutureB) {
                // Оба в прошлом: Самый свежий матч (ближе к нулю) выше
                const res = diffB - diffA;
                if (res !== 0) return res;
              } else if (isFutureA && !isFutureB) {
                // Будущее всегда выше прошлого
                return -1;
              } else if (!isFutureA && isFutureB) {
                return 1;
              }
          }
        }
        
        // 3. Fallback (Дефолт): Сортируем по деньгам (объему)
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
      
      // Маркируем этот запрос, чтобы убить Race Condition
      const currentId = ++this._fetchId; 

      this.isLoadingMarkets = true
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/markets?category=${fetchCategory}&subcategory=${fetchSub}`)
        const data = await res.json()
        
        // 🎯 Обновляем список ТОЛЬКО если пользователь не переключил вкладку в процессе загрузки
        if (this._fetchId === currentId) {
            this.matches = data || []
        }
      } catch (e) {
        console.error("Fetch markets error:", e)
        if (this._fetchId === currentId) {
            this.matches = []
        }
      } finally {
        if (this._fetchId === currentId) {
            this.isLoadingMarkets = false
        }
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