<template>
  <EmptyView :title="title" :subtitle="subtitle">
    <template #actions v-if="$table">
      <template v-if="!finalOptions.embedListActions">
        <div class="list-view-toolbar-row">
          <div
            v-if="$slots['toolbar-actions'] || $slots.toolbarActions"
            class="list-view-toolbar-custom"
          >
            <slot name="toolbar-actions" :table="$table" :page="page" :page-size="pageSize" />
          </div>
          <ActionButtonGroup
            v-if="batchActions.length"
            :actions="batchActions"
            :args="[selectedItems, { options: props, $table }]"
          ></ActionButtonGroup>
          <ActionButtonGroup
            v-if="listActions.length || defaultActions.length"
            :actions="[...listActions, ...defaultActions]"
            :args="[{ options: props, $table }]"
          ></ActionButtonGroup>
        </div>
      </template>
    </template>
    <slot name="before" :table="$table" :page="page" :page-size="pageSize" />
    <ListViewTable
      ref="$table"
      v-model:page="page"
      v-model:page-size="pageSize"
      @loaded="$emit('loaded', $event)"
      @queryUpdated="queryUpdated"
      v-bind="props"
    >
      <template v-for="name in forwardedSlotNames" :key="name" #[name]="slotData">
        <slot :name="name" v-bind="slotData" />
      </template>
    </ListViewTable>
    <slot name="after" :table="$table" :page="page" :page-size="pageSize" />
  </EmptyView>
</template>

<script setup lang="ts">
/**
 * 与 @iottest/vue-core 的 ListView 行为一致，但不调用 router.replace 同步分页与筛选。
 * 原版在 watch(page,pageSize) 与 queryUpdated 中写回 URL，在嵌套路由 + Transition（out-in）下
 * 易与后续导航冲突，表现为离开页面后子路由区域白屏且无控制台报错。
 *
 * 不使用 generic="T"：与 vue-core 的 ListView 一致，且避免泛型 SFC 在 HMR/模板编译下偶发丢失绑定。
 */
import { ref, reactive, watchEffect, computed, useSlots } from 'vue'
import EmptyView from '@iottest/vue-core/src/libs/data-view/components/EmptyView.vue'
import ListViewTable from '@iottest/vue-core/src/libs/data-view/components/ListViewTable.vue'
import {
  getDefaultModelListOptions,
  type ListViewData,
  type ModelListOptions,
  type TableListAction,
  type ModelListViewOptions,
} from '@iottest/vue-core/src/libs/data-view/types/view'
import { finalize, isFinal } from '@iottest/vue-core/src/libs/data-view/utils'
import ActionButtonGroup from '@iottest/vue-core/src/libs/data-view/components/ActionButtonGroup.vue'
import type { ListViewQuery } from '@iottest/vue-core/src/libs/data-view/types/fields'
import { useRouter } from 'vue-router'

const router = useRouter()
const slots = useSlots()

/** 仅转发表格列插槽；顶栏 toolbar-actions / before / after 不得进入表格，否则会污染 GenericTable */
const TABLE_SLOT_EXCLUDE = new Set(['before', 'after', 'toolbar-actions', 'toolbarActions'])

const $table = ref()
const page = ref<number>(1)
const pageSize = ref<number>(10)

const props = withDefaults(defineProps<ModelListViewOptions<unknown>>(), {
  pk: 'id',
  options: () => ({}),
  initQuery: () => ({}),
  filters: () => ({}),
  listActions: () => [],
  batchActions: () => [],
  elTableProps: () => ({}),
})

const finalOptions = reactive<ModelListOptions>(getDefaultModelListOptions())

Object.entries(props.options).map(([key, value]) => {
  if (!(key in finalOptions)) return
  if (isFinal(value)) return (finalOptions[key as keyof ModelListOptions] = value as never)
  watchEffect(async () => {
    finalOptions[key as keyof ModelListOptions] = (await finalize(value as never, {
      props,
      $table: $table.value,
    })) as never
  })
})

const defaultActions = reactive<TableListAction<unknown>[]>([
  {
    label: '创建',
    display: () => finalOptions.canCreate ?? true,
    buttonType: 'success',
    action: async () => $table.value?.applyCreate(),
  },
  {
    label: '刷新',
    action: async () => $table.value?.reload(),
  },
  {
    label: '关闭',
    display: () => finalOptions.canClose,
    action: () => {
      router.back()
    },
  },
])

const selectedItems = computed<unknown[]>(() => [])

/** 需转发给 ListViewTable 的插槽名（computed 放在 defineProps 之后，避免泛型 SFC 模板绑定丢失） */
const forwardedSlotNames = computed(() =>
  Object.keys(slots).filter((n) => !TABLE_SLOT_EXCLUDE.has(n)),
)

const emit = defineEmits<{
  loaded: [data: ListViewData]
  queryUpdated: [data: ListViewQuery]
}>()

const queryUpdated = (queryChange: ListViewQuery) => {
  emit('queryUpdated', queryChange)
}

defineExpose({
  reload: () => $table.value?.reload(),
  doQuery: (query: ListViewQuery) => $table.value?.doQuery(query),
  get listViewQuery(): ListViewQuery {
    return ($table.value?.listViewQuery ?? {}) as ListViewQuery
  },
  triggerEdit: (item: unknown) => $table.value?.triggerEdit(item),
  triggerDelete: (item: unknown) => $table.value?.triggerDelete(item),
})
</script>

<style scoped lang="scss">
.list-view-toolbar-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.list-view-toolbar-custom {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.title {
  display: inline-block;
  font-size: 16px;
  font-weight: bold;
  margin-right: 15px;
}

.subtitle {
  display: inline-block;
  color: var(--text-color-lighter);
}

.actions {
  float: right;
  margin: -20px 0;
  padding: 13px 0;
}
</style>
