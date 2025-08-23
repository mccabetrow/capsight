// Currency formatting
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

// Percentage formatting
export function formatPercent(value: number, decimals: number = 1): string {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100)
}

// Date formatting
export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

// Number formatting with thousand separators
export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

// Square footage formatting
export function formatSquareFeet(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M SF`
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(0)}K SF`
  }
  return `${value.toLocaleString()} SF`
}

// Clean and parse NOI input
export function parseNoiInput(input: string): number {
  // Remove all non-digit characters except decimal point
  const cleaned = input.replace(/[^\d.]/g, '')
  return parseFloat(cleaned) || 0
}

// Format NOI input with thousand separators
export function formatNoiInput(value: string): string {
  const numericValue = parseNoiInput(value)
  if (numericValue === 0) return ''
  return numericValue.toLocaleString('en-US')
}

// Class name utility
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}
