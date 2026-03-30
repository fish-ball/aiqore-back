// 板块相关类型定义

export interface Sector {
  name: string
  display_name?: string
  category?: string
  security_count?: number
}

export type SectorCategoryGrouped = Record<string, Sector[]>

