# Agency Swarm Framework Constitution
**Framework-Specific Governance for Agency Swarm v1.0.0 Projects**

⚠️ **Prerequisites**: This constitution **extends** the IDSE Constitution (Articles I-X).
Read `.idse/governance/IDSE_CONSTITUTION.md` first for universal project governance.

---

## Authority and Scope

This constitution applies **only to projects building AI agent systems** using the **Agency Swarm v1.0.0** framework.

For universal project governance (session management, pipeline stages, validation), see IDSE Constitution.

---

## Article AS-I: Framework Background

Agency Swarm is an open-source framework designed for orchestrating and managing multiple AI agents, built upon the OpenAI Assistants API. Its primary purpose is to facilitate the creation of "AI agencies" or "swarms" where multiple AI agents with distinct roles and capabilities can collaborate to automate complex workflows and tasks.

**Documentation**: https://agency-swarm.ai

### Communication Flow Patterns

In Agency Swarm, communication flows are directional and explicit. Common patterns:

#### Orchestrator-Workers (Most Common)
```python
from agency_swarm import Agency

agency = Agency(
    ceo,  # Entry point for user communication
    communication_flows=[
        (ceo, worker1),
        (ceo, worker2),
        (ceo, worker3),
    ],
    shared_instructions="agency_manifesto.md",
)
```

#### Sequential Pipeline (handoffs)
```python
from agency_swarm.tools.send_message import SendMessageHandoff

agent1 = Agent(..., send_message_tool_class=SendMessageHandoff)
agent2 = Agent(..., send_message_tool_class=SendMessageHandoff)

agency = Agency(
    agent1,
    communication_flows=[
        (agent1, agent2),
        (agent2, agent3),
    ],
    shared_instructions="agency_manifesto.md",
)
```

#### Collaborative Network
```python
agency = Agency(
    ceo,
    communication_flows=[
        (ceo, developer),
        (ceo, designer),
        (developer, designer),
    ],
    shared_instructions="agency_manifesto.md",
)
```

---

## Article AS-II: Agent Structure Requirements

### Realistic Agent Roles
Agents MUST be modeled after actual job positions, not task-specific roles:
- ✅ **Good**: "Data Analyst", "Campaign Manager", "Financial Advisor"
- ❌ **Bad**: "Chart Creator", "Email Sender", "Report Generator"

### Minimize Agent Count
Start with **1 agent**. Only add more if:
1. User explicitly requests multiple agents, OR
2. Absolutely necessary for the use case

**Rationale**: Over-engineering with too many agents increases complexity and reduces reliability.

### Role Consolidation
If agents always work together sequentially, they should probably be **one agent**.

---

## Article AS-III: Development Workflow

Agents MUST be developed in this strict order:

### Step 0: Setup
1. Create a to-do list using TodoWrite tool
2. Verify virtual environment is activated:
```bash
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
```

⚠️ **CRITICAL**: Do NOT start coding until venv is activated.

### Step 1: Project Exploration
1. Check root directory structure
2. Look for PRD (`prd.txt`)
3. Check for example agents to remove (`example_agent/`, `example_agent2/`)
4. Review existing files (`agency.py`, `shared_instructions.md`, etc.)
5. Verify API keys in `.env` file

### Step 2: Folder Structure Creation
Use CLI command to create agent templates:
```bash
agency-swarm create-agent-template \
  --description "Description of the agent" \
  --model "gpt-5.1" \
  --reasoning "medium" \
  "agent_name"
```

**Expected folder structure**:
```
├── agent_name/
│   ├── __init__.py
│   ├── agent_name.py
│   ├── instructions.md
│   ├── files/
│   └── tools/
│       ├── ToolName.py
│       └── ...
├── agency.py
├── shared_instructions.md
├── requirements.txt
└── .env
```

**Rules**:
- Agency folder must be lowercase with underscores
- Tool files must match class names (`ToolName.py` contains `class ToolName`)
- Tools are automatically imported from `tools/` folder
- All dependencies go in `requirements.txt`

### Step 3: Tool Development
See Article AS-IV (Tool Requirements) for detailed standards.

**Order of preference**:
1. MCP servers (highest priority)
2. Built-in tools (WebSearchTool, ImageGenerationTool)
3. Custom tools (only if no MCP/built-in exists)

### Step 4: Instructions Writing
Create `instructions.md` following Article AS-V (Instructions Standards).

### Step 5: Agency Creation
Create `agency.py` with communication flows (Article AS-VI).

### Step 6: Testing
**MANDATORY before declaring complete**:
1. Test each tool individually: `python agent_name/tools/tool_name.py`
2. Test agency: `python -c "from agency import create_agency; agency = create_agency; print(agency.get_response_sync('test query'))"`
3. Verify no errors in terminal
4. Confirm all API keys configured

### Step 7: Iteration
Repeat Steps 3-6 until agency performs consistently to user's satisfaction.

**Do NOT ask for confirmation or wait between iterations**—keep testing and fixing.

---

## Article AS-IV: Tool Requirements

### Tool Characteristics
All tools MUST be:
- **Standalone**: Run independently with minimal dependencies on other tools
- **Configurable**: Expose adjustable parameters (modes, thresholds, timeouts, limits)
- **Composable**: Output format matches input format of other tools where possible

### MCP Server Priority (CRITICAL)

**ALWAYS** search for MCP servers **BEFORE** writing custom tools.

If functionality exists in an MCP server, use it instead of custom code.

**Example**:
```python
from agents.mcp import MCPServerStdio

filesystem_server = MCPServerStdio(
    name="Filesystem_Server",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
    },
    cache_tools_list=True  # Required for performance
)

# Attach to agent:
my_agent = Agent(..., mcp_servers=[filesystem_server])
```

**Search Resources**:
- MCP Server Registry: Use web search to find MCP servers
- Agency Swarm docs: https://agency-swarm.ai/core-framework/tools/mcp-integration

### Custom Tool Template

Only create custom tools when **no MCP server or built-in tool exists**.

```python
from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv

load_dotenv()  # ALWAYS load environment variables

class MyCustomTool(BaseTool):
    """
    Clear, concise description of what this tool does.
    This docstring is used by the agent to determine when to use this tool.
    Be specific about the tool's purpose and expected inputs/outputs.
    """

    # Define fields with descriptions for the agent
    example_field: str = Field(
        ...,
        description="Description of this field for the agent. Explain what format is expected."
    )

    def run(self):
        """
        Implementation of the tool's main functionality.
        This method should utilize the fields defined above.
        """
        # NEVER hardcode API keys—always use environment variables
        api_key = os.getenv("MY_API_KEY")

        if not api_key:
            return "Error: MY_API_KEY not found in environment variables"

        # Your tool logic here
        # Use self.example_field to access the input

        return "Result as a string"

# ALWAYS include a test case
if __name__ == "__main__":
    tool = MyCustomTool(example_field="test value")
    print(tool.run())
```

### Tool Best Practices

**DO**:
- ✅ Perform real-world actions: "FetchInstagramLeads", "SendSlackMessage", "QueryDatabase"
- ✅ Include step-by-step comments: `# Step 1: Validate input`, `# Step 2: Call API`
- ✅ Write production-ready code (no placeholders like `# TODO` or `pass`)
- ✅ Retrieve API keys from environment: `os.getenv("API_KEY")`
- ✅ Use global constants: `ACCOUNT_ID = "12345"` above class definition
- ✅ Include test case in `if __name__ == "__main__":`
- ✅ Keep tools single-purpose (let agents combine them)

**DON'T**:
- ❌ Create abstract tools: "OptimizeText", "AnalyzeData", "MakeDecision"
- ❌ Include API keys as tool inputs/fields
- ❌ Return massive data (b64 images, large files—causes context overflow)
- ❌ Embed complex analysis logic inside tools (let agents do the thinking)
- ❌ Use hypothetical examples or mock data

### Agency Context (Shared State)

For sharing data between tools without passing through conversation:

```python
from agency_swarm.tools import BaseTool
from pydantic import Field

class MyTool(BaseTool):
    value: str = Field(..., description="Value to store in shared context")

    def run(self):
        # Store data in context
        self._context.set("my_key", self.value)

        # Retrieve data from context
        data = self._context.get("my_key", "default_value")

        return f"Stored and retrieved: {data}"
```

**Use agency context for**:
- Large data structures expensive to pass in messages
- State that persists across multiple tool calls
- Data shared among multiple tools/agents

**Best practices**:
- Use descriptive keys to avoid conflicts
- Always provide default values in `get()`
- Clean up unneeded data to keep context small

---

## Article AS-V: Instructions Standards

Each agent MUST have an `instructions.md` file following this structure:

### Template Structure

```markdown
# Role
You are **[insert role, e.g., "a Data Analyst" or "a Campaign Manager"]**

# Goals
- **[High-level business goal, e.g., "Increase sales by 10%"]**
- **[Additional goals as needed]**

# Process

## [Task Name 1]
1. [Step-by-step numbered instructions]
2. [Be specific about tool usage]
3. [Include expected outputs]

## [Task Name 2]
1. [More numbered steps]
2. [Reference tools explicitly]

# Output Format
- **[Specify exact format, e.g., "JSON with keys: name, email, score"]**
- **[Provide examples if helpful]**

# Output Format
- **[Specify exact format, e.g., "JSON with keys: name, email, score"]**
- **[Provide examples if helpful]**

# Additional Notes
- **[Any additional context that doesn't fit above]**
- **[Leave blank if none]**
```

### Instructions Best Practices

**DO**:
- ✅ Use concise, verb-driven instructions ("Fetch data", "Analyze results")
- ✅ Be specific about outputs and formats
- ✅ Provide concrete examples of expected behavior
- ✅ Use positive phrasing ("Do this" not "Don't do that")
- ✅ Show exactly when and how to use each tool in workflow
- ✅ Specify exact output schemas (JSON structure, markdown format, etc.)

**DON'T**:
- ❌ Make unsupported assumptions or guesses
- ❌ Repeat the same information in multiple sections
- ❌ Add unnecessary instructions before testing (start simple, iterate)

**Iteration Strategy**:
- Start with minimal instructions
- Test the agent
- Add specific guidance only where agent fails
- Make smallest change possible to fix behavior

---

## Article AS-VI: Agency Creation Standards

### Agency Structure

```python
from dotenv import load_dotenv
from agency_swarm import Agency
from ceo import ceo
from developer import developer
from virtual_assistant import virtual_assistant

load_dotenv()

# REQUIRED: Export create_agency method for deployment
def create_agency(load_threads_callback=None):
    agency = Agency(
        ceo,  # Entry point for user communication
        communication_flows=[
            (ceo, developer),
            (ceo, virtual_assistant),
            (developer, virtual_assistant),
        ],
        shared_instructions="shared_instructions.md",
    )
    return agency

if __name__ == "__main__":
    agency = create_agency()
    agency.terminal_demo()

    # For single-query testing:
    # print(agency.get_response_sync("your test question here"))
```

### Communication Flows

- **Directional**: Agent on left can initiate conversations with agent on right
- **Entry point**: First argument to `Agency()` is where users send messages
- **Bi-directional**: Add both `(a, b)` and `(b, a)` if agents need to talk both ways

### Shared Instructions

`shared_instructions.md` contains agency-wide context:

```markdown
# Background

[Information about the business, industry, target audience, environment]

## Company Information
[Company name, mission, values]

## Target Audience
[ICP, user personas, customer characteristics]

## Environment
[Tech stack, constraints, integrations]
```

**If user hasn't provided info**: Create template with headings, leave content blank for user to fill in.

---

## Article AS-VII: Testing Requirements

### Mandatory Pre-Completion Checklist

Before declaring an agency complete, ALL of these MUST pass:

1. ✅ **Individual tool tests**
   ```bash
   python agent_name/tools/tool_name.py
   ```
   Every tool must execute without errors.

2. ✅ **Agency response test**
   ```bash
   python -c "from agency import create_agency; agency = create_agency(); print(agency.get_response_sync('test query'))"
   ```
   Agency must return a valid response.

3. ✅ **No terminal errors**
   No exceptions, warnings, or error messages in output.

4. ✅ **API keys configured**
   All required keys present in `.env` file.

5. ✅ **Dependencies installed**
   ```bash
   pip install -r requirements.txt
   ```
   All packages available in venv.

**NEVER stop at testing step until all checks pass.**

**Do NOT ask user for confirmation**—keep iterating until tests pass.

---

## Article AS-VIII: Environment Management

### Virtual Environment (CRITICAL)

**ALWAYS verify venv is active before running any Python code.**

```bash
# Check current interpreter
which python  # Should show: /path/to/.venv/bin/python

# If not in venv, activate
source .venv/bin/activate

# If venv doesn't exist, create it
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Common Environment Issues

**Agency hangs when running**:
- **Cause**: Using system Python instead of venv Python
- **Fix**: `source .venv/bin/activate` before running

**Import errors**:
- **Cause**: Dependencies not installed in venv
- **Fix**: `source .venv/bin/activate && pip install -r requirements.txt`

**MCP tools not loading**:
- **Cause**: Missing `cache_tools_list=True` flag
- **Fix**: Add flag to MCP server initialization

**OAuth timeouts**:
- **Cause**: Default timeout too short
- **Fix**: Set `client_session_timeout_seconds=30` or higher

---

## Article AS-IX: File Creation Policy

1. **NEVER output code snippets in chat**—always create/modify actual files in filesystem
2. **NEVER create files with placeholders**—all code must be production-ready
3. **Test all tools before submitting work**
4. **Follow file creation order**: template → tools → instructions → agency → test
5. **Create to-do list before starting** (use TodoWrite tool)
6. **Verify venv activation** before coding

---

## Article AS-X: Model Requirements

- **Default model**: `gpt-5.1` (latest from OpenAI)
- **Alternative**: `gpt-4.1` if `gpt-5.1` unavailable for your account
- **Verify models**: https://platform.openai.com/docs/models

**In agent template creation**:
```bash
agency-swarm create-agent-template --model "gpt-5.1" --reasoning "medium" "agent_name"
```

---

## Article AS-XI: Orchestration Responsibilities

When acting as **Agency Builder** (coordinating sub-agents to build agencies):

### Core Responsibilities

1. **User Clarification**: Ask questions **one at a time** when idea is vague
2. **Research Delegation**: Launch api-researcher to find MCP servers/APIs
3. **Documentation Management**: Fetch Agency Swarm docs if needed
4. **Parallel Agent Creation**: Launch agent-creator, tools-creator, instructions-writer **simultaneously**
5. **API Key Collection**: **ALWAYS** ask for API keys **before** testing
6. **Issue Escalation**: Relay sub-agent errors/blockers to user
7. **Test Result Routing**: Pass test failures to relevant sub-agents for fixes
8. **Communication Flow Decisions**: Determine agent-to-agent communication patterns
9. **Workflow Updates**: Update workflow documentation when discovering improvements

### Available Sub-Agents

- **api-researcher**: Researches MCP servers and APIs, saves docs locally
- **prd-creator**: Transforms concepts into PRDs using saved API docs
- **agent-creator**: Creates complete agent modules with folder structure
- **tools-creator**: Implements tools prioritizing MCP servers over custom APIs
- **instructions-writer**: Writes optimized instructions using prompt engineering best practices
- **qa-tester**: Tests agents with actual interactions and tool validation

### Orchestration Workflows

#### When user has vague idea:
1. Ask clarifying questions (core purpose, user interactions, APIs needed)
2. **WAIT FOR USER FEEDBACK**
3. Launch api-researcher → saves to `agency_name/api_docs.md`
4. Launch prd-creator → returns PRD path
5. **Present PRD to user for confirmation**
6. **Collect all API keys BEFORE development**
7. **Phased execution**:
   - Phase 1 (parallel): agent-creator + instructions-writer
   - Phase 2 (after Phase 1): tools-creator
8. Launch qa-tester → returns test results
9. Iterate based on qa-tester suggestions
10. Re-test until all queries pass

#### When user has detailed specs:
1. Launch api-researcher if APIs mentioned
2. Create PRD from specs
3. **Get user confirmation**
4. **Collect API keys upfront**
5. Phased execution (Phase 1 → Phase 2)
6. Launch qa-tester
7. Iterate until tests pass

#### When adding agent to existing agency:
1. Update PRD with new agent specs
2. **Get user confirmation**
3. Research new APIs if needed
4. **Collect new API keys**
5. Phased execution for new agent
6. Update `agency.py` communication flows
7. Launch qa-tester for integration validation

#### When refining existing agency:
1. Launch qa-tester
2. Prioritize top issues from results
3. Delegate fixes to relevant sub-agents
4. Re-test to verify improvements
5. Document improvement metrics

### Key Patterns

- **Phased Execution**: Never run tools-creator until agent-creator + instructions-writer complete
- **PRD Confirmation**: Always get user approval before development
- **API Keys First**: Collect ALL keys before any tool development
- **File Ownership**: Each sub-agent owns specific files (prevents conflicts)
- **MCP Priority**: Always prefer MCP servers over custom tools
- **Tool Testing**: tools-creator tests each tool individually
- **QA Testing**: qa-tester sends 5 example queries minimum
- **Iteration**: Use qa-tester feedback to improve (never guess at fixes)
- **Progress Tracking**: Use TodoWrite extensively

---

## Article AS-XII: Detailed Workflow Reference

For step-by-step implementation details, see:

- `.cursor/rules/workflow.mdc` - Complete agent creation workflow
- `.cursor/commands/add-mcp.md` - MCP server integration guide
- `.cursor/commands/write-instructions.md` - Instruction writing best practices
- `.cursor/commands/create-prd.md` - PRD creation for complex systems

---

## Relationship to IDSE Constitution

This constitution **extends** the IDSE Constitution:

- **IDSE Constitution** (`.idse/governance/IDSE_CONSTITUTION.md`) governs:
  - Project structure (Intent → Context → Spec → Plan → Tasks → Implementation → Feedback)
  - Session management
  - Validation requirements
  - Constitutional compliance

- **Agency Swarm Constitution** (this document) governs:
  - How to build agents, tools, and agencies
  - Framework-specific patterns and best practices
  - Testing and quality requirements

### Precedence Rules

1. For **project structure and session management**: IDSE Constitution takes precedence
2. For **Agency Swarm implementation details**: This constitution takes precedence
3. When in conflict: Escalate to user for clarification

---

## Governance Layer Boundary

⚠️ **CRITICAL**: This constitution applies to **application code** (agents, tools, agencies).

For **IDE-level coordination** (Claude ↔ Codex handoffs), see:
- `idse-governance/protocols/handoff_protocol.md`
- `idse-governance/state/state.json`
- `.cursor/tasks/governance.py`

**Never write governance artifacts into application code directories** (`idse_developer_agent/`, `src/`, `backend/`, etc.).

**Never write application code into governance directories** (`idse-governance/`, `.idse/governance/`).

---

*Last updated: 2026-01-10*
*Framework: Agency Swarm v1.0.0*
*Extends: IDSE Constitution Articles I-X*
*Authority: `.idse/governance/IDSE_CONSTITUTION.md` Article I (Intentionality)*
