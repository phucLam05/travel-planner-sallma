import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from core.state import TravelState
from core.logger import get_logger
from core.llm_factory import build_text_llm, invoke_with_retry
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
    
    from core.knowledge_layer import AgentConfigurationCatalog
    config = AgentConfigurationCatalog.get_config("research_agent")

    llm = build_text_llm(
        model=config.get("model"),
        temperature=config.get("temperature", 0.2),
    )
    llm_with_tools = llm.bind_tools([retrieve_places])
    
    system_prompt = config.get("system_prompt", "").format(
        intent=intent,
        context_json=json.dumps(current_context, ensure_ascii=False)
    )
    
    logger.debug(f"System Prompt: {system_prompt}")
    
    messages = [SystemMessage(content=system_prompt)]
    from langchain_core.messages import AIMessage
    for msg in chat_history:
        if msg.get("role") == "User":
            messages.append(HumanMessage(content=msg.get("content")))
        else:
            messages.append(AIMessage(content=msg.get("content")))
            
    logger.debug("Gọi LLM để research dữ liệu...")
    response = invoke_with_retry(llm_with_tools, messages)
    
    MAX_ITERATIONS = 5
    iteration_count = 0
    
    while response.tool_calls and iteration_count < MAX_ITERATIONS:
        iteration_count += 1
        # Quan trọng: Chỉ append AIMessage chứa tool_calls MỘT LẦN duy nhất
        messages.append(response)
        
        for tool_call in response.tool_calls:
            logger.info(f"Research Agent gọi Tool: {tool_call['name']} với args: {tool_call['args']}")
            
            try:
                # Cách chuẩn nhất của Langchain với OpenAI: truyền toàn bộ dict tool_call vào invoke
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
        
        if iteration_count >= MAX_ITERATIONS:
            logger.warning(f"Research Agent đã đạt giới hạn {MAX_ITERATIONS} vòng lặp. Ép buộc xuất JSON.")
            messages.append(SystemMessage(content="Bạn đã đạt giới hạn số lần tìm kiếm. KHÔNG GỌI THÊM TOOL NÀO NỮA. Dựa trên dữ liệu hiện tại, hãy lập tức trả về kết quả theo định dạng JSON như đã yêu cầu. Nếu thiếu dữ liệu, hãy điền danh sách rỗng [] cho hạng mục đó."))
            # Gọi llm GỐC (không bind tools) để ngăn chặn nó gọi tool tiếp
            response = invoke_with_retry(llm, messages)
            break
        else:
            # Tiếp tục vòng lặp bình thường
            response = invoke_with_retry(llm_with_tools, messages)
    
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
        logger.info("Research Agent hoàn thành (JSON parsed).")
        return {"research_context": json_data}
    except Exception as e:
        logger.error(f"Lỗi parse JSON Research: {e}")
        return {"research_context": {"error": "Không thể tổng hợp dữ liệu", "raw_output": final_text}}
