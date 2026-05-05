<template>
  <div class="contract-stub">
    <el-empty :description="description" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const description = computed(() => {
  const d = route.meta.stubDescription
  return typeof d === 'string' && d.length > 0 ? d : '页面建设中'
})
</script>

<style scoped>
.contract-stub {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
  background: #fff;
  border-radius: 4px;
}
</style>
