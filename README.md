# MSBA-B2

**UCLA MSBA AI Agents Project Challenge 2026 · House B Team 2**

## Team Members

- Jiyoung (Flora) Jeong
- Yiu-Hon (Jeremy) Lee
- Nilay Maity
- Zichen (Billy) Qiu
- Chao En (Becca) Shih
- Zhihan (Jasmine) Zhang

## Project

This repository contains our submission for **MGMTMSA413 Industry Seminar II (Spring 2026)** — a multi-agent AI system built for time-critical pharmaceutical logistics.

We redesigned the SeeWeeS Specialty ops-reporting prototype from a linear LangChain pipeline into a **cyclic LangGraph multi-agent system** that plans, audits, and self-corrects 48-hour dispatch schedules across two delivery corridors. The system handles messy upstream data, cold-chain constraints, per-corridor weather risk, and scarce resources (drivers, standard trucks, refrigerated trucks), then produces a one-page executive report ready for leadership review.

### Key Enhancements

- **Multi-Region Resource Allocator** — a deterministic Python algorithm that minimizes penalty points across both corridors and both days.
- **Self-Correction Audit Loop** — a new Auditor agent runs hard-coded safety checks against every plan; failures loop back to the Planner with structured feedback before any report reaches the Director.

## Getting Started

All source code, data, documentation, and setup instructions live in the [`SeeWeeS_Multi_Agent/`](./SeeWeeS_Multi_Agent) subfolder. Head there for the full README, quick-start guide, and technical write-up.

## Brief writeup
See [agentic-ai-langgraph-article.md](./agentic-ai-langgraph-article.md) for the story behind the rebuild, the architecture, and the design rationale.
