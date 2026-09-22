# Human approval requests

SAALCO has not approved these files. A human should review them in order and run `saalco approve` only after the content is acceptable.

- `docs/features/F-001_saalco-v1/10-requirements.md` — H1: confirm that REQ-0001 represents the intended v1.0 product scope.
- `docs/features/F-001_saalco-v1/20-architecture.md` — H2: confirm the CLI/domain-module separation and architecture direction.
- `docs/features/F-001_saalco-v1/00-meta.md` — H3: confirm that Tier L is appropriate for SAALCO v1.0.
- `docs/features/F-001_saalco-v1/30-detailed-design.md` — H3: confirm detailed design and verification methods before treating implementation as conforming.
- `docs/features/F-001_saalco-v1/35-module-design.md` — H3: confirm module responsibilities and boundaries required by Tier L.

The generated test specifications remain draft inputs to that review. Existing automated tests are deliberately marked `impl_aware`; after approval, Specification-derived Tests must be authored from the approved documents and public interfaces in an independent context.
