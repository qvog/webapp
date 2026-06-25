import { defineStore } from 'pinia'
import { tradeApi } from '../api/tradeService'
import { useToast } from 'vue-toastification'

const toast = useToast()

export const useMarketStore = defineStore('market', {
  state: () => ({
    isDark: true,               // Глобальная тема
    matches: [],                // Список всех турниров
    openPositions: [],          // Открытые сделки
    
    // HFT Настройки
    tradeSize: 5,
    tradingMode: 'custom',
    tpOffset: 4,
    slOffset: 12,
    activePreset: '4c'
  }),

  actions: {
    // Загрузка матчей с сортировкой по объему
    async loadMatches() {
      try {
        const data = await tradeApi.getMarkets('Dota 2')
        if (data.matches) {
          this.matches = data.matches.sort((a, b) => b.total_volume - a.total_volume)
        }
      } catch (e) {
        toast.error("Failed to load matches")
      }
    },

    // Загрузка позиций и расчет PnL
    async loadPositions() {
      try {
        const data = await tradeApi.getPositions()
        if (data.success) {
          this.openPositions = data.positions.map(pos => {
            let diff = Math.round(pos.entry_price * 100) - Math.round(pos.entry_price * 100)
            return { ...pos, currentPnL: (diff / 100) * pos.size }
          })
        }
      } catch (e) {
        console.error("Ошибка загрузки позиций", e)
      }
    },

    // Получение имени команды по токену (чистая функция)
    getTeamNameFromToken(tokenId) {
      for (let match of this.matches) {
        for (let sub of match.sub_markets) {
          if (sub.token_id_yes === tokenId) return sub.out1
          if (sub.token_id_no === tokenId) return sub.out2
        }
      }
      return "Order"
    }
  }
})