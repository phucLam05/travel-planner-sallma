import json
import re
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.state import TravelState
from core.logger import get_logger

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
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        base_url="https://models.inference.ai.azure.com",
        api_key=os.getenv("GITHUB_TOKEN")
    )
    
    system_prompt = f"""
    Bạn là Planner Agent thông minh. Nhiệm vụ của bạn là đọc TOÀN BỘ lịch sử hội thoại để hiểu chính xác người dùng muốn gì, sau đó dựa vào TẬP DỮ LIỆU ĐÃ TÌM KIẾM ĐƯỢC (Context) để xếp lịch trình và chọn khách sạn.
    
    Lịch trình cũ đang có: {current_days} ngày.
    Intent: {intent}
    
    TẬP DỮ LIỆU (Context):
    {json.dumps(research_context, ensure_ascii=False)}
    
    LỊCH TRÌNH VÀ KHÁCH SẠN CŨ (Dùng để tham khảo khi có yêu cầu Refine):
    Khách sạn cũ: {json.dumps(old_hotel, ensure_ascii=False)}
    Lịch trình cũ: {json.dumps(old_itinerary, ensure_ascii=False)}
    
    LUẬT QUAN TRỌNG VỀ SỐ NGÀY:
    - Nếu người dùng yêu cầu "thêm ngày", "bớt ngày", "đi N ngày", bạn PHẢI tự động điều chỉnh số lượng mảng `days` cho đúng, đồng thời điều chỉnh số `nights` (đêm) của khách sạn tương ứng (thường số đêm = số ngày - 1, hoặc tùy ngữ cảnh).
    - Nếu người dùng không đề cập đến việc đổi ngày, giữ nguyên số ngày và số đêm như lịch trình cũ.
    
    LUẬT QUAN TRỌNG VỀ REFINE:
    1. Nếu intent là 'refine_hotel': BẠN PHẢI GIỮ NGUYÊN 100% phần `itinerary` (lịch trình) cũ, CHỈ chọn lại `hotel` mới từ Context. (Nếu có thay đổi số ngày thì cập nhật lại `nights` cho hotel).
    2. Nếu intent là 'refine_activities': BẠN PHẢI GIỮ NGUYÊN 100% phần `hotel` cũ, CHỈ cập nhật lại `itinerary` (thêm bớt địa điểm, thay đổi ngày) từ Context.
    3. Nếu intent là 'create' hoặc 'refine_all': Xếp lịch trình và chọn khách sạn hoàn toàn mới. Tối ưu Route: Gom các địa điểm có tọa độ gần nhau vào cùng 1 ngày.
    4. BẮT BUỘC: Mỗi ngày trong lịch trình phải có tối thiểu 3 hoạt động được gán nhãn Ăn uống (Ăn sáng, Ăn trưa, Ăn tối).
    
    CHỈ SỬ DỤNG DỮ LIỆU TỪ CONTEXT VÀ DỮ LIỆU CŨ. KHÔNG BỊA ĐỊA ĐIỂM.
    
    TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON SAU (NẰM TRONG BLOCK ```json ... ```):
    {{
        "hotel": {{
            "hotel_name": "Tên khách sạn",
            "price_per_night": 123,
            "nights": 2,
            "description": "Lý do chọn khách sạn này",
            "lat": 16.0594,
            "lng": 108.2435
        }},
        "itinerary": {{
            "days": [
                {{
                    "day": 1,
                    "activities": [
                        {{
                            "time": "Sáng", 
                            "place": "Tên địa điểm", 
                            "description": "Làm gì", 
                            "price": 100000,
                            "lat": 16.123,
                            "lng": 108.123
                        }}
                    ]
                }}
            ]
        }}
    }}
    """
    
    logger.debug(f"System Prompt: {system_prompt}")
    
    messages = [SystemMessage(content=system_prompt)]
    from langchain_core.messages import AIMessage
    for msg in chat_history:
        if msg.get("role") == "User":
            messages.append(HumanMessage(content=msg.get("content")))
        else:
            messages.append(AIMessage(content=msg.get("content")))
            
    logger.debug("Gọi LLM để lên Plan...")
    response = llm.invoke(messages)
    
    content = response.content
    if isinstance(content, list):
        final_text = "".join(
            block["text"] if isinstance(block, dict) and "text" in block else (block if isinstance(block, str) else "") 
            for block in content
        )
    else:
        final_text = str(content)
        
    try:
        match = re.search(r'```json\n(.*?)\n```', final_text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = final_text
            
        json_data = json.loads(json_str)
        
        state["accommodation_details"] = json_data.get("hotel", {})
        state["itinerary_plan"] = json_data.get("itinerary", {})
        
        logger.info("Planner Agent hoàn thành (JSON parsed).")
    except Exception as e:
        logger.error(f"Lỗi parse JSON Planner: {e}")
        state["accommodation_details"] = {"error": "Lỗi Planner", "raw_output": final_text}
        state["itinerary_plan"] = {"error": "Lỗi Planner", "raw_output": final_text}
    
    return state
