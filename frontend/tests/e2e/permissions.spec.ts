import { expect, test } from '@playwright/test';
import { credentials, ensureSeedShipment, login, openFirstShipmentDetail, openTab } from './helpers';

test.beforeAll(async ({ request }) => {
  await ensureSeedShipment(request);
});

test('VIEW_ONLY cannot mutate records', async ({ page }) => {
  await login(page, credentials('VIEW_ONLY'));
  await page.goto('/shipments/new');
  await expect(page.getByRole('heading', { name: /not allowed/i })).toBeVisible();

  await openFirstShipmentDetail(page);
  await expect(page.getByRole('button', { name: /update status/i })).toHaveCount(0);

  await openTab(page, 'Containers');
  await expect(page.getByRole('button', { name: /add container/i })).toHaveCount(0);

  await openTab(page, 'Documents');
  await expect(page.getByRole('button', { name: /upload/i })).toHaveCount(0);

  await openTab(page, 'Workflow');
  await expect(page.getByText(/view-only role cannot transition workflow state/i)).toBeVisible();
  const transitionButtons = page.getByRole('button', { name: /transition/i });
  const count = await transitionButtons.count();
  for (let index = 0; index < count; index += 1) {
    await expect(transitionButtons.nth(index)).toBeDisabled();
  }
});
