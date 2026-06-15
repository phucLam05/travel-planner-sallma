import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from core.state import TravelState
from core.logger import get_logger

logger = get_logger("WorkflowAgent")

def workflow_node(state: TravelState):
    """
    Agent đầu tiên tiếp nhận yêu cầu.
    Nhiệm vụ: Phân tích intent (create/refine) dựa trên Toàn bộ lịch sử chat.
    """
    logger.info("--- WORKFLOW AGENT ĐANG CHẠY ---")
    
    user_input = state.get("latest_user_input", "")
    chat_history = state.get("chat_history", [])
    if not user_input:
        logger.warning("Không có đầu vào từ người dùng.")
        return state

    logger.info(f"User Input: '{user_input}'")

    # Cấu hình LLM GPT-4o-mini thông qua GitHub Models
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        base_url="https://models.inference.ai.azure.com",
        api_key=os.getenv("GITHUB_TOKEN")
    )
    
    # Prompt chặt chẽ để buộc LLM trả về đúng định dạng
    system_prompt = """
    Bạn là một trợ lý điều phối quy trình du lịch (Workflow Router).
    Nhiệm vụ của bạn là đọc TOÀN BỘ lịch sử hội thoại, chú ý đặc biệt vào câu nói cuối cùng của người dùng, sau đó phân loại mục đích và CHỈ TRẢ VỀ DUY NHẤT 1 TỪ KHÓA Intent:
       - 'create': Người dùng muốn tạo lịch trình mới hoàn toàn (ví dụ: "Lên lịch trình đi...", "Tạo plan đi...").
       - 'refine_activities': Người dùng muốn thay đổi, tinh chỉnh địa điểm tham quan, quán ăn, lịch trình di chuyển, HOẶC thay đổi số ngày đi (thêm/bớt ngày) so với lịch trình đã có.
       - 'refine_hotel': Người dùng CHỈ muốn đổi khách sạn, đổi giá phòng, nơi ở.
       - 'refine_all': Người dùng muốn thay đổi hoàn toàn cả khách sạn và lịch trình cũ.
       
       *CHÚ Ý QUAN TRỌNG: Nếu người dùng dùng các từ như "đổi", "sửa", "thay", "thêm", "bớt", CHẮC CHẮN phải là refine.*
    
    KHÔNG ĐƯỢC GIẢI THÍCH THÊM. CHỈ TRẢ VỀ 1 TRONG 4 TỪ KHÓA INTENT TRÊN.
    """
    
    logger.debug(f"System Prompt: {system_prompt}")
    
    messages = [SystemMessage(content=system_prompt)]
    for msg in chat_history:
        if msg.get("role") == "User":
            messages.append(HumanMessage(content=msg.get("content")))
        else:
            messages.append(AIMessage(content=msg.get("content")))
    
    # Do user_input đã được thêm vào chat_history ở app.py nên không cần append thủ công ở đây nữa
    
    response = llm.invoke(messages)
    content = response.content
    if isinstance(content, list):
        result_text = "".join(
            block["text"] if isinstance(block, dict) and "text" in block else (block if isinstance(block, str) else "") 
            for block in content
        ).strip()
    else:
        result_text = str(content).strip()
    
    logger.debug(f"Workflow Agent LLM Output: {result_text}")
    
    # Tự động chuẩn hóa intent
    intent = result_text.lower()
    valid_intents = ['create', 'refine_activities', 'refine_hotel', 'refine_all']
    if intent not in valid_intents:
        # Fallback nếu LLM sinh ra text thừa
        for v in valid_intents:
            if v in intent:
                intent = v
                break
        else:
            intent = 'create'
            
    state["intent"] = intent
    logger.info(f"Kết quả phân tích: Intent={state.get('intent')}")
    return state
