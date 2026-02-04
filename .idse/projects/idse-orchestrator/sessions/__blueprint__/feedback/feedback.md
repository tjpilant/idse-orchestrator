# Feedback

## External / Internal Feedback
- TODO: Summarize feedback received (who, what, when)

## Impacted Artifacts
- Intent: TODO (yes/no/sections)
- Context: TODO
- Spec: TODO
- Plan / Test Plan: TODO
- Tasks / Implementation: TODO

## Risks / Issues Raised
- TODO

## Actions / Follow-ups
- TODO: Owner, due date, status

## Decision Log
- TODO: Decisions made and rationale

## Lessons Learned (Verbose)

1) **Notion MCP tool schemas are strict and vary by tool name.**  
   `notion-query-database-view` requires `view_url`, and the accepted format was `view://<dashed-uuid>`. HTTPS view URLs failed.

2) **Database ID vs Data Source ID matters.**  
   For `notion-create-pages`, the correct parent is `parent: { type: "database_id" }` (not `data_source_id`) for this database.

3) **Select values are case-sensitive.**  
   Stage values must match the exact Notion select options. We normalized `intent → Intent`, `spec → Specification`, `implementation → Test Plan`.

4) **Content handling is tool-specific.**  
   `notion-create-pages` accepts a `content` string in Notion Markdown.  
   `notion-update-page` requires `data.command` with `replace_content`.

5) **Visibility depends on view filters.**  
   Pages can exist but be hidden by view filters. Always confirm via raw page URLs returned by MCP.

6) **Debug mode was essential.**  
   Logging payloads and results exposed misaligned schemas and wrong parent types quickly.
