# Master 1.1 Pilot UX Issues

## Summary

UX friction points discovered during the internal pilot. These affect usability but not correctness.

---

## UX-001: Slow First AI Response

- **Area:** AI Assistant
- **Severity:** Low
- **Issue:** First AI query takes ~22 seconds (Groq cold start). No loading feedback at API level.
- **Impact:** User thinks the system is broken on first AI interaction
- **Recommendation:** Frontend should show "AI is thinking..." indicator. Consider pre-warming.

## UX-002: Control Tower Load Time

- **Area:** Control Tower
- **Severity:** Low
- **Issue:** Control tower summary takes 7+ seconds to load
- **Impact:** Dashboard feels sluggish
- **Recommendation:** Add skeleton loading states; consider caching with TTL

## UX-003: Tracking Sync Duration

- **Area:** Tracking
- **Severity:** Low
- **Issue:** Mock tracking sync takes ~30 seconds
- **Impact:** User waits with no progress feedback
- **Recommendation:** Make sync async with status polling, or add progress indicator

## UX-004: Prediction Run Duration

- **Area:** Predictive Intelligence
- **Severity:** Low
- **Issue:** Prediction run takes ~6 seconds per shipment
- **Impact:** Acceptable for single shipment, but would be slow for batch
- **Recommendation:** Consider background processing for batch predictions

## UX-005: Party List Load Time

- **Area:** Parties
- **Severity:** Low
- **Issue:** Party list takes ~700ms (with existing data)
- **Impact:** Noticeable but acceptable
- **Recommendation:** Add pagination if party count grows large

## UX-006: Shipment Creation Slow (7s)

- **Area:** Shipments
- **Severity:** Low
- **Issue:** Creating a shipment takes ~7 seconds (includes workflow seeding, event recording, audit logging)
- **Impact:** User waits after clicking "Create"
- **Recommendation:** Optimize or defer non-critical operations (audit, events) to background

## UX-007: No Inline Validation Errors

- **Area:** All Forms (API level)
- **Severity:** Low
- **Issue:** 422 errors return Pydantic validation details but field-level error mapping depends on frontend implementation
- **Impact:** Users may not understand which field is wrong
- **Recommendation:** Ensure frontend maps Pydantic error locations to form fields

---

## Browser QA Status

**NOT PERFORMED** — Playwright is configured but full browser QA was not run during this pilot session. The frontend builds successfully and Playwright has chromium + mobile-chromium projects configured.

Reason: Pilot focused on API-level testing. Browser QA requires running the frontend dev server and executing Playwright tests against it.

**Recommendation:** Run `npx playwright test` as part of the next pilot iteration.
