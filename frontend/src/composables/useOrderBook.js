import { reactive, ref } from 'vue'
import { useToast } from 'vue-toastification'

export function useOrderBook() {
  const toast = useToast()
  
  // 🎯 HFT Архитектура: reactive(new Map()) отслеживает мутации (.set, .delete) 
  // без пересоздания объектов. Память не течет, UI обновляется за миллисекунды.
  const rawBidsYes = reactive(new Map())
  const rawAsksYes = reactive(new Map())
  const rawBidsNo = reactive(new Map())
  const rawAsksNo = reactive(new Map())
  
  const isConnecting = ref(false)
  let ws = null
  let pingInt = null

  const disconnect = () => {
    if (ws) { ws.close(); ws = null }
    if (pingInt) { clearInterval(pingInt); pingInt = null }
  }

  const connectToMarket = (subMarket, onReadyCallback = null) => {
    disconnect()
    isConnecting.value = true
    
    const tokenYes = subMarket.token_id_yes.toLowerCase()
    const tokenNo = subMarket.token_id_no ? subMarket.token_id_no.toLowerCase() : null
    
    rawBidsYes.clear(); rawAsksYes.clear()
    rawBidsNo.clear(); rawAsksNo.clear()

    ws = new WebSocket(`wss://ws-subscriptions-clob.polymarket.com/ws/market`)
    
    ws.onopen = () => {
      let assets = [tokenYes]; if (tokenNo) assets.push(tokenNo)
      ws.send(JSON.stringify({ assets_ids: assets, type: "market" }))
      toast.success("HFT Sync Established", { timeout: 1500 })
    }

    ws.onmessage = (event) => {
      if (event.data === "PONG") return
      const data = JSON.parse(event.data)
      const events = Array.isArray(data) ? data : [data]

      events.forEach(ev => {
        const evToken = ev.asset_id ? ev.asset_id.toLowerCase() : null
        
        // Строгая привязка токена
        let bBook = evToken === tokenYes ? rawBidsYes : (evToken === tokenNo ? rawBidsNo : null)
        let aBook = evToken === tokenYes ? rawAsksYes : (evToken === tokenNo ? rawAsksNo : null)
        if (!bBook || !aBook) return

        if (ev.event_type === "book") {
          bBook.clear(); aBook.clear();
          (ev.bids||[]).forEach(b => bBook.set(parseFloat(b.price), parseFloat(b.size)));
          (ev.asks||[]).forEach(a => aBook.set(parseFloat(a.price), parseFloat(a.size)));
          
          isConnecting.value = false
          if (onReadyCallback) { onReadyCallback(); onReadyCallback = null }
          
        } else if (ev.event_type === "price_change") {
          const process = (arr, isBid) => {
            arr.forEach(i => {
              const p = parseFloat(i.price), s = parseFloat(i.size)
              if (s === 0) (isBid ? bBook : aBook).delete(p); else (isBid ? bBook : aBook).set(p, s)
            })
          }
          
          // 🚨 ИСПРАВЛЕНО: Проверяем length, чтобы пустые массивы не блокировали логику!
          if (ev.changes && ev.changes.length > 0) {
            process(ev.changes.filter(c=>c.side==="BUY"), true)
            process(ev.changes.filter(c=>c.side==="SELL"), false)
          } else {
            if (ev.bids && ev.bids.length > 0) process(ev.bids, true)
            if (ev.asks && ev.asks.length > 0) process(ev.asks, false)
          }
        }
      })
    }

    pingInt = setInterval(() => { if (ws?.readyState === WebSocket.OPEN) ws.send("PING"); }, 10000)
    ws.onclose = () => clearInterval(pingInt)
  }

  return { rawBidsYes, rawAsksYes, rawBidsNo, rawAsksNo, isConnecting, connectToMarket, disconnect }
}