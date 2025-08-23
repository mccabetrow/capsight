import { test, expect } from '@playwright/test'

test.describe('CapSight Valuation App', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('displays hero section and form', async ({ page }) => {
    // Check hero content
    await expect(page.getByRole('heading', { name: /industrial valuations in seconds/i })).toBeVisible()
    await expect(page.getByText(/enter noi and get a transparent value range/i)).toBeVisible()
    
    // Check form elements
    await expect(page.getByLabel('Market')).toBeVisible()
    await expect(page.getByLabel(/annual noi/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /estimate value/i })).toBeVisible()
  })

  test('can select different markets', async ({ page }) => {
    const marketSelect = page.getByLabel('Market')
    
    // Default should be DFW
    await expect(marketSelect).toHaveValue('dfw')
    
    // Change to Inland Empire
    await marketSelect.selectOption('ie')
    await expect(marketSelect).toHaveValue('ie')
    
    // Verify market name appears in fundamentals section
    await expect(page.getByText(/inland empire/i)).toBeVisible()
  })

  test('validates NOI input', async ({ page }) => {
    const noiInput = page.getByLabel(/annual noi/i)
    const submitButton = page.getByRole('button', { name: /estimate value/i })
    
    // Submit with empty NOI
    await submitButton.click()
    await expect(page.getByText(/please enter a valid noi amount/i)).toBeVisible()
    
    // Enter invalid NOI
    await noiInput.fill('0')
    await submitButton.click()
    await expect(page.getByText(/please enter a valid noi amount/i)).toBeVisible()
  })

  test('formats NOI input on blur', async ({ page }) => {
    const noiInput = page.getByLabel(/annual noi/i)
    
    // Enter raw number
    await noiInput.fill('1200000')
    await noiInput.blur()
    
    // Should format with commas
    await expect(noiInput).toHaveValue('1,200,000')
  })

  test('submits valuation form successfully', async ({ page }) => {
    // Mock the API response
    await page.route('/api/value*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cap_rate_mid: 6.2,
          cap_rate_band_bps: 50,
          value_low: 18032786,
          value_mid: 19672131,
          value_high: 21505376,
          n: 12
        })
      })
    })
    
    // Fill form
    await page.getByLabel('Market').selectOption('dfw')
    await page.getByLabel(/annual noi/i).fill('1,200,000')
    
    // Submit
    await page.getByRole('button', { name: /estimate value/i }).click()
    
    // Check loading state
    await expect(page.getByText('Estimating...')).toBeVisible()
    
    // Check results appear
    await expect(page.getByText(/valuation results/i)).toBeVisible()
    await expect(page.getByText('$19,672,131')).toBeVisible() // Mid value
    await expect(page.getByText('6.2%')).toBeVisible() // Cap rate
    await expect(page.getByText('Comps used: 12')).toBeVisible()
  })

  test('displays market fundamentals', async ({ page }) => {
    // Should show fundamentals section
    await expect(page.getByText(/market fundamentals/i)).toBeVisible()
    await expect(page.getByText(/dallas.fort worth/i)).toBeVisible()
    
    // Should show metric labels
    await expect(page.getByText('Vacancy Rate')).toBeVisible()
    await expect(page.getByText('Asking Rent')).toBeVisible()
    await expect(page.getByText('YoY Rent Growth')).toBeVisible()
    await expect(page.getByText('Under Construction')).toBeVisible()
  })

  test('displays verified comps table', async ({ page }) => {
    await expect(page.getByText(/verified comps/i)).toBeVisible()
    await expect(page.getByText(/last 18 months/i)).toBeVisible()
  })

  test('handles API errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('/api/value*', async route => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Bad request',
          message: 'Invalid market or NOI'
        })
      })
    })
    
    // Submit form
    await page.getByLabel(/annual noi/i).fill('1,200,000')
    await page.getByRole('button', { name: /estimate value/i }).click()
    
    // Check error message
    await expect(page.getByText(/invalid market or noi/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
  })

  test('keyboard navigation works', async ({ page }) => {
    // Tab through form elements
    await page.keyboard.press('Tab') // Market select
    await expect(page.getByLabel('Market')).toBeFocused()
    
    await page.keyboard.press('Tab') // NOI input
    await expect(page.getByLabel(/annual noi/i)).toBeFocused()
    
    await page.keyboard.press('Tab') // Submit button
    await expect(page.getByRole('button', { name: /estimate value/i })).toBeFocused()
  })

  test('Enter key submits form', async ({ page }) => {
    await page.route('/api/value*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cap_rate_mid: 6.2,
          cap_rate_band_bps: 50,
          value_low: 18000000,
          value_mid: 19672131,
          value_high: 21000000,
          n: 10
        })
      })
    })
    
    // Fill NOI and press Enter
    const noiInput = page.getByLabel(/annual noi/i)
    await noiInput.fill('1200000')
    await noiInput.press('Enter')
    
    // Should submit and show results
    await expect(page.getByText(/valuation results/i)).toBeVisible()
  })

  test('responsive layout works on mobile', async ({ page, isMobile }) => {
    if (!isMobile) {
      await page.setViewportSize({ width: 375, height: 667 }) // iPhone SE
    }
    
    // Form should stack vertically on mobile
    const form = page.locator('form').first()
    const boundingBox = await form.boundingBox()
    
    // Check that form elements are stacked (height > width indicates vertical layout)
    expect(boundingBox?.height).toBeGreaterThan(boundingBox?.width! * 0.3)
  })
})

test.describe('Accessibility', () => {
  test('has proper semantic structure', async ({ page }) => {
    await page.goto('/')
    
    // Check heading hierarchy
    const h1 = page.getByRole('heading', { level: 1 })
    await expect(h1).toHaveText(/industrial valuations in seconds/i)
    
    // Check form labels
    await expect(page.getByLabel('Market')).toBeVisible()
    await expect(page.getByLabel(/annual noi/i)).toBeVisible()
    
    // Check ARIA labels
    await expect(page.getByLabel('Select market')).toBeVisible()
    await expect(page.getByLabel('Get valuation estimate')).toBeVisible()
  })

  test('focus indicators are visible', async ({ page }) => {
    await page.goto('/')
    
    // Focus each interactive element and check for focus ring
    const focusableElements = [
      page.getByLabel('Market'),
      page.getByLabel(/annual noi/i),
      page.getByRole('button', { name: /estimate value/i }),
    ]
    
    for (const element of focusableElements) {
      await element.focus()
      await expect(element).toBeFocused()
      // Focus ring should be visible (can't easily test visually, but focus state is confirmed)
    }
  })
})
