# Life Pricing Platform — Architecture & Development Rulebook

Version 0.1 — working draft, first pass. This is meant to be argued with and
revised, not treated as final. Sections marked **Open** need a decision
before they can be locked in.

---

## 1. Core principles

1. **Spec before code.** Every module and every non-trivial change starts as
   a written spec, reviewed and versioned, before an LLM or a human writes
   implementation code. 
2. **Contracts over conventions.** Modules talk to each other through
   versioned API contracts (OpenAPI for HTTP, JSON Schema for MCP tool
   inputs/outputs).
3. **JSON/YAML is authoritative; prose describes it.** Where a contract,
   rule, or configuration can be expressed as structured data, that
   structured form is the source of truth. English descriptions are a
   rendering of it, not the other way around.
4. **LLMs accelerate; they don't own consequential decisions.** LLMs draft
   code, review code, draft specs, and run persona checkpoints. A human
   remains accountable for decisions.
5. **Determinism where it matters.** Anything that affects the way the software
   operates must be reproducible: same inputs, same
   model version, same output. 
6. **Cost is a design constraint, not an afterthought.** Every architectural choice 
   gets checked against what it costs at rest and under load, not just whether it works.

---

## 2. System architecture overview

**Shape:** an API-first backend on AWS, fronted by an agentic UI, with a
dedicated MCP server as the integration layer between the modeling core and
everything that consumes it (UI agent, dev tooling, reports).

**Modules** (each with its own repo directory, its own API contract, and its
own owner persona):

- `mortality` — mortality model(s) and their serving interface.
- `propensity` — propensity-to-buy model(s).
- `persistency` — persistency model(s).
- `pricing-engine` — combines the three model outputs into a price and into
  simulation/ROI results. 
- `quote-intel` — the competitive quote scraper/collator and comparison
  logic. Kept separate from `pricing-engine` so that a change to scraping
  logic can never accidentally touch pricing calculations.
- `mcp-server` — exposes the above as tools, split into a **dev-tools**
  server (used by Claude Code / CI) and a **product-agent** server (used by
  the agentic UI), so a bug or a prompt-injection risk in one surface can't
  reach the other.
- `ui` — the agentic-first frontend plus the traditional dashboard/report
  views, likely a static SPA served the same way the existing Irix.AI
  frontend is (S3 + CloudFront).

Each module is a composable, independently deployable unit behind a uniform
interface. A module should be replaceable (e.g., swapping in a new mortality
model version) without the modules around it needing to change.

**Data flow, at a high level:** a pricing simulation request comes in through
the API → the pricing engine calls the three model modules through their
contracts → results are combined into a priced scenario and an ROI estimate
→ the result is returned to the caller and logged for audit/reproducibility.

---

## 3. AWS services and rationale

The overriding constraint is the **$250/month** ceiling covering AWS plus
LLM API spend. That rules out anything with a meaningful always-on cost by
default. The recommendations below default to pay-per-use, scale-to-zero
services, with one exception (Aurora) that's opt-in and explicitly flagged.

| Service | Role | Why this one |
|---|---|---|
| **API Gateway** | HTTP entry point | Pay-per-request, no idle cost. |
| **Lambda** | Compute for the API and for individual model invocations | Pay-per-invocation and per-GB-second; free tier covers most early usage; fits intermittent traffic. 15-minute max runtime and up to 10 GB memory are enough for most model-serving and simulation work. |
| **Step Functions** | Orchestrates the multi-model pricing simulation pipeline (mortality → propensity → persistency → combine) | Pay per state transition; keeps the pipeline's control flow explicit and auditable rather than buried in application code. |
| **S3** | Model artifacts, datasets, scrape results, audit logs, static frontend hosting | Cheapest storage option; already the pattern used on Irix.AI. |
| **DynamoDB (on-demand mode)** | Primary application data store for anything that fits a key-value/document shape (simulation runs, review records, quote-intel results) | No idle cost at on-demand pricing; scales down to zero cost when unused, unlike a provisioned database. |
| **Aurora Serverless v2 (optional, opt-in)** | Only if genuinely relational, multi-table querying is needed | Since November 2024 it can scale to 0 ACUs and pause, so it no longer forces an always-on charge — but resuming from a full pause takes about 15 seconds, which is fine for internal/dev use and unacceptable for a customer-facing request. Use only where DynamoDB's access patterns genuinely don't fit, and don't put it on the customer-facing hot path. |
| **EventBridge** | Scheduling (nightly persistency model runs, weekly competitive quote scrape, weekly cost report) | Cheap, decouples scheduling from application code. |
| **CloudWatch** | Logs, metrics, alarms | Watch log retention settings; unbounded retention is a common silent cost creep. |
| **AWS Budgets + Cost Anomaly Detection** | Cost monitoring | Free. This is the backbone of the cost-monitoring requirement in Section 13. |
| **SES** | Sending the automated cost reports and signoff notifications | Very cheap at this volume. |
| **Secrets Manager / SSM Parameter Store** | Credentials and API keys | Use Parameter Store (free for standard parameters) for most values; reserve Secrets Manager (which costs per secret) for the few that need automatic rotation, such as database credentials. |
| **ECR** | Docker image registry | Small storage cost, needed regardless since Docker is a stated requirement. |
| **CloudFront + S3** | Hosting the agentic UI frontend | Cheap, and matches the existing pattern from Irix.AI. |
| **Amazon Bedrock (Claude models) or direct Anthropic API** | LLM calls for dev tooling and product features | Both are pay-per-token with no idle cost. Bedrock consolidates LLM spend into the same AWS Budgets/Cost Explorer view as everything else, which simplifies the cost-monitoring requirement; the direct Anthropic API may be simpler to integrate with Claude Code and MCP tooling already in use. Worth deciding explicitly rather than defaulting — see Open Question below. |

**Deliberately avoided by default:** NAT Gateways (hourly charge regardless
of traffic — use VPC endpoints or keep Lambdas out of a VPC where possible),
SageMaker real-time endpoints (charged per hour regardless of use),
always-on RDS/EC2 instances, and QuickSight (per-user licensing cost that's
hard to justify at this budget; build reporting as scheduled Lambda jobs
writing to S3/rendered HTML instead).

---

## 4. Repository, environment, and packaging

- Single GitHub repo, organized by module (see Section 2), each with its own
  `Dockerfile`, its own test suite, and its own `contracts/` directory
  holding its OpenAPI or JSON Schema definitions.
- Docker for all services, including local development, so "works on my
  machine" differences can't creep into what actually deploys.
- GitHub Actions for CI, not AWS CodeBuild — avoids a second CI billing
  surface and keeps LLM-as-judge automation (Section 8) close to the PR
  workflow where it's triggered.
- GitHub Actions authenticates to AWS via OIDC (short-lived, per-run
  credentials), not long-lived static AWS keys stored as secrets.
- Any container-based (non-Lambda) compute added later needs the same
  discipline: list and stop existing tasks before every redeploy.

### Folder rules

```
vita/
├── mortality/            \
├── propensity/            \  each: contracts/, tests/, Dockerfile, README.md
├── persistency/            /
├── pricing-engine/        /
├── quote-intel/          /
├── mcp-server/
│   ├── dev-tools/
│   └── product-agent/
├── ui/
├── prompts/<persona>/     — see Section 12 naming convention
├── specs/
├── docs/
│   ├── adr/
│   └── model-cards/
├── ops/
│   ├── runbooks/
│   └── push-log.jsonl
└── AGENTS.md
```

- **One folder per module** (Section 2's list). Each module is
  self-contained: its own `contracts/`, its own `tests/`, its own
  `Dockerfile`, its own `README.md`. Nothing about a module lives outside
  its folder.
- **Cross-cutting stuff gets its own top-level folder**, never scattered
  inside a module: `prompts/`, `specs/`, `docs/`, `ops/`.
- **`ops/` holds anything operational** — runbooks, the push-log, deploy
  scripts. `docs/` holds anything reference-only — ADRs, model cards. (This
  replaces the earlier split where runbooks sat under `docs/runbooks/`;
  matches the `ops/` convention already used on Irix.AI.)
- **Max depth: 3–4 levels.** If something needs a 5th, it's a sign the
  module boundary is wrong, not that the tree needs another layer.
- **Name folders after what they contain, not the tech stack** —
  `pricing-engine/`, not `python-services/`.
- **Nothing sits loose at repo root** except `AGENTS.md` and standard repo
  files (`.gitignore`, `README.md`). Everything else belongs in one of the
  folders above.

---

## 5. Spec-driven requirements and user stories

- Every feature starts as a spec document under `/specs/`, using a fixed
  template: problem statement, intended users, acceptance criteria,
  explicit out-of-scope items. This is the same "design doc before code"
  discipline already used on the Rules Engine project.
- Specs are versioned in-repo (not in an external doc tool) so their history
  lives next to the code they describe.
- User stories live in GitHub Issues/Projects, each one linked to the spec
  it implements and tagged with the persona(s) responsible for reviewing
  and signing off on it.
- Acceptance criteria in a spec must be written so they can become test
  cases directly — if a criterion can't be turned into a test, it's not
  specific enough yet.

---

## 6. LLM usage constraints

These are hard boundaries on what an LLM (any persona, any model) may do
without a human in the loop:

- An LLM may draft, review, and even merge routine code changes under the
  LLM-as-judge gate (Section 8), **except** changes touching `pricing-engine`,
  `mortality`, `propensity`, or `persistency` model logic or parameters,
  which always require a human sign-off regardless of judge score.
- An LLM may propose a model version promotion (new mortality table,
  retrained propensity model, etc.), but promotion to production requires a
  human actuary or data scientist sign-off — not just the Actuary/Data
  Scientist persona's automated review.
- An LLM may draft customer- or carrier-facing pricing output text and
  reports, but may not autonomously send anything externally; that always
  goes through a human-approved send step.
- LLM calls that touch real customer or carrier data go through the same
  data-handling constraints as any other code — no pasting production data
  into ad hoc prompts outside the logged, contract-defined pipeline.
- Tests for LLM-dependent components use offline, deterministic stubs in CI
  (the same approach used on the Rules Engine project), so the test suite
  doesn't depend on live model calls for correctness, cost, or speed.

---

## 7. LLM personas and review checkpoints

Six personas, each a versioned system prompt (see Section 12) with a defined
checklist of what it must check before signing off. None of these replace a
human's final sign-off on consequential changes (Section 6); they're a
structured first pass that surfaces issues before a human spends time on
them.

| Persona | Reviews | Checkpoint |
|---|---|---|
| **Architecture** | Module boundaries, API contract changes, whether a change belongs where it's placed | Any PR touching a contract or crossing a module boundary |
| **Actuary** | Mortality/persistency/pricing logic soundness, regulatory reasonableness (e.g., does a mortality curve behave sensibly across ages) | Any change to model logic or pricing parameters; required before model promotion |
| **Data Scientist** | Modeling methodology, feature engineering, validation approach, backtest results | Model training/retraining changes |
| **Data Engineer** | Data pipeline correctness, schema changes, data quality checks | Changes to data ingestion or the quote-intel pipeline |
| **Marketing** | How pricing/ROI/competitive results are framed and reported | Changes to report templates, competitive positioning narrative |
| **Product Owner** | Scope, prioritization, whether acceptance criteria are actually met | Spec approval; release readiness |

For a solo or small team, these personas function as a structured
LLM-driven first review pass, mirroring the two-level sign-off pattern
already in use on the Rules Engine project (there, a human plays both
levels; here, a persona plays the first level and a human plays the second).

---

## 8. LLM-as-judge code review, and how to automate it

**What it does:** on every pull request, an LLM reviews the diff against a
versioned rubric and posts a structured verdict as a PR comment, gating
merge on both a score threshold and on required human approval for
high-risk paths.

**How to automate it, concretely:**

1. A GitHub Actions workflow triggers on `pull_request` (opened and
   synchronized).
2. The workflow computes the diff and gathers relevant context — the linked
   spec from `/specs/`, the module's API contract, and any persona-specific
   checklist that applies (e.g., the Actuary checklist if the diff touches
   `pricing-engine`).
3. It calls the Claude API with a versioned judge prompt
   (`/prompts/judge/v<N>.md`) and asks for a structured JSON verdict:
   per-dimension scores (correctness, test coverage, security, style,
   contract compliance) plus a flag for "touches high-risk path."
4. The workflow posts the verdict as a PR comment and sets a required GitHub
   status check.
5. Merge is blocked if the aggregate score is below threshold, **or** if the
   high-risk flag is set and the PR doesn't carry a label confirming the
   relevant human persona (e.g., `actuary-approved`) has signed off.
6. Every verdict — prompt version, model version, scores, and the diff hash
   it was run against — is logged to S3 or DynamoDB. In a regulated,
   money-touching system, being able to show what an LLM reviewed and what
   it said is worth having even if nobody asks for it on day one.

**Judge model choice:** use a stronger or at least differently-configured
model for judging than for day-to-day drafting, so the same blind spots
aren't grading their own work. Given current Claude API pricing (roughly
$3/$15 per million input/output tokens for Sonnet and $5/$25 for Opus), a
reasonable split is Sonnet for routine drafting and Opus for judging PRs
that touch high-risk paths, with Sonnet-as-judge acceptable for everything
else. This is a lever to revisit against actual token usage once the system
is running (Section 13).

---

## 9. Testing strategy

- **Unit tests:** `pytest`, consistent with the stack already used on the
  Rules Engine project. Target coverage: 90%+ for `pricing-engine` and the
  three model modules, 80%+ elsewhere.
- **Contract tests:** every API endpoint and every MCP tool is tested
  against its own OpenAPI/JSON Schema contract, so a contract and its
  implementation can't silently drift apart.
- **Model validation tests:** backtesting against holdout data, calibration
  checks, and monotonicity/sanity checks appropriate to each model (for
  example, a mortality curve shouldn't behave nonsensically across
  adjacent ages). These are a distinct test category from unit tests
  because they're about the model being *reasonable*, not just the code
  being *correct*.
- **Golden-file/regression tests:** fixed input → expected output pairs for
  the pricing engine, so a change that silently shifts pricing output gets
  caught even if every unit test still passes.
- **Offline LLM stubs:** as noted in Section 6, LLM-dependent code paths are
  tested against deterministic stubs in CI, with live-model tests kept as a
  separate, manually triggered suite.
- Validation is done by actually running scripts and inspecting real output,
  not by static analysis alone — the same approach already in use on the
  Rules Engine project.

---

## 10. Peer review and sign-off process

Four sign-off gates, each pairing a persona's automated pass with a human
decision on anything consequential:

1. **Spec sign-off** — Product Owner persona plus a human, before any code
   is written against the spec.
2. **Code merge sign-off** — LLM-as-judge (Section 8) plus, for high-risk
   paths, the relevant human persona (actuary, architect).
3. **Model validation sign-off** — Actuary and Data Scientist personas plus
   a human actuary/data scientist, before a model version is promoted to
   production. This gate is not skippable regardless of how the LLM
   personas score it.
4. **Release sign-off** — Product Owner persona plus a human, before a
   deploy that includes a model promotion or a pricing-engine change goes
   out.

---

## 11. Documentation strategy

- **Docs-as-code**, living in the repo under `/docs/`, not in an external
  wiki that drifts out of sync.
- **Architecture Decision Records** under `/docs/adr/NNNN-title.md`,
  lightweight format: context, decision, consequences. Written whenever a
  choice in this rulebook or a later one gets revisited.
- **API contracts** under each module's `contracts/` directory, in
  OpenAPI/JSON Schema — authoritative over any prose description of the
  same endpoint, per the principle in Section 1.
- **Model cards** for each of the three core models: data sources, features,
  validation metrics, known limitations, version history. These are what an
  actuary or a regulator would want to see, so they're written for that
  audience, not for internal dev convenience.
- **Runbooks** under `/ops/runbooks/` for deploy, rollback, and incident
  response — the same pattern as the `ops/` scripts and checklists already
  in use on Irix.AI.
- **Module READMEs** stating purpose, inputs/outputs, and owning persona for
  each module.
- LLMs draft documentation; a human reviews it before it's treated as
  authoritative, same as code.

---

## 12. Prompt and tool versioning

### Naming convention

```
<persona>.<artifact-type>.v<major>.<minor>.md
```

- **Persona:** `architecture`, `actuary`, `data-scientist`, `data-engineer`,
  `marketing`, `product-owner`, `judge`
- **Artifact type:** `prompt` (core system prompt), a checklist named after
  its checkpoint — `spec-review-checklist`, `code-review-checklist`,
  `model-validation-checklist`, `release-checklist` (matches the Section 10
  sign-off gates) — or `rubric` (judge only)
- **Version:** `major.minor`. Major = could change judgment/output, needs an
  eval suite pass before going live. Minor = wording/clarity only.

Examples: `actuary.model-validation-checklist.v2.0.md`,
`judge.rubric.v1.0.md`

Files live under `/prompts/<persona>/`. Each carries frontmatter so the
filename can't drift from its own metadata:

```yaml
---
persona: actuary
artifact_type: model-validation-checklist
version: 2.1
supersedes: 2.0
date: 2026-09-07
---
```

CI checks frontmatter against filename on every change.

### Rules

- Production pins an exact version per persona — never "latest."
- Any bump (major or minor) goes through the same review as a code change.
  Major bumps also require an eval suite pass.
- MCP tool manifest: semver. Breaking schema change = major bump, both
  versions served during a transition period.
- A tool's *description* text versions the same way as its schema — it
  drives which tool the model picks, so a wording change to it counts as a
  version-worthy change, not a casual edit.

---

## 13. Cost monitoring and alerting

- **AWS Budgets:** a hard $250/month budget with alert thresholds at 50%,
  80%, and 100% of the limit, sent to the team via SES.
- **Cost Anomaly Detection:** enabled from day one, since LLM token spend
  and any experimental AWS usage are the most likely sources of an
  unexpected spike.
- **Automated weekly cost report:** a scheduled Lambda (via EventBridge)
  queries the Cost Explorer API and emails a per-service cost breakdown, so
  spend is visible before it becomes a problem rather than after.
- **Tagging:** every resource tagged by module (`mortality`, `pricing-engine`,
  etc.) so the cost report can break spend down by module, not just by AWS
  service.
- **LLM token spend tracked separately** from AWS infrastructure spend,
  since it's the most usage-dependent line item and the one most directly
  affected by which model each persona and each judge review uses (Section
  8). If Bedrock is chosen (Section 3), this shows up in the same Cost
  Explorer view automatically; if the direct Anthropic API is chosen, its
  usage dashboard needs to be checked separately and folded into the weekly
  report by hand or by a small script.

---

## 14. The pricing/simulation engine and the quote scraper — noted, not designed here

Two pieces of the vision need their own dedicated design pass rather than a
few paragraphs here:

- **The real-time pricing and simulation engine** — combining the three
  models into pricing strategies and ROI output. Before this can be
  architected properly, it needs a concrete latency target (see the open
  item in the project notes) and a decision on how much of the simulation
  can be precomputed versus run on demand.
- **The competitive quote scraper** — needs a legal/terms-of-service review
  before build, since scraping other carriers' quote or rate pages may
  violate their terms of service. Worth deciding early whether this starts
  as a licensed data feed, a manual/permitted data source, or a scraper
  built only against sources confirmed to allow it.

---

## Open questions to resolve before locking this in

1. Bedrock vs. direct Anthropic API for LLM calls (Section 3).
2. A concrete latency target for "real-time" simulation (Section 14).
3. Legal footing for the competitive quote scraper (Section 14).
4. Whether the three reference Google Docs contain principles that should
   change any of the above — they aren't accessible yet (see project notes).
