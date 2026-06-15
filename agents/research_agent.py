import json
import re
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.state import TravelState
from core.logger import get_logger
from tools.travel_tools import retrieve_places

logger = get_logger("ResearchAgent")

def research_node(state: TravelState):
    """
    Agent chuyên thu thập dữ liệu (RAG).
    Sử dụng Hybrid Search để gom các options (Khách sạn, Điểm tham quan, Nhà hàng) thành một 'Giỏ hàng' (Context).
    """
    logger.info("--- RESEARCH AGENT ĐANG CHẠY ---")
    
    user_input = state.get("latest_user_input", "")
    chat_history = state.get("chat_history", [])
    intent = state.get("intent", "create")
    current_context = state.get("research_context", {})
    
    logger.info(f"User Input: '{user_input}'")
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        base_url="https://models.inference.ai.azure.com",
        api_key=os.getenv("GITHUB_TOKEN")
    )
    llm_with_tools = llm.bind_tools([retrieve_places])
    
    system_prompt = f"""
    Bạn là một Research Agent chuyên thu thập dữ liệu du lịch.
    Intent hiện tại: {intent}
    Giỏ hàng (Context) hiện tại: {json.dumps(current_context, ensure_ascii=False)}
    
    Nhiệm vụ của bạn là đọc TOÀN BỘ lịch sử hội thoại (đặc biệt là yêu cầu mới nhất) và dùng tool `retrieve_places` để tìm kiếm dữ liệu từ Database.
    
    - Nếu intent là 'create' hoặc 'refine_all': Tìm kiếm khoảng 3-5 khách sạn, 5-7 điểm tham quan, 3-5 nhà hàng.
    - Nếu intent là 'refine_hotel': CHỈ TÌM THÊM khách sạn mới theo yêu cầu. GIỮ NGUYÊN điểm tham quan và nhà hàng từ Giỏ hàng hiện tại.
    - Nếu intent là 'refine_activities': CHỈ TÌM THÊM điểm tham quan hoặc nhà hàng mới theo yêu cầu. GIỮ NGUYÊN khách sạn từ Giỏ hàng hiện tại.
    
    SAU KHI CÓ ĐỦ DỮ LIỆU TỪ CÁC LẦN GỌI TOOL (Hoặc kết hợp với dữ liệu cũ), bạn MỚI tổng hợp lại và TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON SAU (NẰM TRONG BLOCK ```json ... ```):
    {{
        "hotels": [
            {{"id": "...", "name": "...", "price": ..., "description": "...", "lat": ..., "lng": ...}}
        ],
        "attractions": [...],
        "restaurants": [...]
    }}
    
    Tuyệt đối chỉ trả về JSON, không giải thích. Đảm bảo JSON chứa đầy đủ khách sạn, điểm tham quan, nhà hàng (cả cũ và mới).
    """
    
    logger.debug(f"System Prompt: {system_prompt}")
    
    messages = [SystemMessage(content=system_prompt)]
    from langchain_core.messages import AIMessage
    for msg in chat_history:
        if msg.get("role") == "User":
            messages.append(HumanMessage(content=msg.get("content")))
        else:
            messages.append(AIMessage(content=msg.get("content")))
            
    logger.debug("Gọi LLM để research dữ liệu...")
    response = llm_with_tools.invoke(messages)
    
    while response.tool_calls:
        # Quan trọng: Chỉ append AIMessage chứa tool_calls MỘT LẦN duy nhất
        messages.append(response)
        
        for tool_call in response.tool_calls:
            logger.info(f"Research Agent gọi Tool: {tool_call['name']} với args: {tool_call['args']}")
            
            try:
                # Cách chuẩn nhất của Langchain với OpenAI: truyền toàn bộ dict tool_call vào invoke
                # Nó sẽ tự động thực thi và trả về một ToolMessage hợp lệ 100%
                if tool_call['name'] == 'retrieve_places':
                    tool_msg = retrieve_places.invoke(tool_call)
                    messages.append(tool_msg)
                else:
                    from langchain_core.messages import ToolMessage
                    messages.append(ToolMessage(content="Error: Tool not found", tool_call_id=tool_call['id'], name=tool_call['name']))
            except Exception as e:
                logger.error(f"Lỗi khi thực thi tool: {e}")
                from langchain_core.messages import ToolMessage
                messages.append(ToolMessage(content=f"Error: {e}", tool_call_id=tool_call['id'], name=tool_call['name']))
        
        # Gửi lại toàn bộ lịch sử (bao gồm AIMessage chứa tool_calls và các ToolMessage kết quả) cho LLM
        response = llm_with_tools.invoke(messages)
    
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
        state["research_context"] = json_data
        logger.info("Research Agent hoàn thành (JSON parsed).")
    except Exception as e:
        logger.error(f"Lỗi parse JSON Research: {e}")
        state["research_context"] = {"error": "Không thể tổng hợp dữ liệu", "raw_output": final_text}
    
    return state
