import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from core.state import TravelState
from core.logger import get_logger
from core.llm_factory import build_text_llm, invoke_with_retry

logger = get_logger("PlannerAgent")

def planner_node(state: TravelState):
    """
    Agent làm nhiệm vụ lắp ghép. KHÔNG DÙNG TOOL TÌM KIẾM NỮA.
    Nó chỉ đọc `research_context` (chứa tọa độ, giá) và quyết định Lịch trình + Khách sạn sao cho tối ưu route.
    """
    logger.info("--- PLANNER AGENT ĐANG CHẠY ---")
    
    user_input = state.get("latest_user_input", "")
    chat_history = state.get("chat_history", [])
    research_context = state.get("research_context", {})
    intent = state.get("intent", "create")
    old_itinerary = state.get("itinerary_plan", {})
    old_hotel = state.get("accommodation_details", {})
    
    logger.info(f"User Input: '{user_input}'")
    
    # Tính số ngày hiện tại từ lịch trình cũ
    current_days = len(old_itinerary.get("days", [])) if old_itinerary and "days" in old_itinerary else 2
    
    from core.knowledge_layer import AgentConfigurationCatalog
    config = AgentConfigurationCatalog.get_config("planner_agent")

    llm = build_text_llm(
        model=config.get("model"),
        temperature=config.get("temperature", 0.1),
    )
    
    system_prompt = config.get("system_prompt", "").format(
        current_days=current_days,
        intent=intent,
        context_json=json.dumps(research_context, ensure_ascii=False),
        user_input=user_input,
        old_hotel_json=json.dumps(old_hotel, ensure_ascii=False),
        old_itinerary_json=json.dumps(old_itinerary, ensure_ascii=False),
        next_days=current_days + 1,
        max_days=max(1, current_days - 1)
    )
    
    logger.debug(f"System Prompt: {system_prompt}")
    
    messages = [SystemMessage(content=system_prompt)]
    from langchain_core.messages import AIMessage
    for msg in chat_history:
        if msg.get("role") == "User":
            messages.append(HumanMessage(content=msg.get("content")))
        else:
            messages.append(AIMessage(content=msg.get("content")))
            
    logger.debug("Gọi LLM để lên Plan...")
    response = invoke_with_retry(llm, messages)
    
    content = response.content
    if isinstance(content, list):
        result_text = "".join(
            block["text"] if isinstance(block, dict) and "text" in block else (block if isinstance(block, str) else "") 
            for block in content
        )
    else:
        result_text = str(content)
        
    try:
        json_str = result_text
        if "```json" in result_text:
            json_str = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            json_str = result_text.split("```")[1].split("```")[0]
        
        data = json.loads(json_str)
        hotel_data = data.get("hotel", {})
        itinerary_data = data.get("itinerary", {})
        
        # Ép buộc logic: Số đêm = Số ngày - 1
        num_days = len(itinerary_data.get("days", []))
        if num_days > 0:
            hotel_data["nights"] = max(1, num_days - 1)
        
        logger.info(f"Đã tạo Plan thành công. Số ngày: {num_days}, Số đêm: {hotel_data.get('nights')}")
        return {
            "accommodation_details": hotel_data,
            "itinerary_plan": itinerary_data
        }
    except json.JSONDecodeError:
        logger.error(f"Lỗi parse JSON từ LLM Planner. Output gốc:\n{result_text}")
        return {
            "accommodation_details": old_hotel,
            "itinerary_plan": old_itinerary
        }
