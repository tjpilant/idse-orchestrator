# Context

## 1. Environment

- **Product / Project:** IDSE Orchestrator
- **Domain:** Design-time documentation OS / CMS-backed pipeline artifacts
- **Users / Actors:** Maintainers, IDE agents (Claude Code, Codex, Copilot), operators

## 2. Stack

- **Frontend:** None
- **Backend / API:** Python CLI
- **Database / Storage:** SQLite (local), optional Notion/Supabase for remote sync
- **Infrastructure:** Local workspace only
- **Integrations:** Notion MCP (existing), future Supabase backend

## 3. Constraints

- **Scale:** Single-repo scale; artifacts per project likely < 1000 rows
- **Performance:** CLI operations should remain sub-second on common workflows
- **Compliance / Security:** Local file system + local SQLite only; no new auth
- **Team Capabilities:** Python stdlib only (sqlite3)
- **Deadlines:** None fixed; needs safe migration and fallback
- **Legacy Considerations:** Filesystem backend must continue to work

## 4. Risks & Unknowns

- **Technical Risks:** Mapping existing files into DB schema reliably
- **Operational Risks:** Migration process creating partial state or duplicate artifacts
- **Unknowns:** Edge cases with custom artifact structures in existing projects
