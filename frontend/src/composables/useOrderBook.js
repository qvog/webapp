import { shallowRef, ref } from 'vue'
import { useToast } from 'vue-toastification'

export function useOrderBook() {
  const toast = useToast()
  
  // 1. СЛОЙ РЕНДЕРА (Сюда Vue смотрит для отрисовки интерфейса)
  const renderBidsYes = shallowRef(new Map())
  const renderAsksYes = shallowRef(new Map())
  const renderBidsNo = shallowRef(new Map())
  const renderAsksNo = shallowRef(new Map())

  // Переменные для Спреда и лучших цен
  const spreadYes = ref(0)
  const spreadNo = ref(0)
  const bestBidYes = ref(0)
  const bestAskYes = ref(1)
  const bestBidNo = ref(0)
  const bestAskNo = ref(1)

  const isConnecting = ref(false)

  let ws = null
  let pingInt = null
  let renderLoop = null

  // 2. СЛОЙ ДАННЫХ (Быстрые словари, которые не тормозят браузер)
  let rawBidsYes = new Map()
  let rawAsksYes = new Map()
  let rawBidsNo = new Map()
  let rawAsksNo = new Map()
  
  let isDirty = false 
  const DEPTH = 30 // Отрисовываем только топ-30 строк стакана для скорости

  const disconnect = () => {
    if (ws) { ws.close(); ws = null }
    if (pingInt) { clearInterval(pingInt); pingInt = null }
    if (renderLoop) { clearInterval(renderLoop); renderLoop = null }
  }

  const connectToMarket = (subMarket, onReadyCallback = null) => {
    disconnect()
    isConnecting.value = true
    
    const tokenYes = subMarket.token_id_yes.toLowerCase()
    const tokenNo = subMarket.token_id_no ? subMarket.token_id_no.toLowerCase() : null
    
    rawBidsYes.clear(); rawAsksYes.clear(); rawBidsNo.clear(); rawAsksNo.clear()
    isDirty = true

    ws = new WebSocket(`wss://ws-subscriptions-clob.polymarket.com/ws/market`)
    
    ws.onopen = () => {
      let assets = [tokenYes]; if (tokenNo) assets.push(tokenNo)
      ws.send(JSON.stringify({ assets_ids: assets, type: "market" }))
      toast.success("HFT Engine: 20 FPS Active", { timeout: 1500 })
    }

    ws.onmessage = (event) => {
      if (event.data === "PONG") return
      let data;
      try { data = JSON.parse(event.data) } catch(e) { return }

      const events = Array.isArray(data) ? data : [data]

      events.forEach(ev => {
        const evToken = ev.asset_id ? ev.asset_id.toLowerCase() : null
        let bBook = evToken === tokenYes ? rawBidsYes : (evToken === tokenNo ? rawBidsNo : null)
        let aBook = evToken === tokenYes ? rawAsksYes : (evToken === tokenNo ? rawAsksNo : null)
        if (!bBook || !aBook) return

        if (ev.event_type === "book") {
          bBook.clear(); aBook.clear();
          (ev.bids || []).forEach(b => bBook.set(parseFloat(b.price), parseFloat(b.size)));
          (ev.asks || []).forEach(a => aBook.set(parseFloat(a.price), parseFloat(a.size)));
          isDirty = true
          isConnecting.value = false
          if (onReadyCallback) { onReadyCallback(); onReadyCallback = null }
        } else {
          // Парсим точечные обновления цен
          const applyUpdates = (arr, isBid) => {
            arr.forEach(i => {
              const p = parseFloat(i.price), s = parseFloat(i.size)
              if (s === 0) { isBid ? bBook.delete(p) : aBook.delete(p) }
              else { isBid ? bBook.set(p, s) : aBook.set(p, s) }
              isDirty = true
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

    // 🎯 ДВИЖОК: Жесткий цикл рендера (50мс = 20 раз в секунду)
    renderLoop = setInterval(() => {
      if (!isDirty) return

      const extract = (bMap, aMap) => {
        let bArr = [], aArr = []
        for (let [p, s] of bMap.entries()) bArr.push({p, s})
        for (let [p, s] of aMap.entries()) aArr.push({p, s})

        bArr.sort((a, b) => b.p - a.p) // Bids: Лучшие сверху (убывание)
        aArr.sort((a, b) => a.p - b.p) // Asks: Лучшие снизу (возрастание)

        const bestB = bArr.length > 0 ? bArr[0].p : 0
        const bestA = aArr.length > 0 ? aArr[0].p : 1

        return {
          bids: new Map(bArr.slice(0, DEPTH).map(x => [x.p, x.s])),
          asks: new Map(aArr.slice(0, DEPTH).map(x => [x.p, x.s])),
          bestB,
          bestA,
          spread: Math.max(0, bestA - bestB)
        }
      }

      // Обновляем команду 1
      const yesData = extract(rawBidsYes, rawAsksYes)
      renderBidsYes.value = yesData.bids
      renderAsksYes.value = yesData.asks
      bestBidYes.value = yesData.bestB
      bestAskYes.value = yesData.bestA
      spreadYes.value = yesData.spread

      // Обновляем команду 2
      const noData = extract(rawBidsNo, rawAsksNo)
      renderBidsNo.value = noData.bids
      renderAsksNo.value = noData.asks
      bestBidNo.value = noData.bestB
      bestAskNo.value = noData.bestA
      spreadNo.value = noData.spread

      isDirty = false
    }, 50) 

    // Пингуем вебсокет, чтобы не отключился
    pingInt = setInterval(() => { if (ws?.readyState === WebSocket.OPEN) ws.send("PING"); }, 10000)
  }

  return { 
    rawBidsYes: renderBidsYes, 
    rawAsksYes: renderAsksYes, 
    rawBidsNo: renderBidsNo, 
    rawAsksNo: renderAsksNo, 
    spreadYes, 
    spreadNo, 
    bestBidYes, 
    bestAskYes, 
    bestBidNo, 
    bestAskNo,
    isConnecting, 
    connectToMarket, 
    disconnect 
  }
}