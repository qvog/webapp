import { reactive, ref } from 'vue'
import { useToast } from 'vue-toastification'

const WS_URL = 'wss://ws-subscriptions-clob.polymarket.com/ws/market'
const PING_MS = 10_000
/** Only force-reconnect if the stream is truly dead (no book/deltas and no PONG). */
const IDLE_RECONNECT_MS = 45_000
const WATCHDOG_MS = 5_000
const TAPE_MAX = 20
const PROFILE_WINDOW_MS = 60_000
/** Min size drop (shares) to count as aggressive trade print (not a full cancel→0). */
const TAPE_MIN_DROP = 0.5

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
  const midYes = ref(0)
  const midNo = ref(0)
  const imbalanceYes = ref(0)
  const imbalanceNo = ref(0)
  /** Last ~20 inferred aggressive prints for YES / NO. */
  const tapeYes = ref([])
  const tapeNo = ref([])
  /** Book update events per second (shared WS stream). */
  const velocity = ref(0)
  /**
   * Volume profile: price(cents) → volume over last 60s (from inferred tape).
   * Separate maps for YES / NO tokens.
   */
  const volumeProfileYes = ref({})
  const volumeProfileNo = ref({})
  const isConnecting = ref(false)

  let ws = null
  let watchdogInterval = null
  let pingInterval = null
  let metricsLoop = null
  let velocityLoop = null
  let profilePruneLoop = null
  let activeMarketCache = null
  let lastMessageTime = Date.now()
  let hasBookSnapshot = false
  let reconnectTimer = null
  let connectGeneration = 0
  let eventsThisSecond = 0

  // Ring of raw tape events with timestamps for 60s volume profile
  let tapeHistoryYes = []
  let tapeHistoryNo = []

  const clearLadder = () => {
    for (let i = 0; i < 99; i++) {
      ladderYes[i].bidSize = 0
      ladderYes[i].askSize = 0
      ladderNo[i].bidSize = 0
      ladderNo[i].askSize = 0
    }
  }

  const resetMicrostructure = () => {
    tapeYes.value = []
    tapeNo.value = []
    tapeHistoryYes = []
    tapeHistoryNo = []
    volumeProfileYes.value = {}
    volumeProfileNo.value = {}
    velocity.value = 0
    eventsThisSecond = 0
    midYes.value = 0
    midNo.value = 0
    imbalanceYes.value = 0
    imbalanceNo.value = 0
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
    if (velocityLoop) {
      clearInterval(velocityLoop)
      velocityLoop = null
    }
    if (profilePruneLoop) {
      clearInterval(profilePruneLoop)
      profilePruneLoop = null
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
    resetMicrostructure()
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

  /** Top-N levels by price proximity to touch (bids high→low, asks low→high). */
  const topNSize = (ladder, side, n = 5) => {
    const levels = []
    if (side === 'bid') {
      for (let i = 0; i < 99 && levels.length < n; i++) {
        if (ladder[i].bidSize > 0) levels.push(ladder[i].bidSize)
      }
    } else {
      for (let i = 98; i >= 0 && levels.length < n; i--) {
        if (ladder[i].askSize > 0) levels.push(ladder[i].askSize)
      }
    }
    return levels.reduce((a, b) => a + b, 0)
  }

  const calcImbalance = (ladder) => {
    const bidSum = topNSize(ladder, 'bid', 5)
    const askSum = topNSize(ladder, 'ask', 5)
    const denom = bidSum + askSum
    if (denom <= 0) return 0
    return (bidSum - askSum) / denom
  }

  const rebuildVolumeProfile = (history) => {
    const now = Date.now()
    const cutoff = now - PROFILE_WINDOW_MS
    const fresh = history.filter((t) => t.ts >= cutoff)
    const profile = {}
    for (const t of fresh) {
      profile[t.price] = (profile[t.price] || 0) + t.size
    }
    return { fresh, profile }
  }

  /**
   * Infer aggressive trade print when resting size drops but level remains (>0).
   * - Ask size drop → aggressive BUY (lifted offer)
   * - Bid size drop → aggressive SELL (hit bid)
   */
  const inferTapePrint = (ladder, priceCents, side, newSize, isYes) => {
    const idx = 99 - priceCents
    if (idx < 0 || idx > 98) return

    const prev =
      side === 'BUY' ? ladder[idx].bidSize : side === 'SELL' ? ladder[idx].askSize : 0
    const next = parseFloat(newSize) || 0

    // Full wipe to 0 is treated as cancel/pull — skip (per spec)
    if (next <= 0 || prev <= 0) return

    const drop = prev - next
    if (drop < TAPE_MIN_DROP) return

    // BUY side resting size drop → sell aggression; SELL side drop → buy aggression
    const printSide = side === 'BUY' ? 'SELL' : 'BUY'
    const print = {
      price: priceCents,
      size: drop,
      side: printSide,
      ts: Date.now(),
    }

    if (isYes) {
      tapeHistoryYes.push(print)
      const { fresh, profile } = rebuildVolumeProfile(tapeHistoryYes)
      tapeHistoryYes = fresh
      volumeProfileYes.value = profile
      tapeYes.value = [...tapeHistoryYes].slice(-TAPE_MAX).reverse()
    } else {
      tapeHistoryNo.push(print)
      const { fresh, profile } = rebuildVolumeProfile(tapeHistoryNo)
      tapeHistoryNo = fresh
      volumeProfileNo.value = profile
      tapeNo.value = [...tapeHistoryNo].slice(-TAPE_MAX).reverse()
    }
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
      resetMicrostructure()
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
      eventsThisSecond = 0

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

      // Velocity: book-update events per second
      velocityLoop = setInterval(() => {
        if (gen !== connectGeneration) return
        velocity.value = eventsThisSecond
        eventsThisSecond = 0
      }, 1000)

      // Prune volume profile window
      profilePruneLoop = setInterval(() => {
        if (gen !== connectGeneration) return
        const y = rebuildVolumeProfile(tapeHistoryYes)
        tapeHistoryYes = y.fresh
        volumeProfileYes.value = y.profile
        const n = rebuildVolumeProfile(tapeHistoryNo)
        tapeHistoryNo = n.fresh
        volumeProfileNo.value = n.profile
      }, 5000)

      // Toast only on first open of a market, not on silent reconnects
      if (!silent) {
        toast.success('⚡ Connected', { timeout: 1200 })
      }

      // Metrics loop: BBO, spread, mid, imbalance
      metricsLoop = setInterval(() => {
        const calcMetrics = (ladder) => {
          let bB = 0
          let bA = 1
          for (let i = 0; i < 99; i++) {
            if (ladder[i].bidSize > 0 && ladder[i].price / 100 > bB) bB = ladder[i].price / 100
            if (ladder[i].askSize > 0 && ladder[i].price / 100 < bA) bA = ladder[i].price / 100
          }
          if (bA === 1) bA = 0
          const sp = Math.max(0, bA - bB)
          const mid = bB > 0 && bA > 0 ? (bB + bA) / 2 : bB || bA || 0
          return { bB, bA, sp, mid }
        }
        const mY = calcMetrics(ladderYes)
        bestBidYes.value = mY.bB
        bestAskYes.value = mY.bA
        spreadYes.value = mY.sp
        midYes.value = mY.mid
        imbalanceYes.value = calcImbalance(ladderYes)

        const mN = calcMetrics(ladderNo)
        bestBidNo.value = mN.bB
        bestAskNo.value = mN.bA
        spreadNo.value = mN.sp
        midNo.value = mN.mid
        imbalanceNo.value = calcImbalance(ladderNo)
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
          eventsThisSecond += 1
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
          eventsThisSecond += 1
          ;(ev.price_changes || []).forEach((pc) => {
            const pcToken = pc.asset_id ? pc.asset_id.toLowerCase() : null
            const isYes = pcToken === tokenYes
            const isNo = pcToken === tokenNo
            const targetLadder = isYes ? ladderYes : isNo ? ladderNo : null
            if (!targetLadder) return

            const p = Math.round(parseFloat(pc.price) * 100)
            if (p >= 1 && p <= 99) {
              // Infer tape BEFORE mutating ladder (need previous size)
              if (pc.side === 'BUY' || pc.side === 'SELL') {
                inferTapePrint(targetLadder, p, pc.side, pc.size, isYes)
              }
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
    midYes,
    midNo,
    imbalanceYes,
    imbalanceNo,
    tapeYes,
    tapeNo,
    velocity,
    volumeProfileYes,
    volumeProfileNo,
    isConnecting,
    connectToMarket,
    disconnect,
  }
}
