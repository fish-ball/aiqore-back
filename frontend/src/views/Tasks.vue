<template>
  <div class="tasks-page">
    <div class="page-header">
      <h2>任务管理</h2>
      <div>
        <el-button type="primary" @click="refreshTasks" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="autoRefresh = !autoRefresh" :type="autoRefresh ? 'success' : 'default'">
          <el-icon><Timer /></el-icon>
          {{ autoRefresh ? '停止自动刷新' : '自动刷新' }}
        </el-button>
      </div>
    </div>

    <el-card style="margin-top: 20px">
      <el-table
        :data="tasks"
        style="width: 100%"
        v-loading="loading"
        border
        stripe
        :default-sort="{ prop: 'state', order: 'ascending' }"
      >
        <el-table-column prop="task_id" label="任务ID" width="280" show-overflow-tooltip />
        <el-table-column prop="display_name" label="任务名称" width="180">
          <template #default="scope">
            {{ scope.row.display_name || scope.row.name || '未知任务' }}
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120">
          <template #default="scope">
            <el-tag size="small">{{ scope.row.category || '其他' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="state" label="状态" width="100" sortable>
          <template #default="scope">
            <el-tag :type="getStateType(scope.row.state)">
              {{ getStateText(scope.row.state) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态描述" width="200" show-overflow-tooltip />
        <el-table-column prop="progress" label="进度" width="300" sortable>
          <template #default="scope">
            <div v-if="scope.row.state === 'PROGRESS'">
              <el-progress
                :percentage="scope.row.progress || 0"
                :status="scope.row.progress === 100 ? 'success' : undefined"
                :stroke-width="20"
              />
              <div style="margin-top: 5px; font-size: 12px; color: #909399">
                {{ scope.row.current || 0 }} / {{ scope.row.total || 0 }}
              </div>
            </div>
            <div v-else-if="scope.row.state === 'SUCCESS'">
              <el-progress
                :percentage="100"
                status="success"
                :stroke-width="20"
              />
            </div>
            <div v-else-if="scope.row.state === 'FAILURE'">
              <el-progress
                :percentage="0"
                status="exception"
                :stroke-width="20"
              />
            </div>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" min-width="200">
          <template #default="scope">
            <div v-if="scope.row.state === 'SUCCESS' && scope.row.result">
              <el-tag type="success" size="small">成功</el-tag>
              <div style="margin-top: 5px; font-size: 12px; color: #909399">
                <div v-if="scope.row.result.total !== undefined">
                  总计: {{ scope.row.result.total }}
                </div>
                <div v-if="scope.row.result.created !== undefined">
                  新增: {{ scope.row.result.created }}
                </div>
                <div v-if="scope.row.result.updated !== undefined">
                  更新: {{ scope.row.result.updated }}
                </div>
                <div v-if="scope.row.result.errors !== undefined && scope.row.result.errors > 0">
                  错误: {{ scope.row.result.errors }}
                </div>
              </div>
            </div>
            <div v-else-if="scope.row.state === 'FAILURE'">
              <el-tag type="danger" size="small">失败</el-tag>
              <div style="margin-top: 5px; font-size: 12px; color: #F56C6C">
                {{ scope.row.error || '未知错误' }}
              </div>
            </div>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              link
              size="small"
              @click="viewTaskDetail(scope.row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="tasks.length === 0 && !loading" style="text-align: center; padding: 40px; color: #909399">
        <el-icon :size="48"><DocumentDelete /></el-icon>
        <div style="margin-top: 10px">暂无任务</div>
      </div>
    </el-card>

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="任务详情"
      width="600px"
    >
      <div v-if="selectedTask" class="task-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="任务ID">
            {{ selectedTask.task_id }}
          </el-descriptions-item>
          <el-descriptions-item label="任务名称">
            {{ selectedTask.display_name || selectedTask.name || '未知任务' }}
          </el-descriptions-item>
          <el-descriptions-item label="分类">
            <el-tag size="small">{{ selectedTask.category || '其他' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStateType(selectedTask.state)">
              {{ getStateText(selectedTask.state) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态描述">
            {{ selectedTask.status || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="进度" v-if="selectedTask.state === 'PROGRESS'">
            <el-progress
              :percentage="selectedTask.progress || 0"
              :stroke-width="20"
            />
            <div style="margin-top: 5px">
              {{ selectedTask.current || 0 }} / {{ selectedTask.total || 0 }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="结果" v-if="selectedTask.state === 'SUCCESS' && selectedTask.result">
            <pre style="background: #f5f7fa; padding: 10px; border-radius: 4px; overflow-x: auto">{{ JSON.stringify(selectedTask.result, null, 2) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="错误信息" v-if="selectedTask.state === 'FAILURE'">
            <div style="color: #F56C6C">{{ selectedTask.error || '未知错误' }}</div>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { taskApi } from '../api/task'
import { ElMessage } from 'element-plus'
import { Refresh, Timer, DocumentDelete } from '@element-plus/icons-vue'

const loading = ref(false)
const autoRefresh = ref(false)
const tasks = ref([])
const detailDialogVisible = ref(false)
const selectedTask = ref(null)
let refreshTimer = null

const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await taskApi.getList()
    if (response && response.tasks) {
      tasks.value = response.tasks
    } else {
      tasks.value = []
    }
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const refreshTasks = () => {
  fetchTasks()
  ElMessage.success('已刷新')
}

const getStateType = (state) => {
  const typeMap = {
    'PENDING': 'info',
    'PROGRESS': 'warning',
    'SUCCESS': 'success',
    'FAILURE': 'danger'
  }
  return typeMap[state] || 'info'
}

const getStateText = (state) => {
  const textMap = {
    'PENDING': '等待中',
    'PROGRESS': '运行中',
    'SUCCESS': '已完成',
    'FAILURE': '失败'
  }
  return textMap[state] || state
}


const viewTaskDetail = (task) => {
  selectedTask.value = task
  detailDialogVisible.value = true
}

onMounted(() => {
  fetchTasks()
  
  // 自动刷新
  refreshTimer = setInterval(() => {
    if (autoRefresh.value) {
      fetchTasks()
    }
  }, 2000) // 每2秒刷新一次
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.tasks-page {
  padding: 0;
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

.task-detail {
  padding: 10px 0;
}
</style>

