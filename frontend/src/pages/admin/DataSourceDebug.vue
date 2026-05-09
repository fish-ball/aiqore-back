<template>
  <div class="data-source-debug">
    <EmptyView title="接口调试" :subtitle="pageSubtitle">
      <template #actions>
        <el-button text @click="goBack">返回列表</el-button>
      </template>

      <template v-if="loading">
        <div class="debug-body debug-body--state">
          <el-icon class="is-loading"><IconLoading /></el-icon>
          <span>加载连接信息...</span>
        </div>
      </template>
      <template v-else-if="!supportDebug">
        <div class="debug-body">
          <el-alert type="info" :closable="false">
            当前仅支持 miniQMT 类型数据源的接口调试。该连接类型为「{{ sourceTypeLabel }}」，请使用 miniQMT/QMT 连接进行调试。
          </el-alert>
        </div>
      </template>
      <template v-else>
        <div class="debug-body">
          <el-tabs v-model="activeTab" tab-position="left" class="debug-tabs">
            <el-tab-pane
              v-for="tab in tabs"
              :key="tab.key"
              :name="tab.key"
              :label="tab.label"
            >
              <template #label>
                <span>{{ tab.label }}</span>
              </template>
              <div class="tab-content">
                <div class="tab-form">
                  <el-form label-width="100px" label-position="top">
                    <template v-if="tab.key === 'test'">
                      <el-form-item label="说明">
                        <span class="form-hint">检测当前连接是否可用（需本机已启动 miniQMT）。</span>
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'sectors'">
                      <el-form-item label="说明">
                        <span class="form-hint">获取板块列表（如 沪深A股、创业板 等）。</span>
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'stocks-in-sector'">
                      <el-form-item label="板块名称" required>
                        <el-input v-model="form.sector" placeholder="如 沪深A股" clearable />
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'instrument-detail'">
                      <el-form-item label="标的代码" required>
                        <el-input v-model="form.symbol" placeholder="如 000001.SZ" clearable />
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'market-data'">
                      <el-form-item label="标的代码" required>
                        <el-input v-model="form.symbolKline" placeholder="如 000001.SZ" clearable />
                      </el-form-item>
                      <el-form-item label="周期">
                        <el-select v-model="form.period" placeholder="周期" style="width: 100%">
                          <el-option label="1d" value="1d" />
                          <el-option label="1m" value="1m" />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="条数">
                        <el-input-number v-model="form.count" :min="1" :max="2000" style="width: 100%" />
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'realtime-quote'">
                      <el-form-item label="标的代码（多个用逗号分隔）" required>
                        <el-input v-model="form.symbolsText" type="textarea" :rows="2" placeholder="如 000001.SZ,600000.SH" />
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'stock-list'">
                      <el-form-item label="市场（可选）">
                        <el-select v-model="form.market" placeholder="不选为全部" clearable style="width: 100%">
                          <el-option label="SH" value="SH" />
                          <el-option label="SZ" value="SZ" />
                          <el-option label="BJ" value="BJ" />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="板块（可选）">
                        <el-input v-model="form.sectorStockList" placeholder="如 沪深A股，不填则按市场或全量" clearable />
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'positions'">
                      <el-form-item label="资金账号" required>
                        <el-input v-model="form.account_id" placeholder="与 miniQMT 登录账号一致" clearable />
                      </el-form-item>
                    </template>
                    <template v-else-if="tab.key === 'account-info'">
                      <el-form-item label="资金账号" required>
                        <el-input v-model="form.account_id_info" placeholder="与 miniQMT 登录账号一致" clearable />
                      </el-form-item>
                    </template>
                  </el-form>
                  <el-button type="primary" @click="sendRequest(tab)" :loading="requestLoading">发送请求</el-button>
                </div>
                <div class="tab-result">
                  <div class="result-label">返回结果（JSON）</div>
                  <pre class="result-json">{{ resultJson || '发送请求后在此显示返回的 JSON' }}</pre>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </template>
    </EmptyView>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import EmptyView from '@iottest/vue-core/src/libs/data-view/components/EmptyView.vue'
import { api } from '@iottest/vue-core/src/libs/api'

const dataSourceConnResource = api('data-source/connections')

const route = useRoute()
const router = useRouter()
const connectionId = computed(() => Number(route.params.id))

const loading = ref(true)
const connectionName = ref('')
const sourceType = ref('')
const supportDebug = computed(() => sourceType.value === 'qmt')

const sourceTypeLabel = computed(() => {
  const m = { qmt: 'miniQMT/QMT', joinquant: '聚宽', tushare: 'Tushare' }
  return m[sourceType.value] || sourceType.value
})

/** 与原先 h2 副标题一致：连接名称或加载提示 */
const pageSubtitle = computed(() => {
  if (loading.value) return '加载中...'
  return connectionName.value || ''
})

const tabs = [
  { key: 'test', label: '连接测试' },
  { key: 'sectors', label: '板块列表' },
  { key: 'stocks-in-sector', label: '板块股票' },
  { key: 'instrument-detail', label: '标的详情' },
  { key: 'market-data', label: 'K线数据' },
  { key: 'realtime-quote', label: '实时行情' },
  { key: 'stock-list', label: '证券列表' },
  { key: 'positions', label: '持仓查询' },
  { key: 'account-info', label: '账户信息' }
]

const activeTab = ref('test')
const requestLoading = ref(false)
const resultJson = ref('')

const form = ref({
  sector: '沪深A股',
  symbol: '000001.SZ',
  symbolKline: '000001.SZ',
  period: '1d',
  count: 100,
  symbolsText: '000001.SZ,600000.SH',
  market: '',
  sectorStockList: '',
  account_id: '',
  account_id_info: ''
})

function goBack() {
  router.push({ name: 'admin-data-sources' })
}

async function fetchConnection() {
  loading.value = true
  try {
    const resp = await dataSourceConnResource.get({ id: connectionId.value }, {})
    const item = resp.data
    if (item) {
      connectionName.value = item.name || ''
      sourceType.value = item.source_type || ''
    }
  } catch (e) {
    ElMessage.error(e?.message || '加载连接失败')
  } finally {
    loading.value = false
  }
}

async function sendRequest(tab) {
  const id = connectionId.value
  if (!id) return

  const key = tab.key
  if (key === 'stocks-in-sector' && !form.value.sector?.trim()) {
    ElMessage.warning('请填写板块名称')
    return
  }
  if (key === 'instrument-detail' && !form.value.symbol?.trim()) {
    ElMessage.warning('请填写标的代码')
    return
  }
  if (key === 'market-data' && !form.value.symbolKline?.trim()) {
    ElMessage.warning('请填写标的代码')
    return
  }
  if (key === 'realtime-quote') {
    const raw = (form.value.symbolsText || '').trim().split(/[,，\s]+/).filter(Boolean)
    if (raw.length === 0) {
      ElMessage.warning('请填写至少一个标的代码')
      return
    }
  }
  if (key === 'positions' && !form.value.account_id?.trim()) {
    ElMessage.warning('请填写资金账号')
    return
  }
  if (key === 'account-info' && !form.value.account_id_info?.trim()) {
    ElMessage.warning('请填写资金账号')
    return
  }

  requestLoading.value = true
  resultJson.value = ''
  try {
    let data
    switch (key) {
      case 'test': {
        const r = await dataSourceConnResource.post({ id, action: 'test' }, {})
        data = r.data
        break
      }
      case 'sectors': {
        const r = await dataSourceConnResource.get({ id, action: 'debug/sectors' }, {})
        data = r.data
        break
      }
      case 'stocks-in-sector': {
        const r = await dataSourceConnResource.post({ id, action: 'debug/stocks-in-sector' }, {
          sector: form.value.sector.trim(),
        })
        data = r.data
        break
      }
      case 'instrument-detail': {
        const r = await dataSourceConnResource.post({ id, action: 'debug/instrument-detail' }, {
          symbol: (form.value.symbol || '').trim(),
        })
        data = r.data
        break
      }
      case 'market-data': {
        const r = await dataSourceConnResource.post({ id, action: 'debug/market-data' }, {
          symbol: (form.value.symbolKline || '').trim(),
          period: form.value.period,
          count: form.value.count,
        })
        data = r.data
        break
      }
      case 'realtime-quote': {
        const symbols = (form.value.symbolsText || '').trim().split(/[,，\s]+/).filter(Boolean)
        const r = await dataSourceConnResource.post({ id, action: 'debug/realtime-quote' }, { symbols })
        data = r.data
        break
      }
      case 'stock-list': {
        const payload = {}
        if (form.value.market?.trim()) payload.market = form.value.market.trim()
        if (form.value.sectorStockList?.trim()) payload.sector = form.value.sectorStockList.trim()
        const r = await dataSourceConnResource.post({ id, action: 'debug/stock-list' }, payload)
        data = r.data
        break
      }
      case 'positions': {
        const r = await dataSourceConnResource.post({ id, action: 'debug/positions' }, {
          account_id: form.value.account_id.trim(),
        })
        data = r.data
        break
      }
      case 'account-info': {
        const r = await dataSourceConnResource.post({ id, action: 'debug/account-info' }, {
          account_id: form.value.account_id_info.trim(),
        })
        data = r.data
        break
      }
      default:
        data = null
    }
    resultJson.value = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '请求失败'
    resultJson.value = JSON.stringify({ error: msg }, null, 2)
    ElMessage.error(msg)
  } finally {
    requestLoading.value = false
  }
}

watch(connectionId, fetchConnection, { immediate: true })
</script>

<style scoped>
.data-source-debug {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.data-source-debug :deep(.empty-view) {
  min-height: 0;
}

.debug-body {
  margin-top: 0;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.debug-body--state {
  align-items: center;
  gap: 8px;
  padding: 24px 0;
  color: var(--el-text-color-secondary);
}

.form-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.debug-tabs {
  min-height: 420px;
  flex: 1;
  min-width: 0;
}
.debug-tabs :deep(.el-tabs__header) {
  margin-right: 16px;
}
.debug-tabs :deep(.el-tabs__item) {
  text-align: left;
  padding-left: 12px;
}
.debug-tabs :deep(.el-tabs__content) {
  overflow: visible;
}
.tab-content {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}
.tab-form {
  flex: 0 0 280px;
}
.tab-form .el-button {
  margin-top: 8px;
}
.tab-result {
  flex: 1;
  min-width: 320px;
  display: flex;
  flex-direction: column;
}
.result-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}
.result-json {
  flex: 1;
  margin: 0;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  min-height: 200px;
  max-height: 400px;
  overflow: auto;
}
</style>
