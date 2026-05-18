# Vibe Coding Rules

These rules govern all behavior and development process for the Voyager project. Zero exceptions.

---

## 1. NO BULLSHIT

- NO lies, NO guesses, NO invented APIs, NO "it probably works".
- NO mocks, NO placeholders, NO fake functions, NO stubs, NO TODOs.
- NO hype language like "perfect", "flawless", "amazing" unless truly warranted.
- Say EXACTLY what is true. If something might break -> SAY SO.

## 2. CHECK FIRST, CODE SECOND

- ALWAYS review the existing architecture and files BEFORE writing any code.
- ALWAYS request missing files BEFORE touching ANYTHING.
- NEVER assume a file "probably exists". ASK.
- NEVER assume an implementation "likely works". VERIFY.

## 3. NO UNNECESSARY FILES

- Modify existing files unless a new file is absolutely unavoidable.
- NO file-splitting unless justified with evidence.
- Simplicity > complexity.

## 4. REAL IMPLEMENTATIONS ONLY

- Everything must be fully functional production-grade code.
- NO fake returns, NO hardcoded values, NO temporary hacks.
- Test data must be clearly marked as test data.

## 5. DOCUMENTATION = TRUTH

- ALWAYS read documentation when relevant -- PROACTIVELY.
- Use tools (web search, web fetch) to obtain real docs.
- NEVER invent API syntax or behavior.
- Cite documentation: "According to the docs at `<URL>`..."
- If you can't access docs, SAY SO. DO NOT GUESS.

## 6. COMPLETE CONTEXT REQUIRED

- Do NOT modify code without FULL context and flow understanding.
- Must understand:
  - Data flow
  - What calls this code
  - What this code calls
  - Dependencies
  - Architecture links
  - Impact of the change
- If any context is missing -> MUST ASK FIRST.

## 7. REAL DATA & SERVERS ONLY

- Use real data structures when available.
- Request real samples if needed.
- Verify API responses from actual docs or actual servers.
- NO assumptions, NO "expected JSON", NO hallucinated structures.

## 8. API FRAMEWORK POLICY

- **Django/Ninja ONLY**: All API endpoints MUST be implemented with Django + Django Ninja.
- **No FastAPI**: FastAPI/Starlette/uvicorn are prohibited; remove or migrate any remaining FastAPI services.

## 9. UI FRAMEWORK POLICY

- **UI Framework**: ALL UI components MUST use **Lit Web Components** (Lit 3.x).
- **NO Alpine.js**: Alpine.js is DEPRECATED and FORBIDDEN in new code.
- **State Management**: Use Lit Reactive Controllers for state management.
- **Existing Alpine Code**: Must be migrated to Lit Web Components when touched.
- **Component Pattern**: Use custom elements with shadow DOM for encapsulation.

## 10. DATABASE ORM POLICY

- **Django ORM ONLY**: ALL database models MUST use **Django ORM**.
- **NO SQLAlchemy**: SQLAlchemy is FORBIDDEN for new models in this project.
- **Model Location**: Django models go in `apps/<app_name>/models.py` following existing patterns.
- **Reference Pattern**: Use the `TimeStampedModel` from `apps/core/models.py` as the canonical reference.
- **Migrations**: Use Django migrations (`python manage.py makemigrations && python manage.py migrate`), NOT Alembic.
- **Field Types**: Use Django field types: `models.UUIDField`, `models.JSONField`, `models.CharField`, `models.ForeignKey`, etc.
- **Base Models**: All models MUST inherit from `UUIDModel`, `TimeStampedModel`, and `TenantModel` from `apps/core/models.py`.

## 11. CENTRALIZED MESSAGES & I18N

- **NO Hardcoded Strings**: All user-facing text (errors, success messages, notifications) MUST use `apps.common.messages`.
- **Use `get_message`**: Retrieve strings via `get_message(code, **kwargs)`.
- **Error Codes**: Define new error/success codes in `apps/common/messages.py` rather than inline strings.
- **I18N Ready**: Ensure all strings are routable through the message system for future translation.

## 12. FILE SIZE LIMITS

- **Maximum 500 lines per file**.
- Files exceeding 500 lines MUST be split following Django patterns:
  - `views/` directory with `__init__.py` for view functions
  - `services/` directory for business logic
  - `utils/` directory for utility functions
  - `validators/` directory for custom validators
  - `selectors/` directory for query encapsulation
- Split by responsibility, not arbitrarily.

## 13. CODE QUALITY TOOLS

- **Ruff**: All code must pass `ruff check` with zero errors.
- **Black**: All code must be formatted with `black --line-length 100`.
- **Type hints**: All function signatures must have type hints.
- **Docstrings**: Google-style docstrings on all public functions and classes.
- **No `__pycache__`**: Never commit compiled Python files.

## 14. MAXIMUM 500 LINES PER FILE

- NO file may exceed 500 lines.
- Split oversized files using Django subpackage patterns.
- Each split file must have a single, clear responsibility.

---

### I WILL NEVER:

- Invent APIs or syntax
- Guess behavior
- Use placeholders or mocks
- Use shims, use fake, use bypass, use alternate route
- Use alternate not existing routes not in the tasks, roadmap or any files detailing the project
- Hardcode values
- Create new files unnecessarily
- Touch code without full context
- Skip reading documentation
- Assume data structures
- Fake understanding
- Write "TODO", "later", "stub", "temporary"
- Skip error handling
- Say "done" unless COMPLETELY done
- Create a file with more than 500 lines

### I WILL ALWAYS:

- Request missing files
- Verify all information
- Use real servers/data
- Understand complete architecture
- Apply security, performance, UX considerations
- Cite documentation
- Document everything clearly
- Follow all Vibe Coding Rules
- Deliver honest, real, complete solutions
- After every task or milestone, run a second inspection for Vibe Coding Rules violations
- Split any file over 500 lines into properly structured submodules
