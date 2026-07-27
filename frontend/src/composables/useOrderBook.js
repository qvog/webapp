import { reactive, ref } from 'vue'
import { useToast } from 'vue-toastification'

export function useOrderBook() {
  const toast = useToast()

  const createLadder = () => reactive(Array.from({ length: 99 }, (_, i) => ({
    price: 99 - i,
    bidSize: 0,
    askSize: 0
  })))

  const ladderYes = createLadder()
  const ladderNo = createLadder()

  const spreadYes = ref(0); const spreadNo = ref(0)
  const bestBidYes = ref(0); const bestAskYes = ref(1)
  const bestBidNo = ref(0); const bestAskNo = ref(1)
  const isConnecting = ref(false)

  let ws = null
  let watchdogInterval = null
  let activeMarketCache = null
  let metricsLoop = null
  let lastMessageTime = Date.now() // 🎯 Запоминаем время последнего тика

  const teardownSocket = () => {
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    if (watchdogInterval) {
      clearInterval(watchdogInterval)
      watchdogInterval = null
    }
    if (metricsLoop) {
      clearInterval(metricsLoop)
      metricsLoop = null
    }
  }

  /** Fully stop streaming (user navigated away). */
  const disconnect = () => {
    activeMarketCache = null
    teardownSocket()
  }

  const connectToMarket = (subMarket, onReadyCallback = null) => {
    teardownSocket()
    isConnecting.value = true
    activeMarketCache = subMarket

    const tokenYes = subMarket.token_id_yes.toLowerCase()
    const tokenNo = subMarket.token_id_no ? subMarket.token_id_no.toLowerCase() : null

    // Мгновенная очистка без удаления строк
    for (let i = 0; i < 99; i++) {
      ladderYes[i].bidSize = 0; ladderYes[i].askSize = 0;
      ladderNo[i].bidSize = 0; ladderNo[i].askSize = 0;
    }

    ws = new WebSocket(`wss://ws-subscriptions-clob.polymarket.com/ws/market`)

    ws.onopen = () => {
      let assets = [tokenYes]; if (tokenNo) assets.push(tokenNo)
      ws.send(JSON.stringify({ assets_ids: assets, type: "market" }))
      toast.success("⚡ Success!", { timeout: 1500 })
      
      lastMessageTime = Date.now()

      // Passive watchdog: reconnect if no ticks for 15s
      watchdogInterval = setInterval(() => {
        if (Date.now() - lastMessageTime > 15000) {
          console.warn('HFT Watchdog: stream idle 15s, reconnecting...')
          const market = activeMarketCache
          teardownSocket()
          if (market) connectToMarket(market)
        }
      }, 5000)
    }

    ws.onmessage = (event) => {
      lastMessageTime = Date.now() // 🎯 Обновляем таймер жизни при ЛЮБОМ тике
      
      if (event.data === "PONG") return 

      let data;
      try { data = JSON.parse(event.data) } catch(e) { return }
      const events = Array.isArray(data) ? data : [data]

      events.forEach(ev => {
        // 1. ПОЛНЫЙ СЛЕПОК (Синхронизация)
        if (ev.event_type === "book") {
          const evToken = ev.asset_id ? ev.asset_id.toLowerCase() : null
          const targetLadder = evToken === tokenYes ? ladderYes : (evToken === tokenNo ? ladderNo : null)
          if (!targetLadder) return

          for (let i = 0; i < 99; i++) { targetLadder[i].bidSize = 0; targetLadder[i].askSize = 0; }
          ;(ev.bids || []).forEach(b => {
            const p = Math.round(parseFloat(b.price) * 100)
            if (p >= 1 && p <= 99) targetLadder[99 - p].bidSize = parseFloat(b.size)
          });
          ;(ev.asks || []).forEach(a => {
            const p = Math.round(parseFloat(a.price) * 100)
            if (p >= 1 && p <= 99) targetLadder[99 - p].askSize = parseFloat(a.size)
          });
          isConnecting.value = false
          if (onReadyCallback) { onReadyCallback(); onReadyCallback = null }
        }
        
        // 2. ПУЛЕМЕТ ДЕЛЬТ (M249)
        else if (ev.event_type === "price_change") {
          ;(ev.price_changes || []).forEach(pc => {
            const pcToken = pc.asset_id ? pc.asset_id.toLowerCase() : null
            const targetLadder = pcToken === tokenYes ? ladderYes : (pcToken === tokenNo ? ladderNo : null)
            if (!targetLadder) return 

            const p = Math.round(parseFloat(pc.price) * 100)
            if (p >= 1 && p <= 99) {
              if (pc.side === "BUY") {
                targetLadder[99 - p].bidSize = parseFloat(pc.size)
              }
              else if (pc.side === "SELL") {
                targetLadder[99 - p].askSize = parseFloat(pc.size)
              }
            }
          })
        }
      })
    }

    ws.onclose = () => {
      const market = activeMarketCache
      if (market && Date.now() - lastMessageTime < 15000) {
        setTimeout(() => {
          if (activeMarketCache === market) connectToMarket(market)
        }, 1000)
      }
    }

    // Метрики (Считаем в дробных долях 0.74 для PnL)
    metricsLoop = setInterval(() => {
      const calcMetrics = (ladder) => {
        let bB = 0, bA = 1
        for (let i = 0; i < 99; i++) {
          if (ladder[i].bidSize > 0 && (ladder[i].price / 100) > bB) bB = ladder[i].price / 100
          if (ladder[i].askSize > 0 && (ladder[i].price / 100) < bA) bA = ladder[i].price / 100
        }
        if (bA === 1) bA = 0
        return { bB, bA, sp: Math.max(0, bA - bB) }
      }
      const mY = calcMetrics(ladderYes); bestBidYes.value = mY.bB; bestAskYes.value = mY.bA; spreadYes.value = mY.sp;
      const mN = calcMetrics(ladderNo); bestBidNo.value = mN.bB; bestAskNo.value = mN.bA; spreadNo.value = mN.sp;
    }, 100)
  }

  return {
    ladderYes, ladderNo,
    spreadYes, spreadNo, bestBidYes, bestAskYes, bestBidNo, bestAskNo,
    isConnecting, connectToMarket, disconnect
  }
}