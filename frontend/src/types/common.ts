// 通用类型定义（分页等）

export interface Pagination {
  page: number
  pageSize: number
  total: number
}

export interface ListResponse<T> {
  items: T[]
  total: number
}

