/** Sidebar subcategory definitions and icons. */

export const SUBCATEGORIES = {
  most_traded: [],
  live: [],
  favorites: [],
  sports: [
    { id: 'live', label: 'Live' },
    { id: 'starting soon', label: 'Starting soon' },
    { id: 'ucl', label: 'UCL' },
    { id: 'nba', label: 'NBA' },
    { id: 'mlb', label: 'MLB' },
    { id: 'footbal', label: 'Football' },
    { id: 'tennis', label: 'Tennis' },
    { id: 'cricket', label: 'Cricket' },
    { id: 'football', label: 'Am. Football' },
    { id: 'basketbal', label: 'Basketball' },
    { id: 'hockey', label: 'Hockey' },
    { id: 'baseball', label: 'Baseball' },
    { id: 'rugby', label: 'Rugby' },
    { id: 'golf', label: 'Golf' },
    { id: 'ufc', label: 'UFC' },
    { id: 'formula 1', label: 'Formula 1' },
    { id: 'chess', label: 'Chess' },
    { id: 'boxing', label: 'Boxing' },
    { id: 'pickleball', label: 'Pickleball' },
  ],
  esports: [
    { id: 'live', label: 'Live' },
    { id: 'starting soon', label: 'Starting soon' },
    { id: 'dota 2', label: 'Dota 2' },
    { id: 'league of legend', label: 'League of Legends' },
    { id: 'cs2', label: 'CS2' },
    { id: 'valorant', label: 'Valorant' },
    { id: 'rainbow six siege', label: 'Rainbow Six Siege' },
    { id: 'starcraft ii', label: 'StarCraft II' },
    { id: 'overwatch', label: 'Overwatch' },
    { id: 'rocket league', label: 'Rocket League' },
    { id: 'mobile legends: bang bang', label: 'Mobile Legends' },
    { id: 'honor of kings', label: 'Honor of Kings' },
    { id: 'call of duty', label: 'Call of Duty' },
  ],
  crypto: [
    { id: 'all', label: 'All' },
    { id: '5 min', label: '5 Min' },
    { id: '15 min', label: '15 Min' },
    { id: 'hourly', label: 'Hourly' },
    { id: '4 hour', label: '4 Hour' },
    { id: 'daily', label: 'Daily' },
    { id: 'weekly', label: 'Weekly' },
    { id: 'monthly', label: 'Monthly' },
    { id: 'pre-market', label: 'Pre-Market' },
    { id: 'etf', label: 'ETF' },
    { id: 'bitcoin', label: 'Bitcoin' },
    { id: 'ethereum', label: 'Ethereum' },
    { id: 'solana', label: 'Solana' },
    { id: 'xrp', label: 'XRP' },
    { id: 'dogecoin', label: 'Dogecoin' },
    { id: 'microstrategy', label: 'Microstrategy' },
  ],
  others: [
    { id: 'all', label: 'All' },
    { id: 'politics', label: 'Politics' },
    { id: 'pop-culture', label: 'Pop Culture' },
    { id: 'business', label: 'Business' },
    { id: 'science', label: 'Science' },
  ],
}

/** Short crypto tabs that rotate live windows like Polymarket. */
export const CRYPTO_LIVE_WINDOW_SUBS = new Set(['5 min', '15 min', 'hourly', '4 hour'])

const MAIN_NAV = [
  { category: 'most_traded', subcategory: 'all', label: 'Most Traded', keywords: ['most', 'traded', 'popular'] },
  { category: 'live', subcategory: 'all', label: 'Live Markets', keywords: ['live'] },
  { category: 'favorites', subcategory: 'all', label: 'Favorites', keywords: ['favorites', 'fav', 'star'] },
  { category: 'sports', subcategory: 'all', label: 'Sports', keywords: ['sports', 'sport'] },
  { category: 'esports', subcategory: 'all', label: 'Esports', keywords: ['esports', 'e-sports', 'gaming'] },
  { category: 'crypto', subcategory: 'all', label: 'Crypto', keywords: ['crypto', 'cryptocurrency'] },
  { category: 'others', subcategory: 'all', label: 'Others', keywords: ['others', 'other'] },
]

/** Extra search aliases for subcategories (query → match). */
const SUB_KEYWORDS = {
  cs2: ['cs', 'cs2', 'csgo', 'counter strike', 'counter-strike', 'counterstrike'],
  'dota 2': ['dota', 'dota2', 'dota 2'],
  'league of legend': ['lol', 'league', 'league of legends', 'legends'],
  '5 min': ['5m', '5 min', '5min', 'five min'],
  '15 min': ['15m', '15 min', '15min'],
  hourly: ['1h', 'hourly', 'hour', '1 hour'],
  '4 hour': ['4h', '4 hour', '4hr', 'four hour'],
  bitcoin: ['btc', 'bitcoin'],
  ethereum: ['eth', 'ethereum'],
  solana: ['sol', 'solana'],
  dogecoin: ['doge', 'dogecoin'],
  footbal: ['football', 'soccer', 'footbal'],
  football: ['nfl', 'american football', 'am football'],
  basketbal: ['nba', 'basketball', 'basketbal'],
  ucl: ['ucl', 'champions league', 'champions'],
  valorant: ['valorant', 'val'],
}

/**
 * Flatten nav + subcategories for search.
 * @returns {{ category: string, subcategory: string, label: string, path: string, keywords: string[] }[]}
 */
export function getSearchableCategories() {
  const items = MAIN_NAV.map((m) => ({
    ...m,
    path: m.label,
    keywords: [...m.keywords, m.label.toLowerCase()],
  }))

  for (const [cat, subs] of Object.entries(SUBCATEGORIES)) {
    if (!subs?.length) continue
    for (const sub of subs) {
      if (sub.id === 'live' || sub.id === 'starting soon' || sub.id === 'all') {
        // still searchable but with category prefix
      }
      const path = `${cat} / ${sub.label}`
      const kw = [
        sub.id,
        sub.label.toLowerCase(),
        cat,
        path.toLowerCase(),
        ...(SUB_KEYWORDS[sub.id] || []),
      ]
      items.push({
        category: cat,
        subcategory: sub.id,
        label: sub.label,
        path,
        keywords: kw,
      })
    }
  }
  return items
}

function _tokens(text) {
  return String(text || '')
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
}

/** Prefix match that does not treat "5" as a hit for "15". */
function _prefixHit(text, q) {
  const t = String(text || '').toLowerCase()
  if (!t || !q) return false
  if (t === q) return true
  if (!t.startsWith(q)) return false
  if (/^\d+$/.test(q) && /^\d+$/.test(t) && t !== q) return false
  return true
}

/**
 * Rank category hits for a query. Categories with better prefix/exact matches first.
 * Short queries (e.g. "cs") only match keyword/label prefixes — not substrings inside
 * unrelated words like "politiCS".
 */
export function searchCategories(query, limit = 8) {
  const q = (query || '').trim().toLowerCase()
  if (!q) return []

  const scored = []
  for (const item of getSearchableCategories()) {
    let score = 0
    const label = item.label.toLowerCase()
    const sub = String(item.subcategory || '').toLowerCase()
    const tokens = _tokens(`${item.path} ${item.keywords.join(' ')}`)

    if (label === q || sub === q) score = 100
    else if (item.keywords.some((k) => k === q)) score = 95
    else if (_prefixHit(label, q) || _prefixHit(sub, q)) score = 85
    else if (item.keywords.some((k) => _prefixHit(k, q))) score = 75
    else if (tokens.some((t) => _prefixHit(t, q))) score = 65
    else if (q.length >= 3 && item.keywords.some((k) => k.includes(q))) score = 45
    else if (q.length >= 3 && tokens.some((t) => t.includes(q))) score = 35
    else continue

    // Prefer specific subcategories over top-level when query is short (e.g. "cs" → CS2)
    if (item.subcategory && item.subcategory !== 'all') score += 5

    scored.push({ ...item, score })
  }

  scored.sort((a, b) => b.score - a.score || a.path.localeCompare(b.path))

  // Dedupe by category+subcategory
  const seen = new Set()
  const out = []
  for (const item of scored) {
    const key = `${item.category}::${item.subcategory}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(item)
    if (out.length >= limit) break
  }
  return out
}

const S = 'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'

const ICONS = {
  live: `<circle cx="12" cy="12" r="5" fill="currentColor"/><path d="M22 12A10 10 0 0 0 12 2a10 10 0 0 0-10 10" stroke-dasharray="4 4" stroke-width="2"/>`,
  clock: `<circle cx="12" cy="12" r="10" ${S}/><path d="M12 6v6l4 2" ${S}/>`,
  btc: `<path d="M9 8h4a3 3 0 0 1 0 6H9V8zM9 14h4.5a3.5 3.5 0 0 1 0 7H9v-7zM11 5v3M14 5v3M11 21v-3M14 21v-3" ${S}/>`,
  eth: `<path d="M12 2L3 14l9 8 9-8L12 2zM12 2v20M3 14l9-4 9 4" ${S}/>`,
  coin: `<circle cx="12" cy="12" r="10" ${S}/><path d="M8 12h8M12 8v8" ${S}/>`,
  build: `<rect x="4" y="4" width="16" height="16" rx="2" ${S}/><path d="M12 8v8M8 12h8" ${S}/>`,
  graph: `<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" ${S}/>`,
  target: `<circle cx="12" cy="12" r="10" ${S}/><circle cx="12" cy="12" r="5" ${S}/><path d="M12 2v4M12 18v4M2 12h4M18 12h4" ${S}/>`,
  sword: `<path d="M14.5 17.5L3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2" ${S}/>`,
  car: `<path d="M4 14l2-6h12l2 6M2 14h20v4H2z" ${S}/><circle cx="7" cy="18" r="2" ${S}/><circle cx="17" cy="18" r="2" ${S}/>`,
  soccer: `<circle cx="12" cy="12" r="10" ${S}/><path d="M12 7l-4 4h8zM12 17l-4-4h8z" ${S}/>`,
  basket: `<circle cx="12" cy="12" r="10" ${S}/><path d="M5 5l14 14M5 19L19 5M2 12h20M12 2v20" ${S}/>`,
  tennis: `<circle cx="12" cy="12" r="10" ${S}/><path d="M12 2a10 10 0 0 1 0 20M2 12a10 10 0 0 1 20 0" ${S}/>`,
  mma: `<rect x="4" y="8" width="16" height="12" rx="2" ${S}/><path d="M8 8V6a4 4 0 0 1 8 0v2M10 14h4" ${S}/>`,
  chess: `<path d="M8 20h8M10 20v-4h4v4M12 16v-8M10 8l2-4 2 4z" ${S}/>`,
  all: `<rect x="3" y="3" width="7" height="7" rx="1" ${S}/><rect x="14" y="3" width="7" height="7" rx="1" ${S}/><rect x="14" y="14" width="7" height="7" rx="1" ${S}/><rect x="3" y="14" width="7" height="7" rx="1" ${S}/>`,
  dota: `<path fill="currentColor" d="M2.93 9.48c.024 4.12 2.363 7.98 5.313 10.3l1.89-3.39-4.1-4.47 1.38-2.82-3.35-3.65c-.96 1.43-1.49 3.13-1.13 4.03zm15.42 1.63l-2.45-1.88-.71-4.47-5.88 1.43 1.28 2.3 4.22-1.33 1.13 1.23-5.26 1.65 1.5 2.7 4.57-1.44 1.91 2.08-5.56 1.75 1.92 3.44 2.53-2.75 1.64.52-2.5 2.73 1-1.83c2.2-1.74 3.66-4.3 4.05-7.15zm-9.78 3.3l-1.23-2.5-3.52 3.84c1.67-.2 3.36-.28 4.75 1.34z"/>`,
  cs2: `<path d="M12 2A10 10 0 1 0 22 12 10 10 0 0 0 12 2Zm-1.5 14.5v-9L16 12Z" fill="currentColor"/>`,
}

export function getSubcategoryIcon(id) {
  id = (id || '').toLowerCase()
  let svg = ICONS.all
  let color = 'text-[#00e5ff]'

  if (id === 'live') { svg = ICONS.live; color = 'text-red-500' }
  else if (id === 'starting soon' || id.includes('min') || id.includes('hour') || id === 'daily' || id === 'weekly' || id === 'monthly') {
    svg = ICONS.clock; color = 'text-yellow-500'
  }
  else if (id === 'bitcoin') { svg = ICONS.btc; color = 'text-[#F7931A]' }
  else if (id === 'ethereum') { svg = ICONS.eth; color = 'text-[#627EEA]' }
  else if (['solana', 'xrp', 'dogecoin'].includes(id)) { svg = ICONS.coin; color = 'text-indigo-400' }
  else if (['etf', 'microstrategy', 'business', 'politics'].includes(id)) { svg = ICONS.build; color = 'text-gray-400' }
  else if (id === 'pre-market') { svg = ICONS.graph; color = 'text-green-400' }
  else if (id === 'dota 2') { svg = ICONS.dota; color = 'text-[#ef4444]' }
  else if (id === 'cs2') { svg = ICONS.cs2; color = 'text-yellow-400' }
  else if (['valorant', 'rainbow six siege', 'overwatch', 'call of duty'].includes(id)) {
    svg = ICONS.target; color = 'text-rose-500'
  }
  else if (['league of legend', 'starcraft ii', 'mobile legends: bang bang', 'honor of kings'].includes(id)) {
    svg = ICONS.sword; color = 'text-purple-400'
  }
  else if (id === 'rocket league' || id === 'formula 1') { svg = ICONS.car; color = 'text-blue-400' }
  else if (id === 'ucl' || id === 'footbal' || id === 'football') { svg = ICONS.soccer; color = 'text-green-400' }
  else if (id === 'nba' || id === 'basketbal') { svg = ICONS.basket; color = 'text-orange-500' }
  else if (id === 'tennis' || id === 'pickleball' || id === 'baseball') { svg = ICONS.tennis; color = 'text-lime-400' }
  else if (id === 'ufc' || id === 'boxing' || id === 'mma' || id === 'rugby') { svg = ICONS.mma; color = 'text-red-500' }
  else if (id === 'chess' || id === 'science') { svg = ICONS.chess; color = 'text-gray-300' }

  return `<svg viewBox="0 0 24 24" fill="none" class="w-[18px] h-[18px] ${color}">${svg}</svg>`
}

/** Display market times in Moscow (UTC+3), 24h — Polymarket timestamps are UTC. */
const DISPLAY_TZ = 'Europe/Moscow'

function parseMarketDate(dateString) {
  if (!dateString) return null
  let s = String(dateString).trim()
  // "2026-03-10 11:40:00+00" → ISO-friendly
  if (/^\d{4}-\d{2}-\d{2} /.test(s)) s = s.replace(' ', 'T')
  if (s.endsWith('+00')) s = s.slice(0, -3) + '+00:00'
  const date = new Date(s)
  return Number.isNaN(date.getTime()) ? null : date
}

function moscowDateParts(date) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: DISPLAY_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date)
  const get = (type) => parts.find((p) => p.type === type)?.value
  return {
    year: get('year'),
    month: get('month'),
    day: get('day'),
    hour: get('hour') === '24' ? '00' : get('hour'),
    minute: get('minute'),
  }
}

export function formatMarketDate(dateString) {
  const date = parseMarketDate(dateString)
  if (!date) return 'TBA'

  const m = moscowDateParts(date)
  const now = moscowDateParts(new Date())
  const time = `${m.hour}:${m.minute}`

  const isToday = m.year === now.year && m.month === now.month && m.day === now.day
  if (isToday) return `TODAY, ${time}`

  const label = new Intl.DateTimeFormat('en-US', {
    timeZone: DISPLAY_TZ,
    day: 'numeric',
    month: 'short',
  })
    .format(date)
    .toUpperCase()
  return `${label}, ${time}`
}

export function formatVolume(val) {
  const n = Number(val) || 0
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(Math.round(n))
}
