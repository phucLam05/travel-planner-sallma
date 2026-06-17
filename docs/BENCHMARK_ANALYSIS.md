# Benchmark Methodology and Results

This document summarizes the full benchmark run exported at:
- JSON: [benchmark_full_20260617_063715.json](../benchmarks/results/benchmark_full_20260617_063715.json)
- Markdown: [benchmark_full_20260617_063715.md](../benchmarks/results/benchmark_full_20260617_063715.md)

## 1. Experimental Setup

- Benchmark size: `30` create prompts
- Multi-turn memory test: `2` sessions, each with `10` turns
- Latency stress test: `5` concurrent simulated group rooms
- Text model: `gemini-3.1-flash-lite`
- Knowledge base: PostgreSQL `places` table with verified hotels, attractions, and restaurants
- Baselines:
  - `Single-agent`: one LLM generates the full itinerary, hotel choice, and budget estimate without database grounding
  - `Multi-agent`: Workflow Agent + Research Agent + Planner Agent + deterministic Budget Node

## 2. Metric Operationalization

### 2.1 Correctness
Correctness is defined as the percentage of recommended places that can be matched to the verified knowledge base. For each generated output, the benchmark extracts all place names from hotel selection and itinerary activities, normalizes them, and fuzzy-matches them against the PostgreSQL `places` table.

Formula:

```text
verified_rate = verified_places / total_places
hallucination_rate = 1 - verified_rate
```

This metric directly measures grounding quality and is the closest automated implementation of the proposal's "retrieved from verified knowledge base" criterion.

Raw benchmark totals for the reported run:

- Single-agent: `109` verified places out of `249` generated places across `30` create cases
- Multi-agent: `418` verified places out of `420` generated places across `30` create cases

Important note: the published values `43.73%` and `99.39%` are **macro-averages across cases**, computed as the mean of the 30 per-case verified rates. They are not the same as the one-shot pooled ratios `109/249` and `418/420`.

### 2.2 Budget Accuracy
Budget accuracy is defined as the absolute difference between the budget claimed in the generated response and a deterministic recomputation of the total trip cost.

Formula:

```text
budget_delta = abs(claimed_total_cost - recomputed_total_cost)
```

The recomputed total cost is derived from:

```text
hotel.price_per_night * hotel.nights + sum(activity.price)
```

For the multi-agent system, the final budget comes from the dedicated Budget Node, while the single-agent baseline relies on the LLM's own arithmetic.

Raw benchmark totals for the reported run:

- Single-agent total absolute budget error across `30` create cases: `15,940,000 VND`
- Multi-agent total absolute budget error across `30` create cases: `0 VND`

The published `531,333 VND` is therefore:

```text
15,940,000 / 30 = 531,333.33 VND
```

### 2.3 Consistency
Consistency is implemented as a rule-based contradiction counter. The checker inspects the final itinerary and hotel metadata for structural inconsistencies, including:

- mismatch between number of itinerary days and hotel nights
- invalid chronological order of activities
- missing coordinates in itinerary entries
- repeated activities across days
- activities placed too far from the selected hotel

The reported value is the average number of detected violations per case or per final multi-turn session.

Raw benchmark totals for the reported run:

- Create benchmark:
  - Single-agent: `6` total violations across `30` cases -> `6 / 30 = 0.2`
  - Multi-agent: `123` total violations across `30` cases -> `123 / 30 = 4.1`
- Multi-turn final session states:
  - Single-agent: `1` total violation across `2` sessions -> `1 / 2 = 0.5`
  - Multi-agent: `12` total violations across `2` sessions -> `12 / 2 = 6.0`

### 2.4 State Retention
State retention is evaluated through 10-turn sessions that repeatedly refine an existing itinerary. The benchmark verifies whether the final state preserves key constraints and accumulated changes, including:

- hotel still exists after multiple refinement turns
- itinerary days are still present
- expected trip length is not lost
- non-hotel refinements do not accidentally erase hotel state
- budget remains present in the final state

Formula:

```text
state_retention_pass_rate = passed_checks / total_checks
```

Raw benchmark totals for the reported run:

- Single-agent: `10 / 10` checks passed across `2` sessions
- Multi-agent: `10 / 10` checks passed across `2` sessions

### 2.5 Latency
Latency is measured as end-to-end workflow time under concurrent load. The benchmark runs `Create`, `Refine`, and `Budget` workflows with `5` simulated concurrent group rooms and records the runtime for `10` samples per workflow.

This metric reflects the practical user-facing delay of each architecture rather than isolated model inference time.

Raw benchmark totals for the reported run:

- Create latency:
  - Single-agent: `10` samples, average `19.814s`, summed sample time approximately `198.14s`
  - Multi-agent: `10` samples, average `85.533s`, summed sample time approximately `855.33s`
- Refine latency:
  - Single-agent: `10` samples, average `18.628s`, summed sample time approximately `186.28s`
  - Multi-agent: `10` samples, average `50.770s`, summed sample time approximately `507.70s`
- Budget latency:
  - Single-agent: `10` samples, average `19.572s`, summed sample time approximately `195.72s`
  - Multi-agent: `10` samples, average `0.000s`, summed sample time approximately `0.00s`

### 2.6 User-Perceived Usefulness
The current implementation does not yet use a human questionnaire. Instead, it reports an automated proxy score derived from:

- clarity
- trustworthiness
- collaboration

The proxy is computed from correctness, budget accuracy, and consistency signals, then mapped to a 1-5 scale. Therefore, this metric should be reported as a provisional approximation rather than a full questionnaire-based human evaluation.

Raw benchmark totals for the reported run:

- Single-agent: total proxy score `125.05` across `30` create cases -> `125.05 / 30 = 4.17`
- Multi-agent: total proxy score `113.59` across `30` create cases -> `113.59 / 30 = 3.79`

## 3. Results Summary

### 3.1 Create Benchmark

| Metric | Single-Agent | Multi-Agent |
|---|---:|---:|
| Cases | `30` | `30` |
| Average latency per create case | `6.897s` | `26.985s` |
| Verified place rate | `43.73%` from `109/249` raw verified places | `99.39%` from `418/420` raw verified places |
| Hallucination rate | `56.27%` from `140/249` raw unverified places | `0.61%` from `2/420` raw unverified places |
| Average budget delta | `531,333 VND` from `15,940,000 / 30` | `0 VND` from `0 / 30` |
| Average consistency violations | `0.2` from `6 / 30` | `4.1` from `123 / 30` |
| Usefulness proxy | `4.17/5` from `125.05 / 30` | `3.79/5` from `113.59 / 30` |

### 3.2 Multi-Turn State Retention

| Metric | Single-Agent | Multi-Agent |
|---|---:|---:|
| Sessions | `2` | `2` |
| State retention pass rate | `100%` from `10/10` checks | `100%` from `10/10` checks |
| Average turn latency | `8.786s` from session means `[8.862, 8.709]` | `25.786s` from session means `[27.363, 24.208]` |
| Average consistency violations in final session state | `0.5` from `1 / 2` | `6.0` from `12 / 2` |

### 3.3 Workflow Latency Under Concurrent Load

| Workflow | Single-Agent | Multi-Agent |
|---|---:|---:|
| Create | `19.814s` from `10` samples, total about `198.14s` | `85.533s` from `10` samples, total about `855.33s` |
| Refine | `18.628s` from `10` samples, total about `186.28s` | `50.770s` from `10` samples, total about `507.70s` |
| Budget | `19.572s` from `10` samples, total about `195.72s` | `0.000s` from `10` samples, total about `0.00s` |

## 4. Interpretation

### 4.1 Strengths of the Multi-Agent Architecture
The multi-agent system strongly outperforms the single-agent baseline in grounding quality. Its verified place rate reaches `99.39%`, while the single-agent baseline achieves only `43.73%`. This result indicates that the Research Agent successfully constrains itinerary generation to the verified knowledge base instead of letting the language model invent unsupported entities.

The same pattern appears in hallucination control. The multi-agent hallucination rate is only `0.61%`, compared with `56.27%` for the single-agent baseline. This is the clearest empirical evidence that the RAG-based decomposition substantially improves factual reliability.

Budget accuracy also strongly favors the multi-agent architecture. The average budget delta for the single-agent baseline is `531,333 VND`, whereas the multi-agent system produces `0 VND` average error. This result is consistent with the architectural design: arithmetic is delegated to a deterministic Budget Node instead of being inferred by the LLM.

### 4.2 Trade-Offs and Costs
The multi-agent architecture is significantly slower. Under concurrent load, average latency rises from `19.814s` to `85.533s` for `Create`, and from `18.628s` to `50.770s` for `Refine`. This increase is expected because the architecture decomposes one task into multiple sequential stages: intent routing, retrieval, planning, and deterministic post-processing.

The consistency metric also appears unfavorable to the multi-agent system. It records `4.1` average violations per create case and `6.0` violations in final multi-turn session states, compared with `0.2` and `0.5` for the single-agent baseline. However, this result should be interpreted cautiously. The current consistency checker is rule-based and relatively strict, especially regarding duplicate activities, coordinate completeness, and route distance thresholds. As a result, it may penalize grounded plans more heavily than more generic single-agent outputs.

### 4.3 State Retention
Both architectures achieved `100%` state-retention pass rate in the current automated test suite. This means that, under the implemented checks, both systems preserved core itinerary state across 10-turn sessions. However, this should not be over-interpreted as proof that both systems are equally robust in all conversational scenarios. The benchmark validates a finite set of state constraints rather than all possible preference and collaboration behaviors.

### 4.4 User-Perceived Usefulness
The current usefulness result is mixed. The single-agent baseline scores slightly higher in the automated proxy (`4.17/5` vs `3.79/5`), largely because the proxy penalizes consistency violations. Since this score is not yet based on real Likert responses from human participants, it should be reported as a preliminary approximation rather than a definitive user-study outcome.

## 5. Threats to Validity

- The usefulness metric is not yet questionnaire-based, so criterion 6 is only partially satisfied.
- The consistency metric is rule-based and may over-penalize certain grounded outputs.
- The benchmark uses `30` create prompts and `2` multi-turn sessions, which is adequate for engineering validation but still limited for broader statistical generalization.
- Latency results depend on external API response times and current quota/rate-limit conditions.

## 6. Report-Ready Summary

The benchmark shows that the SALLMA multi-agent architecture substantially improves factual grounding and budget correctness compared with a single-agent baseline. Across 30 create scenarios, the multi-agent system achieved a verified place rate of `99.39%` and a hallucination rate of only `0.61%`, whereas the single-agent baseline reached `43.73%` verified grounding and `56.27%` hallucination. Budget accuracy also improved markedly: the multi-agent architecture produced `0 VND` average budget error, while the single-agent baseline exhibited an average absolute deviation of `531,333 VND`.

These gains come with a clear latency trade-off. Under 5 concurrent simulated group rooms, the multi-agent architecture required `85.533s` on average for Create and `50.770s` for Refine, compared with `19.814s` and `18.628s` for the single-agent baseline. Both systems achieved `100%` pass rate on the current automated state-retention checks across 10-turn conversations. However, the present consistency metric produced more violations for the multi-agent system, suggesting that further refinement of route and structural validation rules is needed. Finally, user-perceived usefulness is currently represented by an automated proxy rather than a real Likert survey, so that criterion remains only partially validated.
