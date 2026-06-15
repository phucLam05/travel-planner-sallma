import streamlit as st
import pandas as pd
import pydeck as pdk
from dotenv import load_dotenv
import os

# Nạp biến môi trường từ .env
load_dotenv()

from core.graph import build_graph
from core.state import TravelState

st.set_page_config(page_title="SALLMA Travel Planner", layout="wide")

# Hàm khởi tạo LangGraph
@st.cache_resource
def get_travel_graph():
    return build_graph()

graph = get_travel_graph()

# Tiêu đề ứng dụng
st.title("✈️ SALLMA Travel Planner (Phase 2 - UI Route)")
st.markdown("Hệ thống lên kế hoạch du lịch sử dụng kiến trúc Multi-Agent đồng bộ với JSON, vẽ Route Bản đồ.")

# Khởi tạo state trong Streamlit
if "travel_state" not in st.session_state:
    st.session_state.travel_state = TravelState(
        chat_history=[],
        latest_user_input="",
        intent="",
        research_context={},
        itinerary_plan={},
        accommodation_details={},
        budget_details={}
    )

# Chia layout thành 2 cột chính
col_chat, col_result = st.columns([1, 2])

with col_chat:
    st.header("Trò chuyện & Yêu cầu")
    
    # Hiển thị lịch sử hội thoại
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.travel_state.get("chat_history", []):
            role = msg.get("role", "User")
            if role == "User":
                st.markdown(f"👤 **Bạn**: {msg.get('content')}")
            else:
                st.markdown(f"🤖 **Hệ thống**: {msg.get('content')}")
            
    # Ô nhập liệu
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Nhập yêu cầu (VD: Lên lịch trình Đà Nẵng 2 ngày, đổi quán ăn...)")
        submit_button = st.form_submit_button("Gửi")

with col_result:
    st.header("Kết quả Lịch trình Đồng bộ")
    
    itinerary = st.session_state.travel_state.get("itinerary_plan", {})
    acc = st.session_state.travel_state.get("accommodation_details", {})
    budget = st.session_state.travel_state.get("budget_details", {})
    
    scatter_data = [] # Lưu các điểm để vẽ scatter
    path_data = [] # Lưu route từng ngày để vẽ path
    
    # Màu sắc phân biệt cho các ngày (tối đa 5 ngày demo)
    colors = [
        [255, 0, 0],    # Đỏ
        [0, 255, 0],    # Xanh lá
        [0, 0, 255],    # Xanh dương
        [255, 165, 0],  # Cam
        [128, 0, 128],  # Tím
    ]

    if not itinerary and not acc:
        st.info("Chưa có lịch trình nào được tạo. Hãy nhập yêu cầu bên trái.")
    else:
        # 1. Hiển thị thông tin khách sạn
        hotel_coords = None
        if acc and "hotel_name" in acc:
            st.subheader(f"🏨 {acc.get('hotel_name')}")
            st.write(f"_{acc.get('description', '')}_")
            st.write(f"**Giá mỗi đêm:** {acc.get('price_per_night', 0):,} VNĐ")
            st.write(f"**Số đêm lưu trú:** {acc.get('nights', 0)} đêm")
            
            if "lat" in acc and "lng" in acc:
                hotel_coords = [float(acc["lng"]), float(acc["lat"])]
                scatter_data.append({
                    "lat": float(acc["lat"]), 
                    "lon": float(acc["lng"]), 
                    "name": acc["hotel_name"],
                    "color": [200, 200, 200]
                })
        
        st.divider()
        
        # 2. Hiển thị Lịch trình
        st.subheader("📍 Lịch trình chi tiết")
        if "days" in itinerary:
            for i, day in enumerate(itinerary["days"]):
                day_color = colors[i % len(colors)]
                day_coords = []
                
                # Nếu có khách sạn, ngày nào cũng bắt đầu xuất phát từ khách sạn
                if hotel_coords:
                    day_coords.append(hotel_coords)
                
                with st.expander(f"Ngày {day.get('day', '')}", expanded=True):
                    for act in day.get("activities", []):
                        price_str = f" - 💰 {act.get('price', 0):,} VNĐ" if act.get('price') else ""
                        st.markdown(f"**{act.get('time', '')} | {act.get('place', '')}**{price_str}")
                        st.caption(act.get('description', ''))
                        
                        if "lat" in act and "lng" in act:
                            coord = [float(act["lng"]), float(act["lat"])]
                            day_coords.append(coord)
                            scatter_data.append({
                                "lat": float(act["lat"]), 
                                "lon": float(act["lng"]), 
                                "name": act["place"],
                                "color": day_color
                            })
                            
                # Nếu có từ 2 điểm trở lên thì vẽ line
                if len(day_coords) >= 2:
                    path_data.append({
                        "path": day_coords,
                        "color": day_color
                    })
                    
        elif "error" in itinerary:
            st.error(itinerary["error"])
            
        # 3. Hiển thị Bản đồ (PyDeck)
        if scatter_data:
            st.subheader("🗺️ Bản đồ & Tuyến đường")
            
            # Tính trung tâm bản đồ
            avg_lat = sum(d["lat"] for d in scatter_data) / len(scatter_data)
            avg_lon = sum(d["lon"] for d in scatter_data) / len(scatter_data)
            
            view_state = pdk.ViewState(latitude=avg_lat, longitude=avg_lon, zoom=12, pitch=45)
            
            layers = [
                pdk.Layer(
                    "ScatterplotLayer",
                    data=pd.DataFrame(scatter_data),
                    get_position="[lon, lat]",
                    get_fill_color="color",
                    get_radius=200,
                    pickable=True,
                )
            ]
            
            if path_data:
                layers.append(
                    pdk.Layer(
                        "PathLayer",
                        data=pd.DataFrame(path_data),
                        get_path="path",
                        get_color="color",
                        width_scale=20,
                        width_min_pixels=3,
                    )
                )
                
            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=view_state,
                layers=layers,
                tooltip={"text": "{name}"}
            ))
            
        st.divider()
        
        # 4. Hiển thị Bảng tính tiền
        if budget and "overall_total" in budget:
            st.subheader("💰 Bảng Dự Toán Chi Phí")
            c1, c2 = st.columns(2)
            c1.metric("🏨 Khách sạn", f"{budget.get('hotel_total', 0):,} VNĐ")
            c2.metric("🎫 Tham quan & Ăn uống", f"{budget.get('ticket_costs', 0):,} VNĐ")
            
            st.metric("💵 TỔNG CỘNG", f"{budget.get('overall_total', 0):,} VNĐ")


# Xử lý khi người dùng ấn nút Gửi
if submit_button and user_input:
    # Cập nhật state
    st.session_state.travel_state["latest_user_input"] = user_input
    
    # Thêm tin nhắn user vào lịch sử
    current_history = st.session_state.travel_state.get("chat_history", [])
    current_history.append({"role": "User", "content": user_input})
    st.session_state.travel_state["chat_history"] = current_history
    
    # Hộp trạng thái stream logs
    with st.status("🤖 Khởi động hệ thống Multi-Agent...", expanded=True) as status:
        try:
            # Chạy LangGraph dạng stream để lấy tiến trình
            for output in graph.stream(st.session_state.travel_state):
                for node_name, state_update in output.items():
                    if node_name == "workflow":
                        intent = state_update.get('intent')
                        status.update(label=f"🔄 Đã phân tích yêu cầu: Intent = {intent}")
                        st.write(f"✅ Đã xác định Intent: **{intent}**")
                        
                    elif node_name == "research":
                        status.update(label="🔍 Đang tìm kiếm dữ liệu (Hybrid Search)...")
                        st.write("✅ Đã lấy dữ liệu từ PostgreSQL Vector.")
                        
                    elif node_name == "planner":
                        status.update(label="🧠 Đang sắp xếp lịch trình và tuyến đường...")
                        st.write("✅ Đã lập Plan và chọn Khách sạn tối ưu.")
                        
                    elif node_name == "budget":
                        status.update(label="💰 Đang tính toán chi phí...")
                        st.write("✅ Đã hoàn tất bảng dự toán.")
                        
                    # Cập nhật state nội bộ để giữ luồng
                    st.session_state.travel_state = state_update
            
            status.update(label="Hoàn tất!", state="complete", expanded=False)
            
            # Thêm tin nhắn hệ thống báo thành công
            st.session_state.travel_state["chat_history"].append({
                "role": "System", 
                "content": f"Đã hoàn thành yêu cầu. Intent: {st.session_state.travel_state.get('intent')}."
            })
            
            # Rerun để cập nhật UI
            st.rerun()
            
        except Exception as e:
            status.update(label="Có lỗi xảy ra", state="error")
            st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")
