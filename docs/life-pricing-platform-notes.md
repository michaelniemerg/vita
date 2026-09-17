# Life Pricing Platform — Project Notes (Working Draft)

Consolidated from the initial brain dump. This is the "what and why" — see
`architecture-and-dev-rules.md` for the "how."

## Vision

A life insurance pricing platform that combines mortality, propensity-to-buy,
and persistency models into a single engine, exposed as an API-first,
AWS-first service, and built using spec-based, AI-native development
practices from the start.

## Core capabilities

- **Mortality modeling** — one of the three underlying model families feeding
  the pricing engine.
- **Propensity-to-buy modeling** — likelihood a prospect converts at a given
  price point.
- **Persistency modeling** — likelihood a policy stays in force over time.
- **Combined pricing engine** — draws on all three models to price a policy
  or a book of business.
- **Real-time pricing simulation** — run pricing strategies and get study
  results and ROI back immediately, framed from a life insurer's
  perspective (not the consumer's).
- **Competitive intelligence** — scrape and collate quotes from other life
  insurance carriers, and compare the platform's own pricing against them
  for competitiveness.

## Product experience

- Agentic-first UI: a conversational, tool-using interface is the primary
  way users interact with the platform.
- Traditional elements are kept alongside it: fixed dashboards and standard
  scheduled reports, not just chat.
- A dedicated MCP server exposes the platform's modeling and simulation
  capabilities as callable tools, both to the agentic UI and to development
  tooling.

## Delivery approach

- AWS-first, API-first service.
- GitHub for source control and CI/CD.
- Docker for packaging and deployment.
- Spec-based design principles, written for AI-assisted development.
- Module-based design with explicit API contracts between modules.
- Heavy reliance on LLM tools and skills throughout the development
  lifecycle, within defined constraints.
- LLM-as-judge used in code review, alongside distinct LLM personas
  (architecture, actuary, data scientist, data engineer, marketing, product
  owner) that review and sign off at defined checkpoints.
- Prompt versioning and MCP tool versioning are treated as first-class,
  alongside code versioning.

## Constraints

- Budget: $250/month total, covering AWS infrastructure and LLM API spend
  combined.
- Needs active cost monitoring with automated reports and alerting so the
  budget isn't discovered to be blown after the fact.

## Open items

- Three reference Google Docs were mentioned as source material to extract
  principles from, but they aren't accessible in this conversation yet.
  Paste their content in, share them as text, or connect Google Drive so
  they can be read directly, and the rulebook can be revised against them.
- The competitive quote scraper needs a legal/terms-of-service review before
  being built. Scraping carrier rate or quote pages may violate those
  carriers' terms of service. A licensed data provider or a
  permitted/manual data source may be the safer starting point.
- "Real-time" simulation is a stated goal, but what counts as real-time
  (sub-second, a few seconds, under a minute) hasn't been pinned down yet,
  and the achievable latency depends heavily on model complexity. This needs
  a concrete target before the simulation architecture can be finalized.
