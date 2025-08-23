import { test, expect } from '@playwright/test';

test('homepage loads correctly', async ({ page }) => {
  await page.goto('/');
  
  // Check page title
  await expect(page).toHaveTitle(/CapSight/);
  
  // Check main heading
  await expect(page.getByRole('heading', { name: /CapSight/ })).toBeVisible();
  
  // Check market selector is present
  await expect(page.getByLabel(/Select Market/)).toBeVisible();
  
  // Check NOI input is present
  await expect(page.getByLabel(/Annual NOI/)).toBeVisible();
});

test('market selection and valuation flow', async ({ page }) => {
  await page.goto('/');
  
  // Select DFW market
  await page.getByLabel(/Select Market/).selectOption('dfw');
  
  // Enter NOI amount
  await page.getByLabel(/Annual NOI/).fill('1500000');
  
  // Wait for valuation to appear
  await expect(page.getByText(/Estimated Value/)).toBeVisible({ timeout: 10000 });
  
  // Check that confidence interval is shown
  await expect(page.getByText(/Confidence Interval/)).toBeVisible();
  
  // Check that fundamentals section is visible
  await expect(page.getByText(/Market Fundamentals/)).toBeVisible();
  
  // Check that comparable sales section is visible
  await expect(page.getByText(/Recent Comparable Sales/)).toBeVisible();
});

test('error handling for network failures', async ({ page }) => {
  // Block network requests to simulate offline
  await page.route('**/rest/v1/**', route => route.abort());
  
  await page.goto('/');
  
  // Try to select market and enter NOI
  await page.getByLabel(/Select Market/).selectOption('dfw');
  await page.getByLabel(/Annual NOI/).fill('1500000');
  
  // Should show error message
  await expect(page.getByText(/Error loading/)).toBeVisible({ timeout: 5000 });
});

test('accessibility check', async ({ page }) => {
  await page.goto('/');
  
  // Check keyboard navigation
  await page.keyboard.press('Tab');
  await expect(page.getByLabel(/Select Market/)).toBeFocused();
  
  await page.keyboard.press('Tab');
  await expect(page.getByLabel(/Annual NOI/)).toBeFocused();
  
  // Check ARIA labels are present
  await expect(page.getByLabel(/Select Market/)).toHaveAttribute('aria-label');
  await expect(page.getByLabel(/Annual NOI/)).toHaveAttribute('aria-label');
});
