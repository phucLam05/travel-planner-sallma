**RESEARCH PROPOSAL**

**Enhancing SALLMA for State-Aware Multi-Agent Travel Planning with Real-Time Group Coordination**

| Research title (English) | Enhancing SALLMA for State-Aware Multi-Agent Travel Planning with Real-Time Group Coordination |
| :---: | :---- |
| **Sub-committee** | Information Technology |
| **Group name** | Nhóm 2 |
| **Authors** | Bố tên Dũng |
| **Mentor** | Vũ LS |

**Abstract**

Large Language Model (LLM) applications increasingly require persistent context, verified data sources, and task-specific execution. The original SALLMA paper proposes a two-layer multi-agent architecture that separates real-time agent orchestration (Operational Layer) from workflow, agent, and deployment metamodel management (Knowledge Layer). However, the paper validates SALLMA only through small-scale, qualitative proof-of-concept scenarios and leaves open questions about state synchronization, deterministic computation, conflict handling, and domain-specific evaluation. This proposal extends SALLMA to a practical group travel-planning system — SALLMA Travel Planner — where multiple users collaboratively build and refine an itinerary in real time. The system introduces shared persistent memory for group-room state, a RAG-based Research Agent connected to a travel knowledge base, a Planner Agent for itinerary generation and lodging selection, and a deterministic Budget Node for cost calculation. The study evaluates whether a state-aware multi-agent architecture can reduce hallucination, improve itinerary consistency, and support scalable collaborative planning compared with a single-agent baseline. Expected results include an implemented open-source prototype, a refined SALLMA architecture for travel planning, and evaluation evidence based on correctness, consistency, latency, and user-perceived usefulness.

**Keywords:** *SALLMA, multi-agent system, LLM architecture, travel planner, RAG, shared memory, state synchronization, LangGraph, pgvector*

# **1\. Introduction**

## **1.1. Literature Review**

The SALLMA paper (Becattini et al., SATrends 2025\) identifies a major architectural limitation in current LLM-based systems: many real-world applications rely on a single general-purpose LLM agent. Such systems can answer diverse requests, but they are difficult to optimize for heterogeneous tasks because each task may require different prompts, tools, hyperparameter settings, memory scope, and data sources. The paper therefore proposes SALLMA as a distributed, modular, multi-agent architecture for LLM-intensive software products. Its key idea is to split responsibilities between two layers: the Operational Layer, which processes requests and orchestrates specialized agents at runtime, and the Knowledge Layer, which stores reusable metamodels and configurations for workflows, agents, and deployment.

The six core items from the original paper — its introduction and research gap, motivation, architecture overview, key architectural decisions, proof-of-concept implementation, and conclusion with future work — are summarized and evaluated in the table below. For each item, this proposal identifies an existing limitation and proposes a concrete improvement implemented in the SALLMA Travel Planner.

 

| No. | Original paper item | Existing contribution | Limitation identified | Proposed improvement |
| ----- | ----- | ----- | ----- | ----- |
| 1 | Introduction & research gap | SALLMA addresses the gap between centralized single-agent LLM systems and distributed task-specific multi-agent architectures. | The paper remains general-purpose; no concrete domain is targeted, so evaluation criteria are vague. | Narrow the domain to collaborative group travel planning to enable measurable, repeatable evaluation of the architecture. |
| 2 | Motivation | Single-agent systems lack persistent memory, task-customization, ground-truth validation, and fail under distributed load. | Motivation stays theoretical; no concrete scenario is used to illustrate the pain points of single-agent planning. | Use a travel-planner scenario to concretely demonstrate hallucination in place data, inconsistent budgets, and lost context across turns. |
| 3 | SALLMA overview (two-layer design) | Operational Layer handles real-time orchestration; Knowledge Layer stores metamodels for workflows, agents, and deployments. | State synchronization across concurrent users is not addressed; the design assumes one user per session. | Add a shared persistent group-room memory model with conflict-handling logic (event-log, last-write-wins for minor fields, group confirmation for critical fields). |
| 4 | Key architectural decisions | Modular, containerized, distributed deployment; components are positioned by resource and latency requirements. | The architecture assumes reliable bandwidth and secure environments with no degraded-mode specification. | Define degraded-mode behavior, queue-based request handling, rate limiting, and monitoring hooks for resource constraints. |
| 5 | PoC implementation & technologies | Docker, Kubernetes, Python, LangChain, SQL/NoSQL databases, RAG-based retrieval confirmed multi-agent orchestration at small scale. | Evaluation is qualitative and limited; no baseline comparison, no metric-based results, no scalability data. | Implement evaluation against a single-agent baseline using correctness, budget accuracy, RAG faithfulness, latency, and concurrent-room stability metrics. |
| 6 | Conclusion & future work | SALLMA can support adaptive workflows and needs industrial validation as future work. | No open-source prototype is provided; future-work items are generic with no implementation plan. | Deliver an open-source Travel Planner prototype (LangGraph, PostgreSQL/pgvector, Streamlit, PyDeck) at https://github.com/phucLam05/travel-planner-sallma with reproducible evaluation. |

 

## **1.2. The Necessity of the Research**

Travel planning is a suitable domain for extending SALLMA because it requires multiple simultaneous reasoning capabilities that are difficult for a single LLM agent to handle reliably. A user asking to plan a group trip may need attraction recommendations, restaurant choices, accommodation options, budget estimation, route visualization, schedule constraints, and handling of group member preferences — all within one conversation. If all these responsibilities are handled by a single LLM, the system tends to hallucinate place information, lose previously stated preferences, produce inconsistent budgets, and fail entirely when two users submit changes concurrently. A state-aware multi-agent design is therefore necessary to divide responsibilities while maintaining a shared source of truth across all agents and users.

Research question: How can a SALLMA-based multi-agent architecture be extended to support real-time group travel planning while maintaining persistent context, verified information retrieval, deterministic budget calculation, and scalable task-specific orchestration?

Hypothesis: A state-aware SALLMA Travel Planner with specialized agents, RAG, shared group-room memory, and deterministic computation will generate more consistent and verifiable travel plans than a single-agent LLM planner, particularly under multi-step and multi-user scenarios.

## **1.3. Feasibility of Research**

* Research design: design-science research with prototype implementation and comparative evaluation against a single-agent baseline.  
* Population and sample: small-scale student or user group testing, with 10–20 travel-planning tasks and 3–5 simulated concurrent group-room scenarios.  
* Data sources: curated travel-place records, restaurant and accommodation samples, seed data in PostgreSQL, vector embeddings for RAG in pgvector, and conversation histories generated during testing.  
* Budget and funding: the prototype can be developed with open-source components and limited cloud/API credits; most tests can run locally with Docker Compose.  
* Timeframe: a four-to-six-week prototype cycle is feasible given the defined scope of itinerary generation, RAG retrieval, budget calculation, and map visualization.  
* Risks and mitigation: API rate limits (mitigated by caching and local LLM options), incomplete travel data (mitigated by curated seed data), hallucinated responses (mitigated by deterministic Budget Node and RAG grounding), slow vector search (mitigated by pgvector index tuning), concurrent state conflicts (mitigated by event-log conflict resolution), and limited participants (mitigated by scenario-based scripted tests).

# **2\. Research Objectives**

* Analyze the original SALLMA architecture and identify all limitations that remain unresolved in practical, multi-user applications.  
* Design a state-aware multi-agent Travel Planner based on SALLMA with explicit separation between runtime orchestration and knowledge/configuration management.  
* Implement specialized agents for intent/workflow classification, travel research (RAG), itinerary planning and lodging decisions, and deterministic budgeting.  
* Introduce shared persistent group-room memory and evaluate consistency under sequential and concurrent itinerary changes.  
* Compare the improved multi-agent architecture with a single-agent baseline using measurable correctness, consistency, latency, and collaboration quality criteria.

# **3\. Research Scope**

The research focuses on the backend and architectural improvement of SALLMA for a travel-planning use case. The prototype covers natural-language planning requests, RAG-based retrieval of real places stored in PostgreSQL/pgvector, itinerary generation, deterministic budget calculation, route visualization with PyDeck or a similar library, and shared group-room memory synchronization. The open-source implementation is published at https://github.com/phucLam05/travel-planner-sallma.

Out of scope: real-time booking or payment integration, live hotel inventory APIs, production-grade cloud deployment, and support for languages other than English. These are treated as future extensions. The evaluation focuses on functional correctness, architectural suitability, and group-collaboration consistency rather than commercial deployment readiness.

# **4\. Approach and Method**

## **4.1. Proposed Improved Architecture**

The proposed improvement retains the original SALLMA two-layer design and specializes it for group travel planning. The Operational Layer handles live requests from the user interface and executes cognitive workflows. The Knowledge Layer stores workflow definitions, agent configurations, deployment constraints, travel data, vector indexes, and the shared memory schema.

### **Operational Layer components**

* Intent/Workflow Agent: classifies the incoming request, detects whether the user is creating, refining, budgeting, or visualizing a trip, and selects the correct cognitive workflow from the Knowledge Layer.  
* Research Agent: performs RAG retrieval from PostgreSQL/pgvector to ground recommendations in stored, verified travel data, reducing hallucination.  
* Planner Agent: builds the itinerary, selects activities, meals, and lodging choices based on route constraints, and restructures the schedule after any user-triggered change.  
* Budget Node: a non-LLM deterministic component that computes costs from structured data to eliminate arithmetic hallucination.  
* Map/Route Tool: extracts coordinates from structured JSON output and visualizes the route using PyDeck or a similar map rendering layer.

### **Knowledge Layer components**

* Workflow Metamodel Catalog: templates for Create Trip, Refine Trip, Recalculate Budget, and Update Group Room workflows.  
* Agent Configuration Catalog: stores prompts, model selection, temperature, tool access, memory scope, and retry policy for each agent.  
* Deployment Metamodel Catalog: defines local/cloud execution settings and auto-scaling rules for high-traffic group rooms.  
* Travel Knowledge Base: verified places, activities, restaurants, accommodation, costs, geolocation, opening-time notes, and embeddings stored in PostgreSQL/pgvector for RAG.  
* Shared Persistent Memory: stores the current itinerary state, user preferences, group votes, budget state, and a full change-event history per room.

## **4.2. State Synchronization and Group-Room Improvement**

The primary architectural contribution over the original SALLMA paper is a real-time group-room model for collaborative planning. In the original SALLMA design, each user conversation is isolated. In the proposed system, all members of a travel group share one persistent trip state stored in the Shared Persistent Memory component. When any member changes a travel date, destination, hotel preference, budget ceiling, or activity priority, the update is written as an event to shared memory. The Cognitive Workflow Manager then triggers the affected agents: the Planner Agent rebuilds affected itinerary segments and re-checks lodging consistency, and the Budget Node recalculates costs.

To reduce write conflicts, every change is stored as a structured event record containing the user identifier, timestamp, affected field name, old value, and new value. The latest accepted state is reconstructed from the event log. For minor fields, a last-write-wins policy applies. For critical constraints such as total budget, travel dates, or destination country, the system requires explicit group confirmation before overwriting the shared plan. This makes SALLMA go from a general multi-agent blueprint to a state-aware collaborative planning architecture with auditable change history.

## **4.3. Evaluation Method**

The improved system will be evaluated through scenario-based tests and comparison with a single-agent LLM baseline using the following metrics:

* Correctness: percentage of place recommendations retrieved from the verified knowledge base rather than generated by the LLM without grounding.  
* Budget accuracy: absolute difference between the LLM-generated total cost estimate and the deterministic Budget Node output across all test scenarios.  
* Consistency: number of contradictions detected between the generated itinerary, map route, accommodation choice, and budget across a multi-turn session.  
* State retention: ability to preserve user preferences and group-room changes over 10+ conversation turns without loss or hallucination.  
* Latency: average end-to-end response time for Create, Refine, and Budget workflows under multiple simulated concurrent group rooms.  
* User-perceived usefulness: questionnaire-based rating (1–5 Likert scale) of itinerary clarity, trustworthiness, and ease of group collaboration.

# **5\. Research Plan**

The following table describes the planned tasks, expected outputs, schedule, and responsible team member for each phase of the project.

 

| No. | Date | Task | Output | Person in charge |
| ----- | ----- | ----- | ----- | ----- |
| 1 | Week 1 | Review SALLMA paper; identify 6 core items and their limitations. | Literature review table (this proposal, Section 1.1). | Member 1 |
| 2 | Week 1–2 | Design improved Knowledge Layer schema, shared memory model, and agent configuration catalog. | Architecture design document and data schema. | Member 2 |
| 3 | Week 2–3 | Implement core LangGraph workflow, RAG retrieval pipeline, and agent routing logic. | LangGraph workflow and pgvector RAG prototype. | Member 3 |
| 4 | Week 3 | Implement Planner Agent, Budget Node (deterministic), and PyDeck map visualization. | Working travel-planning prototype with all agents. | Member 4 |
| 5 | Week 4 | Implement group-room shared state, event-log conflict handling, and concurrent-room scenarios. | Shared-state module and event-log mechanism. | Member 5 |
| 6 | Week 5–6 | Run evaluation against single-agent baseline; analyze results; write final report and slides. | Evaluation table, final report, presentation deck. | Member 6 |

 

# **6\. Expected Results**

Theoretical contribution: a domain-specific extension of SALLMA that clarifies how Operational Layer orchestration, Knowledge Layer configuration, RAG retrieval, deterministic tools, and shared persistent memory interact within a realistic multi-user application. The six-item analysis in Section 1.1 constitutes the theoretical foundation.

Methodological contribution: a structured, reproducible evaluation plan for comparing multi-agent and single-agent LLM planners across five measurable dimensions.

Practical contribution: an open-source Travel Planner prototype built with LangGraph, PostgreSQL/pgvector, Streamlit, and PyDeck. The code and evaluation scripts are available at https://github.com/phucLam05/travel-planner-sallma.

Expected improvement over the original paper: this work moves from a general, qualitative PoC to a testable domain-specific use case with measurable correctness, consistency, latency, and collaboration outcomes, directly addressing the six limitations identified in the literature review.

**References**

\[1\] M. Becattini, R. Verdecchia, and E. Vicario, "SALLMA: A Software Architecture for LLM-Based Multi-Agent Systems," SATrends 2025\.

\[2\] phucLam05, "travel-planner-sallma," GitHub, 2026\. Available: [https://github.com/phucLam05/travel-planner-sallma](https://github.com/phucLam05/travel-planner-sallma)

\[3\] J. He, C. Treude, and D. Lo, "LLM-based multi-agent systems for software engineering: Vision and the road ahead," arXiv:2404.04834, 2024\.

\[4\] S. Minaee et al., "Large language models: A survey," arXiv:2402.06196, 2024\.

\[5\] I. K. Aksakalli et al., "Deployment and communication patterns in microservice architectures: A systematic literature review," J. Syst. Softw., vol. 180, 2021\.

\[6\] M. Fowler, "Dealing with properties," https://martinfowler.com, June 1997\.

 

# **Appendix A — Suggested Presentation Distribution**

The following table maps each team member to the section of the proposal they should present, with a single key message for each section.

 

| Member | Main content | Key message |
| ----- | ----- | ----- |
| 1 | Introduction, research problem, hypothesis | Single-agent LLM systems lack persistent context, task-specific configuration, and reliable validation — the core motivation for SALLMA. |
| 2 | SALLMA Knowledge Layer and metamodel design | The Knowledge Layer is a metadata/configuration layer that drives agent behavior without participating in live request processing. |
| 3 | Operational Layer, data flow, and technology stack | Requests move through intent detection → workflow selection → deployment → cognitive workflow execution using LangGraph and pgvector. |
| 4 | Original PoC analysis and limitation identification | The original PoC confirms viability but is qualitative and lacks measurable domain-specific evaluation — the gap this proposal addresses. |
| 5 | Improved Travel Planner and group-room state synchronization | Shared persistent group-room memory synchronizes itinerary, accommodation, and budget changes across concurrent users via an event-log model. |
| 6 | Evaluation plan, expected results, and conclusion | The improved design is tested with correctness, budget accuracy, consistency, latency, and user-usefulness metrics against a single-agent baseline. |

   
**COMMITMENT ON RESPONSIBLE ARTIFICIAL INTELLIGENCE USAGE IN RESEARCH**

We, the authors of the research paper titled "Enhancing SALLMA for State-Aware Multi-Agent Travel Planning with Real-Time Group Coordination", confirm that all members comply with the rules relevant to Artificial Intelligence (AI) regulations and ethical guidelines in research practices, described as follows:

* AI is used only as an assistant for correcting grammar, structure, and phrasing in academic writing.  
* AI usage is NOT engaged with the creation of content or drafting of the research paper, production of fake data, or literature synthesis.  
* AI usage has been checked and confirmed by all authors. Each author bears full responsibility for the accuracy, transparency, and originality of their sections, including citations and references.  
* All authors disclose the use of generative AI and AI-assisted technologies to other co-authors, helping them understand where and how AI was applied in research preparation.

Hereby, we confirm and take full responsibility for the accuracy and transparency of the provided details.

 

| Author 1 | Author 2 | Author 3 |
| ----- | ----- | ----- |
| (Signature & Full name) | (Signature & Full name) | (Signature & Full name) |

**Note:**

* Research proposal presented in English, A4 paper, single column, Times New Roman 11pt, maximum 10 pages (excluding references and appendices).  
* Citations follow APA standard for Economics/Business/Language/Multimedia/Digital Design sub-committees; IEEE standard for Information Technology sub-committee. See https://libguides.murdoch.edu.au/IEEE/home for IEEE and https://libguides.murdoch.edu.au/APA/all for APA.