import { onUnmounted, reactive, watch } from 'vue'

/** Sliding window for comparing book snapshots. */
const WINDOW_MS = 500
/** Poll interval — keep several samples inside the 500ms window. */
const SAMPLE_MS = 50
/** Conservative: flash when best-level size drops by this fraction. */
const SIZE_DROP_RATIO = 0.6
/** Conservative: flash when best bid/ask moves by this many cents. */
const PRICE_JUMP_CENTS = 3
/** How long the CSS flash class stays applied. */
const FLASH_MS = 480

/**
 * Read best bid/ask cents + sizes from a 99-level ladder (price 99→1).
 * @param {Array<{price:number,bidSize:number,askSize:number}>|null|undefined} ladder
 */
export function readTopOfBook(ladder) {
  let bestBid = 0
  let bestAsk = 0
  let bidSize = 0
  let askSize = 0
  if (!ladder || !ladder.length) {
    return { bestBid, bestAsk, bidSize, askSize }
  }
  for (let i = 0; i < ladder.length; i++) {
    const row = ladder[i]
    if (row?.bidSize > 0) {
      bestBid = row.price
      bidSize = row.bidSize
      break
    }
  }
  for (let i = ladder.length - 1; i >= 0; i--) {
    const row = ladder[i]
    if (row?.askSize > 0) {
      bestAsk = row.price
      askSize = row.askSize
      break
    }
  }
  return { bestBid, bestAsk, bidSize, askSize }
}

/**
 * Liquidity radar: 500ms sliding snapshots → flash map for price rows.
 *
 * @param {() => Array|null|undefined} getLadder  reactive getter for the ladder
 * @returns {{ flashes: Record<number, { kind: string, gen: number }>, clear: () => void }}
 */
export function useLiquidityRadar(getLadder) {
  /** @type {Record<number, { kind: 'bid'|'ask'|'jump', gen: number }>} */
  const flashes = reactive({})
  /** @type {Array<{ t:number, bestBid:number, bestAsk:number, bidSize:number, askSize:number }>} */
  const history = []
  const flashTimers = new Map()
  /** @type {Map<number, number>} */
  const flashGen = new Map()
  let sampleTimer = null

  function triggerFlash(price, kind) {
    if (!price || price < 1 || price > 99) return
    const nextGen = (flashGen.get(price) || 0) + 1
    flashGen.set(price, nextGen)
    flashes[price] = { kind, gen: nextGen }
    const prev = flashTimers.get(price)
    if (prev) clearTimeout(prev)
    flashTimers.set(
      price,
      setTimeout(() => {
        if (flashGen.get(price) === nextGen) {
          delete flashes[price]
          flashGen.delete(price)
        }
        flashTimers.delete(price)
      }, FLASH_MS)
    )
  }

  function prune(now) {
    const cutoff = now - WINDOW_MS
    while (history.length && history[0].t < cutoff) history.shift()
  }

  function sample() {
    const ladder = typeof getLadder === 'function' ? getLadder() : getLadder
    const top = readTopOfBook(ladder)
    const now = Date.now()
    prune(now)

    // Need a prior sample that already had liquidity (skip cold start / first fill)
    if (history.length) {
      const oldest = history[0]
      const age = now - oldest.t
      const hadBook = oldest.bestBid > 0 || oldest.bestAsk > 0
      if (age >= 40 && hadBook) {
        // --- Size pull at same best bid ---
        if (
          oldest.bestBid > 0 &&
          top.bestBid === oldest.bestBid &&
          oldest.bidSize > 0 &&
          (oldest.bidSize - top.bidSize) / oldest.bidSize >= SIZE_DROP_RATIO
        ) {
          triggerFlash(top.bestBid, 'bid')
        }
        // --- Size pull at same best ask ---
        if (
          oldest.bestAsk > 0 &&
          top.bestAsk === oldest.bestAsk &&
          oldest.askSize > 0 &&
          (oldest.askSize - top.askSize) / oldest.askSize >= SIZE_DROP_RATIO
        ) {
          triggerFlash(top.bestAsk, 'ask')
        }
        // --- Best bid jump (≥3¢) ---
        if (
          oldest.bestBid > 0 &&
          top.bestBid > 0 &&
          Math.abs(top.bestBid - oldest.bestBid) >= PRICE_JUMP_CENTS
        ) {
          triggerFlash(oldest.bestBid, 'jump')
          triggerFlash(top.bestBid, 'jump')
        }
        // --- Best ask jump (≥3¢) ---
        if (
          oldest.bestAsk > 0 &&
          top.bestAsk > 0 &&
          Math.abs(top.bestAsk - oldest.bestAsk) >= PRICE_JUMP_CENTS
        ) {
          triggerFlash(oldest.bestAsk, 'jump')
          triggerFlash(top.bestAsk, 'jump')
        }
      }
    }

    history.push({ t: now, ...top })
    prune(now)
  }

  function start() {
    if (sampleTimer) return
    sample()
    sampleTimer = setInterval(sample, SAMPLE_MS)
  }

  function stop() {
    if (sampleTimer) {
      clearInterval(sampleTimer)
      sampleTimer = null
    }
    for (const t of flashTimers.values()) clearTimeout(t)
    flashTimers.clear()
    history.length = 0
    for (const k of Object.keys(flashes)) delete flashes[k]
  }

  // Restart history when ladder identity changes (new market)
  watch(
    () => {
      const ladder = typeof getLadder === 'function' ? getLadder() : getLadder
      return ladder?.[0]?.price ?? null
    },
    () => {
      history.length = 0
    }
  )

  start()
  onUnmounted(stop)

  return { flashes, clear: stop, sample }
}
