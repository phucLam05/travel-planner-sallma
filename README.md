# SALLMA Travel Planner (Phase 2 - SALLMA V2 Architecture)

Dự án lên kế hoạch du lịch sử dụng kiến trúc **SALLMA (State-Aware Large Language Model Architecture)**, xây dựng với **LangGraph**, **Streamlit** và **OpenAI (GPT-4o-mini)**.

## Tính năng (Phase 2 - Routing & State Sync)
- **Giao diện 1 cửa (Single-page UI)**: Tích hợp Chatbot, Lịch trình, Dự toán Chi phí và Bản đồ hiển thị song song.
- **Bản đồ Tuyến đường (PyDeck)**: Tự động trích xuất tọa độ từ dữ liệu JSON và vẽ đường nối (PathLayer) lộ trình di chuyển theo từng ngày.
- **Kiến trúc SALLMA V2 bằng LangGraph**:
  - **Workflow Agent**: Phân tích ý định người dùng (Intent) dựa trên toàn bộ lịch sử hội thoại (Shared Memory).
  - **Research Agent**: RAG Agent chuyên kết nối với PostgreSQL `pgvector` để truy xuất địa điểm có thật (Hybrid Search). Hỗ trợ tìm kiếm thông minh bổ sung khi Refine.
  - **Planner Agent**: Agent lập kế hoạch thông minh, tự động tính toán số ngày lưu trú, điều chỉnh lịch trình, bắt buộc phải chọn đủ 3 bữa ăn/ngày, và không ảo giác.
  - **Budget Node**: Node toán học (Non-LLM) tính tổng chi phí chính xác tuyệt đối.
- **Database (PostgreSQL + pgvector)**: Lưu trữ dữ liệu thực và Vector Embeddings (Google `text-embedding-004`).

## Cài đặt và Chạy thử nghiệm

1. **Clone repository:**
   ```bash
   git clone <URL_REPO_CUA_BAN>
   cd travel_planner
   ```

2. **Cài đặt môi trường:**
   Tạo môi trường ảo (khuyến nghị) và cài đặt các gói phụ thuộc:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Trên Windows dùng: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Cấu hình API Key:**
   Tạo file `.env` tại thư mục gốc và thêm token của bạn (Database và LLM):
   ```env
   GOOGLE_API_KEY="Key Gemini của bạn (dùng cho Vector Embeddings)"
   GITHUB_TOKEN="Token GitHub Models (dùng cho ChatOpenAI gpt-4o-mini)"
   DB_HOST="localhost"
   DB_PORT="5432"
   DB_NAME="travel_db"
   DB_USER="postgres"
   DB_PASSWORD="yourpassword"
   ```

4. **Khởi tạo dữ liệu:**
   Chạy script Seed để nạp dữ liệu mẫu vào PostgreSQL:
   ```bash
   python seed_db.py
   ```

5. **Khởi chạy ứng dụng:**
   ```bash
   streamlit run app.py
   ```

## Cấu trúc thư mục

```
travel_planner/
├── app.py                      # Giao diện Streamlit chính (PyDeck Map, Chat, Status Stream)
├── core/
│   ├── database.py             # Database Manager & Vector Search
│   ├── graph.py                # Cấu hình luồng chạy LangGraph
│   ├── logger.py               # Thiết lập ghi log hệ thống
│   └── state.py                # Định nghĩa Shared State (Memory) cho LangGraph
├── agents/
│   ├── workflow_agent.py       # Agent phân loại Intent từ History
│   ├── research_agent.py       # Agent RAG truy xuất dữ liệu từ Postgres
│   ├── planner_agent.py        # Agent lập kế hoạch và tối ưu Route
│   └── budget_node.py          # Hàm tính toán chi phí (Non-LLM)
├── tools/
│   └── travel_tools.py         # Khai báo Tool calling
├── docs/                       # Tài liệu thiết kế kiến trúc
├── .env                        # Biến môi trường (không commit)
├── .gitignore                  # Bỏ qua các file không cần thiết
└── requirements.txt            # Danh sách thư viện phụ thuộc
```

## Giấy phép
Dự án được phân phối dưới giấy phép MIT.
