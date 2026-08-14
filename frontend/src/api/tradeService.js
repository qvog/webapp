import { apiFetch } from './http'

export const tradeApi = {
  getMarkets(category = 'most_traded', subcategory = 'all') {
    const q = new URLSearchParams({ category, subcategory })
    return apiFetch(`/api/markets?${q}`)
  },

  searchMarkets(query) {
    const q = new URLSearchParams({ q: query })
    return apiFetch(`/api/markets/search?${q}`)
  },

  getPositions() {
    return apiFetch('/api/positions')
  },

  placeOrder(payload) {
    return apiFetch('/api/order', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  panicSell(orderId) {
    return apiFetch(`/api/panic_sell/${encodeURIComponent(orderId)}`, {
      method: 'POST',
    })
  },

  /**
   * Manual resolve for stuck/ended positions.
   * @param {string} orderId
   * @param {number} exitPrice 0.0–1.0 (1.0 = win, 0.0 = loss, entry = drop/0 PnL)
   */
  resolvePosition(orderId, exitPrice) {
    return apiFetch(`/api/positions/${encodeURIComponent(orderId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ exit_price: Number(exitPrice) }),
    })
  },

  /** F10 flatten: market-sell all OPEN positions for a token */
  flatten(tokenId) {
    return apiFetch(`/api/flatten/${encodeURIComponent(tokenId)}`, {
      method: 'POST',
    })
  },

  /** Read-only PnL / strategy analytics (period: 24h|7d|30d|90d|1y|all) */
  getStatsSummary(period = 'all') {
    const q = new URLSearchParams({ period })
    return apiFetch(`/api/stats/summary?${q}`)
  },

  getStatsHistory(period = 'all') {
    const q = new URLSearchParams({ period })
    return apiFetch(`/api/stats/history?${q}`)
  },
}
