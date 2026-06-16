import json
from langchain_core.tools import tool
from core.database import DatabaseManager

@tool
def retrieve_places(category: str, semantic_query: str, limit: int = 5) -> str:
    """
    Truy xuất danh sách các địa điểm từ cơ sở dữ liệu bằng Hybrid Search (Lọc Category + Vector Semantic Search).
    
    Args:
        category (str): 'hotel', 'attraction', hoặc 'restaurant'.
        semantic_query (str): Câu truy vấn tự nhiên mô tả nhu cầu (VD: 'khách sạn gần biển', 'quán ăn lãng mạn', 'cảnh đẹp thiên nhiên').
        limit (int): Số lượng kết quả trả về.
        
    Returns:
        str: JSON danh sách địa điểm (kèm tọa độ).
    """
    results = DatabaseManager.hybrid_search(category=category, query=semantic_query, limit=limit)
    
    if not results:
        return f"Không tìm thấy dữ liệu cho query '{semantic_query}'."
        
    return json.dumps(results, ensure_ascii=False, indent=2)


# Removed calculate_budget tool as budgeting is handled natively and deterministically by the Budget Node.
