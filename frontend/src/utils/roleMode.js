/* ============================================================
   S2 — Role-Based Product Experience — Centralized Config
   ============================================================
   Maps user roles to product modes and provides mode-aware
   navigation, quick actions, and Today widget configuration.
   
   Current roles: ADMIN, STAFF, VIEW_ONLY
   Future roles will auto-map: FINANCE→finance, MANAGER→management
   ============================================================ */

import {
  Activity, AlertTriangle, BarChart3, Bot, ClipboardList, CreditCard,
  FileCheck, FileClock, FileText, LayoutDashboard, Mail, Satellite,
  Settings, ShieldAlert, ShieldCheck, Ship, Sun, Truck, Users, UserCog, Bell,
} from 'lucide-react';

/* --- Role → Mode Mapping --- */

const ROLE_MODE_MAP = {
  ADMIN: 'admin',
  STAFF: 'operations',
  VIEW_ONLY: 'readonly',
  // Future roles
  FINANCE: 'finance',
  FINANCE_HEAD: 'finance',
  MANAGER: 'management',
  ORG_MANAGER: 'management',
  HOD: 'management',
  OPERATIONS_HEAD: 'operations',
  CUSTOMS_COORDINATOR: 'operations',
  TRANSPORT_COORDINATOR: 'operations',
  ORG_ADMIN: 'admin',
};

export function getRoleMode(role) {
  return ROLE_MODE_MAP[role] || 'operations';
}

export function getModeLabel(mode) {
  const labels = {
    operations: 'Operations',
    finance: 'Finance',
    management: 'Management',
    admin: 'Admin',
    readonly: 'Read-Only',
  };
  return labels[mode] || 'Operations';
}

export function getModeColor(mode) {
  const colors = {
    operations: '#2563eb',
    finance: '#059669',
    management: '#7c3aed',
    admin: '#dc2626',
    readonly: '#64748b',
  };
  return colors[mode] || '#2563eb';
}

/* --- Navigation Config Per Mode --- */

export function getNavigationGroups(mode) {
  switch (mode) {
    case 'operations':
      return [
        { label: 'Daily Work', links: [
          { to: '/today', label: 'Today', icon: Sun },
          { to: '/shipments', label: 'Shipments', icon: Ship },
          { to: '/validation-issues', label: 'Documents', icon: FileText },
          { to: '/manual-review', label: 'Issues', icon: AlertTriangle },
        ]},
        { label: 'Operations', links: [
          { to: '/customs', label: 'Customs', icon: ShieldCheck },
          { to: '/transport', label: 'Transport', icon: Truck },
          { to: '/approvals', label: 'Approvals', icon: FileCheck },
        ]},
        { label: 'Tools', links: [
          { to: '/ai', label: 'AI Assistant', icon: Bot },
          { to: '/control-tower', label: 'Management Dashboard', icon: Activity },
          { to: '/predictive', label: 'Risk Alerts', icon: BarChart3 },
          { to: '/tasks', label: 'Tasks', icon: ClipboardList },
          { to: '/finance', label: 'Finance', icon: CreditCard },
          { to: '/reports', label: 'Reports', icon: BarChart3 },
        ]},
      ];

    case 'finance':
      return [
        { label: 'Daily Work', links: [
          { to: '/today', label: 'Today', icon: Sun },
          { to: '/finance', label: 'Finance', icon: CreditCard },
          { to: '/shipments', label: 'Shipments', icon: Ship },
          { to: '/approvals', label: 'Approvals', icon: FileCheck },
        ]},
        { label: 'Reports', links: [
          { to: '/control-tower', label: 'Management Dashboard', icon: Activity },
          { to: '/reports', label: 'Reports', icon: BarChart3 },
          { to: '/ai', label: 'AI Assistant', icon: Bot },
        ]},
        { label: 'More', links: [
          { to: '/validation-issues', label: 'Documents', icon: FileText },
          { to: '/manual-review', label: 'Issues', icon: AlertTriangle },
        ]},
      ];

    case 'management':
      return [
        { label: 'Daily Work', links: [
          { to: '/today', label: 'Today', icon: Sun },
          { to: '/control-tower', label: 'Management Dashboard', icon: Activity },
          { to: '/approvals', label: 'Approvals', icon: FileCheck },
          { to: '/predictive', label: 'Risk Alerts', icon: BarChart3 },
        ]},
        { label: 'Operations', links: [
          { to: '/shipments', label: 'Shipments', icon: Ship },
          { to: '/manual-review', label: 'Issues', icon: AlertTriangle },
          { to: '/finance', label: 'Finance', icon: CreditCard },
          { to: '/ai', label: 'AI Assistant', icon: Bot },
        ]},
        { label: 'More', links: [
          { to: '/reports', label: 'Reports', icon: BarChart3 },
          { to: '/tasks', label: 'Tasks', icon: ClipboardList },
        ]},
      ];

    case 'admin':
      return [
        { label: 'Daily Work', links: [
          { to: '/today', label: 'Today', icon: Sun },
          { to: '/shipments', label: 'Shipments', icon: Ship },
          { to: '/validation-issues', label: 'Documents', icon: FileText },
          { to: '/manual-review', label: 'Issues', icon: AlertTriangle },
        ]},
        { label: 'Operations', links: [
          { to: '/finance', label: 'Finance', icon: CreditCard },
          { to: '/customs', label: 'Customs', icon: ShieldCheck },
          { to: '/transport', label: 'Transport', icon: Truck },
          { to: '/tracking', label: 'Tracking', icon: Satellite },
          { to: '/approvals', label: 'Approvals', icon: FileCheck },
        ]},
        { label: 'Management', links: [
          { to: '/control-tower', label: 'Management Dashboard', icon: Activity },
          { to: '/predictive', label: 'Risk Alerts', icon: BarChart3 },
          { to: '/ai', label: 'AI Assistant', icon: Bot },
        ]},
        { label: 'More', links: [
          { to: '/tasks', label: 'Tasks', icon: ClipboardList },
          { to: '/parties', label: 'Parties', icon: Users },
          { to: '/reports', label: 'Reports', icon: BarChart3 },
          { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
          { to: '/notifications', label: 'Notifications', icon: Bell },
          { to: '/email', label: 'Email Automation', icon: Mail },
        ]},
        { label: 'Admin / Advanced', links: [
          { to: '/enterprise', label: 'Admin Settings', icon: ShieldCheck },
          { to: '/bot-governance', label: 'AI Control', icon: Bot },
          { to: '/users', label: 'Users', icon: UserCog },
          { to: '/audit-logs', label: 'Audit Logs', icon: FileClock },
          { to: '/settings', label: 'Settings', icon: Settings },
          { to: '/admin/tools', label: 'Admin Tools', icon: ShieldCheck },
          { to: '/events', label: 'Events', icon: ClipboardList },
          { to: '/rules', label: 'Rules', icon: ShieldAlert },
          { to: '/status', label: 'System Status', icon: Activity },
        ]},
      ];

    case 'readonly':
      return [
        { label: 'Overview', links: [
          { to: '/today', label: 'Today', icon: Sun },
          { to: '/shipments', label: 'Shipments', icon: Ship },
        ]},
        { label: 'Management', links: [
          { to: '/control-tower', label: 'Management Dashboard', icon: Activity },
          { to: '/predictive', label: 'Risk Alerts', icon: BarChart3 },
          { to: '/reports', label: 'Reports', icon: BarChart3 },
          { to: '/ai', label: 'AI Assistant', icon: Bot },
        ]},
      ];

    default:
      return getNavigationGroups('operations');
  }
}

/* --- Quick Actions Per Mode --- */

export function getQuickActions(mode) {
  switch (mode) {
    case 'operations':
      return [
        { label: 'New Shipment', to: '/shipments/new', primary: true },
        { label: 'Upload Document', to: '/shipments', primary: false },
        { label: 'Open Issues', to: '/manual-review', primary: false },
        { label: 'Customs', to: '/customs', primary: false },
        { label: 'Transport', to: '/transport', primary: false },
      ];
    case 'finance':
      return [
        { label: 'Open Finance', to: '/finance', primary: true },
        { label: 'Open Approvals', to: '/approvals', primary: false },
        { label: 'View Shipments', to: '/shipments', primary: false },
      ];
    case 'management':
      return [
        { label: 'Management Dashboard', to: '/control-tower', primary: true },
        { label: 'Review Approvals', to: '/approvals', primary: false },
        { label: 'Open Risk Alerts', to: '/predictive', primary: false },
        { label: 'Open Issues', to: '/manual-review', primary: false },
      ];
    case 'admin':
      return [
        { label: 'New Shipment', to: '/shipments/new', primary: true },
        { label: 'Admin Settings', to: '/enterprise', primary: false },
        { label: 'Users', to: '/users', primary: false },
        { label: 'AI Control', to: '/bot-governance', primary: false },
        { label: 'All Shipments', to: '/shipments', primary: false },
      ];
    case 'readonly':
      return [
        { label: 'View Shipments', to: '/shipments', primary: true },
        { label: 'Management Dashboard', to: '/control-tower', primary: false },
        { label: 'View Risk Alerts', to: '/predictive', primary: false },
      ];
    default:
      return getQuickActions('operations');
  }
}

/* --- Today Page Widget Config Per Mode --- */

export function getTodayWidgets(mode) {
  // Returns which widget sections to show and in what order
  switch (mode) {
    case 'operations':
      return ['tasks', 'documents', 'attention', 'customs', 'transport', 'issues', 'staleTracking', 'approvals'];
    case 'finance':
      return ['financeHolds', 'approvals', 'attention', 'tasks', 'documents'];
    case 'management':
      return ['approvals', 'issues', 'attention', 'financeHolds', 'customs', 'transport', 'staleTracking'];
    case 'admin':
      return ['tasks', 'approvals', 'issues', 'financeHolds', 'attention', 'documents', 'customs', 'transport', 'staleTracking'];
    case 'readonly':
      return ['attention', 'issues', 'approvals'];
    default:
      return getTodayWidgets('operations');
  }
}

/* --- Onboarding Guide Per Mode --- */

export function getOnboardingGuide(mode) {
  switch (mode) {
    case 'operations':
      return { title: 'Operations Quick Start', steps: [
        'Create a shipment', 'Upload documents', 'Add container',
        'Update customs / transport', 'Resolve any issues',
      ]};
    case 'finance':
      return { title: 'Finance Quick Start', steps: [
        'Check pending charges', 'Add receivables / payables',
        'Review credit holds', 'Verify release status',
      ]};
    case 'management':
      return { title: 'Manager Quick Start', steps: [
        'Open Management Dashboard', 'Check blocked shipments',
        'Review approvals', 'Track risks and alerts',
      ]};
    case 'admin':
      return { title: 'Admin Quick Start', steps: [
        'Add users and configure roles', 'Check Enterprise health',
        'Monitor AI and governance', 'Review approvals and risks',
      ]};
    case 'readonly':
      return { title: 'Getting Started', steps: [
        'View active shipments', 'Check Management Dashboard',
        'Review risk alerts and reports',
      ]};
    default:
      return getOnboardingGuide('operations');
  }
}

/* --- Shipment Detail Tab Order Per Mode --- */

export function getShipmentTabOrder(mode) {
  switch (mode) {
    case 'finance':
      return ['charges', 'finance', 'overview', 'documents', 'bl', 'tasks', 'workflow', 'containers', 'followups', 'demurrage'];
    case 'management':
      return ['overview', 'workflow', 'tasks', 'charges', 'finance', 'documents', 'containers', 'bl', 'followups', 'demurrage'];
    case 'readonly':
      return ['overview', 'documents', 'workflow', 'finance', 'charges', 'tasks', 'containers', 'bl', 'followups', 'demurrage'];
    case 'operations':
    case 'admin':
    default:
      return ['overview', 'workflow', 'containers', 'documents', 'tasks', 'bl', 'followups', 'demurrage', 'charges', 'finance'];
  }
}

/* --- Role-Aware Helper Text --- */

export function getRoleHelperPrefix(mode) {
  if (mode === 'readonly') return 'Read-only view. ';
  return '';
}
