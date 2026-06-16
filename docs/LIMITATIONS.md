# Limitations and Future Work

While the current SALLMA Travel Planner successfully implements multi-agent orchestration, persistent group-room event-log memory, and intelligent routing, there are still some limitations compared to the theoretical ideal proposed in the SATrends 2025 paper.

## 1. Kubernetes Deployment & Auto-Scaling
The original SALLMA paper emphasizes containerized deployments orchestrated via Kubernetes for dynamic resource allocation and isolated agent environments.
- **Current State:** The prototype runs locally (or on a single cloud VM) via `streamlit run` and standard Python processes. The agents are logically separated via LangGraph, but physically run in the same container.
- **Future Work:** Package each agent as a separate microservice docker container and deploy them using Kubernetes. This would fulfill the `Deployment Metamodel Catalog` requirement by allowing dynamic scaling of the Research Agent independently from the Planner Agent under heavy load.

## 2. Deployment Metamodel Catalog
The Knowledge Layer currently implements the `WorkflowMetamodelCatalog` and `AgentConfigurationCatalog`.
- **Current State:** The `Deployment Metamodel Catalog` is not fully implemented because the system is not yet running on a distributed Kubernetes cluster.
- **Future Work:** Once migrated to Kubernetes, this catalog will store the Helm charts and resource limits (CPU/Memory) for each agent instance.

## 3. Real-Time WebSocket Synchronization
- **Current State:** While the group-room state is shared via an event-log database (`travel_room_events`), the Streamlit UI does not currently push updates to other users in real-time. A user must perform an action or refresh to see a teammate's changes.
- **Future Work:** Implement WebSocket connections or use a framework like FastAPI + React to push state changes to all connected clients instantly when an event is appended to the log.
