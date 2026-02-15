# Profiler CLI

The profiler command provides intake, validation, and spec document generation.

## Commands

- `idse profiler intake`
- `idse profiler export-schema --out <path>`

## JSON I/O Workflow (Phase 10.5)

Use JSON answer files to avoid re-answering the full intake when validation fails.

### Save answers before validation

```bash
idse profiler intake --save-answers code-review-agent.json --spec-out agent.spec.md
```

If validation fails, the answers file still exists and can be edited.

### Retry from edited answers

```bash
vim code-review-agent.json
idse profiler intake --from-json code-review-agent.json --spec-out agent.spec.md
```

This skips interactive prompts and reruns validation plus spec generation from the edited JSON.

## Notes

- `--save-answers` writes deterministic JSON (sorted keys, UTF-8).
- `--from-json` validates JSON schema before running enforcement rules.
- `--spec-out` writes complete generated `spec.md` including `## Agent Profile` YAML block.
