import { reactive, ref } from 'vue'
import { useToast } from 'vue-toastification'

const WS_URL = 'wss://ws-subscriptions-clob.polymarket.com/ws/market'
const PING_MS = 10_000
/** Only force-reconnect if the stream is truly dead (no book/deltas and no PONG). */
const IDLE_RECONNECT_MS = 45_000
const WATCHDOG_MS = 5_000

export function useOrderBook() {
  const toast = useToast()

  const createLadder = () =>
    reactive(
      Array.from({ length: 99 }, (_, i) => ({
        price: 99 - i,
        bidSize: 0,
        askSize: 0,
      }))
    )

  const ladderYes = createLadder()
  const ladderNo = createLadder()

  const spreadYes = ref(0)
  const spreadNo = ref(0)
  const bestBidYes = ref(0)
  const bestAskYes = ref(1)
  const bestBidNo = ref(0)
  const bestAskNo = ref(1)
  /** Top-3 bid share of top-3 depth: (sumBids / (sumBids+sumAsks)) * 100 */
  const imbalanceYes = ref(50)
  const imbalanceNo = ref(50)
  /** Max sizes across the full ladder (heatmap 100% baseline) */
  const maxBidSizeYes = ref(0)
  const maxAskSizeYes = ref(0)
  const maxBidSizeNo = ref(0)
  const maxAskSizeNo = ref(0)
  const isConnecting = ref(false)

  /**
   * Book depth metrics for one ladder (99 levels, price 99→1).
   * - Top-3 bids: highest prices with bidSize > 0
   * - Top-3 asks: lowest prices with askSize > 0
   * - imbalancePercent = (sumBids / (sumBids + sumAsks)) * 100
   * - max_bid_size / max_ask_size across all levels
   */
  const calcBookMetrics = (ladder) => {
    let bB = 0
    let bA = 1
    let maxBid = 0
    let maxAsk = 0
    const topBidSizes = []
    const topAskSizes = []

    // Ladder index 0 = 99¢, index 98 = 1¢
    for (let i = 0; i < 99; i++) {
      const bid = ladder[i].bidSize || 0
      const ask = ladder[i].askSize || 0
      if (bid > maxBid) maxBid = bid
      if (ask > maxAsk) maxAsk = ask
      if (bid > 0 && ladder[i].price / 100 > bB) bB = ladder[i].price / 100
      if (ask > 0 && ladder[i].price / 100 < bA) bA = ladder[i].price / 100
    }
    if (bA === 1) bA = 0

    // Top-3 bid levels (best = highest price first)
    for (let i = 0; i < 99 && topBidSizes.length < 3; i++) {
      if (ladder[i].bidSize > 0) topBidSizes.push(ladder[i].bidSize)
    }
    // Top-3 ask levels (best = lowest price first)
    for (let i = 98; i >= 0 && topAskSizes.length < 3; i--) {
      if (ladder[i].askSize > 0) topAskSizes.push(ladder[i].askSize)
    }

    const sumBids = topBidSizes.reduce((a, b) => a + b, 0)
    const sumAsks = topAskSizes.reduce((a, b) => a + b, 0)
    const total = sumBids + sumAsks
    const imbalancePercent = total > 0 ? (sumBids / total) * 100 : 50

    return {
      bB,
      bA,
      sp: Math.max(0, bA - bB),
      imbalancePercent,
      maxBidSize: maxBid,
      maxAskSize: maxAsk,
    }
  }

  let ws = null
  let watchdogInterval = null
  let pingInterval = null
  let metricsLoop = null
  let activeMarketCache = null
  let lastMessageTime = Date.now()
  let hasBookSnapshot = false
  let reconnectTimer = null
  let connectGeneration = 0

  const clearLadder = () => {
    for (let i = 0; i < 99; i++) {
      ladderYes[i].bidSize = 0
      ladderYes[i].askSize = 0
      ladderNo[i].bidSize = 0
      ladderNo[i].askSize = 0
    }
  }

  const teardownSocket = () => {
    if (ws) {
      ws.onopen = null
      ws.onmessage = null
      ws.onerror = null
      ws.onclose = null
      try {
        ws.close()
      } catch {
        /* ignore */
      }
      ws = null
    }
    if (watchdogInterval) {
      clearInterval(watchdogInterval)
      watchdogInterval = null
    }
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }
    if (metricsLoop) {
      clearInterval(metricsLoop)
      metricsLoop = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  /** Fully stop streaming (user navigated away). */
  const disconnect = () => {
    activeMarketCache = null
    hasBookSnapshot = false
    connectGeneration += 1
    teardownSocket()
    isConnecting.value = false
  }

  const scheduleSilentReconnect = (market, gen) => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      if (gen !== connectGeneration) return
      if (activeMarketCache !== market) return
      connectToMarket(market, null, { silent: true })
    }, 1000)
  }

  /**
   * @param {object} subMarket
   * @param {Function|null} onReadyCallback
   * @param {{ silent?: boolean }} opts  silent=true: keep last book, no overlay/toast (WS reconnect)
   */
  const connectToMarket = (subMarket, onReadyCallback = null, opts = {}) => {
    const silent = Boolean(opts.silent)
    const gen = ++connectGeneration

    teardownSocket()
    activeMarketCache = subMarket

    const tokenYes = subMarket.token_id_yes.toLowerCase()
    const tokenNo = subMarket.token_id_no ? subMarket.token_id_no.toLowerCase() : null

    if (!silent) {
      // New market selection only — wipe book and show connecting state
      clearLadder()
      hasBookSnapshot = false
      isConnecting.value = true
    }
    // Silent reconnect: keep existing ladder until a fresh "book" snapshot arrives

    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      if (gen !== connectGeneration) return

      const assets = [tokenYes]
      if (tokenNo) assets.push(tokenNo)
      ws.send(JSON.stringify({ assets_ids: assets, type: 'market' }))

      lastMessageTime = Date.now()

      // Keepalive — Polymarket responds with "PONG"
      pingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          try {
            ws.send('PING')
          } catch {
            /* ignore */
          }
        }
      }, PING_MS)

      // Reconnect only if the stream is completely silent (no ticks / pongs)
      watchdogInterval = setInterval(() => {
        if (gen !== connectGeneration) return
        if (!activeMarketCache || reconnectTimer) return
        if (Date.now() - lastMessageTime > IDLE_RECONNECT_MS) {
          console.warn('OrderBook: stream idle, silent reconnect...')
          const market = activeMarketCache
          // Drop dead socket without wiping the ladder; reconnect quietly
          if (ws) {
            ws.onclose = null
            try {
              ws.close()
            } catch {
              /* ignore */
            }
            ws = null
          }
          scheduleSilentReconnect(market, gen)
        }
      }, WATCHDOG_MS)

      // Toast only on first open of a market, not on silent reconnects
      if (!silent) {
        toast.success('⚡ Connected', { timeout: 1200 })
      }

      // Metrics loop (spread + imbalance + heatmap baselines)
      metricsLoop = setInterval(() => {
        const mY = calcBookMetrics(ladderYes)
        bestBidYes.value = mY.bB
        bestAskYes.value = mY.bA
        spreadYes.value = mY.sp
        imbalanceYes.value = mY.imbalancePercent
        maxBidSizeYes.value = mY.maxBidSize
        maxAskSizeYes.value = mY.maxAskSize

        const mN = calcBookMetrics(ladderNo)
        bestBidNo.value = mN.bB
        bestAskNo.value = mN.bA
        spreadNo.value = mN.sp
        imbalanceNo.value = mN.imbalancePercent
        maxBidSizeNo.value = mN.maxBidSize
        maxAskSizeNo.value = mN.maxAskSize
      }, 100)
    }

    ws.onmessage = (event) => {
      if (gen !== connectGeneration) return
      lastMessageTime = Date.now()

      if (event.data === 'PONG') return

      let data
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      const events = Array.isArray(data) ? data : [data]

      events.forEach((ev) => {
        // Full book snapshot
        if (ev.event_type === 'book') {
          const evToken = ev.asset_id ? ev.asset_id.toLowerCase() : null
          const targetLadder =
            evToken === tokenYes ? ladderYes : evToken === tokenNo ? ladderNo : null
          if (!targetLadder) return

          for (let i = 0; i < 99; i++) {
            targetLadder[i].bidSize = 0
            targetLadder[i].askSize = 0
          }
          ;(ev.bids || []).forEach((b) => {
            const p = Math.round(parseFloat(b.price) * 100)
            if (p >= 1 && p <= 99) targetLadder[99 - p].bidSize = parseFloat(b.size)
          })
          ;(ev.asks || []).forEach((a) => {
            const p = Math.round(parseFloat(a.price) * 100)
            if (p >= 1 && p <= 99) targetLadder[99 - p].askSize = parseFloat(a.size)
          })

          hasBookSnapshot = true
          isConnecting.value = false
          if (onReadyCallback) {
            const cb = onReadyCallback
            onReadyCallback = null
            cb()
          }
        }
        // Incremental price changes
        else if (ev.event_type === 'price_change') {
          ;(ev.price_changes || []).forEach((pc) => {
            const pcToken = pc.asset_id ? pc.asset_id.toLowerCase() : null
            const targetLadder =
              pcToken === tokenYes ? ladderYes : pcToken === tokenNo ? ladderNo : null
            if (!targetLadder) return

            const p = Math.round(parseFloat(pc.price) * 100)
            if (p >= 1 && p <= 99) {
              if (pc.side === 'BUY') {
                targetLadder[99 - p].bidSize = parseFloat(pc.size)
              } else if (pc.side === 'SELL') {
                targetLadder[99 - p].askSize = parseFloat(pc.size)
              }
            }
          })
        }
      })
    }

    ws.onerror = () => {
      // onclose will handle reconnect
    }

    ws.onclose = () => {
      if (gen !== connectGeneration) return
      const market = activeMarketCache
      if (!market) return
      // Keep last book visible; reconnect quietly in the background
      scheduleSilentReconnect(market, gen)
    }
  }

  return {
    ladderYes,
    ladderNo,
    spreadYes,
    spreadNo,
    bestBidYes,
    bestAskYes,
    bestBidNo,
    bestAskNo,
    imbalanceYes,
    imbalanceNo,
    maxBidSizeYes,
    maxAskSizeYes,
    maxBidSizeNo,
    maxAskSizeNo,
    isConnecting,
    connectToMarket,
    disconnect,
    /** Pure helper — also used by tests / offline UI if needed */
    calcBookMetrics,
  }
}
