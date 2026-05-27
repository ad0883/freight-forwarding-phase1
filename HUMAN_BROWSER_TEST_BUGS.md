# Human Browser Test Bugs

## Latest Result

The final headed Playwright run passed:

```text
13 passed (18.4s)
```

## Issues Found During Setup

- Desktop shipment navigation test initially used a broad `/shipments/i` link selector and collided with dashboard links such as "Open shipments" and "View shipments". Fixed by selecting the exact sidebar link name.
- Document intelligence verification initially used a broad text matcher that matched multiple elements. Fixed by scoping the assertion to `.document-intelligence-panel`.
- The mobile sidebar test exposed pointer interception with Playwright phone emulation. The e2e mobile project now uses a narrow Chromium viewport, and the mobile menu toggle has a stronger stacking context.
