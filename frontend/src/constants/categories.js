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

export function formatMarketDate(dateString) {
  if (!dateString) return 'TBA'
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return 'TBA'
  const now = new Date()
  const isToday =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()
  const time = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
  if (isToday) return `TODAY, ${time}`
  return (
    date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' }).toUpperCase() +
    `, ${time}`
  )
}

export function formatVolume(val) {
  const n = Number(val) || 0
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(Math.round(n))
}
