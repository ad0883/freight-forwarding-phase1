import { test } from '@playwright/test';
import { credentials, ensureE2EUsers, login, logout, type RoleName } from './helpers';

test.beforeAll(async ({ request }) => {
  await ensureE2EUsers(request);
});

for (const role of ['ADMIN', 'STAFF', 'VIEW_ONLY'] as RoleName[]) {
  test(`login and logout as ${role}`, async ({ page }) => {
    const creds = credentials(role);
    await login(page, creds);
    await logout(page);
  });
}
