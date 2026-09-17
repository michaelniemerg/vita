# Vita — Setup To-Do List

This assumes `architecture-and-dev-rules.md` and `ai-development-key-lessons.md`
as background. Resolved decisions are marked as such and left in place so the
reasoning stays visible; open ones are still open.

---

## 0. Decisions before setup starts

- [ ] Internal tool for one insurer, or a multi-tenant product for several
      carriers (changes auth, data isolation, and MCP server scoping)
- [ ] Real historical policy/claims data, a licensed data source, or
      synthetic/public data (changes the security and compliance bar
      significantly)
- [ ] Solo build, or a team where each persona maps to an actual person
      (changes what "peer review" and "sign-off" mean in practice)
- [ ] Quote scraper scope: which products (term/whole/universal life),
      which carriers, which regions — plus the legal/ToS review this needs
- [ ] A concrete latency target for "real-time" simulation
- [ ] What gets built first (pricing engine core, one of the three models,
      or the MCP server skeleton)
- [x] **RESOLVED — LLM provider split:** Bedrock is used in the product
      (in-product agentic UI, product-agent MCP server). Direct Claude /
      Claude Code is used more heavily as the development tool (persona
      reviews, LLM-as-judge, day-to-day coding). This is a mixed setup, not
      a single choice — see Section 8 (environments) and Section 13 (cost
      monitoring) for what that implies downstream.
- [ ] Whether `pricing-engine` needs a full Tier 3 custom reviewer, or the
      Tier 2 hybrid LLM-as-judge design (Section 9) is enough
- [ ] Memory architecture for the agentic UI: per-user memory (saved
      scenarios, preferences — isolated per user, like a personal
      assistant) vs. shared retrievable product knowledge (rate tables,
      product docs — global and read-only, like a research librarian).
      These are different mechanisms with different isolation requirements;
      decide which parts of Vita need which.
- [ ] The static-vs-dynamic context split for both the dev-tooling agent and
      the product agent: what's always loaded (AGENTS.md, persona prompts)
      versus what's loaded on demand (skills, specs, retrieved docs). Treat
      this as a reviewed, versioned architectural decision, not whatever
      falls out of however the prompts happen to get written.

---

## 1. Repo and access

- [ ] Create the GitHub repo
- [ ] Module-based folder structure: `mortality/`, `propensity/`,
      `persistency/`, `pricing-engine/`, `quote-intel/`, `mcp-server/`, `ui/`
- [ ] Give Claude access to the repo (Claude Code or equivalent) for
      development work — this is the "development tool" channel from the
      resolved LLM-provider decision above, separate from the product's
      Bedrock access
- [ ] `AGENTS.md` at the repo root — start with ~10 lines: stack,
      conventions, hard rules, workflow. Add a line every time an agent does
      something it shouldn't repeat
- [ ] A skills folder for reusable agent workflows (e.g., a docs-maintenance
      skill that keeps README/CHANGELOG current)

## 2. AI development workflow

- [ ] Write a single end-to-end workflow document (a diagram helps) showing
      how a feature actually moves from idea to production: spec →
      persona review → implementation → LLM-as-judge → sign-off gate(s) →
      deploy — naming which persona and which gate applies at each step
- [ ] This should tie together, in one place, what's currently scattered
      across separate sections: specs (Section 7), personas (Section 3),
      LLM-as-judge (Section 9), and sign-off gates (Section 12). Right now
      the sequence between them is only implicit.

## 3. Personas

- [ ] Define the six personas as versioned system prompt files:
      architecture, actuary, data scientist, data engineer, marketing,
      product owner
- [ ] For each persona, write its review checklist and which checkpoint it
      owns (spec review, code merge, model validation, or release — see
      Section 12)

## 4. Prompt versioning

- [ ] `/prompts/<persona>/v1.md`, one file per persona, changelog at the top
      of each file
- [ ] `/prompts/judge/v1.md` for the LLM-as-judge rubric (Section 9)
- [ ] Decide the rule for what counts as a version bump vs. an in-place fix,
      and require the same PR review on prompt changes as on code changes

## 5. Tool versioning

- [ ] MCP tool manifest, versioned with semver
- [ ] Rule: a breaking change to a tool's input/output schema is a major
      version bump, with both versions served for a transition period

## 6. Core models and actuarial definition

- [ ] Define the mortality model: methodology, inputs, outputs
- [ ] Define the propensity-to-buy model: methodology, inputs, outputs
- [ ] Define the persistency model: methodology, inputs, outputs
- [ ] Give each model its own API as its own module of the Vita platform —
      `mortality/`, `propensity/`, and `persistency/` each expose their own
      scoring endpoint under their own contract, independently callable,
      not just internal functions the pricing engine happens to call
- [ ] Create an actuarial requirements document showing how the three
      models' outputs are interrelated and combined into a price, and how
      ROI is calculated — pick the specific metric (loss ratio,
      lapse-adjusted margin, present value of future profits, IRR, or
      other) rather than leaving "ROI" undefined
- [ ] Pricing-run log: every simulation records the exact model versions
      used, a hash of its inputs, and its output, so a price is actually
      reproducible and checkable after the fact — separate from the
      LLM-judge verdict log in Section 9

## 7. Requirements, user stories, and test documentation

- [ ] `/specs/` folder with a template: problem, intended users, acceptance
      criteria, explicit out-of-scope
- [ ] GitHub Issues/Projects for user stories, each linked to its spec and
      tagged with the persona(s) responsible for it
- [ ] `contracts/` directory per module holding its OpenAPI or JSON Schema —
      this is the actual API contract, authoritative over prose
- [ ] Test suite setup: `pytest`, coverage targets (90%+ for
      `pricing-engine` and the three model modules, 80%+ elsewhere)
- [ ] Golden-file/regression fixtures for the pricing engine
- [ ] Offline, deterministic stubs for any LLM-dependent test path
- [ ] A model validation test suite, kept distinct from unit-test coverage:
      backtesting against holdout data, calibration checks, and
      monotonicity/sanity checks per model (e.g., a mortality curve
      shouldn't behave nonsensically across adjacent ages)
- [ ] An eval suite for the agentic UI and for the LLM-as-judge itself, with
      an explicit rubric (task success, tool-use quality, trajectory
      compliance, hallucination rate, response quality) — this is distinct
      from deterministic unit tests and shouldn't get folded into them

## 8. Test and production environments

- [ ] AWS environment split (dev/test/prod) with promotion-only flow between
      them
- [ ] Dockerfile per module
- [ ] GitHub Actions for CI/CD, authenticating to AWS via OIDC — no static
      AWS keys stored as secrets
- [ ] Core AWS infra: API Gateway, Lambda, DynamoDB (on-demand mode), S3,
      Step Functions, EventBridge, ECR, CloudFront
- [ ] Set up Bedrock access and configuration for the product-agent MCP
      server and the in-product agentic UI (the resolved product-side LLM
      channel from Section 0)
- [ ] Wire the pytest suite into CI so it runs on every PR and blocks merge
      on failure — this is separate from the LLM-as-judge score gate
      (Section 9); one is deterministic pass/fail, the other is a scored
      review
- [ ] Credential management: SSM Parameter Store for most values, Secrets
      Manager reserved for credentials that actually need rotation
- [ ] Decide whether Aurora Serverless v2 is actually needed anywhere (only
      if a module genuinely needs relational, multi-table queries — see the
      rulebook for the cold-start caveat)

## 9. LLM-as-judge code review automation

- [ ] GitHub Actions workflow triggered on PR open/sync
- [ ] Workflow gathers the diff plus context (linked spec, module contract,
      relevant persona checklist)
- [ ] Calls Claude (the development-tool channel) with the versioned judge
      prompt, returns a structured verdict (per-dimension scores + a
      high-risk-path flag)
- [ ] Posts the verdict as a PR comment, sets a required status check
- [ ] Merge blocked below the score threshold, or if the high-risk flag is
      set without the matching human-approval label (e.g., `actuary-approved`)
- [ ] Log every verdict (prompt version, model version, scores, diff hash)
      to S3 or DynamoDB for an audit trail

## 10. Governance and safety

- [ ] Policy server in front of MCP tool calls: a fast structural check
      (is this tool allowed for this role/environment?) plus a semantic
      check (is this specific use of an allowed tool actually safe?)
- [ ] Sandboxing for any agent-executed code — ephemeral, low-privilege,
      disposable containers, isolated from the primary network
- [ ] Context hygiene / prompt sanitization utility for the product-agent
      MCP server, so real customer or carrier data never gets hardcoded
      into a prompt or a test fixture
- [ ] Human-in-the-loop checkpoints, enforced (not just documented), for
      production deploys, schema changes, and model promotion
- [ ] A written production-data access rule: where real customer or carrier
      data can and can't be pasted into a prompt, and a log of any LLM call
      that touches it
- [ ] An external-send gate: a human-approval step before anything an LLM
      drafts — reports, pricing output, marketing copy — actually goes
      outside the system

## 11. Documentation

- [ ] `/docs/adr/` with an ADR template (context, decision, consequences)
- [ ] Model cards for the mortality, propensity, and persistency models —
      data sources, features, validation metrics, known limitations,
      version history (this can draw directly on the model definitions from
      Section 6)
- [ ] `/docs/runbooks/` for deploy, rollback, and incident response
- [ ] A README per module: purpose, inputs/outputs, owning persona
- [ ] A docs-drift check: something that actually flags when code changes
      without a corresponding README or CHANGELOG update, rather than
      relying on the habit holding

## 12. Sign-off process

- [ ] Set up the four sign-off gates as GitHub branch protection / required
      reviewers, not just written policy:
      1. **Spec sign-off** — before code is written against it
      2. **Code merge sign-off** — LLM-as-judge plus human approval on
         high-risk paths
      3. **Model validation sign-off** — before a model version is promoted
         to production; not skippable regardless of persona score
      4. **Release sign-off** — before any deploy that includes a model
         promotion or a pricing-engine change

## 13. Cost monitoring

The budget is $250/month total, covering AWS and LLM spend combined.

- [ ] AWS Budgets with alerts at 50%, 80%, and 100% of the limit
- [ ] Cost Anomaly Detection enabled from day one
- [ ] A scheduled Lambda (weekly) that queries Cost Explorer and emails a
      per-service, per-module cost breakdown via SES
- [ ] Resource tagging by module so the report can actually break spend down
      that way
- [ ] LLM token spend tracked across both channels from the resolved
      provider split: Bedrock usage shows up automatically in AWS Cost
      Explorer; direct Claude/Claude Code usage for development is a
      separate billing surface and needs to be pulled into the weekly
      report by hand or by a small script

## 14. Observability

- [ ] Agent-run observability, separate from dollar cost monitoring: traces
      of every agent run (both the dev-tooling agent and the product
      agent), latency metering, and drift detection — the cost report shows
      what's being spent, not whether an agent is quietly getting worse

## 15. Team and process norms (mainly relevant once more than one person is involved)

- [ ] Explicit distinction between prototyping and production branches/
      environments, so a prototype can't ship by accident
- [ ] No-blame norm for agent-caused issues — attribute them to a process
      gap, not the person who ran the agent
- [ ] If the team grows past solo: digital quiet hours (approval requests
      don't bleed into evenings/weekends) and a recurring session to share
      patterns agents surface, so isolated discoveries don't stay siloed
