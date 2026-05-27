import { expect, test } from '@playwright/test';
import { credentials, ensureSeedShipment, login } from './helpers';

test.beforeAll(async ({ request }) => {
  await ensureSeedShipment(request);
});

test('mobile viewport sidebar opens and navigates', async ({ page }) => {
  await login(page, credentials('ADMIN'));
  const menuButton = page.getByRole('button', { name: /open menu/i });
  await expect(menuButton).toBeVisible();
  await menuButton.click();
  await expect(page.locator('.sidebar.open')).toBeVisible();
  await page.getByRole('link', { name: 'Shipments', exact: true }).click();
  await expect(page.getByRole('heading', { name: /shipment list/i })).toBeVisible();
  await expect(page.locator('.sidebar.open')).toHaveCount(0);
});
