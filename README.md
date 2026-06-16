# SALLMA Travel Planner

Dự án lên kế hoạch du lịch sử dụng kiến trúc **SALLMA (State-Aware Large Language Model Architecture)**, xây dựng với **LangGraph**, **Streamlit** và **Google Gemini**.

## Tính năng
- **Giao diện 1 cửa (Single-page UI)**: Tích hợp Chatbot, Lịch trình, Dự toán Chi phí và Bản đồ hiển thị song song.
- **Bản đồ Tuyến đường (PyDeck)**: Tự động trích xuất tọa độ từ dữ liệu JSON và vẽ đường nối (PathLayer) lộ trình di chuyển theo từng ngày.
- **Kiến trúc SALLMA bằng LangGraph**:
  - **Workflow Agent**: Phân tích ý định người dùng (Intent) dựa trên toàn bộ lịch sử hội thoại (Shared Memory).
  - **Research Agent**: RAG Agent chuyên kết nối với PostgreSQL `pgvector` để truy xuất địa điểm có thật (Hybrid Search). Hỗ trợ tìm kiếm thông minh bổ sung khi Refine.
  - **Planner Agent**: Agent lập kế hoạch thông minh, tự động tính toán số ngày lưu trú, điều chỉnh lịch trình, bắt buộc phải chọn đủ 3 bữa ăn/ngày, và không ảo giác.
  - **Budget Node**: Node toán học (Non-LLM) tính tổng chi phí chính xác tuyệt đối.
- **Database (PostgreSQL + pgvector)**: Lưu trữ dữ liệu thực và Vector Embeddings (Google `gemini-embedding-2`).

## 📊 Benchmark Results
Kết quả dưới đây được lấy trực tiếp từ full benchmark gần nhất:
- JSON: [benchmark_full_20260617_063715.json](/home/danielaston/Desktop/Workspace/FPT/SWD392/travel-planner-sallma/benchmarks/results/benchmark_full_20260617_063715.json)
- Markdown: [benchmark_full_20260617_063715.md](/home/danielaston/Desktop/Workspace/FPT/SWD392/travel-planner-sallma/benchmarks/results/benchmark_full_20260617_063715.md)
- Academic write-up: [BENCHMARK_ANALYSIS.md](/home/danielaston/Desktop/Workspace/FPT/SWD392/travel-planner-sallma/docs/BENCHMARK_ANALYSIS.md)

Thiết lập chạy:
- `30` create prompts
- `2` multi-turn sessions, mỗi session `10` turns
- latency suite với `5` concurrent simulated rooms
- text model: `gemini-3.1-flash-lite`

### Tóm tắt so sánh

| Criterion | Single-Agent | Multi-Agent | How the number is produced |
|---|---:|---:|---|
| Correctness | `43.73%` verified rate | `99.39%` verified rate | Với mỗi output, benchmark trích xuất tên khách sạn, nhà hàng, điểm tham quan rồi fuzzy-match với bảng `places` trong PostgreSQL. `verified_rate = verified_places / total_places`. |
| Hallucination | `56.27%` | `0.61%` | `hallucination_rate = 1 - verified_rate`, tức tỷ lệ địa điểm không đối chiếu được với knowledge base đã xác thực. |
| Budget accuracy | `531,333 VND` average delta | `0 VND` average delta | Benchmark lấy `budget.total_cost` do hệ thống trả về rồi tính lại tổng chi phí một cách deterministic từ `hotel.price_per_night * nights + sum(activity.price)`. Sai số tuyệt đối là `budget_delta`. |
| Consistency (create cases) | `0.2` violations/case | `4.1` violations/case | Rule-based consistency checker đếm số mâu thuẫn như `nights_mismatch`, `time_order`, `missing_coordinates`, `duplicate_activity`, `route_distance`. Giá trị là số lỗi trung bình trên mỗi create case. |
| State retention | `100%` pass rate | `100%` pass rate | Mỗi session 10 turns được kiểm tra khả năng giữ hotel, itinerary days, budget và các thay đổi refine. `pass_rate = passed_checks / total_checks`. |
| Consistency (10-turn sessions) | `0.5` violations/session | `6.0` violations/session | Sau khi hoàn tất session nhiều lượt, benchmark chạy lại bộ kiểm tra consistency trên state cuối cùng để đo mâu thuẫn tích lũy trong hội thoại dài. |
| Latency - Create | `19.814s` | `85.533s` | Trung bình end-to-end của workflow `create` trong latency suite, chạy `10` samples dưới `5` concurrent simulated rooms. |
| Latency - Refine | `18.628s` | `50.770s` | Trung bình end-to-end của workflow `refine` trong latency suite, cũng với `10` samples và `5` concurrent simulated rooms. |
| Latency - Budget | `19.572s` | `0.000s` | Single-agent phải dùng LLM để suy ra tổng chi phí, còn multi-agent dùng `Budget Node` Python thuần nên thời gian gần như bằng 0. |
| User-perceived usefulness (proxy) | `4.17/5` | `3.79/5` | Đây là automated proxy, không phải bảng hỏi thật. Điểm được suy ra từ `clarity`, `trustworthiness`, `collaboration`, trong đó trustworthiness tăng khi verified rate cao và budget delta thấp. |

### Diễn giải theo 6 tiêu chí đánh giá

1. **Correctness**
   Benchmark đã phủ tiêu chí này trực tiếp. Con số `43.73%` và `99.39%` là tỷ lệ địa điểm được đối chiếu thành công với knowledge base thật trong database, thay vì do LLM tự sinh không có grounding.

2. **Budget accuracy**
   Benchmark đã phủ trực tiếp. Single-agent lệch trung bình `531,333 VND`, còn multi-agent lệch `0 VND` vì tổng chi phí cuối được tính bởi `Budget Node` deterministic thay vì để LLM tự cộng.

3. **Consistency**
   Benchmark đã phủ bằng một bộ luật kiểm tra tự động. Bộ đo hiện tại xem contradiction là các lỗi cấu trúc và logic giữa itinerary, route, hotel và budget metadata, ví dụ số đêm không khớp số ngày hoặc activity quá xa hotel.

4. **State retention**
   Benchmark đã phủ bằng `2` hội thoại nhiều lượt, mỗi hội thoại `10` turns. Cả hai hệ đều đạt `100%` pass rate trong bộ kiểm tra giữ trạng thái.

5. **Latency**
   Benchmark đã phủ trực tiếp bằng latency suite chạy đồng thời `5` group rooms mô phỏng, tách riêng `Create`, `Refine`, `Budget`. Kết quả cho thấy multi-agent đúng hơn nhưng chậm hơn đáng kể ở hai workflow có LLM orchestration.

6. **User-perceived usefulness**
   Benchmark mới chỉ phủ một phần. Giá trị `4.17/5` và `3.79/5` hiện là **proxy tự động**, chưa phải questionnaire Likert thật từ người dùng. Nếu cần đúng tuyệt đối với tiêu chí nghiên cứu, cần bổ sung khảo sát người dùng sau tác vụ.

### Kết luận ngắn
- Multi-agent vượt trội rất rõ ở `Correctness`, `Hallucination control` và `Budget accuracy`.
- Single-agent đang nhanh hơn đáng kể ở `Create` và `Refine`.
- `State retention` hiện đang ngang nhau theo bộ kiểm tra hiện tại.
- Metric `Consistency` đang phạt multi-agent khá nặng, vì vậy khi viết báo cáo nên mô tả rõ đây là **rule-based consistency metric**, không phải đánh giá thủ công toàn diện.

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
   GOOGLE_API_KEY="Key Gemini của bạn (dùng cho Text Generation va Vector Embeddings)"
   SALLMA_TEXT_MODEL="gemini-3.1-flash-lite"
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
