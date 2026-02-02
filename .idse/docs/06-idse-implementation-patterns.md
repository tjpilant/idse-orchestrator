# IDSE Implementation Patterns

## Architectural Guidelines
- Direct use of frameworks
- Clear domain boundaries
- Avoid abstraction layering unless justified

## Testing Patterns
- Contract tests first
- Integration tests next
- Unit tests last
- Define a test plan before coding; use `kb/templates/test-plan-template.md` to
  capture objectives, environments, data, and success criteria during the Plan
  stage.

## API Design Patterns
- Consistent naming
- Versioned endpoints
- Clear error contracts

## Database Patterns
- Single representation of truth
- Minimal abstraction over ORM/driver

## Frontend Patterns
- Component-driven design
- State where needed, not everywhere
