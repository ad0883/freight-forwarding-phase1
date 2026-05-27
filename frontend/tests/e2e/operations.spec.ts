import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  E2E_UI_TIMEOUT,
  credentials,
  ensureSeedShipment,
  login,
  openFirstShipmentDetail,
  openShipments,
  openTab,
} from './helpers';

test.beforeAll(async ({ request }) => {
  await ensureSeedShipment(request);
});

test.beforeEach(async ({ page }) => {
  await login(page, credentials('ADMIN'));
});

test('dashboard loads', async ({ page }) => {
  await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  await expect(page.getByText(/live shipments/i)).toBeVisible();
});

test('shipments list and detail load', async ({ page }) => {
  await openFirstShipmentDetail(page);
  await expect(page.getByText(/shipment code/i)).toBeVisible();
});

test('shipment tabs open when present', async ({ page }) => {
  await openFirstShipmentDetail(page);
  for (const tabName of ['Overview', 'Workflow', 'Containers', 'Documents', 'Finance']) {
    const tab = page.getByRole('button', { name: tabName });
    if (await tab.count()) {
      await tab.click();
      await expect(tab).toHaveClass(/active/);
    }
  }
});

test('create QA shipment', async ({ page }) => {
  test.setTimeout(90_000);
  await openShipments(page);
  await page.getByRole('link', { name: /create/i }).click();
  await expect(page.getByRole('heading', { name: /create shipment/i })).toBeVisible();
  const stamp = Date.now();
  await page.getByLabel(/shipping line/i).fill(`QA Line ${stamp}`);
  await page.getByLabel(/vessel name/i).fill(`QA Vessel ${stamp}`);
  await page.getByLabel(/voyage no/i).fill(`QA-${stamp}`);
  await page.getByLabel(/origin port/i).fill('INNSA');
  await page.getByLabel(/destination port/i).fill('USLAX');
  await page.getByLabel(/container no/i).fill(`QA${String(stamp).slice(-7)}`);
  await page.getByLabel(/booking ref/i).fill(`QA-BOOK-${stamp}`);
  await page.getByLabel(/commodity/i).fill(`QA shipment created by Playwright ${stamp}`);
  const createResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/shipments') && response.request().method() === 'POST',
    { timeout: E2E_UI_TIMEOUT }
  );
  await page.getByRole('button', { name: /create shipment/i }).click();
  const createResponse = await createResponsePromise;
  expect(createResponse.ok(), `Create shipment returned HTTP ${createResponse.status()}`).toBeTruthy();
  const createdShipment = await createResponse.json();
  await expect(page.getByRole('heading', { name: createdShipment.shipment_code })).toBeVisible({ timeout: E2E_UI_TIMEOUT });
  await expect(page.getByText(`QA Line ${stamp}`)).toBeVisible({ timeout: E2E_UI_TIMEOUT });
});

test('workflow tab shows available transitions', async ({ page }) => {
  test.setTimeout(90_000);
  await openFirstShipmentDetail(page);
  await openTab(page, 'Workflow');
  await expect(page.getByRole('heading', { name: /workflow state/i })).toBeVisible({ timeout: E2E_UI_TIMEOUT });
  await expect(page.getByText('Loading workflow data...')).toHaveCount(0, { timeout: E2E_UI_TIMEOUT });
  await expect(page.getByText(/available next transitions/i)).toBeVisible({ timeout: E2E_UI_TIMEOUT });
  await expect(page.locator('.workflow-transition-card').or(page.getByText(/no transitions available/i))).toBeVisible({ timeout: E2E_UI_TIMEOUT });
});

test('containers tab creates QA container', async ({ page }) => {
  test.setTimeout(90_000);
  await openFirstShipmentDetail(page);
  await openTab(page, 'Containers');
  const stamp = Date.now().toString().slice(-7);
  const containerNumber = `QAAB${stamp}`;
  await page.getByRole('button', { name: /add container/i }).click();
  await page.getByLabel(/container number/i).fill(containerNumber);
  await page.getByLabel(/^size$/i).fill('40');
  await page.getByLabel(/^type$/i).fill('40HC');
  const containerResponsePromise = page.waitForResponse(
    (response) =>
      /\/api\/shipments\/\d+\/containers$/.test(response.url()) && response.request().method() === 'POST',
    { timeout: E2E_UI_TIMEOUT }
  );
  await page.getByRole('button', { name: /^add$/i }).click();
  const containerResponse = await containerResponsePromise;
  expect(containerResponse.ok(), `Create container returned HTTP ${containerResponse.status()}`).toBeTruthy();
  await expect(page.getByText(/container added/i)).toBeVisible({ timeout: E2E_UI_TIMEOUT });
  await expect(page.getByText(containerNumber)).toBeVisible({ timeout: E2E_UI_TIMEOUT });
});

test('documents tab uploads TXT document and runs intelligence', async ({ page }) => {
  test.setTimeout(180_000);
  await openFirstShipmentDetail(page);
  await openTab(page, 'Documents');
  await expect(page.getByRole('heading', { name: /documents/i })).toBeVisible();

  const uploadButton = page.getByRole('button', { name: /upload/i }).first();
  await expect(uploadButton).toBeVisible();
  await uploadButton.click();

  const filePath = path.join(os.tmpdir(), `qa-document-${Date.now()}.txt`);
  fs.writeFileSync(
    filePath,
    'QA booking document\nBooking Ref: QA-E2E\nContainer: QAAB1234567\nVessel: QA Vessel\n'
  );
  await page.locator('input[type="file"]').setInputFiles(filePath);
  await page.getByLabel(/version label/i).fill('QA TXT');
  await page.getByLabel(/notes/i).fill('Uploaded by Playwright e2e');
  const uploadResponsePromise = page.waitForResponse(
    (response) =>
      /\/api\/shipments\/\d+\/document-versions\/upload$/.test(response.url())
      && response.request().method() === 'POST',
    { timeout: 65_000 }
  );
  await page.getByRole('button', { name: /upload version/i }).click();
  const uploadResponse = await uploadResponsePromise;
  expect(uploadResponse.ok(), `Upload document version returned HTTP ${uploadResponse.status()}`).toBeTruthy();
  await expect(page.locator('.success-text').filter({ hasText: /Document version uploaded|Document upload completed/i })).toBeVisible({ timeout: E2E_UI_TIMEOUT });

  const runButton = page.getByRole('button', { name: /run intelligence/i }).first();
  await expect(runButton).toBeVisible({ timeout: E2E_UI_TIMEOUT });
  const runResponsePromise = page.waitForResponse(
    (response) =>
      /\/api\/document-intelligence\/versions\/\d+\/run$/.test(response.url())
      && response.request().method() === 'POST',
    { timeout: 95_000 }
  );
  await runButton.click();
  const runResponse = await runResponsePromise;
  expect(runResponse.ok(), `Run document intelligence returned HTTP ${runResponse.status()}`).toBeTruthy();
  const intelligencePanel = page.locator('.document-intelligence-panel');
  await expect(intelligencePanel).toBeVisible({ timeout: E2E_UI_TIMEOUT });
  await expect(page.getByText('Loading document intelligence...')).toHaveCount(0, { timeout: 20_000 });
  await expect(intelligencePanel).toContainText(/OCR|Detected Type|No fields extracted|No mismatches found/i);
});

test('finance page opens when Phase 14 exists', async ({ page }) => {
  const financeLink = page.getByRole('link', { name: /^finance$/i });
  if (!(await financeLink.count())) test.skip(true, 'Finance navigation is not present in this build');
  await financeLink.click();
  await expect(page.getByRole('heading', { name: /finance/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /overview/i })).toBeVisible();
});
