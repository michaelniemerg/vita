# Key Lessons for AI-Native Development

Extracted from the three papers in the project's knowledge base: *The New
SDLC (with vibe coding)*, *Day 5 — Spec-Driven Production Grade Development
in the Age of Vibe Coding*, and *Day 3 — Context Engineering: Sessions,
Memory*. Organized as a rule list; each rule notes which paper it's drawn
from so it can be checked against the source. These are lessons to fold
into the architecture rulebook, not a replacement for it.

---

## 1. Spec-driven development

1. Specs are written before code, and code is treated as disposable — if the
   spec is solid, the implementation can be regenerated or even rewritten in
   a different language without much cost. *(Day 5 — Spec-Driven
   Development)*
2. A good spec includes the full technical design (requirements, schemas,
   API contracts), background on *why* the feature is needed, visual aids
   where useful, and explicit scenarios covering both what good looks like
   and the edge cases. A one-line feature request is not a spec. *(Day 5 — A
   good specification)*
3. Behavior-driven (Given/When/Then) phrasing forces a spec to state state →
   action → outcome explicitly, which is what keeps an agent from guessing.
   *(Day 5 — Behavior Driven)*
4. Treat the `/specs` folder as a lean, compiled instruction set, not free-form
   prose — every unnecessary token in a spec is reasoning capacity and
   latency spent on formatting instead of on the actual problem. *(Day 5 —
   Behavior Driven)*
5. Requirements work is shifting from a document handed between teams to a
   live conversation between humans and AI that produces the spec and an
   initial implementation together — but architecture (the trade-offs
   between consistency, complexity, cost) stays a human-owned decision,
   because AI doesn't have the business context to make those trade-offs.
   *(The New SDLC — Requirements and planning; Design and architecture)*

## 2. Where instructions live (the harness)

6. Instructions aren't dumped into one giant prompt. They're layered:
   chat/session input for short-lived orchestration, a checked-in `/specs`
   folder for durable technical design, reusable skill files for repeatable
   workflows, and system-prompt-level files (a shared cross-tool `AGENTS.md`
   plus a tool-specific project file) for standing rules and identity. *(Day
   5 — Where do the instructions live?)*
7. A harness — the instructions, tools, sandboxes, orchestration logic,
   guardrails/hooks, and observability around a model — is the team's
   responsibility, not the model provider's. It has to be present in every
   phase of the lifecycle, not just during coding. *(The New SDLC — What's
   in the harness; Harness in SDLC)*
8. Start an `AGENTS.md` (or equivalent) with about ten lines: stack,
   conventions, hard rules, workflow. Add a rule every time an agent does
   something it shouldn't repeat. *(The New SDLC — Where to start)*
9. Different phases of work call for different framings of the same agent —
   architect during scaffolding, author during documentation, librarian
   during data work — because each framing changes what the agent checks
   for and what it explicitly avoids doing (e.g., not writing code
   immediately during scaffolding). *(Day 5 — Different Prompts for
   Different Use Cases)*

## 3. MCP as the integration layer

10. Build one MCP server per capability (a database, an API, a file system)
    and any MCP-compatible agent or framework can use it without a custom
    integration — that's the point of building a dedicated MCP server here
    rather than bespoke glue code per consumer. *(Day 5 — MCP: One
    Integration, Every Framework)*
11. MCP (for tool access) and A2A (for cross-agent delegation) are converging
    into the standard connective tissue for multi-agent systems. Adopting
    open standards now keeps the option open to mix models and frameworks
    later without a re-platform. *(The New SDLC — For organizations)*

## 4. Code review at scale

12. Pick the lowest review tier that catches what actually matters, and only
    move up when it demonstrably doesn't: a managed, off-the-shelf reviewer
    (minutes to enable, generic opinions); a hybrid tier — your own review
    skill wired to a CI action, triggered on every PR (a day to set up,
    your criteria); or a fully custom, stateful reviewer agent (owns its
    own runtime, evaluation, and on-call — justified only when the reviewer
    needs to hold context across PRs or the failure mode is a merged
    regression or a leaked secret, not just a noisy comment). *(Day 5 —
    Deploying Agents That Watch Your Repo)*
13. A structured review skill should explicitly separate critical
    vulnerabilities, logic/efficiency issues, readability, and edge cases,
    and should have a clear "nothing wrong" output (not just silence) so a
    clean PR isn't ambiguous. *(Day 5 — Code Reviews, code-check.md
    example)*
14. Shift human review attention away from nitpicking style on
    agent-written code and toward architectural integrity; let linters and
    shared style skills handle the small stuff. *(Day 5 — Code Reviews)*
15. A "conditional LGTM" — approval contingent on automated tests passing,
    with auto-merge once they do — avoids multi-timezone review bottlenecks
    without dropping the review itself. *(Day 5 — Code Reviews)*
16. When PR volume or merge conflicts spike from agent output, the fix is
    usually process (clearer file/API ownership, smaller PRs, a named
    part-owner for necessary overlaps) rather than reviewing faster. *(Day
    5 — Code Reviews)*
17. Blame issues on broken integration process, not on the individual who
    used the agent — a no-blame culture matters more, not less, as AI
    output volume goes up. *(Day 5 — Code Reviews)*

## 5. Testing and evaluation are different things

18. A unit test asks a binary question (did this return the right value?).
    An evaluation asks a scored question (is this at least as good as the
    baseline?), because a model-driven component can pass every unit test
    on its tools and still fail by choosing the wrong tool or hallucinating
    a fact — that failure mode isn't a bug to eliminate, it's a property of
    the model that has to be measured differently. Keep both, for different
    purposes. *(Day 5 — Evaluation)*
19. Have the agent write a failing test (or a reproduction command) before
    it attempts a fix, so every iteration is backed by a check that
    outlives the session. *(Day 5 — AI Generated Test Coverage)*
20. An eval suite is also how intent gets communicated to an agent — a
    well-written eval tells the agent what "correct" means at least as
    precisely as a natural-language prompt does. *(The New SDLC — AI also
    transforms test generation itself)*
21. Run evaluation as a continuous loop, not a one-time gate: evaluate
    against a benchmark, cluster and diagnose failures, fix the prompt or
    tool that caused them, re-verify, and keep monitoring production for
    new failure modes. *(The New SDLC — continuous quality flywheel)*
22. Set the bar for shipping an agent at "passes an eval suite with a clear
    rubric," not "worked in a demo." A demo proves it can succeed once; an
    eval proves it succeeds reliably — and an eval without a defined rubric
    (task success, tool-use quality, trajectory compliance, hallucination
    rate, response quality) doesn't actually measure anything. *(The New
    SDLC — For engineering leaders)*

## 6. Guardrails, sandboxing, and human-in-the-loop

23. Hard-coding constraints into a system prompt is brittle — contexts
    overflow and agents can be talked out of prompt-level rules via
    injection. High-stakes systems need external, tamper-proof governance
    outside the prompt, not just instructions inside it. *(Day 5 —
    Implementing Guardrails)*
24. A two-layer policy check in front of tool calls works well: a fast,
    deterministic structural check (is this tool even allowed for this
    role and environment?), followed by a semantic check for cases a
    regex can't catch (the tool is allowed, but is this specific use of it
    safe — e.g., is it about to send unmasked PII?). *(Day 5 — Policy
    Server)*
25. Agent-executed code and commands should run in an isolated,
    low-privilege, disposable environment, so that if an agent is tricked
    into a destructive action, the damage is contained to something that
    can be wiped, not the host system. *(Day 5 — Sandboxing)*
26. High-stakes actions — production deploys, schema changes, financial
    transactions — get an explicit human-in-the-loop checkpoint regardless
    of how well the agent has performed otherwise. This is the same
    principle behind requiring a human sign-off on pricing/actuarial
    changes in the rulebook, not a separate idea. *(Day 5 —
    Human-in-the-Loop)*
27. Without a human-in-the-loop or a policy check, an agent will optimize
    for the literal goal it was given using whatever access it has —
    that's the actual mechanism behind an agent "going rogue," not a
    mysterious failure. *(Day 5 — Implementing Guardrails)*

## 7. Context hygiene

28. When an agent lacks specific data it needs, it tends to fill the gap
    with whatever strings are already in its context — including
    hardcoded emails, URLs, or other sensitive values it picked up
    earlier. This is a distinct risk from a normal hallucination and
    needs its own mitigation. *(Day 5 — Context Hygiene & Prompt
    Sanitization)*
29. Replace real sensitive values with placeholders in prompts, skills, and
    test fixtures, and resolve them to real (or safely fake) values only
    at execution time — never hardcode real PII into a prompt or a test
    suite. *(Day 5 — Context Hygiene & Prompt Sanitization)*
30. Sanitize agent outputs, not just inputs, so a prompt-injected string
    can't turn into an unintended action against a real system (their
    example: an unrelated button click triggering an unrelated email
    agent, based on a hallucinated URL). *(Day 5 — Zero-Trust Development)*

## 8. Documentation as source of truth

31. In this workflow, documentation isn't a nice-to-have written after the
    fact — if the docs and the code drift apart, the agent starts
    hallucinating against the stale docs. Keeping `README.md` and
    `CHANGELOG.md` current is itself a maintained skill/workflow, not an
    occasional chore. *(Day 5 — Documentation Writing)*
32. Structured docstrings (Google-style for Python, JSDoc for TypeScript)
    help an agent understand a function's contract without re-reading its
    full implementation every time — this is as much for the agent's
    benefit as for a human's. *(Day 5 — Documentation Writing)*

## 9. Sustainability and team culture

33. Approval fatigue is real: a constant stream of small approvals leads to
    reflexive "approve" clicks, which quietly erodes the review's value
    even though the process looks intact. Design review load with this in
    mind rather than assuming more review requests always means more
    scrutiny. *(Day 5 — Sustainability)*
34. Set boundaries so agent approval requests don't bleed into evenings and
    weekends, and hold a regular session where people share patterns their
    agents have surfaced, so isolated discoveries become shared knowledge
    instead of staying siloed. *(Day 5 — Sustainability)*
35. Keep prototyping work and production work explicitly distinct in team
    norms — which branches, environments, and projects are "vibe coding"
    versus "agentic engineering" should be an explicit, named boundary, not
    an assumption, because a blurred line is how a prototype ships by
    accident. *(The New SDLC — For engineering leaders)*

## 10. Economics and token discipline

36. Every character sent to a model — including whitespace and indentation
    in a deeply nested spec — consumes tokens, and tokens are a real
    development-budget and latency constraint, not an abstraction to
    ignore while writing specs. *(Day 5 — Behavior Driven)*
37. Judge AI-assisted development by total cost of ownership, not just
    velocity. Cost shifts between upfront build cost and ongoing
    run/fix/maintain cost, and in this model the ongoing cost is heavily
    driven by token spend — which is exactly why the rulebook's
    per-persona model tiering and weekly cost report matter in practice,
    not just on paper. *(The New SDLC — The Economics of AI Development)*

## 11. Observability and the production substrate

38. A harness without observability — logs, traces, evals, cost and latency
    metering — gives no way to tell whether an agent is doing well or
    quietly drifting, so observability isn't optional tooling, it's part
    of the harness itself. *(The New SDLC — What's in the harness)*
39. What turns a prototype into a production system is the operations
    discipline around it: evals run in CI, traces of every agent run,
    scoped per-agent permissions, and security review tuned to the actual
    failure modes of generated code (hallucinated dependencies, silent
    correctness gaps) — build this before the first production agent
    ships, not after. *(The New SDLC — For organizations)*

## 12. Memory and context (from the Day 3 paper)

40. Putting retrieved memory directly into the system prompt gives it high
    authority and is a clean fit for stable facts (a user profile), but it
    risks the agent over-relating every topic back to that memory, and it's
    incompatible with letting the agent decide for itself whether to fetch
    memory as a tool. Pick one pattern deliberately per use case rather
    than mixing both. *(Day 3 — Context Engineering: Sessions, Memory)*

---

## What this changes in the architecture rulebook

Three things from these papers aren't yet reflected in
`architecture-and-dev-rules.md` and are worth folding in on the next pass:

- **The tiered code-review model** (Section 4 above) — the rulebook
  currently describes one LLM-as-judge design, which maps to "Tier 2:
  Hybrid." Worth stating that explicitly and deciding up front whether any
  path (e.g., `pricing-engine`) warrants Tier 3.
- **The policy server pattern and sandboxing** (Section 6) — the rulebook's
  LLM usage constraints are written as rules a persona is expected to
  follow, not as an external, tamper-proof check in front of tool calls.
  For an MCP server that both dev tooling and the product agent call, a
  structural-plus-semantic policy check in front of every tool call is
  worth adding as its own component, not just a documented rule.
- **Context hygiene / prompt sanitization** (Section 7) — not currently
  addressed at all. Worth a rule specifically for how the product-agent MCP
  server handles any real customer or carrier data it's given.
