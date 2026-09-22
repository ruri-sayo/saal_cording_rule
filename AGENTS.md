# SAAL development instructions

- `docs/rules/SAAL-DEV-RULES.md` is normative; `saal` and `saalco` are aliases.
- Do not modify `docs/input/`. Write derived artifacts under `docs/features/`.
- Never allocate IDs manually; use `saalco new`.
- Only a human may run `saalco approve`. Stop and request approval with exact paths.
- Agents must not mark `70-acceptance.md` accepted or PASS.
- Create and obtain approval for Tier-required design/test specs before implementation.
- Specification-derived tests use only upstream documents and public interfaces; otherwise mark `impl_aware`.
- Obtain H4 approval before dependency changes or undesigned external I/O/persistence/device effects.
- Record implementation/design differences in `45-implementation-diff.md`.
- Run `saalco check` before claiming completion; commit all changes before Evidence.
- Never falsify markers, verification, or status to pass; record deviations with `saalco new dev`.
