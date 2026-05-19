---
title: "I built a multi-agent AI system that catches its own mistakes"
description: "How our team turned a one-shot LangChain pipeline into a cyclic LangGraph multi-agent system for pharmaceutical dispatch — and why the loop is the whole point."
author: "Yiu-Hon (Jeremy) Lee, with House B Team 2"
date: 2026-05-18
tags: [langgraph, multi-agent, ai, ucla-msba, pharmaceutical-logistics, side-project]
---

## The problem with one-shot AI pipelines

If you've ever shipped an AI feature to production, you know this feeling.

Your demo works beautifully. You feed it clean inputs, the LLM produces a confident-sounding output, and everyone in the room nods. Then someone in the back asks the question that ruins your week: *"What happens when it gets it wrong?"*

In a one-way pipeline — input goes in, output comes out, nothing in between checks the work — the answer is *nothing happens*. The wrong output goes straight to the user. The LLM doesn't know it's wrong. The next step in the chain doesn't know it's wrong. By the time a human sees it, the damage is downstream.

This was the situation we inherited at the start of our UCLA MSBA Industry Seminar II project. SeeWeeS Specialty — a fictional but realistic pharmaceutical logistics company — needed an AI system to help their Director of Operations make the morning dispatch call for time-critical, temperature-sensitive shipments. The starter code was a clean LangChain pipeline: read the playbook PDF, analyze the CSV, check the weather, plan, write a report, email it. Five steps, one direction, done.

It worked. It also had a problem nobody had named yet.

> *If the planner suggests an unsafe plan — a Tier 1 cold-chain shipment on a non-refrigerated truck, say, which costs 180 penalty points per unit — nothing in the pipeline catches it. The report just gets written. The email just gets sent. The Director just gets a confidently-wrong plan for a 7 AM decision involving life-critical medicines.*

The decision-maker is a senior executive with maybe 30 seconds to read the report before approving it. The system was, in effect, trusting the LLM to never be wrong on a problem where being wrong has asymmetric and expensive consequences. That's not a system. That's a demo with a UI.

So we rebuilt it. The rebuilt version is a cyclic LangGraph multi-agent system that plans, then audits its own plan against hard-coded safety rules, and if the audit fails, sends the plan back to the planner with structured feedback before any report reaches leadership. The loop is the whole point.

This is the story of that rebuild.

## The shape of the original pipeline

Here's what we started with. A linear LangChain DAG: every node fires exactly once, every edge points forward, no node can ever ask another node to redo its work.

![Baseline LangChain pipeline: START → pdf_context → csv_analysis → weather → planner → report → email → END, with no validation step](./images/figure1-baseline-pipeline.png)
*Figure 1. The baseline pipeline (LangChain-style). Five steps in a fixed order, no validation, no feedback. If the planner is wrong, leadership gets a wrong plan.*

You can see the architecture in one glance. The data flows left to right, top to bottom, and the only "decision-making" happens inside the `planner` node, which is an LLM call. If that LLM call produces something subtly wrong — forgets to mention an unfulfilled route, understates the total penalty, fails to flag an escalation when weather risk is at the maximum — the `report` node downstream has no idea. It just writes up whatever the planner said.

This isn't a LangChain flaw. LangChain is a perfectly good tool for chaining LLM calls in a fixed sequence. The flaw is using a chained pipeline for a problem that needs a feedback loop. Pharmaceutical dispatch is one of those problems. Most production AI problems are, actually — anything where the cost of a wrong answer is meaningfully higher than the cost of doing the work twice.

## What we changed

We rebuilt the architecture in LangGraph, which adds two things a one-way LangChain pipeline cannot give you:

- **Conditional edges.** After a node runs, a routing function inspects what came out and decides which node to go to next. Different inputs produce different paths through the graph.
- **Cyclic edges.** A node can route *back* to an earlier node. This is what enables self-correction.

We used both. Here's the new architecture, with the three new nodes in amber.

![Enhanced LangGraph multi-agent system: pdf_context → csv_analysis+reconciliation → weather (per route) → allocation (NEW) → planner → auditor (NEW), with a dashed "revise (max 2)" edge from auditor back to planner, a "failed" path through increment_retry (NEW), and a "passed" path to report → email → END](./images/figure2-cyclic-multi-agent.png)
*Figure 2. Enhanced LangGraph multi-agent system. Three new nodes are shown in amber: `allocation`, `auditor`, and `increment_retry`. The auditor sends failed plans back to the planner via the dashed "revise" edge, capped at 2 retries.*

Three architectural changes do most of the work:

- **A new `allocation` node** between `weather` and `planner`. It takes per-route demand, per-route weather risk, and the resource pool (6 drivers, 4 standard trucks, 2 refrigerated trucks per day), and runs a deterministic Python algorithm that minimizes total penalty points. The LLM does not compute the allocation; it only explains it later.
- **A new `auditor` node** between `planner` and `report`. It runs five fixed checks against the proposed plan and returns a structured object describing what passed and what failed.
- **A conditional edge from the auditor.** If the audit passed, go to the report. If it failed and we haven't already retried twice, loop back to the planner with the violations as structured feedback. If it failed and we've hit the retry cap, still go to the report — but flag the plan as not-fully-validated.

That third bullet — the loop — is the whole thing. Everything else is supporting infrastructure.

## The design decision I'm most proud of: deterministic audits

We had a fork-in-the-road moment when designing the auditor. The obvious move, the move every AI tutorial pushes you toward, is to have *another LLM* audit the planner's output. Agent A writes, Agent B critiques, Agent A revises. This is the "LLM-as-judge" pattern and it's everywhere in the agentic-AI literature right now.

We didn't do that. Our auditor is plain Python. Five hard-coded checks, no model calls.

This was the most important design call in the project, so let me explain why we made it.

**Reproducibility.** If you re-run our system on the same inputs, you get the same audit result every single time. LLM judgments don't have this property. At temperature 0.2 they're *mostly* consistent, but "mostly" is not what you want guarding a 7 AM call involving life-critical medicines. A reviewer running our code at midnight should see the same audit outcome we saw at noon.

**Auditability.** A reviewer can read the check code and verify it matches the playbook. The check `CHECK_3_HIGH_WEATHER_ESCALATION` is twelve lines of Python that say *"if any route has weather risk = 3, the plan narrative must contain the word 'escalation' (case-insensitive)."* You can hand that to a compliance officer and they can sign off. You cannot hand them an LLM and ask them to verify what it'll judge tomorrow.

**Speed and cost.** Each LLM audit call would be a few hundred to a few thousand tokens. Each Python audit completes in microseconds and costs nothing. Over a year of daily dispatches, with up to 2 retry loops per run, this is the difference between a $0 audit budget and a meaningful one.

**Trust.** When our system says "audit passed," it actually passed measurable rules. When an LLM judge says "audit passed," it means an LLM thinks it passed. Those are different statements and only one of them is something a regulated industry can act on.

The pattern, stated generally: **keep the math in Python, let the AI handle the storytelling.** The allocator computes the optimal assignment. The auditor checks the plan against rules. The LLMs write the executive narrative, summarize the risks, draft the email. Each part of the system does what it's good at, and the system as a whole is more reliable than any single agent inside it.

## The five audit checks

For concreteness, here's what the auditor actually checks:

1. Every unfulfilled route must be named in the plan narrative. (No silently dropping shipments.)
2. Allocated resources cannot exceed the available pool. (No phantom trucks.)
3. If any route has weather risk = 3, the plan must mention escalation. (No quietly accepting storm-level risk.)
4. If total penalty is greater than zero, the plan must state the exact number. (No hiding the cost.)
5. No Tier 1 deadline miss may be silently accepted. (Life-critical shipments get named.)

A sixth optional check (`--demo-loop` flag) requires the plan to show its summation arithmetic explicitly — *"120 + 120 + 120 + 240 = 600"*, not just *"600 points total"*. This one is engineered to fail on the first pass so we can reliably demonstrate the audit loop firing.

## The loop in action

Two screenshots are worth a thousand words of architecture talk. First, the normal path — audit passes on the first try, plan goes straight to the report:

![Console output: [AUDITOR pass #1] passed=True, violations=0 (demo_mode=False); [ROUTER] Audit passed -> proceeding to report.](./images/figure3-normal-mode-console.png)
*Figure 3. Normal mode. Audit passes on the first attempt and the system proceeds straight to the report node.*

Now the demo mode, with the stricter sixth check engaged. The first plan fails because it states the penalty total but doesn't show the arithmetic. The auditor returns structured feedback. The planner consumes that feedback, revises, and the second attempt passes:

![Console output: [AUDITOR pass #1] passed=False, violations=1 (demo_mode=True) — [medium] (CHECK_6_GRAND_TOTAL_SUMMATION_DEMO) Plan states the 600-point total but does not show an explicit summation line; [ROUTER] Audit failed (attempt 1) -> looping back to planner; [AUDITOR pass #2] passed=True, violations=0; [ROUTER] Audit passed -> proceeding to report.](./images/figure4-demo-mode-console.png)
*Figure 4. Demo mode. The first audit pass fails with structured feedback, the planner revises, and the second pass succeeds.*

That single screenshot proves three things at once:

- The cyclic graph genuinely loops back. It is not a linear pipeline with a try/except dressed up to look like a loop.
- The planner consumes the structured audit feedback. The revised plan addresses the specific violation, which means the feedback channel between agents is actually carrying signal.
- The system stops correctly. It does not loop forever. The retry cap is 2, and after that the report goes out with a not-fully-validated flag — graceful degradation, not silent failure.

The first time I saw this fire end-to-end on real data, the planner produced a plan that didn't show the penalty math, the auditor flagged it, the planner revised, and the audit passed. I sat there watching the console and felt the system click into being *alive* in a way the linear version never did. A demo can look polished. A multi-agent loop can be *correct* even when the AI gets it wrong on the first pass, because it knows how to check itself.

## The other enhancement: deterministic resource allocation

The `allocation` node deserves a quick mention because it's where the second project enhancement lives.

The Director's morning problem, stated as math, is: assign 6 drivers, 4 standard trucks, and 2 refrigerated trucks across two delivery corridors (Newark → Boston via I-95, Newark → Philadelphia) on a 48-hour planning horizon, such that total penalty points are minimized.

The penalty model is asymmetric and that's what makes the problem interesting:

| Violation | Penalty per unit |
|---|---|
| Tier 1 deadline missed (life-critical, 6h deadline) | 100 pts |
| Tier 2 deadline missed (specialty, 12h deadline) | 40 pts |
| Cold-chain breach (added on top of deadline penalty) | +80 pts |
| Late delivery still within deadline | 10 pts |

A Tier 1 cold-chain shipment on a non-refrigerated truck costs 100 + 80 = 180 penalty points per unit. A Tier 2 standard shipment that's late but on time costs 10. That's an 18× difference, which means the allocator's job is mostly about getting cold-chain capacity to the right place and not getting clever about anything else.

We implemented this as a greedy allocator that serves demand in descending order of per-unit penalty exposure:

1. Tier 1 cold-chain (180 pts/unit) — served first
2. Tier 2 cold-chain (120 pts/unit) — next
3. Tier 1 standard (100 pts/unit)
4. Tier 2 standard (40 pts/unit)

Within a tier, ties are broken by weather risk: the corridor with the higher weather risk gets served first, because weather risk increases the chance of a downstream miss.

Greedy is not globally optimal in general, but for two corridors and four tiers it matches the brute-force optimum on every test case we ran. If we extended this to ten corridors we'd swap in an integer-programming solver; for two, greedy is correct and far easier to audit.

Why do this in Python instead of asking the LLM to allocate? Same reason as the auditor. LLMs are bad at arithmetic, bad at constraint satisfaction, and inconsistent at both. They are *great* at taking a deterministic answer and writing a paragraph explaining it. We let each tool do what it's good at.

## What the Director actually sees

Everything I've described above — the agents, the loops, the audits, the allocations — is invisible to the actual end user. The Director of Operations gets one thing in the morning: a one-page PDF report. Here it is.

![One-page executive PDF report titled "SeeWeeS Specialty Dispatch Report - 48-Hour Multi-Corridor Operations Plan - 2026-05-10 11:34" with a VALIDATED badge, sections for Executive Summary (600 total penalty points, plan validation passed), Top Risks, Recommended Actions, Per-Corridor Demand table, Per-Corridor Weather Risk table, Resource Allocation Plan table, Violations table totaling 600 points, Audit Trail showing Attempt 1 PASSED with 0 violations, and Data Quality stats showing 129 rows in, 124 kept, 29 fixes, 5 excluded](./images/figure5-executive-pdf-report.png)
*Figure 5. The one-page executive dispatch report. Everything above the fold can be read in 30 seconds: total penalty, validation status, executive summary, top 3 risks, top 3 recommended actions.*

A few things worth noticing in this report:

**The VALIDATED badge in the top right.** That badge is the surface signal of the audit loop. If the audit had failed twice and the report went out with the not-fully-validated flag, the badge would change. The Director can tell at a glance whether to trust the plan or escalate.

**The 600-point penalty is reported in three places** — the headline number top-right, the prose summary, and the violations table at the bottom that itemizes how the 600 was assembled (`120 + 120 + 120 + 240 = 600`). This is exactly what audit check #6 enforces. The arithmetic is visible because we wrote a rule that says it has to be.

**The audit trail near the bottom.** "Attempt 1 PASSED, 0 violations" is provenance. If the run had needed a retry, this section would show "Attempt 1 FAILED, Attempt 2 PASSED" with the violations from attempt 1 listed. Auditability for the people who'll audit *us*.

**Data Quality & Reconciliation at the very bottom.** 129 rows in, 124 kept, 29 fixes, 5 excluded. This is the silent part of the pipeline doing its job: alias matching against the Item Master Appendix, legacy ID resolution, disambiguation. The Director doesn't need to know the details, but the row counts tell them whether the upstream data quality is normal or pathological.

## What I'd do differently

A few honest notes on limitations:

**The greedy allocator isn't globally optimal in general.** For two corridors and a small resource pool it matches brute-force, but if we scaled this to ten corridors we'd hit the wall fast. The right next step is an integer-programming solver (or an LP relaxation with rounding); the current Python code is structured so that the allocator is a single function you can swap.

**No human-in-the-loop checkpoint.** The original project brief included a "human approval" enhancement (#4) that we did not implement. In a real deployment, the Director probably wants to manually approve high-risk plans even when the auto-audit passes. LangGraph's `interrupt()` function is the right tool here and we'd build it next.

**Static weather thresholds.** The playbook hard-codes 15 mm rain, 45 km/h winds, and 0°C as the risk thresholds. These don't account for seasonality or local micro-climates. In real operations these would be dynamic.

**Shallow trend analysis.** We have 14 days of synthetic history. Real trend detection needs months. We didn't pursue Enhancement #3 (deep-dive trends) because the data didn't support it.

**No cost model.** The allocator minimizes *penalty points*, but a real Director also cares about operational cost. Sometimes paying for an extra refrigerated truck rental is cheaper than absorbing 240 penalty points. We'd add a cost layer that lets the allocator optimize the trade-off, not just penalty alone.

**Two-corridor scope.** The brief specified Newark→Boston and Newark→Philadelphia. Real specialty pharma logistics covers dozens of lanes. The architecture scales, but every test we ran was on these two.

## The thing I want you to take away

The biggest lesson from this project, if you're building anything similar:

**A linear AI pipeline is a demo. A cyclic multi-agent system is a product.**

The cycle is what makes the difference. Not because cycles are inherently magical — they're just edges in a graph — but because the cycle is where validation lives, and validation is where reliability lives, and reliability is the difference between something you can put in front of a real executive making a real decision and something you can only show at a hackathon.

The cycle does not need to involve another LLM. In fact, it probably shouldn't. The most reliable cycles are the ones where deterministic checks gate the LLM's output and force it to revise on failure. The AI handles the storytelling. The Python handles the safety. The graph wires them together.

That's the whole architecture. Five agents, five audit checks, one Python allocator, two-retry loop, one PDF. That's the system that knows when to send the plan and when to send it back.

---

**Project repo:** [github.com/lyhjeremy/MSBA-B2](https://github.com/lyhjeremy/MSBA-B2) — source code, data, and full technical write-up under [`SeeWeeS_Multi_Agent/`](https://github.com/lyhjeremy/MSBA-B2/tree/main/SeeWeeS_Multi_Agent).

**Team:** Jiyoung (Flora) Jeong, Yiu-Hon (Jeremy) Lee, Nilay Maity, Zichen (Billy) Qiu, Chao En (Becca) Shih, Zhihan (Jasmine) Zhang. UCLA MSBA, MGMTMSA413 Industry Seminar II, Spring 2026.
