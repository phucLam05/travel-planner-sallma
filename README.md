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
- JSON: [benchmark_full_20260617_063715.json](benchmarks/results/benchmark_full_20260617_063715.json)
- Markdown: [benchmark_full_20260617_063715.md](benchmarks/results/benchmark_full_20260617_063715.md)
- Academic write-up: [BENCHMARK_ANALYSIS.md](docs/BENCHMARK_ANALYSIS.md)

Thiết lập chạy:
- `30` create prompts
- `2` multi-turn sessions, mỗi session `10` turns
- latency suite với `5` concurrent simulated rooms
- text model: `gemini-3.1-flash-lite`

### Tóm tắt so sánh

| Criterion | Single-Agent | Multi-Agent | How the number is produced |
|---|---:|---:|---|
| Correctness | `43.73%` verified rate | `99.39%` verified rate | Kết quả này là **macro-average trên 30 cases**. Single-agent có `109` địa điểm verified trên `249` địa điểm sinh ra tổng cộng; multi-agent có `418/420`. Tuy nhiên số công bố `43.73%` và `99.39%` được tính theo `mean(case_verified_rate)` chứ không phải gộp toàn bộ địa điểm rồi chia một lần. |
| Hallucination | `56.27%` | `0.61%` | Cũng là **macro-average trên 30 cases** với công thức `hallucination_rate = 1 - verified_rate`. Tính theo tổng raw counts thì single-agent có `140/249` địa điểm không verify được, còn multi-agent là `2/420`. |
| Budget accuracy | `531,333 VND` average delta | `0 VND` average delta | Benchmark tính `budget_delta = abs(claimed_total_cost - recomputed_total_cost)` cho từng case, rồi lấy trung bình trên `30` cases. Tổng sai số raw của single-agent là `15,940,000 VND`, chia `30` ra `531,333 VND`; multi-agent có tổng sai số `0 VND`. |
| Consistency (create cases) | `0.2` violations/case | `4.1` violations/case | Bộ kiểm tra consistency đếm các lỗi như `nights_mismatch`, `time_order`, `missing_coordinates`, `duplicate_activity`, `route_distance`. Single-agent có tổng `6` violations trên `30` create cases nên trung bình `0.2`; multi-agent có `123/30 = 4.1`. |
| State retention | `100%` pass rate | `100%` pass rate | Có `2` session, mỗi session có `5` checks, nên tổng là `10/10` checks passed cho cả hai hệ. Công thức là `state_retention_pass_rate = passed_checks / total_checks`. |
| Consistency (10-turn sessions) | `0.5` violations/session | `6.0` violations/session | Sau khi hoàn tất `2` session nhiều lượt, benchmark chạy lại consistency checker trên state cuối cùng. Single-agent có tổng `1` violation trên `2` session nên ra `0.5`; multi-agent có `12/2 = 6.0`. |
| Latency - Create | `19.814s` | `85.533s` | Đây là trung bình của `10` samples trong latency suite dưới `5` concurrent simulated rooms. Tổng thời gian cộng dồn xấp xỉ là `198.14s` cho single-agent và `855.33s` cho multi-agent. |
| Latency - Refine | `18.628s` | `50.770s` | Trung bình của `10` samples. Tổng thời gian cộng dồn xấp xỉ là `186.28s` cho single-agent và `507.70s` cho multi-agent. |
| Latency - Budget | `19.572s` | `0.000s` | Trung bình của `10` samples. Tổng thời gian cộng dồn xấp xỉ là `195.72s` cho single-agent; multi-agent dùng `Budget Node` Python thuần nên gần như `0s` trên mọi sample. |
| User-perceived usefulness (proxy) | `4.17/5` | `3.79/5` | Đây là **automated proxy**, không phải questionnaire thật. Single-agent có tổng điểm raw `125.05` trên `30` cases nên trung bình `4.17`; multi-agent có `113.59/30 = 3.79`. |

### Diễn giải theo 6 tiêu chí đánh giá

1. **Correctness**
   Benchmark đã phủ tiêu chí này trực tiếp. Con số `43.73%` và `99.39%` là **trung bình theo từng case** của tỷ lệ địa điểm được đối chiếu thành công với knowledge base thật trong database. Raw counts tương ứng là `109/249` địa điểm cho single-agent và `418/420` cho multi-agent.

2. **Budget accuracy**
   Benchmark đã phủ trực tiếp. Single-agent có tổng sai số `15,940,000 VND` trên `30` cases nên lệch trung bình `531,333 VND`, còn multi-agent lệch `0 VND` vì tổng chi phí cuối được tính bởi `Budget Node` deterministic thay vì để LLM tự cộng.

3. **Consistency**
   Benchmark đã phủ bằng một bộ luật kiểm tra tự động. Bộ đo hiện tại xem contradiction là các lỗi cấu trúc và logic giữa itinerary, route, hotel và budget metadata, ví dụ số đêm không khớp số ngày hoặc activity quá xa hotel. Ở create benchmark, raw totals là `6` violations cho single-agent và `123` cho multi-agent.

4. **State retention**
   Benchmark đã phủ bằng `2` hội thoại nhiều lượt, mỗi hội thoại `10` turns. Cả hai hệ đều đạt `10/10` checks passed, tương đương `100%` pass rate trong bộ kiểm tra giữ trạng thái.

5. **Latency**
   Benchmark đã phủ trực tiếp bằng latency suite chạy đồng thời `5` group rooms mô phỏng, tách riêng `Create`, `Refine`, `Budget`. Mỗi workflow có `10` samples. Kết quả cho thấy multi-agent đúng hơn nhưng chậm hơn đáng kể ở hai workflow có LLM orchestration.

6. **User-perceived usefulness**
   Benchmark mới chỉ phủ một phần. Giá trị `4.17/5` và `3.79/5` hiện là **proxy tự động**, với raw totals lần lượt là `125.05/30` và `113.59/30`, chưa phải questionnaire Likert thật từ người dùng. Nếu cần đúng tuyệt đối với tiêu chí nghiên cứu, cần bổ sung khảo sát người dùng sau tác vụ.

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
