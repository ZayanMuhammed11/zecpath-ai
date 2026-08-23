# Day 55 Decisions — governance_ai

- `governance_ai/` is fully isolated — zero cross-module imports,
  confirmed. It does not import from, and is not imported by,
  decision_ai, interview_ai, screening_ai, ats_engine, scoring,
  technical_ai, machine_test_ai, visual_behavior_ai, integrity_ai,
  final_decision_ai, or hiring_report_ai.
- `AccessRole` is deliberately distinct from any candidate-seniority
  "RoleLevel" concept elsewhere in the platform; no import relationship
  exists between them, and none should ever be introduced. `AccessRole`
  is about platform-user RBAC; the other, unrelated `RoleLevel` concept
  is about candidate seniority.
- No retention-day default was hardcoded anywhere; `retention_days` is
  caller-supplied only, per explicit direction — retention windows are a
  business/legal decision, not an engineering one.
- `ConsentRecord` defines a data shape only; it does not implement or
  claim to implement consent capture, enforcement, or storage. The
  platform's consent implementation gap remains open and is not resolved
  by this module.
- `log_event()` is a pure function with zero persistence; no audit-log
  storage or retrieval layer exists in this codebase yet.
- No encryption of any kind was implemented; there is no persistent data
  store yet for this module to encrypt.
- `datetime.now(timezone.utc)` is used throughout — never
  `datetime.utcnow()`.
- No use of the `random` module anywhere in `governance_ai/`.

## Open ambiguities (explicitly not silently resolved)

- The final, complete list of valid `consent_type` values (beyond the
  illustrative examples "ai_interview", "recording", "data_processing")
  has not been specified. `ConsentRecord.consent_type` is left as a free
  string field rather than an enum, per the spec, until that list is
  finalized elsewhere.
- Whether `AuditLogEntry.data` should have any required sub-shape (as
  opposed to an arbitrary `dict`) was not specified. It is left as a
  generic `dict` here; any event-specific schema is left to future
  callers/modules to define.
- No guidance was given on what should happen if `RetentionPolicy` with
  `retention_days=None` is used anywhere "actionable" (e.g. to actually
  purge data). Since no storage/purge layer exists in this module, this
  is left unresolved and flagged for whoever builds that layer later.
