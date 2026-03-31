export function formatMoneyValue(value: unknown): string {
  return `¥${Number.parseFloat(String(value ?? 0)).toFixed(2)}`
}

export function formatPercentValue(value: unknown): string {
  const num = Number.parseFloat(String(value ?? 0))
  return `${(num * 100).toFixed(2)}%`
}
