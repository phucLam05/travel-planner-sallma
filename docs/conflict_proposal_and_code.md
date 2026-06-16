### **Danh sách việc cần làm để code khớp với proposal**

#### **🔴 Bug cần fix trước khi demo (bắt buộc)**

**1\. `agents/planner_agent.py` — lỗi biến `result_text` vs `final_text`**  
 Trong nhánh `if isinstance(content, list)` gán vào `final_text`, nhưng phía dưới lại dùng `result_text` → NameError lúc chạy. Đổi tất cả về `result_text` cho nhất quán.

**2\. `requirements.txt` — file bị null bytes**  
 `langchain-openai` bị lỗi encoding. Xóa file, tạo lại sạch với đúng các thư viện đang dùng: `langgraph`, `langchain-core`, `langchain-openai`, `langchain-google-genai`, `streamlit==1.36.0`, `python-dotenv`, `psycopg2-binary`, `pgvector`, `pydeck`, `pandas`.

---

#### **🟡 Cần thêm để khớp với proposal (quan trọng cho thuyết trình)**

**3\. `tools/travel_tools.py` — xóa `calculate_budget` tool**  
 Tool này được định nghĩa nhưng không bao giờ gọi vì Budget Node dùng pure Python. Nên xóa đi hoặc thêm comment giải thích rõ "intentionally replaced by deterministic budget\_node" để tránh người đọc nhầm.

**4\. `core/graph.py` — hàm `route_intent` chưa thực sự route**  
 Hiện tại luôn return `"research"` bất kể intent là gì. Proposal mô tả routing thông minh hơn: nếu `refine_hotel` thì có thể bỏ qua research (đã có context). Tối thiểu nên thêm comment giải thích đây là "simplified routing — future work".

**5\. Thêm file `agents/accommodation_agent.py` hoặc ghi chú rõ**  
 Proposal liệt kê Accommodation Agent riêng, nhưng code hiện tại Planner Agent xử lý luôn cả hotel \+ itinerary trong 1 LLM call. Hai lựa chọn: tách thành agent riêng, hoặc thêm docstring vào `planner_agent.py` giải thích rõ "handles both planning and accommodation selection as a unified agent".

**6\. Thêm `docs/EVALUATION.md`**  
 Proposal có mục 4.3 đề cập 6 metrics đánh giá (correctness, budget accuracy, consistency, state retention, latency, user usefulness). Hiện repo chưa có file này. Cần thêm ít nhất một file mô tả cách đo từng metric, kèm kết quả thử nghiệm sơ bộ dù là manual test.

---

#### **🟢 Thêm để strengthen điểm cải tiến so với SALLMA gốc**

**7\. Thêm `docs/LIMITATIONS.md`**  
 Ghi thẳng thắn những gì proposal đề xuất nhưng chưa implement: group-room multi-user, event-log conflict resolution, Kubernetes deployment, Accommodation Agent tách riêng. Giúp bài thuyết trình có phần "honest limitation \+ future work" rõ ràng.

**8\. Thêm README section so sánh với single-agent baseline**  
 Proposal nhấn mạnh điểm cải tiến so với single-agent. Trong README thêm 1 bảng nhỏ mô tả: nếu dùng 1 LLM call duy nhất thì sẽ bị hallucinate địa điểm, quên context, budget sai — và hệ thống này giải quyết thế nào.

**9\. `core/database.py` — thêm embedding model fallback**  
 Hiện dùng `models/gemini-embedding-2` nhưng trong README ghi `text-embedding-004`. Nên đồng nhất tên model trong code và tài liệu để tránh câu hỏi khi demo.

---

#### **Thứ tự ưu tiên**

| Ưu tiên | Việc | Lý do |
| ----- | ----- | ----- |
| 1 | Fix bug `planner_agent.py` | App sẽ crash khi content là list |
| 2 | Fix `requirements.txt` | Người chấm clone về không chạy được |
| 3 | Thêm `docs/EVALUATION.md` | Proposal có mục này, thiếu sẽ bị hỏi |
| 4 | Thêm `docs/LIMITATIONS.md` | Thể hiện hiểu rõ giới hạn của mình |
| 5 | Fix `route_intent` \+ comment | Khớp với mô tả kiến trúc trong proposal |
| 6 | Ghi chú Accommodation Agent | Tránh mâu thuẫn với proposal |
| 7 | Fix tên embedding model | Nhất quán giữa code và docs |
| 8 | README baseline comparison | Strengthen điểm cải tiến |

\======================================================================

#### **Mâu thuẫn cần điều chỉnh trong proposal hoặc code**

**1\. Accommodation Agent — proposal nói có, code không có**  
 [ĐÃ GIẢI QUYẾT] Đã cập nhật lại RESEARCH_PROPOSAL.md để loại bỏ Accommodation Agent và gộp nhiệm vụ chọn khách sạn vào Planner Agent. Cách làm này tinh gọn hơn và đã được điều chỉnh nhất quán.

**2\. Group-room / multi-user — proposal là điểm cải tiến chính, code chưa có**  
 Section 4.2 của proposal dành cả trang mô tả group-room, event-log, last-write-wins, group confirmation. Đây là đóng góp trọng tâm được nhấn mạnh. Nhưng code chỉ có session 1 người (UUID per browser), `save_session` dùng `ON CONFLICT DO UPDATE` ghi đè hoàn toàn.

→ Đây là task **lớn nhất** cần làm nếu muốn code khớp proposal. Nếu không làm kịp thì phải **điều chỉnh lại ngôn ngữ proposal** từ "implemented" sang "proposed as future work".

**3\. Knowledge Layer — proposal mô tả chi tiết, code chỉ implement một phần**  
 Proposal liệt kê: Workflow Metamodel Catalog, Agent Configuration Catalog, Deployment Metamodel Catalog. Trong code, những thứ này nằm rải rác trong prompt string và `graph.py`, không có catalog thực sự nào được lưu vào DB.

→ Cần thêm ghi chú trong `docs/` giải thích mapping giữa khái niệm trong proposal và cách implement thực tế trong code.

