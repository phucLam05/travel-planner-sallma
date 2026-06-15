from core.state import TravelState
from core.logger import get_logger

logger = get_logger("BudgetNode")

def budget_node(state: TravelState):
    """
    Node tính toán cuối cùng. KHÔNG DÙNG LLM.
    Chỉ đơn thuần đọc data JSON từ Itinerary và Accommodation để tính ra tổng chi phí.
    """
    logger.info("--- BUDGET NODE ĐANG CHẠY ---")
    
    itinerary_plan = state.get("itinerary_plan", {})
    accommodation_details = state.get("accommodation_details", {})
    
    # 1. Chi phí khách sạn
    hotel_price = accommodation_details.get("price_per_night", 0)
    nights = accommodation_details.get("nights", 2)
    total_hotel = hotel_price * nights
    
    # 2. Chi phí vé tham quan & nhà hàng (Tính trực tiếp từ giá của từng activity)
    ticket_costs = 0
    days = itinerary_plan.get("days", [])
    num_days = len(days) if days else (nights + 1)
    
    for day in days:
        for act in day.get("activities", []):
            ticket_costs += act.get("price", 0)
    
    # 3. Tổng cộng
    total_overall = total_hotel + ticket_costs
    
    budget_details = {
        "hotel_total": total_hotel,
        "ticket_costs": ticket_costs,
        "num_days": num_days,
        "nights": nights,
        "overall_total": total_overall
    }
    
    state["budget_details"] = budget_details
    logger.info("Budget Node tính toán xong chi phí.")
    
    return state
