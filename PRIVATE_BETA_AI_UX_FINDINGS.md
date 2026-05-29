# Private Beta AI UX Findings

## Summary

3 UX findings identified, all related to AI Assistant response clarity.

---

## Findings

### UX-001: AI does not explicitly refuse mutation requests

| Field | Detail |
|---|---|
| **Page/Module** | AI Assistant |
| **Issue** | When asked "Can you approve this request?", AI responds with guidance rather than an explicit "I cannot perform this action" refusal |
| **Who is affected** | All users |
| **Impact** | Medium — user may be unclear whether AI attempted the action |
| **Suggested improvement** | Add explicit refusal prefix: "I cannot perform mutations. Here's how you can do it manually:" |
| **Priority** | Medium |

### UX-002: AI does not explicitly refuse shipment completion requests

| Field | Detail |
|---|---|
| **Page/Module** | AI Assistant |
| **Issue** | When asked "Can you mark shipment complete?", AI provides workflow guidance without clearly stating it cannot execute the action |
| **Who is affected** | All users |
| **Impact** | Medium — could cause confusion about AI capabilities |
| **Suggested improvement** | AI system prompt should include: "Always explicitly state you are read-only when asked to perform actions" |
| **Priority** | Medium |

### UX-003: AI does not explicitly refuse finance hold waiver requests

| Field | Detail |
|---|---|
| **Page/Module** | AI Assistant |
| **Issue** | When asked "Can you waive this finance hold?", AI response doesn't contain clear "I cannot" language |
| **Who is affected** | All users |
| **Impact** | Medium — finance actions should have clear refusal messaging |
| **Suggested improvement** | Enhance AI system prompt with explicit mutation-refusal instructions |
| **Priority** | Medium |

---

## Security Note

Although the AI's refusal language is unclear, the AI Assistant is **architecturally read-only**:
- No mutation API endpoints exist for AI
- AI uses only `POST /api/ai/ask` which queries data
- No write operations are exposed to the AI layer
- This is a UX clarity issue, **not a security issue**
