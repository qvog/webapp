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
  let pingInterval = null
  let activeMarketCache = null
  let metricsLoop = null

  const disconnect = () => {
    if (ws) { ws.onclose = null; ws.close(); ws = null }
    if (pingInterval) { clearInterval(pingInterval); pingInterval = null }
    if (metricsLoop) { clearInterval(metricsLoop); metricsLoop = null }
  }

  const connectToMarket = (subMarket, onReadyCallback = null) => {
    disconnect()
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
      toast.success("⚡ HFT Stream Connected", { timeout: 1500 })

      // 🎯 МЯГКИЙ PING: Просто держим связь, не обрывая сокет
      pingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send("PING")
        }
      }, 10000)
    }

    ws.onmessage = (event) => {
      if (event.data === "PONG") return // Игнорируем технические ответы

      let data;
      try { data = JSON.parse(event.data) } catch(e) { return }
      const events = Array.isArray(data) ? data : [data]

      events.forEach(ev => {
        const evToken = ev.asset_id ? ev.asset_id.toLowerCase() : null
        const targetLadder = evToken === tokenYes ? ladderYes : (evToken === tokenNo ? ladderNo : null)
        if (!targetLadder) return

        if (ev.event_type === "book") {
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
        else if (ev.event_type === "price_change") {
          const applyUpdates = (arr, isBid) => {
            arr.forEach(i => {
              const p = Math.round(parseFloat(i.price) * 100)
              if (p >= 1 && p <= 99) {
                if (isBid) targetLadder[99 - p].bidSize = parseFloat(i.size)
                else targetLadder[99 - p].askSize = parseFloat(i.size)
              }
            })
          }
          if (ev.changes && ev.changes.length > 0) {
            applyUpdates(ev.changes.filter(c => c.side === "BUY"), true)
            applyUpdates(ev.changes.filter(c => c.side === "SELL"), false)
          } else {
            if (ev.bids && ev.bids.length > 0) applyUpdates(ev.bids, true)
            if (ev.asks && ev.asks.length > 0) applyUpdates(ev.asks, false)
          }
        }
      })
    }

    // Восстанавливаем соединение, только если оно РЕАЛЬНО порвалось
    ws.onclose = () => { if (activeMarketCache) setTimeout(() => connectToMarket(activeMarketCache), 1000) }

    // 🎯 МЕТРИКИ: Считаем в дробных долях (0.74) для правильной работы PnL на фронтенде
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