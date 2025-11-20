<template>
  <div class="sectors-page">
    <div class="page-header">
      <h2>板块管理</h2>
      <div>
        <el-button type="primary" @click="syncSectors" :loading="syncing">
          <el-icon><Refresh /></el-icon>
          {{ syncing ? '同步中...' : '同步板块' }}
        </el-button>
        <el-button @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-card style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>板块列表</span>
          <div>
            <el-select v-model="filterCategory" placeholder="选择分类" style="width: 150px; margin-right: 10px" @change="handleFilterChange" clearable>
              <el-option label="全部" value="" />
              <el-option label="股票" value="股票" />
              <el-option label="基金" value="基金" />
              <el-option label="债券" value="债券" />
              <el-option label="期货" value="期货" />
              <el-option label="期权" value="期权" />
              <el-option label="指数" value="指数" />
            </el-select>
            <el-select v-model="filterMarket" placeholder="选择市场" style="width: 120px" @change="handleFilterChange" clearable>
              <el-option label="全部" value="" />
              <el-option label="上海" value="SH" />
              <el-option label="深圳" value="SZ" />
              <el-option label="跨市场" value="" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
        stripe
        height="600"
      >
        <el-table-column prop="name" label="板块名称" width="200" sortable>
          <template #default="scope">
            <el-link type="primary" @click="viewSectorSecurities(scope.row.name)">
              {{ scope.row.display_name || scope.row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100" sortable>
          <template #default="scope">
            <el-tag :type="getCategoryTagType(scope.row.category)" size="small">
              {{ scope.row.category || '其他' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="market" label="市场" width="100" sortable>
          <template #default="scope">
            <el-tag v-if="scope.row.market" :type="scope.row.market === 'SH' ? 'success' : 'warning'" size="small">
              {{ scope.row.market === 'SH' ? '上海' : scope.row.market === 'SZ' ? '深圳' : scope.row.market }}
            </el-tag>
            <span v-else style="color: #909399">跨市场</span>
          </template>
        </el-table-column>
        <el-table-column prop="security_count" label="证券数量" width="120" sortable>
          <template #default="scope">
            <el-tag type="info" size="small">{{ scope.row.security_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_sync_at" label="最后同步" width="180" sortable>
          <template #default="scope">
            {{ scope.row.last_sync_at ? formatDateTime(scope.row.last_sync_at) : '--' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" @click="syncSectorSecurities(scope.row.name)">
              同步证券
            </el-button>
            <el-button type="info" size="small" @click="viewSectorSecurities(scope.row.name)">
              查看证券
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import sectorApi from '../api/sector.js'

const router = useRouter()

const loading = ref(false)
const syncing = ref(false)
const tableData = ref([])
const filterCategory = ref('')
const filterMarket = ref('')

const fetchSectors = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterCategory.value) params.category = filterCategory.value
    if (filterMarket.value) params.market = filterMarket.value
    const response = await sectorApi.getList(params)
    tableData.value = response.items || []
  } catch (error) {
    ElMessage.error('获取板块列表失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const syncSectors = async () => {
  try {
    await ElMessageBox.confirm('确定要从QMT同步板块列表吗？', '确认同步', {
      type: 'warning'
    })
    
    syncing.value = true
    const response = await sectorApi.sync()
    ElMessage.success(`同步完成: 新增 ${response.created || 0} 个，更新 ${response.updated || 0} 个`)
    await fetchSectors()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('同步失败: ' + error.message)
    }
  } finally {
    syncing.value = false
  }
}

const syncSectorSecurities = async (sectorName) => {
  try {
    await ElMessageBox.confirm(`确定要同步板块 "${sectorName}" 的证券吗？`, '确认同步', {
      type: 'warning'
    })
    
    // 调用证券更新API，传入板块参数
    const response = await fetch('/api/security/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sector: sectorName })
    })
    
    const result = await response.json()
    if (result.code === 0) {
      ElMessage.success('同步任务已提交，请查看任务列表')
    } else {
      ElMessage.error(result.message || '提交同步任务失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('提交同步任务失败: ' + error.message)
    }
  }
}

const viewSectorSecurities = (sectorName) => {
  router.push({
    name: 'SecurityList',
    query: { sector: sectorName }
  })
}

const handleFilterChange = () => {
  fetchSectors()
}

const refreshData = () => {
  fetchSectors()
}

const getCategoryTagType = (category) => {
  const typeMap = {
    '股票': 'success',
    '基金': 'primary',
    '债券': 'warning',
    '期货': 'danger',
    '期权': 'info',
    '指数': ''
  }
  return typeMap[category] || ''
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '--'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  fetchSectors()
})
</script>

<style scoped>
.sectors-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}
</style>

