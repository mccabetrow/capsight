import { formatCurrency, formatPercent, formatDate, parseNoiInput, formatNoiInput } from '@/lib/format'

describe('Format utilities', () => {
  describe('formatCurrency', () => {
    it('formats currency without decimals', () => {
      expect(formatCurrency(1234567)).toBe('$1,234,567')
      expect(formatCurrency(0)).toBe('$0')
      expect(formatCurrency(123.89)).toBe('$124')
    })
  })

  describe('formatPercent', () => {
    it('formats percentage with 1 decimal by default', () => {
      expect(formatPercent(6.2)).toBe('6.2%')
      expect(formatPercent(0)).toBe('0.0%')
      expect(formatPercent(12.345)).toBe('12.3%')
    })

    it('formats percentage with custom decimals', () => {
      expect(formatPercent(6.2, 0)).toBe('6%')
      expect(formatPercent(6.25, 2)).toBe('6.25%')
    })
  })

  describe('formatDate', () => {
    it('formats date in US format', () => {
      expect(formatDate('2024-03-15')).toBe('Mar 15, 2024')
      expect(formatDate('2023-12-01')).toBe('Dec 1, 2023')
    })
  })

  describe('parseNoiInput', () => {
    it('parses numeric strings', () => {
      expect(parseNoiInput('1234567')).toBe(1234567)
      expect(parseNoiInput('1,234,567')).toBe(1234567)
      expect(parseNoiInput('$1,234,567')).toBe(1234567)
      expect(parseNoiInput('1.5')).toBe(1.5)
    })

    it('handles invalid input', () => {
      expect(parseNoiInput('')).toBe(0)
      expect(parseNoiInput('abc')).toBe(0)
      expect(parseNoiInput('$')).toBe(0)
    })
  })

  describe('formatNoiInput', () => {
    it('formats with thousand separators', () => {
      expect(formatNoiInput('1234567')).toBe('1,234,567')
      expect(formatNoiInput('1000')).toBe('1,000')
      expect(formatNoiInput('500')).toBe('500')
    })

    it('handles empty input', () => {
      expect(formatNoiInput('')).toBe('')
      expect(formatNoiInput('0')).toBe('')
    })
  })
})
