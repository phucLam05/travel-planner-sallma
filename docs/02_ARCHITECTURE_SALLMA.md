# Kiến trúc Hệ thống SALLMA V2 (Operational Layer)

SALLMA (State-Aware Large Language Model Architecture) là kiến trúc xoay quanh một bộ nhớ dùng chung duy nhất để giữ tính nhất quán tuyệt đối giữa các tiến trình suy luận.

* *Shared Memory (Data for Memory for Persistence)*: Được định nghĩa bằng `TravelState` của LangGraph. Đây là "Bộ não" trung tâm lưu trữ toàn bộ lịch sử hội thoại (`chat_history`), danh sách địa điểm thu thập được, lịch trình đang có, và tổng chi phí. Các Agent không giao tiếp chéo với nhau mà chỉ tương tác qua State này.

* *Workflow Agent (Intent Router)*: Agent cổng vào. Đọc toàn bộ `chat_history` và câu lệnh mới nhất để xác định ý định của người dùng (`create`, `refine_hotel`, `refine_activities`, `refine_all`). Nó không can thiệp sâu vào dữ liệu mà chỉ định hướng luồng.

* *Research Agent (RAG/Retrieval Agent)*: Agent "Thủ thư". Không tự tạo lịch trình, nhiệm vụ duy nhất là gọi Tool `retrieve_places` (Hybrid Search với PostgreSQL `pgvector`) để gom dữ liệu (Khách sạn, Điểm tham quan, Nhà hàng) bỏ vào "Giỏ hàng" (Context) trong State.

* *Planner Agent (Specialized Planner)*: Agent "Kiến trúc sư". Đọc toàn bộ `chat_history`, Giỏ hàng, và Lịch trình cũ. Nó tự động cân đối số ngày/đêm, gắp các địa điểm từ Giỏ hàng để xếp thành lịch trình và đường đi tối ưu. Nó tuyệt đối không gọi Tool tìm kiếm nào nữa, để tránh ảo giác.

* *Budgeting Node (Non-LLM)*: Một hàm Python thuần túy, duyệt qua mảng JSON do Planner tạo ra để cộng dồn chi phí chính xác từng đồng, không phụ thuộc vào dự đoán của LLM.