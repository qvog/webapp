import { ref } from 'vue'
import { useToast } from 'vue-toastification'

export function useOrderBook() {
  const toast = useToast()
  
  // Реактивные данные стакана
  const rawBidsYes = ref(new Map())
  const rawAsksYes = ref(new Map())
  const rawBidsNo = ref(new Map())
  const rawAsksNo = ref(new Map())
  const isConnecting = ref(false)
  
  let ws = null
  let pingInt = null

  // Уничтожение соединения (защита от утечек памяти)
  const disconnect = () => {
    if (ws) {
      ws.close()
      ws = null
    }
    if (pingInt) {
      clearInterval(pingInt)
      pingInt = null
    }
  }

  // Главная функция подключения к рынку
  const connectToMarket = (subMarket, onReadyCallback = null) => {
    disconnect()
    isConnecting.value = true
    
    const tokenYes = subMarket.token_id_yes.toLowerCase()
    const tokenNo = subMarket.token_id_no ? subMarket.token_id_no.toLowerCase() : null
    
    rawBidsYes.value.clear(); rawAsksYes.value.clear()
    rawBidsNo.value.clear(); rawAsksNo.value.clear()

    // 1. Сначала скачиваем статический Snapshot (Rest API)
    Promise.all([
      fetch(`https://clob.polymarket.com/book?token_id=${tokenYes}`).then(r=>r.json()),
      tokenNo ? fetch(`https://clob.polymarket.com/book?token_id=${tokenNo}`).then(r=>r.json()) : Promise.resolve({bids:[], asks:[]})
    ]).then(([dataYes, dataNo]) => {
      (dataYes.bids||[]).forEach(b => rawBidsYes.value.set(parseFloat(b.price), parseFloat(b.size)));
      (dataYes.asks||[]).forEach(a => rawAsksYes.value.set(parseFloat(a.price), parseFloat(a.size)));
      (dataNo.bids||[]).forEach(b => rawBidsNo.value.set(parseFloat(b.price), parseFloat(b.size)));
      (dataNo.asks||[]).forEach(a => rawAsksNo.value.set(parseFloat(a.price), parseFloat(a.size)));
      
      isConnecting.value = false
      if (onReadyCallback) onReadyCallback() // Сигнал, что можно центрировать стакан
    }).catch(() => { 
      isConnecting.value = false
      toast.error("Failed to load order book snapshot")
    })

    // 2. Затем открываем живой поток (WebSocket)
    ws = new WebSocket(`wss://ws-subscriptions-clob.polymarket.com/ws/market`)
    
    ws.onopen = () => {
      let assets = [tokenYes]; if (tokenNo) assets.push(tokenNo)
      ws.send(JSON.stringify({ assets_ids: assets, type: "market" }))
      toast.success("Synced!", { timeout: 1500 })
    }

    ws.onmessage = (event) => {
      if (event.data === "PONG") return
      const data = JSON.parse(event.data)
      const events = Array.isArray(data) ? data : [data]

      events.forEach(ev => {
        const evToken = ev.asset_id ? ev.asset_id.toLowerCase() : null
        let bBook = evToken === tokenYes ? rawBidsYes.value : rawBidsNo.value
        let aBook = evToken === tokenYes ? rawAsksYes.value : rawAsksNo.value
        if (!bBook) return

        if (ev.event_type === "book") {
          bBook.clear(); aBook.clear();
          (ev.bids||[]).forEach(b => bBook.set(parseFloat(b.price), parseFloat(b.size)));
          (ev.asks||[]).forEach(a => aBook.set(parseFloat(a.price), parseFloat(a.size)));
        } else if (ev.event_type === "price_change") {
          const process = (arr, isBid) => {
            arr.forEach(i => {
              const p = parseFloat(i.price), s = parseFloat(i.size)
              if (s === 0) (isBid ? bBook : aBook).delete(p); else (isBid ? bBook : aBook).set(p, s)
            })
          }
          if (ev.changes) {
            process(ev.changes.filter(c=>c.side==="BUY"), true)
            process(ev.changes.filter(c=>c.side==="SELL"), false)
          } else {
            if (ev.bids) process(ev.bids, true)
            if (ev.asks) process(ev.asks, false)
          }
        }
      })
      // Принудительно триггерим реактивность Vue
    }

    // Поддержка соединения
    pingInt = setInterval(() => { 
      if (ws?.readyState === WebSocket.OPEN) ws.send("PING"); 
    }, 10000)

    ws.onclose = () => {
      clearInterval(pingInt)
    }
  }

  // Отдаем наружу только то, что нужно компонентам
  return {
    rawBidsYes,
    rawAsksYes,
    rawBidsNo,
    rawAsksNo,
    isConnecting,
    connectToMarket,
    disconnect
  }
}