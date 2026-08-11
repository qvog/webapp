<template>
  <div class="flex h-screen w-full bg-[#000000] text-gray-200 font-sans overflow-hidden">
    <Sidebar
      :active-tab="activeTab"
      @change-tab="activeTab = $event"
      @home="activeTab = 'terminal'"
    />

    <Terminal v-if="activeTab === 'terminal'" />
    <StatsDashboard v-else-if="activeTab === 'stats'" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Terminal from './components/Terminal.vue'
import Sidebar from './components/Terminal/Sidebar.vue'
import StatsDashboard from './components/Stats/StatsDashboard.vue'

const activeTab = ref('terminal')
</script>
