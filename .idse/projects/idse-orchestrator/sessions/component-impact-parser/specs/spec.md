# Spec: Component Impact Parser

## 1. Functional Requirements

### 1.1 Parsing
- **Input**: The content of `implementation/README.md`.
- **Target Section**: "Component Impact Report".
- **Sub-sections**: "Modified Components", "New Components Created".
- **Extraction**: Name, Source File, Parent Primitives, Type, Changes.

### 1.2 Validation
- **Mandatory Chain**: Component MUST list Parent Primitive.
- **Rules**: Type must be valid.

### 1.3 Synchronization
- **Trigger**: `idse sync push`.
- **Flow**:
  1. Parse Markdown → `ComponentImpact` objects.
  2. **Persist**: Upsert to SQLite `components` table (Source of Truth).
  3. **Sync**: Push from SQLite to Notion `Components` database (View).

## 2. Technical Architecture

### 2.1 Data Structures
```python
@dataclass
class ComponentImpact:
    name: str
    source_file: Optional[str]
    parent_primitives: List[str]
    type: Optional[str]
    idse_id: str  # Calculated hash or unique ID
    changes: List[str]
    is_new: bool
    last_session_id: str
```

### 2.2 SQLite Schema (New)
Table: `components`
- `id` (PK, Integer)
- `name` (Text, Unique)
- `type` (Text)
- `source_file` (Text)
- `parent_primitives` (Text - JSON list)
- `last_seen_in_session` (Text)
- `last_updated_at` (Datetime)

### 2.3 ComponentImpactParser
- Located in: `src/idse_orchestrator/component_impact_parser.py`

### 2.4 Integration
- `NotionDesignStore` calls Parser → `ArtifactDatabase` → `_sync_components_to_notion`.

