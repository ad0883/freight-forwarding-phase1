# Master 1.1 Known Limitations

## Document Metadata

| Field | Value |
|-------|-------|
| Date | 2026-05-29 |
| Commit Hash | 80b301f |
| Branch | phase-25-master-1-1-completion-certification |
| Scope | Master 1.1 (Phases 1–24) |

---

## Accepted Limitations

These limitations are by design within the Master 1.1 phased scope. They do not represent bugs or missing requirements — they represent features intentionally deferred to future phases.

---

### 1. No Real AIS / Live Vessel Tracking API

**Current State:** Tracking adapters support mock sync and manual observations. Provider infrastructure is ready for real integrations.

**Impact:** Vessel position data requires manual entry or future API integration.

**Mitigation:** Mock sync demonstrates the full pipeline. Real provider integration is a configuration change, not an architecture change.

---

### 2. No Real GPS Provider Integration

**Current State:** Transport location updates are manual. GPS infrastructure (lat/lng, speed, heading) is modeled and ready.

**Impact:** Real-time vehicle tracking requires a GPS provider integration.

**Mitigation:** Manual location updates work. The data model supports future GPS feeds without schema changes.

---

### 3. No ICEGATE / Customs Filing Automation

**Current State:** Customs cases track milestones, checklists, OOC/LEO status, and duty records. Filing is manual.

**Impact:** Users must file customs documents through government portals separately.

**Mitigation:** The system tracks customs status comprehensively. Government API integration is a future enhancement.

---

### 4. No Payment Gateway / Accounting Sync

**Current State:** Finance module tracks receivables, payables, payments, and P&L. Payment recording is manual.

**Impact:** No automatic bank reconciliation or accounting software sync.

**Mitigation:** Full financial tracking is available. Integration with Tally/QuickBooks/bank APIs is a future phase.

---

### 5. No Public Tracking Page

**Current State:** Tracking data is available via authenticated portal endpoints.

**Impact:** External parties without portal accounts cannot view tracking status.

**Mitigation:** Portal accounts can be created for customers. A public tracking page is a future enhancement.

---

### 6. Predictive Intelligence is Deterministic / Rule-Based

**Current State:** Prediction models use rule-based scoring (container age, document completeness, customs status, etc.) rather than trained ML models.

**Impact:** Predictions are based on business rules, not historical pattern learning.

**Mitigation:** The prediction framework supports model versioning and outcome feedback. ML models can replace rule-based models without API changes.

---

### 7. Maps are Placeholder / Readiness-Only

**Current State:** Control tower includes map readiness endpoint. Actual map rendering depends on frontend map library integration.

**Impact:** No visual map display of shipment/container/vehicle positions.

**Mitigation:** Location data (lat/lng) is stored and available. Map visualization is a frontend enhancement.

---

### 8. Enterprise Multi-Org Enforcement is Foundation-Level

**Current State:** Organization model exists with memberships, roles, and permissions. Default organization is created. Admin membership is enforced. However, not all operational tables (shipments, parties, charges, etc.) are fully filtered by `organization_id` in every query.

**Impact:** In a true multi-tenant deployment, additional query scoping would be needed to enforce strict data isolation between organizations.

**Mitigation:** The foundation is in place. Full multi-org query scoping can be added incrementally without schema changes (organization_id columns exist on key tables).

---

### 9. Frontend Bundle Size

**Current State:** The production JS bundle is 530KB (gzipped: 131KB), slightly over Vite's 500KB warning threshold.

**Impact:** Slightly longer initial load on slow connections.

**Mitigation:** Acceptable for an internal pilot. Code splitting with dynamic imports can reduce this in a future optimization pass.

---

### 10. Document OCR Limited to Text-Based PDFs

**Current State:** Document intelligence extracts text from text-based PDFs and TXT/CSV files. Image-based OCR (`DOCUMENT_OCR_IMAGE_ENABLED`) is disabled by default.

**Impact:** Scanned documents (image PDFs) are not automatically processed.

**Mitigation:** The OCR pipeline is ready for image processing. Enabling it requires optional local OCR tooling or a cloud OCR service.

---

## Severity Assessment

| Limitation | Severity | Blocking for Pilot? |
|-----------|----------|-------------------|
| No live vessel API | Low | No |
| No GPS integration | Low | No |
| No ICEGATE automation | Low | No |
| No payment gateway | Low | No |
| No public tracking page | Low | No |
| Rule-based predictions | Low | No |
| Map placeholder | Low | No |
| Multi-org foundation-level | Medium | No (single-org pilot) |
| Bundle size | Low | No |
| Image OCR disabled | Low | No |

---

## Conclusion

All known limitations are acceptable within the Master 1.1 phased scope. None are blocking for an internal pilot deployment. Each limitation has a clear path to resolution in future phases without requiring architectural changes.
