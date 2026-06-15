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
    
    Yêu cầu MỚI NHẤT của người dùng: "{user_input}"
    
    LỊCH TRÌNH VÀ KHÁCH SẠN CŨ (Dùng để tham khảo khi có yêu cầu Refine):
    Khách sạn cũ: {json.dumps(old_hotel, ensure_ascii=False)}
    Lịch trình cũ: {json.dumps(old_itinerary, ensure_ascii=False)}
    
    LUẬT QUAN TRỌNG VỀ SỐ NGÀY:
    - Hãy tập trung vào Yêu cầu MỚI NHẤT ("{user_input}"). 
    - Lịch trình cũ đang có {current_days} ngày. Nếu yêu cầu mới nhất là "thêm 1 ngày", BẮT BUỘC bạn phải trả về lịch trình mới gồm {current_days + 1} ngày! Nếu yêu cầu là "bớt 1 ngày", BẮT BUỘC trả về {max(1, current_days - 1)} ngày.
    - Nếu yêu cầu mới nhất chỉ là đổi khách sạn hoặc quán ăn mà không nhắc gì đến việc thay đổi số ngày, BẮT BUỘC giữ nguyên {current_days} ngày như lịch trình cũ.
    - Tuyệt đối không để số ngày bị mắc kẹt. Phải đảm bảo mảng `days` bạn trả ra có độ dài khớp với phép toán trên.
    
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
