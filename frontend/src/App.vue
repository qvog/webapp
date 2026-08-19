<template>
  <div class="flex h-screen w-full bg-[#000000] text-gray-200 font-sans overflow-hidden">
    <Sidebar
      :active-tab="activeTab"
      @change-tab="activeTab = $event"
      @home="onHome"
    />

    <Terminal v-if="activeTab === 'terminal'" />
    <StatsDashboard v-else-if="activeTab === 'stats'" />

    <GlobalPositionsSidebar @open-terminal="activeTab = 'terminal'" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Terminal from './components/Terminal.vue'
import Sidebar from './components/Terminal/Sidebar.vue'
import StatsDashboard from './components/Stats/StatsDashboard.vue'
import GlobalPositionsSidebar from './components/GlobalPositionsSidebar.vue'
import { useMarketStore } from './store/marketStore'

const marketStore = useMarketStore()
const activeTab = ref('terminal')

function onHome() {
  activeTab.value = 'terminal'
  marketStore.goHome()
}
</script>
