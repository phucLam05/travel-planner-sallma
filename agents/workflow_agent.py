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

    from core.knowledge_layer import AgentConfigurationCatalog
    config = AgentConfigurationCatalog.get_config("workflow_agent")

    # Cấu hình LLM GPT-4o-mini thông qua GitHub Models
    llm = ChatOpenAI(
        model=config.get("model", "gpt-4o-mini"),
        temperature=config.get("temperature", 0.0),
        base_url="https://models.inference.ai.azure.com",
        api_key=os.getenv("GITHUB_TOKEN")
    )
    
    # Prompt chặt chẽ để buộc LLM trả về đúng định dạng
    system_prompt = config.get("system_prompt", "")
    
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
            
    logger.info(f"Kết quả phân tích: Intent={intent}")
    return {"intent": intent}
