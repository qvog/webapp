export const tradeApi = {
  async getMarkets(game = 'Dota 2') {
    const res = await fetch(`/api/markets?game=${game}`)
    return res.json()
  },
  
  async getPositions() {
    const res = await fetch('/api/positions')
    return res.json()
  },
  
  async placeOrder(payload) {
    const res = await fetch('/api/trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    return res.json()
  },
  
  async panicSell(orderId) {
    const res = await fetch('/api/panic_sell', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: orderId })
    })
    return res.json()
  }
}