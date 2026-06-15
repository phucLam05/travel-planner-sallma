from langgraph.graph import StateGraph, START, END
from core.state import TravelState
from agents.workflow_agent import workflow_node
from agents.research_agent import research_node
from agents.planner_agent import planner_node
from agents.budget_node import budget_node
from core.logger import get_logger

logger = get_logger("Graph")

def route_intent(state: TravelState):
    """
    Định tuyến sau Workflow Agent.
    Nếu tạo mới hoặc thay đổi lớn -> Research lại.
    Nếu chỉ refine nhỏ (với context đã có đủ data) thì có thể chỉ chạy Planner, 
    nhưng để đơn giản và an toàn nhất cho hybrid search, ta chạy Research -> Planner cho mọi refine 
    trừ phi bạn muốn tối ưu cực sâu (chưa cần ở Phase này).
    Tạm thời: Workflow -> Research -> Planner -> Budget.
    """
    return "research"

def build_graph():
    """
    Xây dựng luồng xử lý bằng LangGraph.
    """
    logger.info("Đang khởi tạo StateGraph...")
    builder = StateGraph(TravelState)

    # Đăng ký các Node (các Agent)
    builder.add_node("workflow", workflow_node)
    builder.add_node("research", research_node)
    builder.add_node("planner", planner_node)
    builder.add_node("budget", budget_node)

    # Đăng ký các Edge (luồng chuyển)
    builder.add_edge(START, "workflow")
    
    # Từ workflow đi đâu?
    builder.add_conditional_edges("workflow", route_intent, {
        "research": "research"
    })
    
    builder.add_edge("research", "planner")
    builder.add_edge("planner", "budget")
    builder.add_edge("budget", END)

    # Biên dịch đồ thị
    graph = builder.compile()
    logger.info("Đã compile thành công StateGraph.")
    return graph
