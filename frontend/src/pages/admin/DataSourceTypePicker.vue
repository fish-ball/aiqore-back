<template>
  <div class="data-source-type-picker">
    <div
      v-for="opt in typeOptions"
      :key="opt.type"
      class="type-card"
      @click="$emit('pick', opt.type)"
    >
      <div class="type-card-title">{{ opt.title }}</div>
      <div class="type-card-desc">{{ opt.desc }}</div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['pick'])

const typeOptions = [
  {
    type: 'qmt',
    title: 'miniQMT / QMT',
    desc: '国金 QMT 或 miniQMT 本地行情与交易，需配置 xtquant 路径等。',
  },
  {
    type: 'joinquant',
    title: '聚宽',
    desc: '聚宽平台数据源，需配置 Token / API（后续开放）。',
  },
  {
    type: 'tushare',
    title: 'Tushare',
    desc: 'Tushare 数据源，需配置 Token（后续开放）。',
  },
]
</script>

<style scoped>
.data-source-type-picker {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.type-card {
  padding: 14px 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    background 0.2s;
}
.type-card:hover {
  border-color: var(--el-color-primary);
  background: var(--el-fill-color-light);
}
.type-card-title {
  font-weight: 600;
  margin-bottom: 6px;
}
.type-card-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
</style>
