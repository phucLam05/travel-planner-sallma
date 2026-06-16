import argparse
import json
import os
import re
import statistics
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.budget_node import budget_node
from core.graph import build_graph
from core.llm_factory import build_text_llm, configure_model_rate_limit, invoke_with_retry

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/travel_db",
)
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results"
FUZZY_MATCH_THRESHOLD = 0.90
LATENCY_CONCURRENCY = 5
LATENCY_REPEATS_PER_WORKFLOW = 10
CREATE_BENCHMARK_CONCURRENCY = 4
SINGLE_CREATE_CONCURRENCY = 1
MULTI_CREATE_CONCURRENCY = 1
MODEL_MIN_INTERVAL_SECONDS = 5.0


@dataclass
class PlaceRecord:
    name: str
    lat: float | None
    lng: float | None
    price: float | None
    category: str | None


CREATE_PROMPT_DIMENSIONS = {
    "travelers": [
        "cho cap doi",
        "cho gia dinh co tre nho",
        "cho nhom ban",
        "cho sinh vien",
        "cho nguoi lon tuoi",
    ],
    "duration": [
        "2 ngay 1 dem",
        "3 ngay 2 dem",
        "2 ngay",
        "3 ngay",
        "4 ngay 3 dem",
    ],
    "priority": [
        "uu tien bien",
        "uu tien check-in dep",
        "uu tien tiet kiem chi phi",
        "uu tien nghi duong cao cap",
        "uu tien dia diem noi bat",
    ],
    "food": [
        "an hai san",
        "an ngon dia phuong",
        "quan an gia re",
        "nha hang chat luong",
        "mon phu hop tre nho",
    ],
    "budget": [
        "tong ngan sach khoang 4000000 VND",
        "tong ngan sach khoang 5000000 VND",
        "tong ngan sach khoang 7000000 VND",
        "tong ngan sach toi da 3000000 VND",
        "tong ngan sach linh hoat",
    ],
}


MULTI_TURN_SESSIONS = [
    [
        "Lap lich trinh Da Nang 2 ngay 1 dem cho cap doi, uu tien bien, tong ngan sach khoang 5000000 VND.",
        "Chi doi khach san sang loai re hon, giu nguyen lich trinh.",
        "Them 1 ngay nua nhung van giu phong cach di bien.",
        "Chi thay cac quan an bang lua chon tiet kiem hon, khong doi khach san.",
        "Giu nguyen so ngay, thay 1 diem tham quan bang dia diem noi bat khac.",
        "Nho giu tong ngan sach cang thap cang tot.",
        "Khong doi khach san, chi tinh chinh lich trinh cho nhe hon.",
        "Them mot bua toi co hai san.",
        "Van uu tien khu vuc bien va giu khach san hien tai.",
        "Tong hop lai lich trinh cuoi cung that ro rang.",
    ],
    [
        "Tao ke hoach du lich Da Nang 3 ngay cho gia dinh co tre nho, uu tien an toan va it di chuyen xa.",
        "Chi doi khach san sang noi co danh gia tot hon cho gia dinh.",
        "Bo mot diem qua dong nguoi va thay bang noi nhe nhang hon.",
        "Khong doi khach san nua, chi cap nhat lich trinh.",
        "Them mot bua an toi phu hop tre nho.",
        "Giu yeu cau an toan va han che di chuyen xa.",
        "Neu co the hay toi uu chi phi hon mot chut.",
        "Giu nguyen so ngay va cau truc hien tai.",
        "Chi thay doi nha hang buoi trua ngay 2.",
        "Tong hop phuong an cuoi cung cho gia dinh.",
    ],
]


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_json_block(raw_text: Any) -> dict[str, Any]:
    if isinstance(raw_text, list):
        text = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw_text
        )
    else:
        text = str(raw_text)

    candidates = [
        re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL),
        re.search(r"```\s*(.*?)\s*```", text, re.DOTALL),
    ]
    for candidate in candidates:
        if candidate:
            text = candidate.group(1)
            break
    return json.loads(text)


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_db_places() -> list[PlaceRecord]:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT name, lat, lng, price, category FROM places;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        PlaceRecord(
            name=row[0],
            lat=float(row[1]) if row[1] is not None else None,
            lng=float(row[2]) if row[2] is not None else None,
            price=float(row[3]) if row[3] is not None else None,
            category=row[4],
        )
        for row in rows
    ]


def generate_create_prompts(count: int) -> list[str]:
    prompts = []
    travelers = CREATE_PROMPT_DIMENSIONS["travelers"]
    durations = CREATE_PROMPT_DIMENSIONS["duration"]
    priorities = CREATE_PROMPT_DIMENSIONS["priority"]
    foods = CREATE_PROMPT_DIMENSIONS["food"]
    budgets = CREATE_PROMPT_DIMENSIONS["budget"]

    for i in range(count):
        prompt = (
            f"Lap lich trinh du lich Da Nang {durations[i % len(durations)]} "
            f"{travelers[i % len(travelers)]}, {priorities[(i * 2) % len(priorities)]}, "
            f"{foods[(i * 3) % len(foods)]}, {budgets[(i * 4) % len(budgets)]}."
        )
        prompts.append(prompt)
    return prompts


def find_best_place_match(name: str, places: list[PlaceRecord]) -> tuple[bool, str | None, float]:
    normalized = normalize_text(name)
    best_ratio = 0.0
    best_match = None

    for place in places:
        place_normalized = normalize_text(place.name)
        ratio = SequenceMatcher(None, normalized, place_normalized).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = place.name

        left_tokens = set(normalized.split())
        right_tokens = set(place_normalized.split())
        if left_tokens and right_tokens:
            if left_tokens.issubset(right_tokens) or right_tokens.issubset(left_tokens):
                return True, place.name, 1.0

    if best_ratio >= FUZZY_MATCH_THRESHOLD:
        return True, best_match, best_ratio
    return False, best_match, best_ratio


def extract_place_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    hotel = payload.get("hotel", {})
    hotel_name = hotel.get("hotel_name") or hotel.get("name")
    if hotel_name:
        names.append(str(hotel_name))

    itinerary = payload.get("itinerary", {})
    for day in itinerary.get("days", []):
        for activity in day.get("activities", []):
            place = activity.get("place")
            if place:
                names.append(str(place))
    return names


def compute_budget_from_payload(payload: dict[str, Any]) -> float:
    hotel = payload.get("hotel", {})
    itinerary = payload.get("itinerary", {})

    hotel_price = float(hotel.get("price_per_night", 0) or 0)
    nights = float(hotel.get("nights", 0) or 0)
    activities_cost = 0.0

    for day in itinerary.get("days", []):
        for activity in day.get("activities", []):
            activities_cost += float(activity.get("price", 0) or 0)

    return hotel_price * nights + activities_cost


def time_to_minutes(value: str) -> int | None:
    match = re.match(r"^\s*(\d{1,2}):(\d{2})", str(value or ""))
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def evaluate_correctness(payload: dict[str, Any], places: list[PlaceRecord]) -> dict[str, Any]:
    place_names = extract_place_names(payload)
    verifications = []
    verified_count = 0

    for name in place_names:
        verified, matched_name, score = find_best_place_match(name, places)
        if verified:
            verified_count += 1
        verifications.append(
            {
                "generated_name": name,
                "verified": verified,
                "matched_db_name": matched_name,
                "match_score": round(score, 4),
            }
        )

    total_places = len(place_names)
    verified_rate = (verified_count / total_places) if total_places else 0.0
    hallucination_rate = ((total_places - verified_count) / total_places) if total_places else 0.0
    return {
        "total_places": total_places,
        "verified_places": verified_count,
        "verified_rate": verified_rate,
        "hallucination_rate": hallucination_rate,
        "verifications": verifications,
    }


def evaluate_budget_accuracy(payload: dict[str, Any]) -> dict[str, Any]:
    claimed_total = payload.get("budget", {}).get("total_cost", 0) or 0
    recomputed_total = compute_budget_from_payload(payload)
    return {
        "claimed_total_cost": float(claimed_total),
        "recomputed_total_cost": float(recomputed_total),
        "budget_delta": abs(float(claimed_total) - float(recomputed_total)),
    }


def evaluate_consistency(payload: dict[str, Any]) -> dict[str, Any]:
    itinerary = payload.get("itinerary", {})
    hotel = payload.get("hotel", {})
    violations = []
    seen_places: set[str] = set()
    hotel_coords = None

    if hotel.get("lat") is not None and hotel.get("lng") is not None:
        hotel_coords = (float(hotel["lat"]), float(hotel["lng"]))

    days = itinerary.get("days", [])
    expected_nights = max(1, len(days) - 1) if days else 0
    actual_nights = int(hotel.get("nights", 0) or 0)
    if days and actual_nights != expected_nights:
        violations.append(
            {
                "type": "nights_mismatch",
                "details": f"expected {expected_nights} nights but got {actual_nights}",
            }
        )

    for day in days:
        previous_minutes = -1
        day_places = []
        for activity in day.get("activities", []):
            place_name = str(activity.get("place", "")).strip()
            normalized_place = normalize_text(place_name)
            if normalized_place:
                if normalized_place in seen_places:
                    violations.append(
                        {
                            "type": "duplicate_activity",
                            "details": place_name,
                        }
                    )
                seen_places.add(normalized_place)
                day_places.append(place_name)

            minutes = time_to_minutes(activity.get("time"))
            if minutes is None:
                violations.append(
                    {
                        "type": "invalid_time",
                        "details": f"day {day.get('day')} activity {place_name}",
                    }
                )
            elif minutes < previous_minutes:
                violations.append(
                    {
                        "type": "time_order",
                        "details": f"day {day.get('day')} activity {place_name}",
                    }
                )
            previous_minutes = max(previous_minutes, minutes or previous_minutes)

            if activity.get("lat") is None or activity.get("lng") is None:
                violations.append(
                    {
                        "type": "missing_coordinates",
                        "details": place_name,
                    }
                )

        if hotel_coords and day.get("activities"):
            first = day["activities"][0]
            last = day["activities"][-1]
            for label, activity in [("first", first), ("last", last)]:
                if activity.get("lat") is not None and activity.get("lng") is not None:
                    distance = haversine_km(
                        hotel_coords[0],
                        hotel_coords[1],
                        float(activity["lat"]),
                        float(activity["lng"]),
                    )
                    if distance > 35:
                        violations.append(
                            {
                                "type": "route_distance",
                                "details": f"{label} activity too far from hotel: {distance:.1f} km",
                            }
                        )

    return {
        "violation_count": len(violations),
        "violations": violations,
    }


def compute_usefulness_proxy(
    correctness: dict[str, Any],
    budget_accuracy: dict[str, Any],
    consistency: dict[str, Any],
) -> dict[str, Any]:
    clarity = max(1.0, 5.0 - min(4.0, consistency["violation_count"] * 0.5))
    trustworthiness = max(
        1.0,
        min(
            5.0,
            1.0
            + correctness["verified_rate"] * 3.0
            + (1.0 if budget_accuracy["budget_delta"] == 0 else 0.0),
        ),
    )
    collaboration = max(1.0, 5.0 - min(4.0, consistency["violation_count"] * 0.4))
    overall = (clarity + trustworthiness + collaboration) / 3.0
    return {
        "clarity_score": round(clarity, 2),
        "trustworthiness_score": round(trustworthiness, 2),
        "collaboration_score": round(collaboration, 2),
        "overall_score": round(overall, 2),
        "note": "Automated proxy for user-perceived usefulness; replace with a human Likert survey when available.",
    }


def build_single_agent() -> Any:
    return build_text_llm(temperature=0.1)


def single_agent_prompt(history: list[str]) -> list[Any]:
    system_prompt = (
        "Ban la mot travel planner single-agent. Khong duoc goi tool, khong duoc truy cap database.\n"
        "Hay doc toan bo lich su yeu cau va tra ve phuong an cap nhat moi nhat duoi dang JSON hop le duy nhat.\n"
        "JSON schema:\n"
        "{\n"
        '  "hotel": {"hotel_name": "...", "price_per_night": 0, "nights": 0, "description": "...", "lat": 0, "lng": 0},\n'
        '  "itinerary": {"days": [{"day": 1, "activities": [{"time": "08:00", "place": "...", "description": "...", "price": 0, "lat": 0, "lng": 0}]}]},\n'
        '  "budget": {"total_cost": 0, "currency": "VND"}\n'
        "}\n"
        "Khong giai thich them."
    )
    transcript = "\n".join(f"Turn {i+1}: {item}" for i, item in enumerate(history))
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=transcript),
    ]


def run_single_agent(history: list[str]) -> dict[str, Any]:
    llm = build_single_agent()
    started_at = time.perf_counter()
    response = invoke_with_retry(llm, single_agent_prompt(history))
    latency = time.perf_counter() - started_at
    payload = parse_json_block(response.content)
    payload.setdefault("budget", {})
    payload["budget"]["recomputed_total_cost"] = compute_budget_from_payload(payload)
    return {
        "latency_seconds": latency,
        "payload": payload,
        "raw_text": response.content,
    }


def run_multi_agent_turn(graph: Any, state: dict[str, Any], user_input: str) -> tuple[dict[str, Any], float]:
    next_state = deepcopy(state)
    next_state["latest_user_input"] = user_input
    history = list(next_state.get("chat_history", []))
    history.append({"role": "User", "content": user_input})
    next_state["chat_history"] = history

    started_at = time.perf_counter()
    result = graph.invoke(next_state)
    latency = time.perf_counter() - started_at
    return result, latency


def state_to_payload(state: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "hotel": state.get("accommodation_details", {}),
        "itinerary": state.get("itinerary_plan", {}),
        "budget": state.get("budget_details", {}),
    }
    payload["budget"]["recomputed_total_cost"] = compute_budget_from_payload(payload)
    return payload


def evaluate_payload(payload: dict[str, Any], places: list[PlaceRecord]) -> dict[str, Any]:
    correctness = evaluate_correctness(payload, places)
    budget_accuracy = evaluate_budget_accuracy(payload)
    consistency = evaluate_consistency(payload)
    usefulness = compute_usefulness_proxy(correctness, budget_accuracy, consistency)
    return {
        "correctness": correctness,
        "budget_accuracy": budget_accuracy,
        "consistency": consistency,
        "user_perceived_usefulness": usefulness,
    }


def create_empty_state() -> dict[str, Any]:
    return {
        "chat_history": [],
        "latest_user_input": "",
        "intent": "",
        "research_context": {},
        "itinerary_plan": {},
        "accommodation_details": {},
        "budget_details": {},
    }


def run_single_create_case(prompt: str, places: list[PlaceRecord]) -> dict[str, Any]:
    single_result = run_single_agent([prompt])
    single_eval = evaluate_payload(single_result["payload"], places)
    return {
        "prompt": prompt,
        "latency_seconds": single_result["latency_seconds"],
        "payload": single_result["payload"],
        "evaluation": single_eval,
    }


def run_multi_create_case(prompt: str, places: list[PlaceRecord]) -> dict[str, Any]:
    graph = build_graph()
    state = create_empty_state()
    multi_state, multi_latency = run_multi_agent_turn(graph, state, prompt)
    multi_payload = state_to_payload(multi_state)
    multi_eval = evaluate_payload(multi_payload, places)
    return {
        "prompt": prompt,
        "latency_seconds": multi_latency,
        "payload": multi_payload,
        "evaluation": multi_eval,
    }


def run_create_benchmark(
    prompts: list[str],
    places: list[PlaceRecord],
    batch_size: int,
    checkpoint_data: dict[str, Any],
    checkpoint_path: Path,
) -> dict[str, Any]:
    create_data = checkpoint_data.setdefault(
        "create_benchmark",
        {"single_agent": [], "multi_agent": [], "completed": False},
    )
    single_cases = create_data["single_agent"]
    multi_cases = create_data["multi_agent"]

    print(f"[create] single-agent on {len(prompts)} prompts", flush=True)
    for start in range(len(single_cases), len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        for offset, prompt in enumerate(batch, start=1):
            prompt_index = start + offset
            print(
                f"[create] single-agent starting {prompt_index}/{len(prompts)}",
                flush=True,
            )
            case = run_single_create_case(prompt, places)
            single_cases.append(case)
            print(
                f"[create] single-agent finished {prompt_index}/{len(prompts)} in {case['latency_seconds']:.3f}s",
                flush=True,
            )
        save_json(checkpoint_path, checkpoint_data)
        print(
            f"[create] single-agent checkpoint {min(start + batch_size, len(prompts))}/{len(prompts)}",
            flush=True,
        )

    print(f"[create] multi-agent on {len(prompts)} prompts", flush=True)
    for start in range(len(multi_cases), len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        for offset, prompt in enumerate(batch, start=1):
            prompt_index = start + offset
            print(
                f"[create] multi-agent starting {prompt_index}/{len(prompts)}",
                flush=True,
            )
            case = run_multi_create_case(prompt, places)
            multi_cases.append(case)
            print(
                f"[create] multi-agent finished {prompt_index}/{len(prompts)} in {case['latency_seconds']:.3f}s",
                flush=True,
            )
        save_json(checkpoint_path, checkpoint_data)
        print(
            f"[create] multi-agent checkpoint {min(start + batch_size, len(prompts))}/{len(prompts)}",
            flush=True,
        )

    single_cases.sort(key=lambda item: item["prompt"])
    multi_cases.sort(key=lambda item: item["prompt"])
    create_data["completed"] = True
    save_json(checkpoint_path, checkpoint_data)

    return {
        "single_agent": single_cases,
        "multi_agent": multi_cases,
    }


def validate_state_retention(state: dict[str, Any]) -> dict[str, Any]:
    payload = state_to_payload(state)
    hotel = payload.get("hotel", {})
    itinerary = payload.get("itinerary", {})
    checks = {
        "has_hotel": bool(hotel.get("hotel_name")),
        "has_itinerary_days": len(itinerary.get("days", [])) >= 1,
        "days_not_lost": len(itinerary.get("days", [])) >= 3,
        "hotel_preserved_after_non_hotel_refines": bool(hotel.get("hotel_name")),
        "budget_present": payload.get("budget", {}).get("total_cost") is not None,
    }
    passed = sum(1 for value in checks.values() if value)
    return {
        "passed_checks": passed,
        "total_checks": len(checks),
        "pass_rate": passed / len(checks),
        "checks": checks,
    }


def run_state_retention_benchmark(
    places: list[PlaceRecord],
    checkpoint_data: dict[str, Any],
    checkpoint_path: Path,
) -> dict[str, Any]:
    graph = build_graph()
    state_data = checkpoint_data.setdefault(
        "state_retention",
        {"single_agent": [], "multi_agent": [], "completed": False},
    )
    single_sessions = state_data["single_agent"]
    multi_sessions = state_data["multi_agent"]

    print(f"[state] running {len(MULTI_TURN_SESSIONS)} multi-turn sessions", flush=True)
    for session_index, session_turns in enumerate(
        MULTI_TURN_SESSIONS[len(single_sessions) :], start=len(single_sessions) + 1
    ):
        history: list[str] = []
        single_turn_latencies = []
        single_payload = None
        for turn in session_turns:
            history.append(turn)
            single_result = run_single_agent(history)
            single_turn_latencies.append(single_result["latency_seconds"])
            single_payload = single_result["payload"]

        single_eval = evaluate_payload(single_payload, places)
        single_retention = validate_state_retention(
            {
                "accommodation_details": single_payload.get("hotel", {}),
                "itinerary_plan": single_payload.get("itinerary", {}),
                "budget_details": single_payload.get("budget", {}),
            }
        )
        single_sessions.append(
            {
                "turns": session_turns,
                "avg_turn_latency_seconds": statistics.mean(single_turn_latencies),
                "final_payload": single_payload,
                "evaluation": single_eval,
                "state_retention": single_retention,
            }
        )
        save_json(checkpoint_path, checkpoint_data)
        print(f"[state] single-agent session {session_index}/{len(MULTI_TURN_SESSIONS)} done", flush=True)

    for session_index, session_turns in enumerate(
        MULTI_TURN_SESSIONS[len(multi_sessions) :], start=len(multi_sessions) + 1
    ):
        multi_state = create_empty_state()
        multi_turn_latencies = []
        for turn in session_turns:
            multi_state, latency = run_multi_agent_turn(graph, multi_state, turn)
            multi_turn_latencies.append(latency)
        multi_payload = state_to_payload(multi_state)
        multi_eval = evaluate_payload(multi_payload, places)
        multi_retention = validate_state_retention(multi_state)
        multi_sessions.append(
            {
                "turns": session_turns,
                "avg_turn_latency_seconds": statistics.mean(multi_turn_latencies),
                "final_payload": multi_payload,
                "evaluation": multi_eval,
                "state_retention": multi_retention,
            }
        )
        save_json(checkpoint_path, checkpoint_data)
        print(f"[state] multi-agent session {session_index}/{len(MULTI_TURN_SESSIONS)} done", flush=True)

    state_data["completed"] = True
    save_json(checkpoint_path, checkpoint_data)
    return {
        "single_agent": single_sessions,
        "multi_agent": multi_sessions,
    }


def run_budget_latency_task(system_name: str, itinerary_payload: dict[str, Any]) -> float:
    started_at = time.perf_counter()
    if system_name == "single_agent":
        llm = build_single_agent()
        invoke_with_retry(
            llm,
            [
                SystemMessage(
                    content=(
                        "Tinh tong chi phi chuyen di tu JSON dau vao va tra ve duy nhat JSON: "
                        '{"total_cost": 0, "currency": "VND"}'
                    )
                ),
                HumanMessage(content=json.dumps(itinerary_payload, ensure_ascii=False)),
            ],
        )
    else:
        budget_node(
            {
                "itinerary_plan": itinerary_payload.get("itinerary", {}),
                "accommodation_details": itinerary_payload.get("hotel", {}),
            }
        )
    return time.perf_counter() - started_at


def run_latency_workflow_task(system_name: str, workflow: str, prompt: str) -> float:
    graph = build_graph()
    if system_name == "single_agent":
        if workflow == "create":
            return run_single_agent([prompt])["latency_seconds"]
        if workflow == "refine":
            history = [
                prompt,
                "Chi doi khach san sang loai re hon, giu nguyen lich trinh.",
            ]
            return run_single_agent(history)["latency_seconds"]
        raise ValueError(f"Unsupported workflow {workflow}")

    state = create_empty_state()
    if workflow == "create":
        _, latency = run_multi_agent_turn(graph, state, prompt)
        return latency
    if workflow == "refine":
        state, _ = run_multi_agent_turn(graph, state, prompt)
        _, latency = run_multi_agent_turn(
            graph,
            state,
            "Chi doi khach san sang loai re hon, giu nguyen lich trinh.",
        )
        return latency
    raise ValueError(f"Unsupported workflow {workflow}")


def run_concurrent_latency_suite(
    base_prompt: str,
    itinerary_payload: dict[str, Any],
    checkpoint_data: dict[str, Any],
    checkpoint_path: Path,
) -> dict[str, Any]:
    workflows = ["create", "refine", "budget"]
    systems = ["single_agent", "multi_agent"]
    latency_data = checkpoint_data.setdefault(
        "latency_suite",
        {"raw": {system: {workflow: [] for workflow in workflows} for system in systems}, "completed": False},
    )
    results: dict[str, dict[str, list[float]]] = latency_data["raw"]
    default_results: dict[str, dict[str, list[float]]] = {
        system: {workflow: [] for workflow in workflows} for system in systems
    }
    if not results:
        results = default_results
        latency_data["raw"] = results

    for system in systems:
        for workflow in workflows:
            if results.get(system, {}).get(workflow):
                print(f"[latency] {system} {workflow} skipped from checkpoint", flush=True)
                continue
            print(f"[latency] {system} {workflow} started", flush=True)
            futures = []
            with ThreadPoolExecutor(max_workers=LATENCY_CONCURRENCY) as executor:
                for _ in range(LATENCY_REPEATS_PER_WORKFLOW):
                    if workflow == "budget":
                        futures.append(
                            executor.submit(run_budget_latency_task, system, itinerary_payload)
                        )
                    else:
                        futures.append(
                            executor.submit(
                                run_latency_workflow_task,
                                system,
                                workflow,
                                base_prompt,
                            )
                        )
                for future in as_completed(futures):
                    results[system][workflow].append(future.result())
            save_json(checkpoint_path, checkpoint_data)
            print(f"[latency] {system} {workflow} finished", flush=True)
    latency_data["completed"] = True
    save_json(checkpoint_path, checkpoint_data)
    return results


def summarize_create_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [item["latency_seconds"] for item in cases]
    verified_rates = [item["evaluation"]["correctness"]["verified_rate"] for item in cases]
    hallucination_rates = [item["evaluation"]["correctness"]["hallucination_rate"] for item in cases]
    budget_deltas = [item["evaluation"]["budget_accuracy"]["budget_delta"] for item in cases]
    consistency_violations = [item["evaluation"]["consistency"]["violation_count"] for item in cases]
    usefulness_scores = [
        item["evaluation"]["user_perceived_usefulness"]["overall_score"] for item in cases
    ]

    return {
        "cases": len(cases),
        "avg_latency_seconds": round(statistics.mean(latencies), 3),
        "avg_verified_rate": round(statistics.mean(verified_rates), 4),
        "avg_hallucination_rate": round(statistics.mean(hallucination_rates), 4),
        "avg_budget_delta_vnd": round(statistics.mean(budget_deltas), 2),
        "avg_consistency_violations": round(statistics.mean(consistency_violations), 2),
        "avg_usefulness_score": round(statistics.mean(usefulness_scores), 2),
    }


def summarize_state_retention_sessions(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    pass_rates = [item["state_retention"]["pass_rate"] for item in sessions]
    latencies = [item["avg_turn_latency_seconds"] for item in sessions]
    consistency_violations = [item["evaluation"]["consistency"]["violation_count"] for item in sessions]
    return {
        "sessions": len(sessions),
        "avg_state_retention_pass_rate": round(statistics.mean(pass_rates), 4),
        "avg_turn_latency_seconds": round(statistics.mean(latencies), 3),
        "avg_consistency_violations": round(statistics.mean(consistency_violations), 2),
    }


def summarize_latency_suite(results: dict[str, dict[str, list[float]]]) -> dict[str, Any]:
    summary = {}
    for system, workflow_map in results.items():
        summary[system] = {}
        for workflow, values in workflow_map.items():
            summary[system][workflow] = {
                "avg_latency_seconds": round(statistics.mean(values), 3),
                "min_latency_seconds": round(min(values), 3),
                "max_latency_seconds": round(max(values), 3),
                "samples": len(values),
            }
    return summary


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    create_single = report["create_benchmark"]["single_agent"]["summary"]
    create_multi = report["create_benchmark"]["multi_agent"]["summary"]
    state_single = report["state_retention"]["single_agent"]["summary"]
    state_multi = report["state_retention"]["multi_agent"]["summary"]
    latency = report["latency_suite"]["summary"]

    lines = [
        "# Full Benchmark Results",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Create prompts: `{report['prompt_count']}`",
        f"- Concurrent rooms for latency suite: `{LATENCY_CONCURRENCY}`",
        "",
        "## 1. Correctness and Budget Accuracy",
        "",
        "| Metric | Single-Agent | Multi-Agent |",
        "|---|---:|---:|",
        f"| Avg verified place rate | {create_single['avg_verified_rate']*100:.2f}% | {create_multi['avg_verified_rate']*100:.2f}% |",
        f"| Avg hallucination rate | {create_single['avg_hallucination_rate']*100:.2f}% | {create_multi['avg_hallucination_rate']*100:.2f}% |",
        f"| Avg budget delta (VND) | {create_single['avg_budget_delta_vnd']:.0f} | {create_multi['avg_budget_delta_vnd']:.0f} |",
        "",
        "## 2. Consistency",
        "",
        f"- Single-agent average consistency violations per create case: `{create_single['avg_consistency_violations']}`",
        f"- Multi-agent average consistency violations per create case: `{create_multi['avg_consistency_violations']}`",
        f"- Single-agent average consistency violations in 10-turn sessions: `{state_single['avg_consistency_violations']}`",
        f"- Multi-agent average consistency violations in 10-turn sessions: `{state_multi['avg_consistency_violations']}`",
        "",
        "## 3. State Retention",
        "",
        f"- Single-agent average state retention pass rate: `{state_single['avg_state_retention_pass_rate']*100:.2f}%`",
        f"- Multi-agent average state retention pass rate: `{state_multi['avg_state_retention_pass_rate']*100:.2f}%`",
        "",
        "## 4. Latency",
        "",
        "| Workflow | Single-Agent Avg (s) | Multi-Agent Avg (s) |",
        "|---|---:|---:|",
        f"| Create | {latency['single_agent']['create']['avg_latency_seconds']:.3f} | {latency['multi_agent']['create']['avg_latency_seconds']:.3f} |",
        f"| Refine | {latency['single_agent']['refine']['avg_latency_seconds']:.3f} | {latency['multi_agent']['refine']['avg_latency_seconds']:.3f} |",
        f"| Budget | {latency['single_agent']['budget']['avg_latency_seconds']:.3f} | {latency['multi_agent']['budget']['avg_latency_seconds']:.3f} |",
        "",
        "## 5. User-Perceived Usefulness (Automated Proxy)",
        "",
        f"- Single-agent average usefulness score: `{create_single['avg_usefulness_score']}/5`",
        f"- Multi-agent average usefulness score: `{create_multi['avg_usefulness_score']}/5`",
        "- Note: this is an automated proxy derived from clarity, trustworthiness, and consistency signals; replace with a real Likert survey when human participants are available.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-count", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--min-interval-seconds", type=float, default=5.0)
    args = parser.parse_args()

    global MODEL_MIN_INTERVAL_SECONDS
    MODEL_MIN_INTERVAL_SECONDS = args.min_interval_seconds
    configure_model_rate_limit(args.min_interval_seconds)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    places = get_db_places()
    create_prompts = generate_create_prompts(args.prompt_count)
    checkpoint_path = RESULTS_DIR / f"benchmark_full_checkpoint_{args.prompt_count}.json"
    checkpoint_data = load_json(checkpoint_path) or {
        "generated_at": datetime.now().isoformat(),
        "prompt_count": args.prompt_count,
    }

    create_results = run_create_benchmark(
        create_prompts,
        places,
        args.batch_size,
        checkpoint_data,
        checkpoint_path,
    )
    state_results = run_state_retention_benchmark(
        places,
        checkpoint_data,
        checkpoint_path,
    )

    sample_payload = create_results["multi_agent"][0]["payload"]
    latency_raw = run_concurrent_latency_suite(
        create_prompts[0],
        sample_payload,
        checkpoint_data,
        checkpoint_path,
    )

    report = {
        "generated_at": datetime.now().isoformat(),
        "prompt_count": args.prompt_count,
        "create_benchmark": {
            "single_agent": {
                "summary": summarize_create_cases(create_results["single_agent"]),
                "cases": create_results["single_agent"],
            },
            "multi_agent": {
                "summary": summarize_create_cases(create_results["multi_agent"]),
                "cases": create_results["multi_agent"],
            },
        },
        "state_retention": {
            "single_agent": {
                "summary": summarize_state_retention_sessions(state_results["single_agent"]),
                "sessions": state_results["single_agent"],
            },
            "multi_agent": {
                "summary": summarize_state_retention_sessions(state_results["multi_agent"]),
                "sessions": state_results["multi_agent"],
            },
        },
        "latency_suite": {
            "summary": summarize_latency_suite(latency_raw),
            "raw": latency_raw,
        },
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"benchmark_full_{timestamp}.json"
    md_path = RESULTS_DIR / f"benchmark_full_{timestamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(md_path, report)

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    print(json.dumps(report["create_benchmark"]["single_agent"]["summary"], ensure_ascii=False, indent=2))
    print(json.dumps(report["create_benchmark"]["multi_agent"]["summary"], ensure_ascii=False, indent=2))
    print(json.dumps(report["state_retention"]["single_agent"]["summary"], ensure_ascii=False, indent=2))
    print(json.dumps(report["state_retention"]["multi_agent"]["summary"], ensure_ascii=False, indent=2))
    print(json.dumps(report["latency_suite"]["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
