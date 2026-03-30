<template>
  <router-view></router-view>
  <!-- 为了支持动态弹窗组件插入，要有一个这样的注入点，后续考虑如何移进内核 -->
  <DynamicComponentHolder></DynamicComponentHolder>
</template>

<script setup lang="ts">
import DynamicComponentHolder from '@iottest/vue-core/src/libs/dynamic-components/DynamicComponentHolder.vue'
</script>
