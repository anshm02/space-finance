# AGENTS.md

Space Money is a financial discipline app for young professionals (25-35) in UAE/GCC. It transforms raw transaction data into actionable guidance through automated categorization, behavioral analysis, and timely interventions.

**Goal**: Help users save AED 500-1500/month through subscription cleanup, spending fixes, and budget management.

## Tech Stack

**Backend**: Python 3.11+, FastAPI, bcrypt, OAuth 2.0, boto3, Lean Technologies REST API  
**Mobile**: React Native 5.x+, TypeScript, Google/Facebook OAuth, geolocation, Lean Link SDK, Firebase/Notifee  
**Database**: PostgreSQL 15+ with two schemas:
- `transactions` - PII and sensitive financial data
- `derived_data` - Analytics, aggregates, KPIs

**Storage**: AWS S3 me-central-1 (Abu Dhabi) with SSE-KMS encryption

## Project Structure
```
space-money/
├── backend/              # Python FastAPI services
├── mobile/               # React Native app
│   └── features/         # Feature-based folders
│       └── [name]/       # Each feature contains:
│           ├── components/
│           ├── hooks/
│           ├── api/
│           └── types/
├── specs/                # Feature specifications
│   ├── onboarding/       # Each feature has its own folder
│   │   ├── feature.md    # Requirements and specifications
│   │   └── implementation-notes.md  # Testing, edge cases, decisions
│   ├── data-pipeline/
│   │   ├── feature.md
│   │   └── implementation-notes.md
│   └── dashboards/
│       ├── feature.md
│       └── implementation-notes.md
└── AGENTS.md       
```

## Core Features

1. **User Onboarding** - Account creation, Open Finance linking (Lean) or manual PDF/CSV upload
2. **Data Pipeline** - Extract, transform, categorize transactions
3. **Dashboards** - NEEDS/WANTS/SAVINGS expenses breakdown, merchant analysis, trends
4. **Anomaly Detection** - Spending concentration, credit risks, small leaks
5. **Subscriptions** - Auto-detect recurring charges, self-serve or concierge cancellation
6. **Health Checkup** - Color-coded wellness indicators (savings rate, credit utilization, etc.)
7. **Smart Budgeting** - Category caps, drift detection, repair mechanisms
8. **AI Coach** - Query-driven guidance, affordability checks, scenario analysis
9. **Notifications** - Timely nudges with user-controlled tone/frequency
10. **Expense Buffers** - Detect irregular expenses, create savings buffers
11. **Multi-Account** - Multiple banks/cards, payment linking, double-counting prevention


## Workflow

1. **Read specs first** - Check `specs/[feature-name]/feature.md` before coding
2. **Review patterns** - Look at similar implementations
3. **Ask about edge cases** - Never assume, always clarify
4. **Update implementation notes** - After coding, document in `specs/[feature-name]/implementation-notes.md`:
   - How to test this specific feature
   - Edge cases and how they're handled
   - Feature-specific setup or data requirements
   - Design decisions made
   - Known limitations 

## Data Architecture Rules

**Schema separation** (critical):
- PII/sensitive data → `transactions` schema ONLY
- Analytics/aggregates → `derived_data` schema ONLY
- Never mix schema purposes
- Never query across schemas directly (use application layer)

**Data flow**:
1. Raw data → `transactions.raw_transactions`
2. Categorized → `transactions.categorized_transactions`
3. Feature KPIs → `derived_data.[feature]_kpis`

**Storage**:
- All files → AWS S3 me-central-1 only
- SSE-KMS encryption required
- Path: `statements/{user_id}/{file_id}.{ext}`
- Statements purged 7 days after processing

## Code Style

**Backend (Python/FastAPI)**:
- Async/await for all I/O operations (database, API calls, file operations)
- Pydantic models for request/response validation (FastAPI's native validation - type-safe, automatic docs)
- Dependency injection for DB sessions, auth, and shared services
- Type hints on all functions: `def get_user(user_id: str) -> User:`
- Explicit error handling with FastAPI HTTPException
- Snake_case for variables/functions, PascalCase for classes
- Proper HTTP status codes: 200 (success), 201 (created), 400 (bad request), 401 (unauthorized), 404 (not found)
- bcrypt cost factor 12+ for password hashing
- Keep route handlers thin - delegate business logic to service layer

**Mobile (React Native)**:
- TypeScript strict mode always
- Functional components only
- Keep files focused on single responsibility - split when handling multiple concerns
- Extract complex logic into custom hooks
- Separate UI components from business logic
- Feature-based folders: `features/[name]/{components,hooks,api,types}`


## UAE/DIFC Compliance

- Data residency: me-central-1 region only
- Encrypt all PII at rest and in transit
- Log all auth attempts and financial transactions
- Lean API: OAuth 2.0 only, never store bank credentials
- 15-minute idle timeout on financial screens

## Security Boundaries

**Never do**:
- Store PII outside `transactions` schema
- Use AWS regions other than me-central-1
- Skip S3 SSE-KMS encryption
- Store OAuth tokens client-side
- Store sensitive data in AsyncStorage
- Hardcode API keys or secrets

**Always do**:
- Use environment variables for secrets
- Server-side validation for all inputs
- Encrypted refresh tokens in database
- OAuth tokens server-side only

## When Stuck

- Check `specs/[feature].md` for requirements
- Ask clarifying questions about edge cases
- Present options with pros/cons, don't assume
- Stop and ask when specs are unclear

## Development Principles

- Build feature-by-feature, not all at once
- Simple first, optimize later
- Present edge cases with options
- Test thoroughly before marking done
- Update specs as you learn