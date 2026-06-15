from typing import TypedDict, List, Dict, Any, Annotated
import operator

class TravelState(TypedDict):
    """
    Trạng thái lưu trữ (Shared Memory) cho LangGraph.
    Dùng để truyền thông tin giữa các Agent thay vì gọi trực tiếp.
    """
    # Lịch sử chat giữa người dùng và hệ thống
    chat_history: Annotated[List[Dict[str, str]], operator.add]
    
    # Câu hỏi/yêu cầu mới nhất từ người dùng
    latest_user_input: str
    
    # Mục đích của người dùng: 'create', 'refine_activities', 'refine_hotel', 'refine_all'
    intent: str
    
    # Kết quả tìm kiếm từ Research Agent (Giỏ hàng/Danh sách ứng viên)
    research_context: dict
    
    # Lịch trình chi tiết (được Planner Agent tạo ra, dạng JSON dict)
    itinerary_plan: dict
    
    # Chi tiết về khách sạn/chỗ ở (được Planner Agent tạo ra, dạng JSON dict)
    accommodation_details: dict
    
    # Tổng chi phí chuyến đi (được Budget Node tính toán)
    budget_details: dict
