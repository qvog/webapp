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

export function getSearchableCategories() {
  const items = MAIN_NAV.map((m) => ({
    ...m,
    path: m.label,
    keywords: [...m.keywords, m.label.toLowerCase()],
  }))

  for (const [cat, subs] of Object.entries(SUBCATEGORIES)) {
    if (!subs?.length) continue
    for (const sub of subs) {
      if (sub.id === 'live' || sub.id === 'starting soon' || sub.id === 'all') { }
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
  return String(text || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
}

function _prefixHit(text, q) {
  const t = String(text || '').toLowerCase()
  if (!t || !q) return false
  if (t === q) return true
  if (!t.startsWith(q)) return false
  if (/^\d+$/.test(q) && /^\d+$/.test(t) && t !== q) return false
  return true
}

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

    if (item.subcategory && item.subcategory !== 'all') score += 5
    scored.push({ ...item, score })
  }

  scored.sort((a, b) => b.score - a.score || a.path.localeCompare(b.path))

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

// ВОЗВРАЩАЕМСЯ К 100% ОРИГИНАЛЬНЫМ ИСТОЧНИКАМ POLYMARKET
const PM_ICONS = 'https://polymarket-upload.s3.us-east-2.amazonaws.com/league-icons'
const PM_ROOT = 'https://polymarket-upload.s3.us-east-2.amazonaws.com'
const CRYPTO_ICONS = 'https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color'

const IMAGE_ICONS = {
  // Esports
  'dota 2': `${PM_ICONS}/dota2.png`,
  'league of legend': `${PM_ICONS}/lol.png`,
  cs2: `${PM_ICONS}/cs2.png`,
  valorant: `${PM_ICONS}/val.png`,
  'rainbow six siege': `${PM_ICONS}/r6siege.png`,
  'starcraft ii': `${PM_ICONS}/sc2.png`,
  overwatch: `${PM_ICONS}/ow.png`,
  'rocket league': `${PM_ICONS}/rl.png`,
  'mobile legends: bang bang': `${PM_ICONS}/mlbb.png`,
  'honor of kings': `${PM_ICONS}/hok.png`,
  'call of duty': `${PM_ICONS}/codmw.png`,

  // Sports
  ucl: `${PM_ICONS}/ucl.png`,
  nba: `${PM_ICONS}/nba.png`,
  mlb: `${PM_ICONS}/mlb.png`,
  footbal: `${PM_ICONS}/epl.png`,
  football: `${PM_ICONS}/nfl.png`,
  tennis: `${PM_ICONS}/atp.png`,
  cricket: `${PM_ROOT}/cricket-ball-a0b0bf2dc9.png`,
  basketbal: `${PM_ICONS}/nba.png`,
  hockey: `${PM_ICONS}/nhl.png`,
  baseball: `${PM_ICONS}/mlb.png`,
  golf: `${PM_ICONS}/pga.png`,
  ufc: `${PM_ICONS}/ufc.png`,
  'formula 1': `${PM_ICONS}/f1.png`,
  chess: `${PM_ICONS}/chess.png`,
  boxing: `${PM_ICONS}/boxing-cba26879.png`,

  // Crypto
  bitcoin: `${CRYPTO_ICONS}/btc.png`,
  ethereum: `${CRYPTO_ICONS}/eth.png`,
  solana: `${CRYPTO_ICONS}/sol.png`,
  xrp: `${CRYPTO_ICONS}/xrp.png`,
  dogecoin: `${CRYPTO_ICONS}/doge.png`,
}

const S = 'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
const SVG_PATHS = {
  live: `<circle cx="12" cy="12" r="5" fill="currentColor"/><path d="M22 12A10 10 0 0 0 12 2a10 10 0 0 0-10 10" stroke-dasharray="4 4" stroke-width="2"/>`,
  clock: `<circle cx="12" cy="12" r="10" ${S}/><path d="M12 6v6l4 2" ${S}/>`,
  graph: `<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" ${S}/>`,
  build: `<rect x="4" y="4" width="16" height="16" rx="2" ${S}/><path d="M12 8v8M8 12h8" ${S}/>`,
  culture: `<path d="M4 19V5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" ${S}/><path d="M14 3v5h5" ${S}/>`,
  science: `<circle cx="12" cy="12" r="3" ${S}/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1L7 17M17 7l2.1-2.1" ${S}/>`,
  rugby: `<ellipse cx="12" cy="12" rx="9" ry="6" transform="rotate(-35 12 12)" ${S}/><path d="M7 9l10 6M7 15l10-6" ${S}/>`,
  pickle: `<circle cx="12" cy="12" r="9" ${S}/><path d="M8 10h.01M12 8h.01M16 10h.01M9 14h.01M14 15h.01" ${S}/>`,
  sports: `<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" ${S}/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" ${S}/><path d="M4 22h16" ${S}/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" ${S}/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" ${S}/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" ${S}/>`,
  esports: `<rect x="2" y="6" width="20" height="12" rx="2" ${S}/><path d="M6 12h4M8 10v4M15 13h.01M18 11h.01" ${S}/>`,
  crypto: `<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" ${S}/>`,
  chart: `<polyline points="23 6 13.5 15.5 8.5 10.5 1 18" ${S}/><polyline points="17 6 23 6 23 12" ${S}/>`,
  star: `<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" ${S}/>`,
  all: `<rect x="3" y="3" width="7" height="7" rx="1" ${S}/><rect x="14" y="3" width="7" height="7" rx="1" ${S}/><rect x="14" y="14" width="7" height="7" rx="1" ${S}/><rect x="3" y="14" width="7" height="7" rx="1" ${S}/>`,
}

function _svgHtml(path, color = 'text-[#00e5ff]') {
  return `<svg viewBox="0 0 24 24" fill="none" class="w-[18px] h-[18px] ${color} shrink-0">${path}</svg>`
}

/** 
 * ГЕНЕРАТОР КАРТИНОК С УЛЬТИМАТИВНЫМ CSS-ФИЛЬТРОМ
 */
function _imgHtml(url, isCrypto) {
  // Для цветной крипты просто отдаем картинку
  if (isCrypto) {
    return `<img src="${url}" alt="" class="w-[18px] h-[18px] shrink-0 object-cover" loading="lazy" decoding="async" />`
  }
  
  // Для Полимаркета применяем магию: 
  // 1. invert(1) делает черные логотипы белыми (и белый фон - черным)
  // 2. mix-blend-mode: screen делает любой черный фон абсолютно прозрачным!
  return `<img src="${url}" alt="" class="w-[18px] h-[18px] shrink-0 object-cover" style="filter: invert(1) brightness(1.2); mix-blend-mode: screen; opacity: 0.85;" loading="lazy" decoding="async" />`
}

function _svgFallback(id) {
  if (id === 'live') return _svgHtml(SVG_PATHS.live, 'text-red-500')
  if (
    id === 'starting soon' ||
    id.includes('min') ||
    id.includes('hour') ||
    id === 'daily' ||
    id === 'weekly' ||
    id === 'monthly'
  ) {
    return _svgHtml(SVG_PATHS.clock, 'text-yellow-500')
  }
  if (id === 'pre-market') return _svgHtml(SVG_PATHS.graph, 'text-green-400')
  if (['etf', 'microstrategy', 'business', 'politics'].includes(id)) {
    return _svgHtml(SVG_PATHS.build, 'text-gray-400')
  }
  if (id === 'pop-culture') return _svgHtml(SVG_PATHS.culture, 'text-pink-400')
  if (id === 'science') return _svgHtml(SVG_PATHS.science, 'text-sky-400')
  if (id === 'rugby') return _svgHtml(SVG_PATHS.rugby, 'text-green-500')
  if (id === 'pickleball') return _svgHtml(SVG_PATHS.pickle, 'text-lime-400')
  if (id === 'sports') return _svgHtml(SVG_PATHS.sports, 'text-[#00e5ff]')
  if (id === 'esports') return _svgHtml(SVG_PATHS.esports, 'text-[#00e5ff]')
  if (id === 'crypto') return _svgHtml(SVG_PATHS.crypto, 'text-[#00e5ff]')
  if (id === 'most_traded') return _svgHtml(SVG_PATHS.chart, 'text-[#00e5ff]')
  if (id === 'favorites') return _svgHtml(SVG_PATHS.star, 'text-yellow-500')
  if (id === 'others' || id === 'all') return _svgHtml(SVG_PATHS.all, 'text-zinc-400')
  
  return _svgHtml(SVG_PATHS.all, 'text-[#00e5ff]')
}

export function getSubcategoryIconInfo(id) {
  const key = (id || '').toLowerCase().trim()
  const url = IMAGE_ICONS[key]
  
  if (url) {
    const isCrypto = url.includes('cryptocurrency-icons')
    // ХАК ДЛЯ VUE: мы намеренно отдаем { type: 'svg' }, даже если это картинка.
    // Это заставляет SubcategoryNav.vue отрисовать наш сгенерированный HTML (через v-html), 
    // чтобы применились CSS-фильтры `invert` и `screen`, которые решают проблему темного фона!
    return { type: 'svg', html: _imgHtml(url, isCrypto) }
  }
  
  return { type: 'svg', html: _svgFallback(key) }
}

export function getSubcategoryIcon(id) {
  return getSubcategoryIconInfo(id).html
}

const DISPLAY_TZ = 'Europe/Moscow'

function parseMarketDate(dateString) {
  if (!dateString) return null
  let s = String(dateString).trim()
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