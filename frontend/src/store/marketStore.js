import { defineStore } from 'pinia'
import { tradeApi } from '../api/tradeService'
import { CRYPTO_LIVE_WINDOW_SUBS } from '../constants/categories'

const FAV_KEY = 'qscalp_fav_v2'
/** Silent refresh interval for rotating 5m/15m/1h/4h crypto windows. */
const LIVE_WINDOW_POLL_MS = 15_000

export const useMarketStore = defineStore('market', {
  state: () => ({
    matches: [],
    openPositions: [],
    tradingMode: 'custom',
    tradeSize: 10,
    tpOffset: 5,
    slOffset: 15,
    /** Active strategy key: custom | draft_early | draft_win | short_range | high_range | all_in_half */
    activeStrategy: 'custom',
    /** @deprecated legacy alias — prefer activeStrategy */
    activePreset: 'custom',

    /** Most recent successfully placed order id (Ctrl+Z undo target) */
    lastPlacedOrderId: null,

    isLoadingMarkets: false,
    activeCategory: 'most_traded',
    activeSubcategory: 'all',

    favorites: JSON.parse(localStorage.getItem(FAV_KEY) || '[]'),
    isSidebarExpanded: false,
    sortBy: 'volume',

    _fetchId: 0,
    _liveWindowTimer: null,
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

    isLiveCryptoWindow(state) {
      return (
        state.activeCategory === 'crypto' && CRYPTO_LIVE_WINDOW_SUBS.has(state.activeSubcategory)
      )
    },
  },

  actions: {
    async loadMatches({ silent = false } = {}) {
      if (this.activeCategory === 'favorites') {
        this._stopLiveWindowPoll()
        return
      }

      const fetchCategory = this.activeCategory
      const fetchSub = this.activeSubcategory
      const currentId = ++this._fetchId

      if (!silent) this.isLoadingMarkets = true
      try {
        const data = await tradeApi.getMarkets(fetchCategory, fetchSub)
        if (this._fetchId === currentId) {
          this.matches = Array.isArray(data) ? data : []
        }
      } catch {
        if (this._fetchId === currentId && !silent) this.matches = []
      } finally {
        if (this._fetchId === currentId) this.isLoadingMarkets = false
        this._syncLiveWindowPoll()
      }
    },

    _stopLiveWindowPoll() {
      if (this._liveWindowTimer) {
        clearInterval(this._liveWindowTimer)
        this._liveWindowTimer = null
      }
    },

    _syncLiveWindowPoll() {
      this._stopLiveWindowPoll()
      if (!this.isLiveCryptoWindow) return
      // Silently rotate windows when the current 5m/15m/… slot expires
      this._liveWindowTimer = setInterval(() => {
        if (this.isLiveCryptoWindow) this.loadMatches({ silent: true })
        else this._stopLiveWindowPoll()
      }, LIVE_WINDOW_POLL_MS)
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

    /** Navigate from search: open category + subcategory in one shot. */
    navigateToCategory(category, subcategory = 'all') {
      const cat = category || 'most_traded'
      const sub = subcategory || 'all'
      if (this.activeCategory === cat && this.activeSubcategory === sub) {
        this.loadMatches()
        return
      }
      this.activeCategory = cat
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

    /** Remember last successful /order id for Ctrl+Z undo. */
    setLastPlacedOrderId(orderId) {
      this.lastPlacedOrderId = orderId || null
    },

    clearLastPlacedOrderId() {
      this.lastPlacedOrderId = null
    },

    /**
     * Ctrl+Z: panic-sell / cancel the last placed order.
     * @returns {Promise<{success:boolean, message?:string, error?:string, skipped?:boolean}>}
     */
    async undoLastOrder() {
      const orderId = this.lastPlacedOrderId
      if (!orderId) {
        return { success: false, skipped: true, error: 'No last order to undo' }
      }
      try {
        const data = await tradeApi.panicSell(orderId)
        // Always clear so we don't double-fire on the same id
        this.lastPlacedOrderId = null
        if (data && data.success) {
          await this.loadPositions()
          return { success: true, message: data.message || 'Last order canceled' }
        }
        return {
          success: false,
          error: (data && data.error) || 'Undo failed',
        }
      } catch (e) {
        this.lastPlacedOrderId = null
        return { success: false, error: e.message || 'Undo failed' }
      }
    },

    getTeamNameFromToken(tokenId) {
      const meta = this.resolveMarketFromToken(tokenId)
      return meta.teamName || 'UNKNOWN'
    },

    /**
     * Resolve match/event metadata for a CLOB token_id from loaded markets + favorites.
     * @returns {{ teamName: string|null, title: string|null, image: string|null, question: string|null }}
     */
    resolveMarketFromToken(tokenId) {
      const empty = { teamName: null, title: null, image: null, question: null }
      if (tokenId == null || tokenId === '') return empty
      const tid = String(tokenId)
      const allMarkets = [...this.matches, ...this.favorites]
      for (const match of allMarkets) {
        for (const sub of match.sub_markets || []) {
          const yes = sub.token_id_yes != null ? String(sub.token_id_yes) : ''
          const no = sub.token_id_no != null ? String(sub.token_id_no) : ''
          if (yes === tid || no === tid) {
            const teamName =
              yes === tid ? sub.out1 || 'YES' : sub.out2 || 'NO'
            return {
              teamName,
              title: match.title || null,
              image: match.image || null,
              question: sub.question || match.title || null,
            }
          }
        }
      }
      return empty
    },

    /** Event icon URL for a token, or null if unknown. */
    getImageFromToken(tokenId) {
      return this.resolveMarketFromToken(tokenId).image || null
    },
  },
})
