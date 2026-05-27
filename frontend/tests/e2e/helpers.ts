import { expect, type APIRequestContext, type Page } from '@playwright/test';

export type RoleName = 'ADMIN' | 'STAFF' | 'VIEW_ONLY';

export type Credentials = {
  role: RoleName;
  email: string;
  password: string;
};

export function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export function credentials(role: RoleName): Credentials {
  const prefix = role === 'VIEW_ONLY' ? 'VIEW' : role;
  return {
    role,
    email: requiredEnv(`E2E_${prefix}_EMAIL`),
    password: requiredEnv(`E2E_${prefix}_PASSWORD`),
  };
}

export function allCredentials(): Credentials[] {
  return [credentials('ADMIN'), credentials('STAFF'), credentials('VIEW_ONLY')];
}

export function frontendBaseURL(): string {
  return requiredEnv('E2E_BASE_URL');
}

export function apiBaseURL(): string {
  if (process.env.VITE_API_BASE_URL) return process.env.VITE_API_BASE_URL;
  const frontendURL = new URL(frontendBaseURL());
  if (frontendURL.hostname === 'localhost' || frontendURL.hostname === '127.0.0.1') {
    frontendURL.port = '8000';
    frontendURL.pathname = '/api';
    frontendURL.search = '';
    frontendURL.hash = '';
    return frontendURL.toString().replace(/\/$/, '');
  }
  return new URL('/api', frontendURL).toString().replace(/\/$/, '');
}

export async function apiLogin(request: APIRequestContext, creds: Credentials): Promise<string> {
  const body = new URLSearchParams();
  body.set('username', creds.email);
  body.set('password', creds.password);
  const response = await request.post(`${apiBaseURL()}/auth/login`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: body.toString(),
  });
  if (!response.ok()) {
    const detail = await response.text();
    throw new Error(`${creds.role} API login failed with HTTP ${response.status()}: ${detail}`);
  }
  const data = await response.json();
  return data.access_token;
}

export async function ensureUser(request: APIRequestContext, adminToken: string, user: Credentials) {
  if (user.role === 'ADMIN') return;
  const headers = { Authorization: `Bearer ${adminToken}` };
  const usersResponse = await request.get(`${apiBaseURL()}/users`, { headers });
  expect(usersResponse.ok(), 'Admin should list users during e2e setup').toBeTruthy();
  const users = await usersResponse.json();
  const existing = users.find((item: { email: string }) => item.email === user.email);
  if (!existing) {
    const createResponse = await request.post(`${apiBaseURL()}/users`, {
      headers,
      data: {
        name: `QA ${user.role}`,
        email: user.email,
        password: user.password,
        role: user.role,
        is_active: true,
      },
    });
    expect(createResponse.ok(), `Create ${user.role} user`).toBeTruthy();
    return;
  }
  const updateResponse = await request.patch(`${apiBaseURL()}/users/${existing.id}`, {
    headers,
    data: {
      name: existing.name || `QA ${user.role}`,
      role: user.role,
      is_active: true,
    },
  });
  expect(updateResponse.ok(), `Update ${user.role} user`).toBeTruthy();
  const resetResponse = await request.patch(`${apiBaseURL()}/users/${existing.id}/password-reset`, {
    headers,
    data: { new_password: user.password },
  });
  expect(resetResponse.ok(), `Reset ${user.role} password`).toBeTruthy();
}

export async function ensureE2EUsers(request: APIRequestContext) {
  const admin = credentials('ADMIN');
  const adminToken = await apiLogin(request, admin);
  await ensureUser(request, adminToken, credentials('STAFF'));
  await ensureUser(request, adminToken, credentials('VIEW_ONLY'));
  return adminToken;
}

export async function ensureSeedShipment(request: APIRequestContext) {
  const adminToken = await ensureE2EUsers(request);
  const headers = { Authorization: `Bearer ${adminToken}` };
  const existingResponse = await request.get(`${apiBaseURL()}/shipments`, {
    headers,
    params: { search: 'QA E2E Seed Shipment' },
  });
  expect(existingResponse.ok(), 'List shipments during e2e setup').toBeTruthy();
  const existing = await existingResponse.json();
  if (existing.length) return existing[0];

  const response = await request.post(`${apiBaseURL()}/shipments`, {
    headers,
    data: {
      type: 'export',
      shipping_line: 'QA Seed Line',
      vessel_name: 'QA Seed Vessel',
      voyage_no: `QA-SEED-${Date.now()}`,
      origin_port: 'INNSA',
      dest_port: 'USLAX',
      container_no: 'QASEED1234',
      container_type: '40HC',
      booking_ref: `QA-SEED-${Date.now()}`,
      commodity: 'QA E2E Seed Shipment',
    },
  });
  expect(response.ok(), 'Create seed shipment during e2e setup').toBeTruthy();
  return response.json();
}

export async function login(page: Page, creds: Credentials) {
  await page.goto('/login');
  await page.getByLabel(/email address/i).fill(creds.email);
  await page.getByLabel(/password/i).fill(creds.password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  await expect(page.getByText(creds.role, { exact: true }).first()).toBeVisible();
}

export async function logout(page: Page) {
  await page.getByRole('button', { name: /logout/i }).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
}

export async function openShipments(page: Page) {
  await page.getByRole('link', { name: 'Shipments', exact: true }).click();
  await expect(page.getByRole('heading', { name: /shipment list/i })).toBeVisible();
}

export async function openFirstShipmentDetail(page: Page) {
  await openShipments(page);
  const firstShipmentCell = page.locator('tbody tr').first().locator('td').first();
  await expect(firstShipmentCell).toBeVisible();
  const shipmentCode = (await firstShipmentCell.innerText()).trim();
  await page.locator('tbody tr').first().click();
  await expect(page.getByRole('heading', { name: shipmentCode })).toBeVisible();
  return shipmentCode;
}

export async function openTab(page: Page, name: string | RegExp) {
  await page.getByRole('button', { name }).click();
  await expect(page.getByRole('button', { name })).toHaveClass(/active/);
}
