# Evaluation Methods

To validate the SALLMA Architecture improvements, we use the following methods to measure our 6 core metrics against a single-agent baseline.

## 1. Correctness (RAG Faithfulness)
**Definition:** Percentage of place recommendations retrieved from the verified knowledge base rather than hallucinated by the LLM.
**Measurement:** 
- Extract all `name`, `lat`, and `lng` properties from the Planner Agent's JSON output.
- Perform a direct match against the `places` table in the PostgreSQL database.
- **Formula:** `Accuracy = (Verified Places / Total Suggested Places) * 100%`
- *Expected Goal:* > 95% (Multi-agent) vs ~60% (Single-agent baseline).

## 2. Budget Accuracy
**Definition:** Absolute difference between LLM-generated math and deterministic calculation.
**Measurement:**
- We utilize the deterministic **Budget Node** rather than an LLM tool. 
- A Python script iterates through the output itinerary and accommodation JSON arrays, summing the prices.
- The script compares this manual sum with the output of the Budget Node.
- **Formula:** `Delta = Abs(Sum(prices) - BudgetNode.Total)`
- *Expected Goal:* Delta = 0 (Multi-agent) vs Delta > 0 (Single-agent baseline due to arithmetic hallucination).

## 3. Consistency
**Definition:** Number of logical contradictions between itinerary, map route, accommodation choice, and budget across multi-turn sessions.
**Measurement:**
- Apply a validation script to check:
  1. No duplicate activities across different days.
  2. Each day starts and ends near the chosen hotel (calculate distance based on `lat`/`lng`).
  3. Proper ordering of meals (Breakfast -> Lunch -> Dinner).
- *Expected Goal:* 0 violations over a 5-day itinerary.

## 4. State Retention (Group-Room Memory)
**Definition:** Ability to preserve user preferences and group-room changes over 10+ conversation turns without loss.
**Measurement:**
- Automated end-to-end test scripts that issue 10 sequential API calls to update the state (e.g., change hotel, add a day, swap a restaurant).
- After each turn, the `travel_room_events` table is queried to rebuild the state. 
- We verify that constraints introduced in Turn 1 (e.g., "Must be near the beach") are still respected in Turn 10.

## 5. Latency
**Definition:** Average end-to-end response time for Create, Refine, and Budget workflows.
**Measurement:**
- Use a load testing tool (like Locust) to simulate 5 concurrent group-rooms.
- Measure the execution time of `graph.invoke()` for each request.
- *Expected Goal:* < 15 seconds per request (dependent on external LLM API speeds).

## 6. User-Perceived Usefulness
**Definition:** Questionnaire-based rating (1–5 Likert scale).
**Measurement:**
- Recruit 10-20 test users to collaboratively plan a trip in the Streamlit app.
- Provide a post-task survey evaluating: 
  - Itinerary clarity (1-5)
  - Trustworthiness of data (1-5)
  - Ease of group collaboration (1-5)
