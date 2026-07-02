<template>
  <div class="flex h-screen w-full bg-[#000000] text-gray-200 font-sans overflow-hidden">
    
    <aside :class="['flex flex-col justify-between border-r border-zinc-900 bg-[#020202] transition-all duration-300 z-50 shrink-0 overflow-hidden whitespace-nowrap', marketStore.isSidebarExpanded ? 'w-56' : 'w-16']">
      <div class="flex flex-col gap-1 py-4">
        <div class="flex items-center px-4 mb-6 cursor-pointer" @click="closeTerminal">
          <div class="w-8 h-8 rounded shrink-0 flex items-center justify-center font-black text-black bg-[#00e5ff] tracking-tighter shadow-[0_0_15px_rgba(0,229,255,0.3)]">
            qS
          </div>
          <span :class="['font-black text-lg tracking-widest text-white transition-opacity duration-300', marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0']">
            QSCALP
          </span>
        </div>

        <button @click="marketStore.setCategory('crypto')" :class="['flex items-center px-5 py-3 transition-colors relative', marketStore.activeCategory === 'crypto' ? 'text-[#00e5ff]' : 'text-zinc-500 hover:text-zinc-300']">
          <div v-if="marketStore.activeCategory === 'crypto'" class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#00e5ff] rounded-r shadow-[0_0_10px_rgba(0,229,255,0.5)]"></div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          <span :class="['font-bold text-sm tracking-wider uppercase transition-opacity duration-300', marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0']">Crypto</span>
        </button>

        <button @click="marketStore.setCategory('sports')" :class="['flex items-center px-5 py-3 transition-colors relative', marketStore.activeCategory === 'sports' ? 'text-[#00e5ff]' : 'text-zinc-500 hover:text-zinc-300']">
          <div v-if="marketStore.activeCategory === 'sports'" class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#00e5ff] rounded-r shadow-[0_0_10px_rgba(0,229,255,0.5)]"></div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          <span :class="['font-bold text-sm tracking-wider uppercase transition-opacity duration-300', marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0']">Sports</span>
        </button>

        <div class="h-px bg-zinc-900 mx-4 my-2 shrink-0"></div>

        <button @click="marketStore.setCategory('live')" :class="['flex items-center px-5 py-3 transition-colors relative', marketStore.activeCategory === 'live' ? 'text-red-500' : 'text-zinc-500 hover:text-zinc-300']">
          <div v-if="marketStore.activeCategory === 'live'" class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-red-500 rounded-r shadow-[0_0_10px_rgba(239,68,68,0.5)]"></div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-14a6 6 0 1 0 6 6 6 6 0 0 0-6-6zm0 10a4 4 0 1 1 4-4 4 4 0 0 1-4 4z"/></svg>
          <span :class="['font-bold text-sm tracking-wider uppercase transition-opacity duration-300', marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0']">Live Markets</span>
        </button>

        <button @click="marketStore.setCategory('favorites')" :class="['flex items-center px-5 py-3 transition-colors relative', marketStore.activeCategory === 'favorites' ? 'text-yellow-500' : 'text-zinc-500 hover:text-zinc-300']">
          <div v-if="marketStore.activeCategory === 'favorites'" class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-yellow-500 rounded-r shadow-[0_0_10px_rgba(234,179,8,0.5)]"></div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          <span :class="['font-bold text-sm tracking-wider uppercase transition-opacity duration-300', marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0']">Favorites</span>
        </button>
      </div>

      <div class="flex flex-col border-t border-zinc-900">
        <button @click="marketStore.isSidebarExpanded = !marketStore.isSidebarExpanded" class="flex items-center px-5 h-14 text-zinc-500 hover:text-[#00e5ff] transition-colors cursor-pointer w-full focus:outline-none shrink-0">
          <svg v-if="!marketStore.isSidebarExpanded" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0"><path d="M13 5l7 7-7 7M5 5l7 7-7 7"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0"><path d="M11 19l-7-7 7-7M19 19l-7-7 7-7"/></svg>
        </button>

        <button class="flex items-center px-5 h-16 w-full text-zinc-500 hover:text-[#00e5ff] transition-colors border-t border-zinc-900 shrink-0 bg-[#050505]">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6 shrink-0"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <div :class="['flex flex-col text-left transition-opacity duration-300', marketStore.isSidebarExpanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0']">
            <span class="font-bold text-xs text-white uppercase tracking-widest">Profile</span>
            <span class="text-[10px] font-medium opacity-70">Connect Wallet</span>
          </div>
        </button>
      </div>
    </aside>

    <aside v-if="!currentEvent && ['sports', 'crypto'].includes(marketStore.activeCategory)" class="w-48 border-r border-zinc-900 bg-[#050505] flex flex-col shrink-0 z-40">
      <div class="h-14 flex items-center px-5 border-b border-zinc-900 shrink-0">
        <span class="font-bold text-[10px] uppercase tracking-widest text-zinc-500">{{ marketStore.activeCategory }} Markets</span>
      </div>
      <div class="flex flex-col p-3 gap-1 overflow-y-auto custom-scrollbar">
        <button 
          v-for="sub in activeSubcategoriesList" :key="sub.id"
          @click="marketStore.setSubcategory(sub.id)" 
          :class="['text-left px-3 py-2 text-[11px] font-bold uppercase tracking-widest rounded transition-colors', marketStore.activeSubcategory === sub.id ? 'text-[#00e5ff] bg-[#00e5ff]/5' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/50']"
        >
          {{ sub.label }}
        </button>
      </div>
    </aside>

    <main class="flex-1 flex flex-col min-w-0 bg-gradient-to-br from-[#000000] via-[#030303] to-[#001012]">
      
      <header class="h-12 flex items-center border-b border-zinc-900 shrink-0 bg-[#020202] overflow-x-auto hide-scrollbar z-20 w-full flex-nowrap">
        
        <div v-if="marketStore.favorites.length === 0" class="text-zinc-700 font-mono text-[10px] uppercase tracking-widest px-6 whitespace-nowrap">
          No pinned markets
        </div>

        <div 
          v-for="fav in marketStore.favorites" :key="fav.event_id"
          @click="openEvent(fav)" 
          :class="['relative h-full flex items-center px-4 gap-2.5 border-r border-zinc-900/50 cursor-pointer transition-all group shrink-0 min-w-[140px] max-w-[200px]', currentEvent?.event_id === fav.event_id ? 'bg-[#0a0a0a]' : 'hover:bg-zinc-900/30']"
        >
          <div v-if="currentEvent?.event_id === fav.event_id" class="absolute bottom-0 left-0 w-full h-[2px] bg-[#00e5ff] shadow-[0_0_8px_rgba(0,229,255,0.8)]"></div>
          
          <img v-if="fav.image" :src="fav.image" class="w-4 h-4 rounded-full object-cover border border-zinc-800 shrink-0" />
          <div v-else class="w-4 h-4 rounded-full bg-zinc-800 shrink-0"></div>

          <span :class="['text-[10px] font-bold uppercase tracking-widest truncate flex-1', currentEvent?.event_id === fav.event_id ? 'text-[#00e5ff]' : 'text-zinc-500 group-hover:text-zinc-300']" :title="fav.title">
            {{ fav.title }}
          </span>

          <button @click.stop="marketStore.toggleFavorite(fav)" class="text-zinc-700 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 shrink-0 p-1">
            <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
      </header>

      <div v-if="currentEvent" class="flex-1 flex overflow-hidden p-3 gap-3">
        <div class="w-64 flex flex-col gap-3 shrink-0">
          <div class="border border-zinc-800/60 rounded-2xl bg-[#0a0a0a]/80 backdrop-blur-sm p-4 shrink-0 shadow-lg">
            <div class="flex items-center gap-3 mb-5">
              <button @click="closeTerminal" class="text-zinc-500 hover:text-[#00e5ff] transition-colors">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-5 h-5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
              </button>
              <h3 class="font-bold text-gray-300 text-[11px] tracking-widest uppercase truncate">{{ currentEvent.title }}</h3>
            </div>
            
            <div class="flex justify-between items-center mb-4">
              <span class="font-bold text-zinc-500 text-[10px] uppercase tracking-widest">Strategy</span>
              <div class="flex rounded border border-zinc-800 bg-[#050505] p-0.5">
                <button @click="marketStore.tradingMode = 'custom'" :class="['px-2.5 py-1 text-[10px] font-bold rounded transition-colors uppercase tracking-wider', marketStore.tradingMode === 'custom' ? 'bg-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.3)]' : 'text-zinc-500 hover:text-zinc-300']">Cust</button>
                <button @click="marketStore.tradingMode = 'presets'" :class="['px-2.5 py-1 text-[10px] font-bold rounded transition-colors uppercase tracking-wider', marketStore.tradingMode === 'presets' ? 'bg-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.3)]' : 'text-zinc-500 hover:text-zinc-300']">Fast</button>
              </div>
            </div>

            <div class="mb-4">
              <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">Volume (USDC)</label>
              <input v-model="marketStore.tradeSize" type="number" class="w-full border border-zinc-800 rounded-lg px-3 py-2 text-sm font-bold outline-none focus:border-[#00e5ff] focus:ring-1 focus:ring-[#00e5ff]/30 bg-[#050505] text-white transition-all" />
            </div>

            <div v-if="marketStore.tradingMode === 'custom'" class="flex gap-2">
              <div class="flex-1">
                <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">TP (¢)</label>
                <input v-model="marketStore.tpOffset" type="number" class="w-full border border-zinc-800 rounded-lg px-2 py-2 text-sm font-bold outline-none focus:border-[#00e5ff] bg-[#050505] text-[#00e5ff] transition-all" />
              </div>
              <div class="flex-1">
                <label class="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-widest">SL (¢)</label>
                <input v-model="marketStore.slOffset" type="number" class="w-full border border-zinc-800 rounded-lg px-2 py-2 text-sm font-bold outline-none focus:border-indigo-400 bg-[#050505] text-indigo-400 transition-all" />
              </div>
            </div>

            <div v-if="marketStore.tradingMode === 'presets'" class="grid grid-cols-2 gap-2">
              <button @click="marketStore.activePreset = '4c'" :class="['p-2 rounded-lg text-xs font-bold border transition-colors', marketStore.activePreset === '4c' ? 'bg-[#00e5ff] border-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.3)]' : 'bg-[#050505] border-zinc-800 text-zinc-500 hover:text-white']">4c Gap</button>
              <button @click="marketStore.activePreset = '8c'" :class="['p-2 rounded-lg text-xs font-bold border transition-colors', marketStore.activePreset === '8c' ? 'bg-[#00e5ff] border-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.3)]' : 'bg-[#050505] border-zinc-800 text-zinc-500 hover:text-white']">8c Gap</button>
            </div>
          </div>

          <div class="border border-zinc-800/60 rounded-2xl bg-[#0a0a0a]/80 backdrop-blur-sm p-4 flex-1 overflow-y-auto custom-scrollbar shadow-lg">
            <h3 class="font-bold text-zinc-500 text-[10px] mb-3 tracking-widest uppercase">Orderbooks</h3>
            <div class="flex flex-col gap-2">
              <button 
                v-for="sub in currentEvent.sub_markets" :key="sub.condition_id"
                @click="openSubMarket(sub)"
                :class="['w-full p-3 rounded-xl text-left text-[11px] font-mono leading-relaxed transition-all border', activeSubMarket?.condition_id === sub.condition_id ? 'border-[#00e5ff] bg-[#00e5ff]/10 text-white shadow-[0_0_15px_rgba(0,229,255,0.1)]' : 'border-zinc-800/50 bg-[#050505] text-zinc-400 hover:bg-zinc-800']"
              >
                {{ sub.question }}
              </button>
            </div>
          </div>
        </div>

        <div class="flex-1 relative flex flex-col min-w-[350px]">
          <div v-if="isConnecting" class="absolute inset-0 z-50 flex items-center justify-center backdrop-blur-sm bg-[#050505]/80 rounded-2xl border border-zinc-800">
            <span class="text-[#00e5ff] text-sm font-bold font-mono animate-pulse tracking-widest uppercase shadow-[#00e5ff]">Connecting to L2 Stream...</span>
          </div>
          
          <div v-if="activeSubMarket" class="mb-3 flex items-center justify-between border-b border-zinc-800/60 pb-3 px-2">
            <h2 class="text-base font-bold truncate pr-4 text-gray-100 tracking-tight" :title="activeSubMarket.question">
              {{ activeSubMarket.question }}
            </h2>
            <div :class="['px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border transition-colors whitespace-nowrap', spreadBadgeClass]">
              SPREAD: {{ activeSpreadCents }}¢
            </div>
          </div>

          <OrderBook 
            ref="orderBookRef"
            v-if="activeSubMarket"
            :isDark="true"
            v-model:activeTeam="activeTeam"
            :team1Name="activeSubMarket.out1"
            :team2Name="activeSubMarket.out2"
            :ladderYes="ladderYes"
            :ladderNo="ladderNo"
            :bestBid="activeTeam === 1 ? bestBidYes : bestBidNo" 
            :bestAsk="activeTeam === 1 ? bestAskYes : bestAskNo"
            :currentTokenId="activeTeam === 1 ? activeSubMarket.token_id_yes : activeSubMarket.token_id_no"
            @placeOrder="handlePlaceOrder"
          />
        </div>

        <div class="w-64 border border-zinc-800/60 rounded-2xl bg-[#0a0a0a]/80 backdrop-blur-sm p-4 flex flex-col shrink-0 shadow-lg">
          <div class="flex justify-between items-center mb-4"> 
            <h3 class="font-bold text-zinc-500 text-[10px] tracking-widest uppercase">Live Positions</h3>
            <button @click="marketStore.loadPositions()" class="text-[10px] text-[#00e5ff] hover:text-white transition-colors uppercase font-mono tracking-wider">↻ Sync</button>
          </div>
          
          <div class="flex-1 overflow-y-auto custom-scrollbar space-y-3 pr-1">
            <div v-if="livePositions.length === 0" class="text-center font-mono text-zinc-600 text-[10px] mt-10 uppercase tracking-widest">No Open Orders</div>
            
            <div v-for="pos in livePositions" :key="pos.order_id" class="border border-zinc-800 rounded-xl bg-[#050505] p-3 flex flex-col gap-2 transition-colors hover:border-zinc-600">
              <div class="flex justify-between items-center">
                <span class="font-bold text-[11px] truncate max-w-[110px] text-gray-200 uppercase tracking-wide" :title="marketStore.getTeamNameFromToken(pos.token_id)">
                  {{ marketStore.getTeamNameFromToken(pos.token_id) }}
                </span>
                
                <div class="flex items-center">
                  <span v-if="pos.status === 'PENDING'" class="text-[9px] px-1.5 py-0.5 rounded font-bold bg-yellow-500/10 text-yellow-500 border border-yellow-500/30 animate-pulse uppercase tracking-widest">
                    PENDING
                  </span>
                  <span v-else :class="['font-mono font-bold text-xs', pos.liveDiff >= 0 ? 'text-[#00e5ff]' : 'text-indigo-400']">
                    {{ pos.liveDiff > 0 ? '+' : '' }}{{ pos.liveDiff }}¢
                  </span>
                </div>
              </div>
              
              <div class="text-[10px] flex flex-col gap-1.5 text-zinc-500 font-mono">
                <div class="flex justify-between px-2 py-1.5 rounded-lg bg-[#0a0a0a]">
                  <span>IN: <b class="text-white">{{ Math.round(pos.entry_price * 100) }}¢</b></span>
                  <span>SZ: <b class="text-white">{{ pos.size.toFixed(1) }}</b></span>
                </div>
                
                <div class="flex justify-between px-1.5 mt-0.5">
                  <span class="text-[#00e5ff]/70">TP: <b class="text-[#00e5ff]">{{ pos.tp_price ? Math.round(pos.tp_price * 100) + '¢' : '--' }}</b></span>
                  <span class="text-indigo-400/70">SL: <b class="text-indigo-400">{{ pos.sl_trigger_price ? Math.round(pos.sl_trigger_price * 100) + '¢' : '--' }}</b></span>
                </div>
              </div>
              
              <button @click="executePanicSell(pos.order_id)" class="w-full mt-1 bg-indigo-500/10 hover:bg-[#312E81] text-indigo-400 hover:text-white text-[10px] py-1.5 rounded-lg transition-all font-bold uppercase tracking-widest border border-indigo-500/30">
                {{ pos.status === 'PENDING' ? 'CANCEL' : 'MARKET DUMP' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="flex-1 flex flex-col overflow-hidden relative">
        
        <header class="h-14 border-b border-zinc-800/60 flex items-center px-8 shrink-0 bg-[#050505]/80 backdrop-blur-md z-10 w-full justify-between">
           
           <h2 class="text-sm font-black uppercase tracking-widest text-[#00e5ff] flex items-center gap-2">
             <span v-if="marketStore.activeCategory === 'favorites'" class="text-yellow-500">★</span>
             <span v-else-if="marketStore.activeCategory === 'live'" class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
             
             <template v-if="marketStore.activeCategory === 'favorites'">Saved Markets</template>
             <template v-else-if="marketStore.activeCategory === 'live'">Live Action</template>
             <template v-else>
               <span class="text-zinc-600">{{ marketStore.activeCategory }} / </span> {{ marketStore.activeSubcategory }}
             </template>
           </h2>

           <div class="flex items-center gap-2 border-zinc-800/60 shrink-0">
             <span class="text-[9px] font-mono text-zinc-600 uppercase tracking-widest mr-1">Sort by:</span>
             <button @click="marketStore.sortBy = 'volume'" :class="['px-3 py-1.5 rounded-md text-[9px] font-black uppercase tracking-widest transition-colors', marketStore.sortBy === 'volume' ? 'text-[#00e5ff] bg-[#00e5ff]/10 border border-[#00e5ff]/30' : 'text-zinc-500 border border-transparent hover:text-zinc-300']">VOL</button>
             <button @click="marketStore.sortBy = 'date'" :class="['px-3 py-1.5 rounded-md text-[9px] font-black uppercase tracking-widest transition-colors', marketStore.sortBy === 'date' ? 'text-[#00e5ff] bg-[#00e5ff]/10 border border-[#00e5ff]/30' : 'text-zinc-500 border border-transparent hover:text-zinc-300']">DATE</button>
           </div>
        </header>

        <div class="flex-1 overflow-y-auto p-8 relative custom-scrollbar">
          <div v-if="marketStore.isLoadingMarkets" class="absolute inset-0 flex items-center justify-center z-10 bg-[#0a0a0a]/60 backdrop-blur-sm">
             <span class="text-[#00e5ff] font-mono animate-pulse font-bold text-sm uppercase tracking-widest">Scanning Blockchain...</span>
          </div>

          <div class="max-w-[1600px] mx-auto">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-5">
              
              <div v-for="match in marketStore.filteredMatches" :key="match.event_id" 
                   class="relative bg-[#0a0a0a]/90 backdrop-blur-sm border border-zinc-900 rounded-2xl flex flex-col h-[230px] transition-all duration-300 hover:border-zinc-700 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)] hover:-translate-y-1 group overflow-hidden">
                
                <div class="flex justify-between items-start p-5 shrink-0">
                  <span class="text-[10px] font-medium font-mono text-zinc-500 uppercase tracking-widest">
                    {{ formatDate(match.start_date) }}
                  </span>
                  <div class="flex items-center gap-2">
                    <span v-if="match.is_live" class="bg-red-500/10 border border-red-500/30 text-red-500 text-[9px] font-black px-1.5 py-0.5 rounded animate-pulse uppercase tracking-widest">LIVE</span>
                    <button @click.stop="marketStore.toggleFavorite(match)" class="text-zinc-600 hover:text-yellow-500 transition-colors">
                      <svg viewBox="0 0 24 24" :fill="marketStore.favorites.some(f => f.event_id === match.event_id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" class="w-4 h-4" :class="{'text-yellow-500 drop-shadow-[0_0_5px_rgba(234,179,8,0.5)]': marketStore.favorites.some(f => f.event_id === match.event_id)}"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </button>
                  </div>
                </div>

                <div class="px-5 flex-1 overflow-hidden flex gap-4 items-start">
                  <img v-if="match.image" :src="match.image" class="w-10 h-10 rounded-full shrink-0 object-cover border-2 border-zinc-800 group-hover:border-[#00e5ff]/50 transition-colors" />
                  <h3 class="font-bold text-base text-gray-200 line-clamp-3 leading-snug tracking-tight group-hover:text-white transition-colors" :title="match.title">
                    {{ match.title }}
                  </h3>
                </div>

                <div class="p-5 border-t border-zinc-900 bg-[#050505]/50 shrink-0 flex flex-col gap-3">
                  <div v-if="match.sub_markets && match.sub_markets.length > 0" class="flex flex-col gap-2">
                    
                    <div class="flex justify-between items-center font-mono">
                      <div class="flex flex-col">
                        <span class="text-[9px] uppercase tracking-widest text-zinc-500 truncate max-w-[80px]" :title="match.sub_markets[0].out1">{{ match.sub_markets[0].out1 || 'YES' }}</span>
                        <span class="font-bold text-[#00e5ff] text-xs">{{ Math.round(match.sub_markets[0].price_yes * 100) }}%</span>
                      </div>
                      
                      <div class="flex flex-col text-right">
                        <span class="text-[9px] uppercase tracking-widest text-zinc-500 truncate max-w-[80px]" :title="match.sub_markets[0].out2">{{ match.sub_markets[0].out2 || 'NO' }}</span>
                        <span class="font-bold text-indigo-400 text-xs">{{ Math.round(match.sub_markets[0].price_no * 100) }}%</span>
                      </div>
                    </div>

                    <div class="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden flex">
                      <div class="h-full bg-[#00e5ff] transition-all duration-500" :style="{ width: Math.round(match.sub_markets[0].price_yes * 100) + '%' }"></div>
                      <div class="h-full bg-[#312E81] transition-all duration-500" :style="{ width: Math.round(match.sub_markets[0].price_no * 100) + '%' }"></div>
                    </div>

                  </div>

                  <div class="flex justify-between items-end mt-1">
                    <div class="text-[9px] text-zinc-600 font-mono uppercase tracking-widest">Vol: <span class="text-zinc-300 font-medium">${{ formatVolume(match.total_volume) }}</span></div>
                    <button @click="openEvent(match)" class="px-5 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all border border-[#00e5ff]/30 bg-[#00e5ff]/10 text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black hover:shadow-[0_0_15px_rgba(0,229,255,0.4)]">
                      TRADE
                    </button>
                  </div>
                </div>

              </div>
            </div>
            
            <div v-if="!marketStore.isLoadingMarkets && marketStore.filteredMatches.length === 0" class="flex flex-col items-center justify-center h-64 opacity-50">
              <span class="text-sm font-mono uppercase tracking-widest text-zinc-600">Zero Markets Found</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useToast } from 'vue-toastification'
import OrderBook from './Terminal/OrderBook.vue'

import { useMarketStore } from '../store/marketStore'
import { useOrderBook } from '../composables/useOrderBook'

const toast = useToast()
const marketStore = useMarketStore()

const { 
  ladderYes, ladderNo, 
  spreadYes, spreadNo, 
  bestBidYes, bestAskYes, 
  bestBidNo, bestAskNo,
  isConnecting, connectToMarket, disconnect 
} = useOrderBook()

const currentEvent = ref(null)
const activeSubMarket = ref(null)
const activeTeam = ref(1)
const orderBookRef = ref(null)

const sportsCategories = [
  { id: 'all', label: 'All Sports' },
  { id: 'dota 2', label: 'Dota 2' },
  { id: 'soccer', label: 'Soccer' },
  { id: 'basketball', label: 'Basketball' },
  { id: 'tennis', label: 'Tennis' },
  { id: 'mma', label: 'MMA' }
]

const cryptoCategories = [
  { id: 'all', label: 'All Crypto' },
  { id: 'bitcoin', label: 'Bitcoin' },
  { id: 'ethereum', label: 'Ethereum' }
]

const activeSubcategoriesList = computed(() => {
  return marketStore.activeCategory === 'crypto' ? cryptoCategories : sportsCategories
})

const activeSpreadCents = computed(() => {
  const sp = activeTeam.value === 1 ? spreadYes.value : spreadNo.value
  return Math.round(sp * 100)
})

const spreadBadgeClass = computed(() => {
  const cents = activeSpreadCents.value
  if (cents <= 2) return 'bg-[#00e5ff]/10 text-[#00e5ff] border-[#00e5ff]/30'
  if (cents <= 5) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
  return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
})

const livePositions = computed(() => {
  return marketStore.openPositions.map(pos => {
    if (pos.status === 'CLOSED_TP' || pos.status === 'CLOSED_SL' || pos.status === 'RESOLVED') {
      const exitP = pos.exit_price || pos.entry_price;
      const profitCents = Math.round((exitP - pos.entry_price) * 100);
      return { ...pos, liveDiff: profitCents };
    }

    let currentMarketPrice = 0;
    if (activeSubMarket.value) {
      if (pos.token_id === activeSubMarket.value.token_id_yes) {
        currentMarketPrice = bestBidYes.value;
      } else if (pos.token_id === activeSubMarket.value.token_id_no) {
        currentMarketPrice = bestBidNo.value;
      }
    }
    
    if (!currentMarketPrice) currentMarketPrice = pos.entry_price;

    const profitCents = Math.round((currentMarketPrice - pos.entry_price) * 100);
    return { ...pos, liveDiff: profitCents, currentMarketPrice };
  });
});

const handleKeydown = (e) => {
  if (e.code === 'Space' && currentEvent.value && e.target.tagName !== 'INPUT') {
    e.preventDefault()
    orderBookRef.value?.scrollToSpread()
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'TBA'
  const date = new Date(dateString)
  const now = new Date()
  
  const isToday = date.getDate() === now.getDate() && date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear()
  const time = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
  
  if (isToday) return `TODAY, ${time}`
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' }).toUpperCase() + `, ${time}`
}

const formatVolume = (val) => val >= 1000000 ? (val / 1000000).toFixed(2) + 'M' : val >= 1000 ? (val / 1000).toFixed(1) + 'K' : Math.round(val)

const closeTerminal = () => {
  disconnect()
  currentEvent.value = null
  activeSubMarket.value = null
}

const openEvent = (match) => {
  currentEvent.value = match
  if (match.sub_markets.length > 0) openSubMarket(match.sub_markets[0])
}

const openSubMarket = (sub) => {
  activeSubMarket.value = sub
  connectToMarket(sub, () => {
    nextTick(() => orderBookRef.value?.scrollToSpread())
  })
}

const handlePlaceOrder = async (side, priceCents) => {
  if (side === 'SELL') return
  const targetToken = activeTeam.value === 1 ? activeSubMarket.value.token_id_yes : activeSubMarket.value.token_id_no
  
  let finalTpCents = null
  let finalSlCents = null  
  let finalStrategy = 'custom'

  if (marketStore.tradingMode === 'custom') {
    finalTpCents = marketStore.tpOffset > 0 ? priceCents + marketStore.tpOffset : null
    finalSlCents = marketStore.slOffset > 0 ? priceCents - marketStore.slOffset : null
  } else {
    finalStrategy = marketStore.activePreset
    if (marketStore.activePreset === '4c') {
      finalTpCents = priceCents + 4
      finalSlCents = priceCents - 12
    }
    if (marketStore.activePreset === '8c') {
      finalTpCents = priceCents + 8
      finalSlCents = priceCents - 12
    }
  }

  const reqBody = {
    token_id: targetToken,
    condition_id: activeSubMarket.value.condition_id,
    price: priceCents / 100.0,
    side: "BUY", 
    bankroll: marketStore.tradeSize, 
    risk_percent: 100, 
    is_custom_limit: true,
    take_profit_price: finalTpCents ? Math.min(0.99, finalTpCents / 100.0) : null,
    stop_loss_price: finalSlCents ? Math.max(0.01, finalSlCents / 100.0) : null,
    strategy: finalStrategy
  }
  
  try {
    toast.info(`Transmitting order...`)
    const res = await fetch('http://127.0.0.1:8000/api/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody)
    })
    const data = await res.json()
    if (data.success) {
      toast.success(`✅ FILLED ${priceCents}¢`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ REJECTED: ${data.error}`)
    }
  } catch (e) {
    toast.error("❌ TIMEOUT: Node Unreachable")
  }
}

const executePanicSell = async (orderId) => {
  try {
    toast.warning("⚡ Market Dump Initiation...")
    const res = await fetch(`http://127.0.0.1:8000/api/panic_sell/${orderId}`, {
      method: 'POST'
    })
    const data = await res.json()
    if (data.success) {
      toast.success(`✅ ${data.message}`)
      marketStore.loadPositions()
    } else {
      toast.error(`❌ ERROR: ${data.error}`)
    }
  } catch(e) {
    toast.error("❌ TIMEOUT: Node Unreachable")
  }
}

onMounted(() => { 
  window.addEventListener('keydown', handleKeydown)
  marketStore.loadMatches()
  marketStore.loadPositions()
  setInterval(() => { marketStore.loadPositions() }, 3000) 
})

onUnmounted(() => { 
  window.removeEventListener('keydown', handleKeydown)
  disconnect()
})
</script>

<style>
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>