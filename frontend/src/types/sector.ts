// 板块相关类型定义（与 GET /api/sector/list 返回的 sector_to_public_dict 一致）

export interface Sector {
  id: number
  name: string
  /** 数据源侧板块键，与 instrument 列表筛选参数 sector 一致 */
  alias: string
  source: string
  /** AssetClass.value */
  asset_class: string
  /** InstrumentType.value */
  instrument_type: string
  parent_id?: number | null
  remark?: string | null
  created_at?: string | null
  updated_at?: string | null
  /** 子节点摘要（详情接口） */
  children?: Sector[]
}

export type SectorCategoryGrouped = Record<string, Sector[]>
