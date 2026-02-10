# Context

## 1. Environment
- **Product**: IDSE Orchestrator CLI.
- **Domain**: Developer Tooling / Design System Management.
- **Users**: Developers running `idse sync push`.

## 2. Stack
- **Language**: Python 3.
- **Libraries**:
  - `markdown-it-py` (if available, else regex). Existing `FileViewGenerator` uses regex.
  - `NotionDesignStore` for API interactions.
  - `ArtifactDatabase` for local state.

## 3. Constraints
- **Execution Context**: Runs synchronously during `idse sync push`.
- **Latency**: Must not add significant delay (seconds, not minutes).
- **Format**: The `implementation/README.md` format is specified in templates but human-edited. Parser must be robust or fail gracefully.
- **Auth**: Uses existing Notion credentials via MCP or direct API config.

## 4. Risks & Unknowns
- **Markdown Variability**: Users might vary casing, spacing, or heading levels (`###` vs `####`).
- **Ambiguous References**: A component might reference a Primitive that doesn't exist or is misspelt.
- **Conflict Resolution**: What if the Component Impact Report contradicts the actual Notion state? (We assume the Report is the intent to update).
- **API Limits**: Batch updating many components might hit Notion rate limits if not efficient.
