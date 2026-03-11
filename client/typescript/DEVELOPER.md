# TypeScript Client — Developer Guide

Development reference for the `client/typescript` package.

## Prerequisites

- **Node.js** ≥ 18
- **npm** (ships with Node.js)

## Setup

```bash
cd client/typescript
npm install
```

## Project Structure

```
client/typescript/
├── src/
│   ├── index.ts          # Public API exports
│   ├── client.ts         # MaestroClient — main HTTP client class
│   ├── commands.ts       # Step builders (tapOn, inputText, swipe, …)
│   ├── models.ts         # Data models (ElementSelector, ExecutionResult, DeviceInfo)
│   └── exceptions.ts     # Error classes (MaestroError, SessionError, StepError)
├── tests/
│   ├── setup.ts          # Shared test harness — auto-starts maestro-runner server
│   ├── pages/            # Page Object Model base + page classes
│   │   ├── BasePage.ts
│   │   ├── ContactListPage.ts
│   │   └── EditContactPage.ts
│   └── *.test.ts         # Test files
├── eslint.config.mjs     # ESLint v9 flat config
├── tsconfig.json         # TypeScript compiler options
├── jest.config.js        # Jest config (ts-jest preset)
└── package.json
```

## Build

```bash
npm run build        # Compiles src/ → dist/ via tsc
```

Output goes to `dist/` with declarations (`.d.ts`), declaration maps, and source maps.

## Lint

ESLint is configured with `typescript-eslint` in flat-config format (`eslint.config.mjs`).

```bash
npm run lint         # Check for issues
npm run lint:fix     # Auto-fix what's possible
```

### Key Rules

| Rule | Scope | Behavior |
|------|-------|----------|
| `consistent-type-imports` | `src/` | Enforces `import type` for type-only imports |
| `no-explicit-any` | `src/` warn, `tests/` off | Discourages `any` in production code |
| `no-unused-vars` | all | Errors; `_`-prefixed names are ignored |
| `eqeqeq` | all | Strict equality required (`!= null` exempted) |
| `no-console` | `src/` warn, `tests/` off | Prevents accidental console logs in library code |
| `curly` | all | Braces required for multi-line blocks |

## Test

Tests use **Jest** with **ts-jest** and run against a live maestro-runner server.

```bash
# Run all tests (requires emulator + server)
npm test

# Run E2E tests only
npm run test:e2e

# Run a specific test file
npx jest tests/test_add_contact.test.ts
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAESTRO_SERVER_URL` | `http://localhost:9999` | Server URL |
| `MAESTRO_PLATFORM` | `android` | Target platform (`android` / `ios`) |
| `MAESTRO_RUNNER_BIN` | `../../maestro-runner` | Path to maestro-runner binary |

The test setup (`tests/setup.ts`) auto-starts the maestro-runner server if it isn't already running.

### Test Reports And Server Traces

Jest writes test reports under `client/typescript/reports/`:

```
reports/report.html
reports/junit-report.xml
```

The setup harness also persists worker-aware server logs for analysis:

```
reports/server-run-<YYYYMMDD-HHMMSS>-<worker>.log
reports/server-latest.json
reports/jest-run-<runId>.log
reports/artifact-summary-<runId>.json
```

- `server-run-...log` is the canonical server stdout/stderr log for that worker run.
- `server-latest.json` maps each worker id to its latest run metadata and log path.
- `jest-run-...log` records worker and node-aware test harness events for correlation.
- `artifact-summary-...json` captures artifact paths/sizes and includes tail snippets for quick triage.
- Appium-style trace lines are emitted in server logs as `[TRACE]` entries, including request/response step, status, and duration.

## Code Conventions

### Architecture

The client follows a thin layered design:

1. **`commands.ts`** — Pure functions that build step JSON payloads (`Record<string, unknown>`)
2. **`client.ts`** — `MaestroClient` wraps HTTP calls to the REST API; each high-level method delegates to a command builder then calls `executeStep()`
3. **`models.ts`** — Typed classes (`ElementSelector`, `ExecutionResult`, `DeviceInfo`) with `fromDict()` / `toDict()` for JSON serialization
4. **`exceptions.ts`** — Error hierarchy (`MaestroError` → `SessionError` / `StepError`)

### Adding a New Command

1. Add a builder function in `src/commands.ts`:

```ts
export function myCommand(arg: string, label?: string): Step {
  const step: Step = { type: "myCommand", arg };
  if (label != null) step.label = label;
  return step;
}
```

2. Add a convenience method in `src/client.ts`:

```ts
async myCommand(arg: string, label?: string): Promise<ExecutionResult> {
  return this.exec(commands.myCommand(arg, label));
}
```

3. Export any new public types from `src/index.ts`.

### Page Object Model (Tests)

Tests use the Page Object pattern to keep test logic decoupled from selectors:

- **`BasePage`** — common helpers (`waitForAnimation`, `hideKeyboard`)
- Concrete pages extend `BasePage` and expose domain actions (e.g., `contactList.openCreateContact()`)
- Tests compose page methods; they never call `client.tap()` directly

### Type-Only Imports

ESLint enforces `import type` for imports used only in type positions:

```ts
// ✓ correct
import type { ElementSelector } from "./models";

// ✗ will fail lint
import { ElementSelector } from "./models";  // if only used as a type
```
