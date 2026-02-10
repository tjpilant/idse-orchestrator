# Plan: Automated Component Impact Parser

## Strategy
We will implement the parsing logic as a pure standalone module to facilitate testing (`component_impact_parser.py`).
Then, we will update the `ArtifactDatabase` to persist these components as first-class entities.
Finally, we will integrate it into the `NotionDesignStore`'s `save_artifact` method, using the SQLite data to drive the Notion update.

## Tasks

### Phase 1: Parsing Logic
- [ ] Create `src/idse_orchestrator/component_impact_parser.py`.
- [ ] Define `ComponentImpact` dataclass.
- [ ] Implement `parse_component_impact_report(content: str) -> List[ComponentImpact]`.
  - Handle "Modified Components" section.
  - Handle "New Components Created" section.
  - Extract bullets key-values.
- [ ] Create tests `tests/test_component_impact_parser.py` covering various markdown shapes.

### Phase 2: SQLite Integration (Source of Truth)
- [ ] Update `src/idse_orchestrator/artifact_database.py`:
  - Add `components` table to schema in `_ensure_columns`.
  - Implement `save_component(data)` and `get_component(name)`.
- [ ] Add tests in `tests/test_artifact_database.py` for component persistence.

### Phase 3: Notion Sync Integration
- [ ] Add `_sync_to_components_db` method to `NotionDesignStore`.
  - Fetch Primitives map (Name -> PageID).
  - Component lookup/upsert logic.
- [ ] Integrate into `save_artifact`:
  - Detect if stage is `implementation`.
  - Parse content.
  - **Save to SQLite**.
  - Log findings.
  - Call sync method.
- [ ] Add tests in `tests/test_design_store_notion.py` (mocking the Notion calls).

### Phase 4: E2E Verification
- [ ] Create a dummy implementation artifact with a valid report.
- [ ] Run `idse sync push`.
- [ ] Verify components exist in Notion and SQLite.
- [ ] Verify relation to parent primitives is correct.
- [ ] Document in `implementation/README.md`.
