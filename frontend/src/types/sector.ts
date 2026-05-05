// 板块相关类型定义（与 /api/sector/list 扁平字段一致）

export interface Sector {
  id: number
  /** 显示名称 */
  name: string
  /** 唯一别名，与数据源板块键一致（如 QMT），用于筛选与同步接口 */
  alias: string
  parent_id?: number | null
  metadata?: Record<string, unknown> | null
  /** 以下字段来自 metadata.stats，便于表格展示 */
  category?: string | null
  market?: string | null
  security_count?: number
  is_active?: number
  last_sync_at?: string | null
  /** 用户备注（仅本地维护，不参与 QMT 同步） */
  remark?: string | null
}

export type SectorCategoryGrouped = Record<string, Sector[]>
