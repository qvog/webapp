import { apiFetch } from './http'

export const tradeApi = {
  getMarkets(category = 'most_traded', subcategory = 'all') {
    const q = new URLSearchParams({ category, subcategory })
    return apiFetch(`/api/markets?${q}`)
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
}
