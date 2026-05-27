import {
  Archive,
  ArchiveRestore,
  Ban,
  CheckCircle2,
  Download,
  Edit3,
  ExternalLink,
  FileText,
  History,
  Plus,
  RotateCcw,
  Save,
  ToggleRight,
  Trash2,
  UploadCloud,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api/client.js';
import { ConfirmDialog, EmptyState, ErrorState, LoadingState } from '../components/States.jsx';
import ContainersPanel from '../components/ContainersPanel.jsx';
import ShipmentFinancePanel from '../components/ShipmentFinancePanel.jsx';
import WorkflowPanel from '../components/WorkflowPanel.jsx';

const exportStatuses = [
  'Booking Received',
  'Container Booked',
  'SI Submitted',
  'VGM Filed',
  'BL Draft Received',
  'BL Approved',
  'Final BL Received',
  'Docs Collected',
  'Docs Dispatched',
  'Overseas Coordinated',
  'Freight Invoiced',
  'Vessel Sailed',
  'Completed',
];

const importStatuses = [
  'Pre-Alert Received',
  'ETA Tracking Active',
  'IGM Filed',
  'Freight Invoice Received',
  'BL Surrender Confirmed',
  'DO Received',
  'DO Handed to CHA',
  'Clearance In Progress',
  'Container Delivered',
  'Freight Collected',
  'Completed',
];

const emptyFollowup = {
  party_id: '',
  channel: 'email',
  summary: '',
  next_action: '',
  status: 'open',
  date: new Date().toISOString().slice(0, 10),
};

const chargeTypeOptions = [
  ['ocean_freight', 'Ocean Freight'],
  ['do_charges', 'DO Charges'],
  ['bl_charges', 'BL Charges'],
  ['hbl_charges', 'HBL Charges'],
  ['liner_charges', 'Liner Charges'],
  ['clearance_charges', 'Clearance Charges'],
  ['courier_charges', 'Courier Charges'],
  ['agent_charges', 'Agent Charges'],
  ['demurrage', 'Demurrage'],
  ['documentation', 'Documentation'],
  ['handling', 'Handling'],
  ['transport', 'Transport'],
  ['other', 'Other'],
];

const chargeTypeLabels = Object.fromEntries(chargeTypeOptions);

const chargeStatusOptions = {
  payable: ['pending', 'paid', 'cancelled'],
  receivable: ['pending', 'received', 'cancelled'],
};

function emptyChargeForm() {
  return {
    charge_type: 'ocean_freight',
    direction: 'receivable',
    amount: '',
    currency: 'INR',
    party_id: '',
    status: 'pending',
    invoice_no: '',
    date: new Date().toISOString().slice(0, 10),
    notes: '',
  };
}

function InfoItem({ label, value }) {
  return (
    <div className="info-item">
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </div>
  );
}

function formatMoney(amount, currency = 'INR') {
  return `${currency} ${Number(amount || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatConfidence(value) {
  if (value === null || value === undefined) return '-';
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function reviewBadgeClass(status) {
  if (status === 'approved') return 'priority-info';
  if (status === 'rejected') return 'priority-critical';
  if (status === 'pending_review') return 'priority-warning';
  return 'priority-none';
}

function documentLibrarySummary(item) {
  const versions = item.versions || [];
  if (!versions.length) {
    return item.required ? 'No upload history · required' : 'No upload history';
  }

  const currentCount = versions.filter((version) => version.is_current && version.status === 'active').length;
  const previousCount = versions.filter((version) => version.status === 'superseded').length;
  const removedCount = versions.filter((version) => ['archived', 'rejected'].includes(version.status)).length;
  const otherCount = Math.max(versions.length - currentCount - previousCount - removedCount, 0);

  const parts = [];
  parts.push(currentCount ? `${currentCount} current upload` : 'No current upload');
  if (previousCount) {
    parts.push(`${previousCount} previous`);
  }
  if (removedCount) {
    parts.push(`${removedCount} removed history`);
  }
  if (otherCount) {
    parts.push(`${otherCount} historical`);
  }
  if (item.required) {
    parts.push('required');
  }
  return parts.join(' · ');
}

function emptyUploadDraft() {
  return {
    file: null,
    version_label: '',
    notes: '',
    review_status: 'pending_review',
  };
}

function cleanNullableForm(form) {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => {
      if (value === '') return [key, null];
      if (key === 'party_id') return [key, value ? Number(value) : null];
      return [key, value];
    })
  );
}

function ShipmentDetailPage() {
  const { id } = useParams();
  const [shipment, setShipment] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [documentLibrary, setDocumentLibrary] = useState([]);
  const [uploadTarget, setUploadTarget] = useState(null);
  const [uploadDraft, setUploadDraft] = useState(emptyUploadDraft());
  const [historyTarget, setHistoryTarget] = useState(null);
  const [detailTarget, setDetailTarget] = useState(null);
  const [intelligenceTarget, setIntelligenceTarget] = useState(null);
  const [intelligenceSummary, setIntelligenceSummary] = useState(null);
  const [versionHistory, setVersionHistory] = useState([]);
  const [historyEvents, setHistoryEvents] = useState({});
  const [documentBusy, setDocumentBusy] = useState(false);
  const [intelligenceBusy, setIntelligenceBusy] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [bl, setBl] = useState(null);
  const [demurrage, setDemurrage] = useState(null);
  const [followups, setFollowups] = useState([]);
  const [charges, setCharges] = useState([]);
  const [pnl, setPnl] = useState(null);
  const [parties, setParties] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [includeCancelledTasks, setIncludeCancelledTasks] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState('');
  const [followupForm, setFollowupForm] = useState(emptyFollowup);
  const [chargeForm, setChargeForm] = useState(emptyChargeForm());
  const [editingChargeId, setEditingChargeId] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [confirmDeleteTask, setConfirmDeleteTask] = useState(null);

  const canWrite = currentUser && currentUser.role !== 'VIEW_ONLY';
  const canAdmin = currentUser?.role === 'ADMIN';
  const workflowStatuses = useMemo(
    () => (shipment?.type === 'export' ? exportStatuses : importStatuses),
    [shipment?.type]
  );

  async function loadFinance() {
    const [chargesResponse, pnlResponse] = await Promise.all([
      api.get(`/shipments/${id}/charges`),
      api.get(`/shipments/${id}/pnl`),
    ]);
    setCharges(chargesResponse.data);
    setPnl(pnlResponse.data);
  }

  async function loadTasks() {
    const response = await api.get('/tasks', {
      params: {
        shipment_id: id,
        ...(includeCancelledTasks ? { include_cancelled: true } : {}),
      },
    });
    setTasks(response.data);
  }

  async function loadAll() {
    const [meResponse, shipmentResponse] = await Promise.all([
      api.get('/auth/me'),
      api.get(`/shipments/${id}`),
    ]);
    setCurrentUser(meResponse.data);
    setShipment(shipmentResponse.data);
    setWorkflowStatus(shipmentResponse.data.status);

    const [
      documentsResponse,
      tasksResponse,
      blResponse,
      demurrageResponse,
      followupsResponse,
      partiesResponse,
      chargesResponse,
      pnlResponse,
      documentLibraryResponse,
    ] =
      await Promise.all([
        api.get(`/documents/shipment/${id}`),
        api.get('/tasks', {
          params: {
            shipment_id: id,
            ...(includeCancelledTasks ? { include_cancelled: true } : {}),
          },
        }),
        api.get(`/shipments/${id}/bl`),
        api.get(`/shipments/${id}/demurrage`),
        api.get(`/shipments/${id}/followups`),
        api.get('/parties'),
        api.get(`/shipments/${id}/charges`),
        api.get(`/shipments/${id}/pnl`),
        api.get(`/shipments/${id}/document-library`).catch(() => ({ data: [] })),
      ]);
    setDocuments(documentsResponse.data);
    setTasks(tasksResponse.data);
    setBl(blResponse.data);
    setDemurrage(demurrageResponse.data);
    setFollowups(followupsResponse.data);
    setParties(partiesResponse.data);
    setCharges(chargesResponse.data);
    setPnl(pnlResponse.data);
    setDocumentLibrary(documentLibraryResponse.data);
  }

  useEffect(() => {
    loadAll().catch((err) => setError(err.response?.data?.detail || 'Unable to load shipment'));
  }, [id]);

  useEffect(() => {
    if (shipment) {
      loadTasks().catch((err) => setError(err.response?.data?.detail || 'Unable to load shipment tasks'));
    }
  }, [includeCancelledTasks]);

  function updateDocument(documentId, field, value) {
    setDocuments((current) =>
      current.map((document) => (document.id === documentId ? { ...document, [field]: value } : document))
    );
  }

  async function saveDocument(document) {
    setNotice('');
    try {
      const response = await api.patch(`/documents/${document.id}`, {
        status: document.status,
        file_url: document.file_url || null,
        notes: document.notes || null,
        is_required: document.is_required,
      });
      setDocuments((current) => current.map((item) => (item.id === document.id ? response.data : item)));
      setNotice('Document saved');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save document');
    }
  }

  async function loadDocumentLibrary() {
    const response = await api.get(`/shipments/${id}/document-library`);
    setDocumentLibrary(response.data);
  }

  function openUpload(documentRow) {
    setError('');
    setNotice('');
    setUploadTarget(documentRow);
    setUploadDraft(emptyUploadDraft());
    setHistoryTarget(null);
    setDetailTarget(null);
    setIntelligenceTarget(null);
    setIntelligenceSummary(null);
  }

  async function uploadDocumentVersion(event) {
    event.preventDefault();
    if (!uploadTarget || !uploadDraft.file) {
      setError('Choose a document file to upload');
      return;
    }
    setNotice('');
    setDocumentBusy(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadDraft.file);
      formData.append('document_id', uploadTarget.id);
      formData.append('document_type', uploadTarget.doc_type);
      formData.append('version_label', uploadDraft.version_label || '');
      formData.append('notes', uploadDraft.notes || '');
      formData.append('review_status', uploadDraft.review_status);
      const response = await api.post(`/shipments/${id}/document-versions/upload`, formData, {
        timeout: 60000,
      });
      applyUploadedVersion(response.data);
      setUploadTarget(null);
      setUploadDraft(emptyUploadDraft());
      setNotice('Document version uploaded');
      refreshDocumentsAfterUpload().catch(() => {
        setNotice('Document version uploaded. Refresh the page if the latest details do not appear.');
      });
    } catch (err) {
      const recovered = await recoverUploadStateAfterError();
      if (recovered) {
        setUploadTarget(null);
        setUploadDraft(emptyUploadDraft());
        setNotice('Document upload completed, but the response was interrupted. The latest document state is loaded.');
      } else {
        setError(err.response?.data?.detail || 'Unable to upload document version');
      }
    } finally {
      setDocumentBusy(false);
    }
  }

  function applyUploadedVersion(version) {
    setDocuments((current) =>
      current.map((document) => {
        if (document.id !== version.document_id) return document;
        return {
          ...document,
          current_version_id: version.id,
          current_version_no: version.version_no,
          current_review_status: version.review_status,
          uploaded_file_count: Number(document.uploaded_file_count || 0) + 1,
          latest_uploaded_at: version.created_at,
          latest_file_name: version.file?.sanitized_filename || document.latest_file_name,
        };
      })
    );
  }

  async function refreshDocumentsAfterUpload() {
    const [documentsResponse, libraryResponse] = await Promise.all([
      api.get(`/documents/shipment/${id}`),
      api.get(`/shipments/${id}/document-library`),
    ]);
    setDocuments(documentsResponse.data);
    setDocumentLibrary(libraryResponse.data);
  }

  async function recoverUploadStateAfterError() {
    if (!uploadTarget) return false;
    try {
      const beforeVersionId = uploadTarget.current_version_id || null;
      const [documentsResponse, libraryResponse] = await Promise.all([
        api.get(`/documents/shipment/${id}`),
        api.get(`/shipments/${id}/document-library`).catch(() => ({ data: documentLibrary })),
      ]);
      setDocuments(documentsResponse.data);
      setDocumentLibrary(libraryResponse.data);
      const refreshed = documentsResponse.data.find((document) => document.id === uploadTarget.id);
      return Boolean(
        refreshed?.current_version_id
        && refreshed.current_version_id !== beforeVersionId
      );
    } catch (_refreshError) {
      return false;
    }
  }

  async function openVersionHistory(document) {
    setDocumentBusy(true);
    setHistoryTarget(document);
    setUploadTarget(null);
    setDetailTarget(null);
    setIntelligenceTarget(null);
    setIntelligenceSummary(null);
    setHistoryEvents({});
    try {
      const response = await api.get(`/shipments/${id}/document-versions`, {
        params: { document_id: document.id },
      });
      setVersionHistory(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load document history');
    } finally {
      setDocumentBusy(false);
    }
  }

  async function loadVersionEvents(version) {
    if (historyEvents[version.id]) {
      setHistoryEvents((current) => {
        const next = { ...current };
        delete next[version.id];
        return next;
      });
      return;
    }
    try {
      const response = await api.get(`/document-versions/${version.id}/events`);
      setHistoryEvents((current) => ({ ...current, [version.id]: response.data }));
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load document version events');
    }
  }

  async function openIntelligence(document) {
    if (!document.current_version_id) return;
    setError('');
    setNotice('');
    setUploadTarget(null);
    setHistoryTarget(null);
    setDetailTarget(null);
    setIntelligenceTarget({
      id: document.current_version_id,
      document_type: document.doc_type,
      version_no: document.current_version_no,
    });
    setIntelligenceBusy(true);
    try {
      const response = await api.get(`/document-intelligence/versions/${document.current_version_id}/summary`);
      setIntelligenceSummary(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load document intelligence');
    } finally {
      setIntelligenceBusy(false);
    }
  }

  async function runIntelligence(document) {
    if (!document.current_version_id) return;
    setError('');
    setNotice('');
    setIntelligenceBusy(true);
    setIntelligenceTarget({
      id: document.current_version_id,
      document_type: document.doc_type,
      version_no: document.current_version_no,
    });
    try {
      const response = await api.post(`/document-intelligence/versions/${document.current_version_id}/run`, {
        run_type: 'full',
      }, {
        timeout: 90000,
      });
      setIntelligenceSummary(response.data);
      setNotice('Document intelligence completed');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to run document intelligence');
    } finally {
      setIntelligenceBusy(false);
    }
  }

  async function reviewIntelligenceSuggestion(suggestion, action) {
    setError('');
    setNotice('');
    const payload = {};
    if (action !== 'approve') {
      const reason = window.prompt(`${action} suggestion`, '');
      if (reason === null) return;
      payload.reason = reason;
      payload.notes = reason;
    }
    setIntelligenceBusy(true);
    try {
      const response = await api.patch(`/document-intelligence/suggestions/${suggestion.id}/${action}`, payload);
      setIntelligenceSummary((current) => {
        if (!current) return current;
        return {
          ...current,
          suggestions: current.suggestions.map((item) => (item.id === suggestion.id ? response.data : item)),
        };
      });
      setNotice(`Suggestion ${action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'dismissed'}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update suggestion');
    } finally {
      setIntelligenceBusy(false);
    }
  }

  async function refreshDocumentsAfterVersionAction() {
    const [documentsResponse] = await Promise.all([
      api.get(`/documents/shipment/${id}`),
      loadDocumentLibrary(),
    ]);
    setDocuments(documentsResponse.data);
    if (historyTarget) {
      const response = await api.get(`/shipments/${id}/document-versions`, {
        params: { document_id: historyTarget.id },
      });
      setVersionHistory(response.data);
    }
  }

  async function downloadDocumentVersion(version) {
    setNotice('');
    try {
      const response = await api.get(`/document-versions/${version.id}/download`, {
        responseType: 'blob',
      });
      const blobUrl = URL.createObjectURL(new Blob([response.data], { type: version.file?.content_type || 'application/octet-stream' }));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = version.file?.sanitized_filename || `${version.document_type}-v${version.version_no}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
      setNotice('Document download started');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to download document');
    }
  }

  async function runVersionAction(version, action) {
    setNotice('');
    let payload = {};
    if (action === 'reject' || action === 'archive' || action === 'rollback') {
      const actionLabel = action === 'archive' ? 'Remove upload' : action === 'rollback' ? 'Restore version' : 'Reject version';
      const reason = window.prompt(`${actionLabel}: ${version.document_type} v${version.version_no}`, '');
      if (reason === null) return;
      payload = action === 'archive' || action === 'rollback' ? { reason } : { notes: reason };
    }
    setDocumentBusy(true);
    try {
      if (action === 'rollback') {
        await api.post(`/document-versions/${version.id}/rollback`, payload);
      } else {
        await api.patch(`/document-versions/${version.id}/${action}`, payload);
      }
      await refreshDocumentsAfterVersionAction();
      const pastTense = {
        approve: 'approved',
        reject: 'rejected',
        archive: 'removed from current documents',
        rollback: 'restored',
      }[action];
      setNotice(`Document version ${pastTense}`);
    } catch (err) {
      setError(err.response?.data?.detail || `Unable to ${action} document version`);
    } finally {
      setDocumentBusy(false);
    }
  }

  async function toggleTask(task) {
    setNotice('');
    try {
      const response = await api.patch(`/tasks/${task.id}`, {
        status: task.status === 'open' ? 'done' : 'open',
      });
      setTasks((current) => current.map((item) => (item.id === task.id ? response.data : item)));
      setNotice('Task updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update task');
    }
  }

  async function cancelTask(task) {
    setNotice('');
    try {
      await api.patch(`/tasks/${task.id}/cancel`);
      await loadTasks();
      setNotice('Task cancelled');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to cancel task');
    }
  }

  async function restoreTask(task) {
    setNotice('');
    try {
      await api.patch(`/tasks/${task.id}/restore`);
      await loadTasks();
      setNotice('Task restored');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to restore task');
    }
  }

  async function deleteManualTask() {
    if (!confirmDeleteTask) return;
    setNotice('');
    try {
      await api.delete(`/tasks/${confirmDeleteTask.id}`);
      await loadTasks();
      setNotice('Manual task deleted');
      setConfirmDeleteTask(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete task');
      setConfirmDeleteTask(null);
    }
  }

  async function archiveShipment() {
    const reason = window.prompt(`Reason for archiving ${shipment.shipment_code}`, '');
    if (reason === null) return;
    setNotice('');
    try {
      const response = await api.patch(`/shipments/${id}/archive`, { reason: reason || null });
      setShipment(response.data);
      setWorkflowStatus(response.data.status);
      setNotice('Shipment archived');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to archive shipment');
    }
  }

  async function restoreShipment() {
    setNotice('');
    try {
      const response = await api.patch(`/shipments/${id}/restore`);
      setShipment(response.data);
      setWorkflowStatus(response.data.status);
      setNotice('Shipment restored');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to restore shipment');
    }
  }

  async function saveWorkflowStatus() {
    setNotice('');
    try {
      const response = await api.patch(`/shipments/${id}/workflow-status`, { status: workflowStatus });
      setShipment(response.data);
      await loadAll();
      setNotice('Workflow status updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update workflow status');
    }
  }

  async function saveBl() {
    setNotice('');
    try {
      const response = await api.patch(`/shipments/${id}/bl`, cleanNullableForm(bl));
      setBl(response.data);
      setNotice('BL management saved');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save BL management');
    }
  }

  async function saveDemurrage() {
    setNotice('');
    try {
      const payload = cleanNullableForm(demurrage);
      const response = await api.patch(`/shipments/${id}/demurrage`, {
        free_days: payload.free_days === null ? null : Number(payload.free_days),
        start_date: payload.start_date,
        rate_per_day: payload.rate_per_day === null ? null : Number(payload.rate_per_day),
        currency: payload.currency,
        alert_at_days: payload.alert_at_days === null ? null : Number(payload.alert_at_days),
        container_count: payload.container_count === null ? null : Number(payload.container_count),
      });
      setDemurrage(response.data);
      setNotice('Demurrage saved');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save demurrage');
    }
  }

  async function createFollowup(event) {
    event.preventDefault();
    setNotice('');
    try {
      const response = await api.post(`/shipments/${id}/followups`, cleanNullableForm(followupForm));
      setFollowups((current) => [response.data, ...current]);
      setFollowupForm(emptyFollowup);
      setNotice('Follow-up logged');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create follow-up');
    }
  }

  async function updateFollowupStatus(followup, status) {
    setNotice('');
    try {
      const response = await api.patch(`/followups/${followup.id}`, { status });
      setFollowups((current) => current.map((item) => (item.id === followup.id ? response.data : item)));
      setNotice('Follow-up updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update follow-up');
    }
  }

  async function deleteFollowup(followupId) {
    setNotice('');
    try {
      await api.delete(`/followups/${followupId}`);
      setFollowups((current) => current.filter((item) => item.id !== followupId));
      setNotice('Follow-up deleted');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete follow-up');
    }
  }

  function updateChargeForm(field, value) {
    setChargeForm((current) => {
      const next = { ...current, [field]: value };
      if (field === 'direction' && !chargeStatusOptions[value].includes(next.status)) {
        next.status = 'pending';
      }
      return next;
    });
  }

  function resetChargeForm() {
    setChargeForm(emptyChargeForm());
    setEditingChargeId(null);
  }

  function editCharge(charge) {
    setEditingChargeId(charge.id);
    setChargeForm({
      charge_type: charge.charge_type,
      direction: charge.direction,
      amount: charge.amount,
      currency: charge.currency || 'INR',
      party_id: charge.party_id || '',
      status: charge.status,
      invoice_no: charge.invoice_no || '',
      date: charge.date || '',
      notes: charge.notes || '',
    });
    setActiveTab('charges');
  }

  function chargePayload() {
    return {
      shipment_id: Number(id),
      charge_type: chargeForm.charge_type,
      direction: chargeForm.direction,
      amount: Number(chargeForm.amount),
      currency: chargeForm.currency || 'INR',
      party_id: chargeForm.party_id ? Number(chargeForm.party_id) : null,
      status: chargeForm.status,
      invoice_no: chargeForm.invoice_no || null,
      date: chargeForm.date || null,
      notes: chargeForm.notes || null,
    };
  }

  async function saveCharge(event) {
    event.preventDefault();
    setNotice('');
    if (chargeForm.amount === '' || Number(chargeForm.amount) < 0) {
      setError('Charge amount is required and cannot be negative');
      return;
    }
    try {
      if (editingChargeId) {
        await api.patch(`/charges/${editingChargeId}`, chargePayload());
        setNotice('Charge updated');
      } else {
        await api.post(`/shipments/${id}/charges`, chargePayload());
        setNotice('Charge added');
      }
      resetChargeForm();
      await loadFinance();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to save charge');
    }
  }

  async function updateChargeStatus(charge, status) {
    setNotice('');
    try {
      await api.patch(`/charges/${charge.id}`, { status });
      await loadFinance();
      setNotice(status === 'cancelled' ? 'Charge cancelled' : 'Charge status updated');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update charge');
    }
  }

  async function cancelCharge(charge) {
    setNotice('');
    try {
      await api.delete(`/charges/${charge.id}`);
      await loadFinance();
      setNotice('Charge cancelled');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to cancel charge');
    }
  }

  if (error && !shipment) {
    return (
      <div className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Shipment</p>
            <h1>Shipment Detail</h1>
          </div>
        </div>
        <ErrorState message={error} onRetry={() => { setError(''); loadAll().catch((err) => setError(err.response?.data?.detail || 'Unable to load shipment')); }} />
      </div>
    );
  }

  if (!shipment) {
    return (
      <div className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Shipment</p>
            <h1>Shipment Detail</h1>
          </div>
        </div>
        <LoadingState label="Loading shipment..." />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">{shipment.type}</p>
          <h1>{shipment.shipment_code}</h1>
        </div>
        <div className="header-actions">
          <span className={`badge status-${shipment.status === 'Completed' ? 'completed' : 'active'}`}>{shipment.status}</span>
          {shipment.is_archived && <span className="badge status-archived">Archived</span>}
          {canAdmin && (
            shipment.is_archived ? (
              <button className="secondary-button" type="button" onClick={restoreShipment}>
                <ArchiveRestore size={16} />
                <span>Restore</span>
              </button>
            ) : (
              <button className="secondary-button danger-text" type="button" onClick={archiveShipment}>
                <Archive size={16} />
                <span>Archive</span>
              </button>
            )
          )}
        </div>
      </div>

      <ErrorState message={error} />
      {notice && <p className="success-text">{notice}</p>}

      <div className="tabs" role="tablist">
        {['overview', 'workflow', 'containers', 'documents', 'tasks', 'bl', 'followups', 'demurrage', 'charges', 'finance'].map((tab) => (
          <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
            {tab === 'bl'
              ? 'BL Management'
              : tab === 'followups'
              ? 'Follow-up Log'
              : tab === 'workflow'
              ? 'Workflow'
              : tab === 'finance'
              ? 'Finance'
              : tab[0].toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'workflow' && <WorkflowPanel shipmentId={shipment.id} />}

      {activeTab === 'containers' && (
        <ContainersPanel shipmentId={shipment.id} shipmentType={shipment.type} />
      )}

      {activeTab === 'overview' && (
        <section className="panel form-grid">
          <div className="panel-header span-2 no-margin">
            <h2>Workflow Status</h2>
          </div>
          <label>
            Current Status
            <select value={workflowStatus} disabled={!canWrite} onChange={(event) => setWorkflowStatus(event.target.value)}>
              {workflowStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <div className="form-actions">
            {canWrite && (
              <button className="primary-button" type="button" onClick={saveWorkflowStatus}>
                <Save size={18} />
                <span>Update Status</span>
              </button>
            )}
          </div>
          <div className="span-2 info-grid">
            <InfoItem label="Shipment Code" value={shipment.shipment_code} />
            <InfoItem label="Type" value={shipment.type} />
            <InfoItem label="Status" value={shipment.status} />
            <InfoItem label="Archived" value={shipment.is_archived ? 'Yes' : 'No'} />
            <InfoItem label="Shipping Line" value={shipment.shipping_line} />
            <InfoItem label="Vessel" value={shipment.vessel_name} />
            <InfoItem label="Voyage No" value={shipment.voyage_no} />
            <InfoItem label="Origin Port" value={shipment.origin_port} />
            <InfoItem label="Destination Port" value={shipment.dest_port} />
            <InfoItem label="Container No" value={shipment.container_no} />
            <InfoItem label="Container Type" value={shipment.container_type} />
            <InfoItem label="ETD" value={shipment.etd} />
            <InfoItem label="ETA" value={shipment.eta} />
            <InfoItem label="Booking Ref" value={shipment.booking_ref} />
            <InfoItem label="Commodity" value={shipment.commodity} />
            {shipment.is_archived && <InfoItem label="Archive Reason" value={shipment.archive_reason} />}
          </div>
        </section>
      )}

      {activeTab === 'documents' && (
        <section className="panel">
          <div className="panel-header">
            <h2>Documents</h2>
          </div>
          {!documents.length ? (
            <EmptyState title="No documents for this shipment" />
          ) : (
            <div className="table-wrap">
              <table className="documents-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Checklist</th>
                    <th>Uploaded Version</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document) => (
                    <tr key={document.id}>
                      <td className="document-type-cell"><strong>{document.doc_type}</strong></td>
                      <td>
                        <select
                          value={document.status}
                          disabled={!canWrite}
                          onChange={(event) => updateDocument(document.id, 'status', event.target.value)}
                        >
                          <option value="pending">pending</option>
                          <option value="received">received</option>
                          <option value="sent">sent</option>
                          <option value="approved">approved</option>
                          <option value="not_required">not_required</option>
                        </select>
                      </td>
                      <td>
                        {document.current_version_no ? (
                          <div className="document-version-cell">
                            <div className="document-version-badges">
                              <span className="badge priority-info">v{document.current_version_no}</span>
                              <span className={`badge ${reviewBadgeClass(document.current_review_status)}`}>
                                {document.current_review_status || 'not reviewed'}
                              </span>
                            </div>
                            <p className="document-file-name" title={document.latest_file_name || ''}>
                              {document.latest_file_name || 'Uploaded file'}
                            </p>
                          </div>
                        ) : (
                          <span className="muted">No upload</span>
                        )}
                      </td>
                      <td>
                        <div className="row-actions document-row-actions">
                          {canWrite && (
                            <>
                              <button className="icon-button" type="button" onClick={() => saveDocument(document)} title="Save checklist row">
                                <Save size={16} />
                              </button>
                              <button className="icon-button" type="button" onClick={() => setDetailTarget(detailTarget?.id === document.id ? null : document)} title="Edit link and notes">
                                <Edit3 size={16} />
                              </button>
                              <button className="secondary-button" type="button" onClick={() => openUpload(document)}>
                                <UploadCloud size={16} />
                                <span>Upload</span>
                              </button>
                            </>
                          )}
                          <button className="icon-button" type="button" onClick={() => openVersionHistory(document)} title="Version history">
                            <History size={16} />
                          </button>
                          {document.current_version_id && (
                            <button className="secondary-button" type="button" onClick={() => openIntelligence(document)}>
                              <FileText size={16} />
                              <span>Intelligence</span>
                            </button>
                          )}
                          {canWrite && document.current_version_id && (
                            <button className="secondary-button" type="button" onClick={() => runIntelligence(document)} disabled={intelligenceBusy}>
                              <ToggleRight size={16} />
                              <span>Run Intelligence</span>
                            </button>
                          )}
                          {canAdmin && document.current_version_id && (
                            <button
                              className="secondary-button danger-text"
                              type="button"
                              onClick={() => runVersionAction({
                                id: document.current_version_id,
                                document_type: document.doc_type,
                                version_no: document.current_version_no,
                                status: 'active',
                              }, 'archive')}
                            >
                              <Trash2 size={16} />
                              <span>Remove upload</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {detailTarget && (
            <div className="inline-panel document-details-panel">
              <div className="panel-header">
                <h3>{detailTarget.doc_type} Details</h3>
                <button className="secondary-button" type="button" onClick={() => setDetailTarget(null)}>
                  Close
                </button>
              </div>
              <div className="form-grid">
                <label>
                  External File URL
                  <div className="link-cell">
                    <input
                      value={(documents.find((item) => item.id === detailTarget.id)?.file_url) || ''}
                      disabled={!canWrite}
                      onChange={(event) => updateDocument(detailTarget.id, 'file_url', event.target.value)}
                      placeholder="External file URL"
                    />
                    {documents.find((item) => item.id === detailTarget.id)?.file_url && (
                      <a href={documents.find((item) => item.id === detailTarget.id)?.file_url} target="_blank" rel="noreferrer" title="Open link">
                        <ExternalLink size={16} />
                      </a>
                    )}
                  </div>
                </label>
                <label>
                  Notes
                  <input
                    value={(documents.find((item) => item.id === detailTarget.id)?.notes) || ''}
                    disabled={!canWrite}
                    onChange={(event) => updateDocument(detailTarget.id, 'notes', event.target.value)}
                    placeholder="Notes"
                  />
                </label>
                {canWrite && (
                  <div className="form-actions span-2">
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => saveDocument(documents.find((item) => item.id === detailTarget.id) || detailTarget)}
                    >
                      <Save size={18} />
                      <span>Save Details</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
          {uploadTarget && (
            <div className="dialog-backdrop" role="presentation" onClick={() => setUploadTarget(null)}>
              <form
                className="dialog-panel wide form-grid"
                role="dialog"
                aria-modal="true"
                aria-label={`Upload ${uploadTarget.doc_type}`}
                onSubmit={uploadDocumentVersion}
                onClick={(event) => event.stopPropagation()}
              >
                <div className="panel-header span-2 no-margin">
                  <div>
                    <p className="eyebrow">Document Upload</p>
                    <h3>Upload {uploadTarget.doc_type}</h3>
                  </div>
                  <button className="secondary-button" type="button" onClick={() => setUploadTarget(null)}>
                    Cancel
                  </button>
                </div>
                <label>
                  File
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.csv,.txt,application/pdf,image/png,image/jpeg,text/csv,text/plain"
                    onChange={(event) => setUploadDraft((current) => ({ ...current, file: event.target.files?.[0] || null }))}
                  />
                </label>
                <label>
                  Version Label
                  <input
                    value={uploadDraft.version_label}
                    onChange={(event) => setUploadDraft((current) => ({ ...current, version_label: event.target.value }))}
                    placeholder="Draft, revised, final"
                  />
                </label>
                <label>
                  Review Status
                  <select
                    value={uploadDraft.review_status}
                    onChange={(event) => setUploadDraft((current) => ({ ...current, review_status: event.target.value }))}
                  >
                    <option value="pending_review">pending_review</option>
                    <option value="approved">approved</option>
                    <option value="not_required">not_required</option>
                  </select>
                </label>
                <label>
                  Notes
                  <input
                    value={uploadDraft.notes}
                    onChange={(event) => setUploadDraft((current) => ({ ...current, notes: event.target.value }))}
                    placeholder="Optional upload notes"
                  />
                </label>
                <div className="form-actions span-2">
                  <button className="primary-button" type="submit" disabled={documentBusy}>
                    <UploadCloud size={18} />
                    <span>Upload Version</span>
                  </button>
                </div>
              </form>
            </div>
          )}
          {historyTarget && (
            <div className="inline-panel">
              <div className="panel-header">
                <h3>{historyTarget.doc_type} History</h3>
                <button className="secondary-button" type="button" onClick={() => setHistoryTarget(null)}>
                  Close
                </button>
              </div>
              {!versionHistory.length ? (
                <p className="muted">No uploaded versions yet.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>File</th>
                        <th>Status</th>
                        <th>Uploaded</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {versionHistory.map((version) => (
                        <tr key={version.id}>
                          <td>
                            <strong>v{version.version_no}</strong>
                            {version.version_label ? <p className="muted">{version.version_label}</p> : null}
                          </td>
                          <td>{version.file?.sanitized_filename || '-'}</td>
                          <td>
                            <span className={`badge ${version.is_current ? 'priority-info' : 'priority-none'}`}>
                              {version.is_current ? 'current' : version.status}
                            </span>
                            <span className={`badge ${reviewBadgeClass(version.review_status)}`}>
                              {version.review_status}
                            </span>
                          </td>
                          <td>
                            {version.created_at ? new Date(version.created_at).toLocaleString() : '-'}
                            {version.created_by_name ? <p className="muted">{version.created_by_name}</p> : null}
                          </td>
                          <td>
                            <div className="row-actions">
                              <button className="secondary-button" type="button" onClick={() => downloadDocumentVersion(version)}>
                                <Download size={16} />
                                <span>Download</span>
                              </button>
                              <button className="secondary-button" type="button" onClick={() => loadVersionEvents(version)}>
                                <History size={16} />
                                <span>Events</span>
                              </button>
                              {canWrite && version.review_status !== 'approved' && (
                                <button className="secondary-button" type="button" onClick={() => runVersionAction(version, 'approve')}>
                                  <CheckCircle2 size={16} />
                                  <span>Approve</span>
                                </button>
                              )}
                              {canWrite && version.review_status !== 'rejected' && (
                                <button className="secondary-button danger-text" type="button" onClick={() => runVersionAction(version, 'reject')}>
                                  <Ban size={16} />
                                  <span>Reject</span>
                                </button>
                              )}
                              {canAdmin && version.status !== 'archived' && (
                                <button className="secondary-button danger-text" type="button" onClick={() => runVersionAction(version, 'archive')}>
                                  <Trash2 size={16} />
                                  <span>Remove</span>
                                </button>
                              )}
                              {canAdmin && !version.is_current && version.status !== 'archived' && version.status !== 'rejected' && (
                                <button className="secondary-button" type="button" onClick={() => runVersionAction(version, 'rollback')}>
                                  <RotateCcw size={16} />
                                  <span>Rollback</span>
                                </button>
                              )}
                            </div>
                            {historyEvents[version.id] && (
                              <div className="event-mini-list">
                                {historyEvents[version.id].map((entry) => (
                                  <p key={entry.id}>
                                    <strong>{entry.event_type}</strong>
                                    {entry.actor_name ? ` · ${entry.actor_name}` : ''}
                                  </p>
                                ))}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
          {intelligenceTarget && (
            <div className="inline-panel document-intelligence-panel">
              <div className="panel-header">
                <div>
                  <h3>{intelligenceTarget.document_type} Intelligence</h3>
                  <p className="muted">Version v{intelligenceTarget.version_no}</p>
                </div>
                <button className="secondary-button" type="button" onClick={() => setIntelligenceTarget(null)}>
                  Close
                </button>
              </div>
              {intelligenceBusy && !intelligenceSummary ? (
                <LoadingState label="Loading document intelligence..." />
              ) : !intelligenceSummary?.latest_run ? (
                <div className="empty-state">
                  <p>No intelligence run yet.</p>
                  {canWrite && (
                    <button
                      className="primary-button"
                      type="button"
                      disabled={intelligenceBusy}
                      onClick={() => runIntelligence({
                        current_version_id: intelligenceTarget.id,
                        doc_type: intelligenceTarget.document_type,
                        current_version_no: intelligenceTarget.version_no,
                      })}
                    >
                      <ToggleRight size={18} />
                      <span>Run Intelligence</span>
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <div className="summary-grid">
                    <div className="summary-tile">
                      <span>OCR</span>
                      <strong>{intelligenceSummary.latest_run.status}</strong>
                    </div>
                    <div className="summary-tile">
                      <span>Detected Type</span>
                      <strong>{intelligenceSummary.latest_extraction?.detected_document_type || '-'}</strong>
                    </div>
                    <div className="summary-tile">
                      <span>Confidence</span>
                      <strong>{formatConfidence(intelligenceSummary.latest_extraction?.overall_confidence)}</strong>
                    </div>
                    <div className="summary-tile">
                      <span>Mismatches</span>
                      <strong>{intelligenceSummary.mismatches?.length || 0}</strong>
                    </div>
                  </div>

                  {intelligenceSummary.latest_extraction?.ocr_text_preview && (
                    <div className="inline-panel">
                      <h4>OCR Preview</h4>
                      <p className="muted">{intelligenceSummary.latest_extraction.ocr_text_preview}</p>
                    </div>
                  )}

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Field</th>
                          <th>Extracted Value</th>
                          <th>Normalized</th>
                          <th>Confidence</th>
                          <th>Status</th>
                          <th>Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(intelligenceSummary.fields || []).map((field) => (
                          <tr key={field.id}>
                            <td>{field.field_key}</td>
                            <td>{field.field_value}</td>
                            <td>{field.normalized_value || '-'}</td>
                            <td>{formatConfidence(field.confidence)}</td>
                            <td><span className={`badge ${field.status === 'mismatch' ? 'priority-warning' : ''}`}>{field.status}</span></td>
                            <td><span className="muted">{field.source_text || '-'}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!intelligenceSummary.fields?.length && <p className="muted">No fields extracted.</p>}
                  </div>

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Severity</th>
                          <th>Rule</th>
                          <th>Field</th>
                          <th>System</th>
                          <th>Extracted</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(intelligenceSummary.mismatches || []).map((mismatch) => (
                          <tr key={mismatch.id}>
                            <td><span className={`badge priority-${mismatch.severity}`}>{mismatch.severity}</span></td>
                            <td>
                              <strong>{mismatch.rule_key}</strong>
                              <p className="muted">{mismatch.message}</p>
                            </td>
                            <td>{mismatch.field_key || '-'}</td>
                            <td>{mismatch.system_value || '-'}</td>
                            <td>{mismatch.extracted_value || '-'}</td>
                            <td>{mismatch.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!intelligenceSummary.mismatches?.length && <p className="muted">No mismatches found.</p>}
                  </div>

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Suggestion</th>
                          <th>Target</th>
                          <th>Confidence</th>
                          <th>Status</th>
                          <th>Payload</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(intelligenceSummary.suggestions || []).map((suggestion) => (
                          <tr key={suggestion.id}>
                            <td>{suggestion.suggestion_type}</td>
                            <td>{suggestion.target_entity_type}</td>
                            <td>{formatConfidence(suggestion.confidence)}</td>
                            <td><span className="badge">{suggestion.status}</span></td>
                            <td><code>{JSON.stringify(suggestion.payload_json || {})}</code></td>
                            <td>
                              {canWrite && suggestion.status === 'pending' ? (
                                <div className="row-actions">
                                  <button className="secondary-button" type="button" onClick={() => reviewIntelligenceSuggestion(suggestion, 'approve')}>
                                    Approve
                                  </button>
                                  <button className="secondary-button danger-text" type="button" onClick={() => reviewIntelligenceSuggestion(suggestion, 'reject')}>
                                    Reject
                                  </button>
                                  <button className="secondary-button" type="button" onClick={() => reviewIntelligenceSuggestion(suggestion, 'dismiss')}>
                                    Dismiss
                                  </button>
                                </div>
                              ) : (
                                <span className="muted">Review tracked</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!intelligenceSummary.suggestions?.length && <p className="muted">No suggestions created.</p>}
                  </div>
                </>
              )}
            </div>
          )}
          {documentLibrary.length > 0 && (
            <details className="inline-panel document-library-panel">
              <summary>Document Library</summary>
              <div className="document-library-grid">
                {documentLibrary.map((item) => (
                  <article className="document-library-row" key={`${item.document_id || 'custom'}-${item.document_type}`}>
                    <div>
                      <strong>{item.document_type}</strong>
                      <p className="muted">{documentLibrarySummary(item)}</p>
                    </div>
                    {item.current_version ? (
                      <div className="document-library-current">
                        <span className="badge priority-info">v{item.current_version.version_no}</span>
                        <span className={`badge ${reviewBadgeClass(item.current_version.review_status)}`}>
                          {item.current_version.review_status}
                        </span>
                      </div>
                    ) : (
                      <span className="badge priority-warning">missing</span>
                    )}
                  </article>
                ))}
              </div>
            </details>
          )}
        </section>
      )}

      {activeTab === 'tasks' && (
        <section className="panel">
          <div className="panel-header">
            <h2>Shipment Tasks</h2>
            <label className="checkbox-label compact-toggle">
              <input
                type="checkbox"
                checked={includeCancelledTasks}
                onChange={(event) => setIncludeCancelledTasks(event.target.checked)}
              />
              Include Cancelled
            </label>
          </div>
          {!tasks.length ? (
            <EmptyState title="No tasks for this shipment" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Task Title</th>
                    <th>Description</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr key={task.id}>
                      <td><strong>{task.title}</strong></td>
                      <td>{task.description || '-'}</td>
                      <td>
                        <span className={`badge priority-${task.priority}`}>{task.priority}</span>
                      </td>
                      <td>
                        <span className={`badge task-${task.status}`}>{task.status}</span>
                      </td>
                      <td>
                        {canWrite && (
                          <div className="row-actions">
                            {task.status === 'cancelled' ? (
                              <button className="secondary-button" type="button" onClick={() => restoreTask(task)}>
                                <RotateCcw size={16} />
                                <span>Restore</span>
                              </button>
                            ) : (
                              <>
                                <button className="secondary-button" type="button" onClick={() => toggleTask(task)}>
                                  {task.status === 'open' ? <ToggleRight size={16} /> : <RotateCcw size={16} />}
                                  <span>{task.status === 'open' ? 'Done' : 'Reopen'}</span>
                                </button>
                                <button className="secondary-button danger-text" type="button" onClick={() => cancelTask(task)}>
                                  <Ban size={16} />
                                  <span>Cancel</span>
                                </button>
                              </>
                            )}
                            {!task.auto_generated && (
                              <button className="secondary-button danger-text" type="button" onClick={() => setConfirmDeleteTask(task)}>
                                <Trash2 size={16} />
                                <span>Delete</span>
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {activeTab === 'bl' && bl && (
        <section className="panel form-grid">
          <div className="panel-header span-2 no-margin">
            <h2>BL Management</h2>
          </div>
          <label>
            BL Type
            <select value={bl.bl_type || 'Ocean'} disabled={!canWrite} onChange={(event) => setBl({ ...bl, bl_type: event.target.value })}>
              {['OBL', 'HBL', 'Surrender', 'Telex', 'Seaway', 'Ocean'].map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            Draft Received
            <input type="date" value={bl.draft_received || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, draft_received: event.target.value })} />
          </label>
          <label>
            Approval Date
            <input type="date" value={bl.approval_date || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, approval_date: event.target.value })} />
          </label>
          <label>
            Final BL Date
            <input type="date" value={bl.final_bl_date || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, final_bl_date: event.target.value })} />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={bl.surrender_done} disabled={!canWrite} onChange={(event) => setBl({ ...bl, surrender_done: event.target.checked })} />
            Surrender Done
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={bl.telex_release} disabled={!canWrite} onChange={(event) => setBl({ ...bl, telex_release: event.target.checked })} />
            Telex Release
          </label>
          <label className="span-2">
            Final BL Google Drive Link
            <input value={bl.file_url || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, file_url: event.target.value })} placeholder="Paste Google Drive link" />
          </label>
          <label className="span-2">
            Corrections
            <textarea value={bl.corrections || ''} disabled={!canWrite} onChange={(event) => setBl({ ...bl, corrections: event.target.value })} placeholder="Note any BL corrections" />
          </label>
          {canWrite && (
            <div className="form-actions span-2">
              <button className="primary-button" type="button" onClick={saveBl}>
                <Save size={18} />
                <span>Save BL</span>
              </button>
            </div>
          )}
        </section>
      )}

      {activeTab === 'demurrage' && (
        <section className="panel">
          {shipment.type === 'export' ? (
            <EmptyState title="Not applicable" detail="Demurrage tracking is mainly applicable to import shipments." />
          ) : (
            demurrage && (
              <div className="page-stack">
                <div className="form-grid">
                  <label>
                    Free Days Allowed
                    <input type="number" value={demurrage.free_days ?? ''} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, free_days: event.target.value })} />
                  </label>
                  <label>
                    Start Date
                    <input type="date" value={demurrage.start_date || ''} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, start_date: event.target.value })} />
                  </label>
                  <label>
                    Rate Per Day
                    <input type="number" value={demurrage.rate_per_day ?? ''} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, rate_per_day: event.target.value })} />
                  </label>
                  <label>
                    Currency
                    <input value={demurrage.currency || 'INR'} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, currency: event.target.value })} />
                  </label>
                  <label>
                    Alert At Days
                    <input type="number" value={demurrage.alert_at_days ?? 3} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, alert_at_days: event.target.value })} />
                  </label>
                  <label>
                    Container Count
                    <input type="number" value={demurrage.container_count ?? 1} disabled={!canWrite} onChange={(event) => setDemurrage({ ...demurrage, container_count: event.target.value })} />
                  </label>
                  {canWrite && (
                    <div className="form-actions span-2">
                      <button className="primary-button" type="button" onClick={saveDemurrage}>
                        <Save size={18} />
                        <span>Save Demurrage</span>
                      </button>
                    </div>
                  )}
                </div>
                <div
                  className={`demurrage-summary ${
                    demurrage.is_demurrage_running
                      ? 'critical'
                      : demurrage.days_remaining !== null && demurrage.days_remaining <= demurrage.alert_at_days
                        ? 'warning'
                        : ''
                  }`}
                >
                  <InfoItem label="Free Days End Date" value={demurrage.free_days_end_date} />
                  <InfoItem label="Days Used" value={demurrage.days_used} />
                  <InfoItem label="Days Remaining" value={demurrage.days_remaining ?? '-'} />
                  <InfoItem label="Status" value={demurrage.status} />
                  <InfoItem label="Demurrage Running" value={demurrage.is_demurrage_running ? 'Yes' : 'No'} />
                  <InfoItem label="Total Due" value={`${demurrage.currency} ${demurrage.total_demurrage_due}`} />
                </div>
              </div>
            )
          )}
        </section>
      )}

      {activeTab === 'followups' && (
        <section className="page-stack">
          {canWrite && (
            <form className="panel form-grid" onSubmit={createFollowup}>
              <div className="panel-header span-2 no-margin">
                <h2>Log Follow-up</h2>
              </div>
              <label>
                Party
                <select value={followupForm.party_id} onChange={(event) => setFollowupForm({ ...followupForm, party_id: event.target.value })}>
                  <option value="">No party</option>
                  {parties.map((party) => (
                    <option key={party.id} value={party.id}>
                      {party.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Channel
                <select value={followupForm.channel} onChange={(event) => setFollowupForm({ ...followupForm, channel: event.target.value })}>
                  <option value="email">email</option>
                  <option value="call">call</option>
                  <option value="whatsapp">whatsapp</option>
                  <option value="meeting">meeting</option>
                </select>
              </label>
              <label>
                Date
                <input type="date" value={followupForm.date} onChange={(event) => setFollowupForm({ ...followupForm, date: event.target.value })} />
              </label>
              <label>
                Status
                <select value={followupForm.status} onChange={(event) => setFollowupForm({ ...followupForm, status: event.target.value })}>
                  <option value="open">open</option>
                  <option value="closed">closed</option>
                </select>
              </label>
              <label className="span-2">
                Summary <span style={{ color: 'var(--color-danger)' }}>*</span>
                <textarea required value={followupForm.summary} onChange={(event) => setFollowupForm({ ...followupForm, summary: event.target.value })} placeholder="What was discussed or communicated" />
              </label>
              <label className="span-2">
                Next Action
                <textarea value={followupForm.next_action} onChange={(event) => setFollowupForm({ ...followupForm, next_action: event.target.value })} placeholder="What needs to happen next" />
              </label>
              <div className="form-actions span-2">
                <button className="primary-button" type="submit">
                  <Plus size={18} />
                  <span>Add Follow-up</span>
                </button>
              </div>
            </form>
          )}
          <div className="panel">
            <div className="panel-header">
              <h2>Follow-up History</h2>
            </div>
            {!followups.length ? (
              <EmptyState title="No follow-ups yet" />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Party</th>
                      <th>Channel</th>
                      <th>Summary</th>
                      <th>Next Action</th>
                      <th>Status</th>
                      <th>Logged By</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {followups.map((followup) => (
                      <tr key={followup.id}>
                        <td style={{ whiteSpace: 'nowrap' }}>{followup.date}</td>
                        <td>{followup.party?.name || '-'}</td>
                        <td>{followup.channel}</td>
                        <td>{followup.summary}</td>
                        <td>{followup.next_action || '-'}</td>
                        <td>
                          <span className={`badge task-${followup.status === 'open' ? 'open' : 'done'}`}>{followup.status}</span>
                        </td>
                        <td>{followup.logger?.name || followup.logged_by}</td>
                        <td>
                          {canWrite && (
                            <div className="row-actions">
                              <button className="secondary-button" type="button" onClick={() => updateFollowupStatus(followup, followup.status === 'open' ? 'closed' : 'open')}>
                                {followup.status === 'open' ? 'Close' : 'Reopen'}
                              </button>
                              <button className="icon-button danger" type="button" onClick={() => deleteFollowup(followup.id)} title="Delete">
                                <Trash2 size={16} />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {activeTab === 'charges' && (
        <section className="page-stack">
          {pnl && (
            <>
              <div className="metric-grid finance-grid">
                <article className="metric-card">
                  <span>Total Receivable</span>
                  <strong>{formatMoney(pnl.total_receivable, pnl.currency)}</strong>
                </article>
                <article className="metric-card">
                  <span>Total Payable</span>
                  <strong>{formatMoney(pnl.total_payable, pnl.currency)}</strong>
                </article>
                <article className={`metric-card ${Number(pnl.net_profit) < 0 ? 'critical-card' : 'success-card'}`}>
                  <span>Net Profit</span>
                  <strong>{formatMoney(pnl.net_profit, pnl.currency)}</strong>
                </article>
                <article className="metric-card warning-card">
                  <span>Pending Receivable</span>
                  <strong>{formatMoney(pnl.pending_receivable, pnl.currency)}</strong>
                </article>
                <article className="metric-card info-card">
                  <span>Pending Payable</span>
                  <strong>{formatMoney(pnl.pending_payable, pnl.currency)}</strong>
                </article>
              </div>
              {pnl.multiple_currencies && (
                <p className="finance-note">Multiple currencies are present. Totals are not converted automatically.</p>
              )}
            </>
          )}

          {canWrite && (
            <form className="panel form-grid" onSubmit={saveCharge}>
              <div className="panel-header span-2 no-margin">
                <h2>{editingChargeId ? 'Edit Charge' : 'Add Charge'}</h2>
              </div>
              <label>
                Charge Type
                <select value={chargeForm.charge_type} onChange={(event) => updateChargeForm('charge_type', event.target.value)}>
                  {chargeTypeOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Direction
                <select value={chargeForm.direction} onChange={(event) => updateChargeForm('direction', event.target.value)}>
                  <option value="receivable">receivable</option>
                  <option value="payable">payable</option>
                </select>
              </label>
              <label>
                Amount <span style={{ color: 'var(--color-danger)' }}>*</span>
                <input
                  required
                  min="0"
                  step="0.01"
                  type="number"
                  value={chargeForm.amount}
                  onChange={(event) => updateChargeForm('amount', event.target.value)}
                  placeholder="0.00"
                />
              </label>
              <label>
                Currency
                <input value={chargeForm.currency} onChange={(event) => updateChargeForm('currency', event.target.value.toUpperCase())} />
              </label>
              <label>
                Party
                <select value={chargeForm.party_id} onChange={(event) => updateChargeForm('party_id', event.target.value)}>
                  <option value="">No party</option>
                  {parties.map((party) => (
                    <option key={party.id} value={party.id}>
                      {party.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Status
                <select value={chargeForm.status} onChange={(event) => updateChargeForm('status', event.target.value)}>
                  {chargeStatusOptions[chargeForm.direction].map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Invoice No
                <input value={chargeForm.invoice_no} onChange={(event) => updateChargeForm('invoice_no', event.target.value)} placeholder="Invoice number" />
              </label>
              <label>
                Date
                <input type="date" value={chargeForm.date} onChange={(event) => updateChargeForm('date', event.target.value)} />
              </label>
              <label className="span-2">
                Notes
                <textarea value={chargeForm.notes} onChange={(event) => updateChargeForm('notes', event.target.value)} placeholder="Optional notes" />
              </label>
              <div className="form-actions span-2">
                {editingChargeId && (
                  <button className="secondary-button" type="button" onClick={resetChargeForm}>
                    Cancel Edit
                  </button>
                )}
                <button className="primary-button" type="submit">
                  <Save size={18} />
                  <span>{editingChargeId ? 'Save Charge' : 'Add Charge'}</span>
                </button>
              </div>
            </form>
          )}

          <div className="panel">
            <div className="panel-header">
              <h2>Charges</h2>
            </div>
            {!charges.length ? (
              <EmptyState title="No charges for this shipment" />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Direction</th>
                      <th>Amount</th>
                      <th>Party</th>
                      <th>Status</th>
                      <th>Invoice No</th>
                      <th>Date</th>
                      <th>Notes</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {charges.map((charge) => (
                      <tr key={charge.id}>
                        <td>{chargeTypeLabels[charge.charge_type] || charge.charge_type}</td>
                        <td>{charge.direction}</td>
                        <td><strong>{formatMoney(charge.amount, charge.currency)}</strong></td>
                        <td>{charge.party_name || '-'}</td>
                        <td>
                          <span className={`badge charge-${charge.status}`}>{charge.status}</span>
                        </td>
                        <td>{charge.invoice_no || '-'}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>{charge.date || '-'}</td>
                        <td>{charge.notes || '-'}</td>
                        <td>
                          {canWrite && charge.status !== 'cancelled' && (
                            <div className="row-actions">
                              <button className="icon-button" type="button" onClick={() => editCharge(charge)} title="Edit charge">
                                <Edit3 size={16} />
                              </button>
                              {charge.direction === 'payable' && charge.status !== 'paid' && (
                                <button className="secondary-button" type="button" onClick={() => updateChargeStatus(charge, 'paid')}>
                                  <CheckCircle2 size={16} />
                                  <span>Paid</span>
                                </button>
                              )}
                              {charge.direction === 'receivable' && charge.status !== 'received' && (
                                <button className="secondary-button" type="button" onClick={() => updateChargeStatus(charge, 'received')}>
                                  <CheckCircle2 size={16} />
                                  <span>Received</span>
                                </button>
                              )}
                              <button className="secondary-button danger-text" type="button" onClick={() => cancelCharge(charge)}>
                                <Ban size={16} />
                                <span>Cancel</span>
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {activeTab === 'finance' && (
        <ShipmentFinancePanel shipmentId={shipment.id} canWrite={canWrite} />
      )}

      <ConfirmDialog
        open={Boolean(confirmDeleteTask)}
        title="Delete Manual Task"
        message={`Delete "${confirmDeleteTask?.title}" permanently? This cannot be undone.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setConfirmDeleteTask(null)}
        onConfirm={deleteManualTask}
      />
    </div>
  );
}

export default ShipmentDetailPage;
