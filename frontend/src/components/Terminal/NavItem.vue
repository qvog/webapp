<template>
  <button
    :class="[
      'flex items-center px-5 py-3 transition-colors relative w-full',
      active ? activeClass : 'text-zinc-500 hover:text-zinc-300',
    ]"
    @click="$emit('click')"
  >
    <div
      v-if="active"
      :class="['absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r', barClass]"
    />
    <slot name="icon" />
    <span
      :class="[
        'font-bold text-sm tracking-wider uppercase transition-opacity duration-300',
        expanded ? 'opacity-100 ml-4' : 'opacity-0 ml-0',
      ]"
    >
      {{ label }}
    </span>
  </button>
</template>

<script setup>
defineProps({
  active: Boolean,
  expanded: Boolean,
  label: String,
  activeClass: { type: String, default: 'text-[#00e5ff]' },
  barClass: { type: String, default: 'bg-[#00e5ff]' },
})
defineEmits(['click'])
</script>
