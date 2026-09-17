# AGENTS.md

Stack: Python, AWS (Lambda, API Gateway, DynamoDB, S3, Step Functions, EventBridge, ECR, CloudFront), Docker per module. Bedrock for in-product LLM calls; Claude / Claude Code for development work.

Folders: model modules live under modules/ (modules/mortality/, modules/propensity/, modules/persistency/, modules/pricing-engine/, modules/quote-intel/), each self-contained with contracts/, tests/, Dockerfile, README.md. mcp-server/ and ui/ stay at the repo root, not under modules/. Cross-cutting material lives in prompts/, specs/, docs/, ops/ -- never inside a module.

Every feature begins with a spec in specs/ before implementation. Acceptance criteria must be objective and specific enough to translate directly into tests. Derive acceptance tests from those criteria before or alongside implementation.

No code changes are allowed to be pushed unless signed off by a human as reviewed and there are both unit tests, regression test, and acceptance testing. 

Make the smallest change that satisfies the spec. Do not refactor unrelated code, rename unrelated symbols, modify infrastructure, or upgrade dependencies unless the spec requires it.

Every behavioral change requires tests. Bug fixes require a regression test that demonstrates the failure before the fix and passes afterward. Do not weaken, remove, skip, or rewrite tests merely to make a change pass. Run the affected module's unit and contract tests before considering implementation complete.

Public module interfaces belong in contracts/. Changes to a contract require corresponding consumer, test, and documentation updates. Prefer backward-compatible contract changes. Breaking contract changes require explicit approval in the spec.

Follow least-privilege IAM. Do not introduce wildcard permissions, hard-coded secrets, account IDs, environment-specific endpoints, or credentials unless explicitly required and justified by the spec.

LLM-as-judge evaluations must use the rubric and success threshold defined by the feature spec. Evaluation inputs, model/version, rubric version, and results must be reproducible. A failing evaluation blocks deployment but cannot substitute for required human approval.

Prompts and tools are versioned as <persona>.<artifact-type>.v<major>.<minor>.md; frontmatter must match the filename.

Hard rule: changes to pricing-engine, mortality, propensity, or persistency model logic or parameters always require human sign-off, regardless of LLM-as-judge score.

Hard rule: GitHub Actions authenticates to AWS via OIDC -- no static AWS keys stored as secrets.

Hard rule: no production customer or carrier data in ad hoc prompts, only through the logged, contract-defined pipeline.

Workflow: spec -> persona review by each person -> planning -> human signoff -> implementation -> automated tests →  LLM-as-judge -> required human sign-off sign-off gate(s) -> deploy.


