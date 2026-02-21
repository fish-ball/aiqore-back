<template>
  <div class="data-source-debug">
    <div class="page-header">
      <div>
        <el-button text @click="goBack" style="margin-right: 8px">返回列表</el-button>
        <h2>接口调试：{{ connectionName || '加载中...' }}</h2>
      </div>
    </div>

    <template v-if="loading">
      <el-card style="margin-top: 16px"><el-icon class="is-loading"><Loading /></el-icon> 加载连接信息...</el-card>
    </template>
    <template v-else-if="!supportDebug">
      <el-card style="margin-top: 16px">
        <el-alert type="info" :closable="false">
          当前仅支持 miniQMT 类型数据源的接口调试。该连接类型为「{{ sourceTypeLabel }}」，请使用 miniQMT/QMT 连接进行调试。
        </el-alert>
      </el-card>
    </template>
    <template v-else>
      <el-card style="margin-top: 16px">
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
                      <span class="form-hint">检测当前连接是否可用（xtquant 路径与账号）。</span>
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
                  <template v-else-if="tab.key === 'search-stocks'">
                    <el-form-item label="关键词" required>
                      <el-input v-model="form.keyword" placeholder="代码或名称关键词" clearable />
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
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { dataSourceApi } from '../api/dataSource'

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

const tabs = [
  { key: 'test', label: '连接测试' },
  { key: 'sectors', label: '板块列表' },
  { key: 'stocks-in-sector', label: '板块股票' },
  { key: 'instrument-detail', label: '标的详情' },
  { key: 'market-data', label: 'K线数据' },
  { key: 'realtime-quote', label: '实时行情' },
  { key: 'stock-list', label: '证券列表' },
  { key: 'positions', label: '持仓查询' },
  { key: 'account-info', label: '账户信息' },
  { key: 'search-stocks', label: '股票搜索' }
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
  account_id_info: '',
  keyword: ''
})

function goBack() {
  router.push('/data-sources')
}

async function fetchConnection() {
  loading.value = true
  try {
    const item = await dataSourceApi.getOne(connectionId.value)
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
  if (key === 'search-stocks' && !form.value.keyword?.trim()) {
    ElMessage.warning('请填写关键词')
    return
  }

  requestLoading.value = true
  resultJson.value = ''
  try {
    let data
    switch (key) {
      case 'test':
        data = await dataSourceApi.test(id)
        break
      case 'sectors':
        data = await dataSourceApi.debugSectors(id)
        break
      case 'stocks-in-sector':
        data = await dataSourceApi.debugStocksInSector(id, form.value.sector.trim())
        break
      case 'instrument-detail':
        data = await dataSourceApi.debugInstrumentDetail(id, (form.value.symbol || '').trim())
        break
      case 'market-data':
        data = await dataSourceApi.debugMarketData(
          id,
          (form.value.symbolKline || '').trim(),
          form.value.period,
          form.value.count
        )
        break
      case 'realtime-quote': {
        const symbols = (form.value.symbolsText || '').trim().split(/[,，\s]+/).filter(Boolean)
        data = await dataSourceApi.debugRealtimeQuote(id, symbols)
        break
      }
      case 'stock-list': {
        const payload = {}
        if (form.value.market?.trim()) payload.market = form.value.market.trim()
        if (form.value.sectorStockList?.trim()) payload.sector = form.value.sectorStockList.trim()
        data = await dataSourceApi.debugStockList(id, payload)
        break
      }
      case 'positions':
        data = await dataSourceApi.debugPositions(id, form.value.account_id.trim())
        break
      case 'account-info':
        data = await dataSourceApi.debugAccountInfo(id, form.value.account_id_info.trim())
        break
      case 'search-stocks':
        data = await dataSourceApi.debugSearchStocks(id, form.value.keyword.trim())
        break
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
.data-source-debug .page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.data-source-debug h2 {
  margin: 0;
  font-size: 18px;
}
.form-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.debug-tabs {
  min-height: 420px;
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
