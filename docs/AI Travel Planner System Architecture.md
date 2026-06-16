# SOFTWARE REQUIREMENT SPECIFICATION & BACKEND ARCHITECTURE

# AI TRAVEL PLANNER SYSTEM

## 1\. Mục tiêu tài liệu

Tài liệu này mô tả cách hệ thống Backend của ứng dụng AI Travel Planner vận hành, quản lý dữ liệu, tích hợp LLM/RAG, xây dựng database và tổ chức source code để triển khai một hệ thống có khả năng tạo lịch trình du lịch hoàn chỉnh.

Hệ thống không chỉ dừng ở việc tìm địa điểm, tính đường đi hoặc ước lượng chi phí từng địa điểm, mà phải có khả năng ghép các dữ liệu đó thành một travel plan hoàn chỉnh gồm:

* Lịch trình theo từng ngày.

* Lịch trình theo từng khung giờ.

* Địa điểm cụ thể cho từng hoạt động.

* Chi phí dự kiến.

* Thời gian di chuyển giữa các địa điểm.

* Tổng ngân sách.

* Route summary.

* Khả năng chỉnh sửa và lưu version plan.

---

# 2\. Phạm vi MVP

## 2.1. MVP sẽ làm

Trong giai đoạn MVP, hệ thống tập trung vào các tính năng cốt lõi sau:

1. User authentication cơ bản.

2. Tạo trip / travel room.

3. Nhập thông tin chuyến đi:

   * Điểm đến.

   * Ngày đi / ngày về.

   * Số người.

   * Ngân sách.

   * Sở thích.

   * Phong cách du lịch.

4. Truy xuất địa điểm từ database đã crawl.

5. Tạo 3 plan:

   * Budget Plan.

   * Chill Plan.

   * Balanced Plan.

6. Ghép địa điểm thành lịch trình theo ngày / giờ.

7. Tính toán:

   * Chi phí từng địa điểm.

   * Tổng chi phí từng ngày.

   * Tổng chi phí toàn chuyến.

   * Khoảng cách / thời gian di chuyển giữa các địa điểm.

8. Validate plan:

   * Không vượt ngân sách.

   * Không trùng địa điểm.

   * Không xếp lịch quá dày.

   * Không xếp địa điểm ngoài giờ mở cửa.

   * Không chọn địa điểm quá xa nhau trong cùng một buổi.

9. Cho phép user chọn một plan làm bản nháp.

10. Lưu plan version để phục vụ chỉnh sửa về sau.

## 2.2. MVP chưa làm

Các tính năng sau không thuộc MVP:

1. Live location.

2. Group chat real-time.

3. Voting nâng cao.

4. Community post / review.

5. Reputation / badge.

6. Offline map.

7. CRAG / Web Search fallback.

8. LoRA fine-tuning.

9. GraphRAG.

10. Sự kiện real-time.

11. Weather-aware planning.

12. Tự động xử lý kẹt xe / trời mưa.

13. Tối ưu TSP phức tạp toàn chuyến.

14. Cá nhân hóa dài hạn theo lịch sử user.

Các tính năng này có thể đưa vào các phiên bản cập nhật tương lai.

---

# 3\. Tổng quan kiến trúc Backend

## 3.1. Nguyên tắc thiết kế

Hệ thống sử dụng mô hình:

Backend-Orchestrated AI Planner

Tức là:

LLM không tự quyết định toàn bộ.  
Backend kiểm soát data, rule, validation, routing, budget và persistence.  
LLM chỉ hỗ trợ hiểu intent, diễn giải preference và format output.

## 3.2. Vai trò của từng thành phần

### Backend

Backend chịu trách nhiệm:

* Nhận request từ frontend.

* Validate input.

* Truy xuất dữ liệu địa điểm.

* Ranking địa điểm.

* Ghép địa điểm thành itinerary.

* Gọi routing service.

* Tính ngân sách.

* Validate plan.

* Lưu plan.

* Lưu version.

* Lưu log AI request.

* Trả JSON cho frontend.

### LLM

LLM chịu trách nhiệm:

* Parse input tự nhiên của user.

* Chuẩn hóa sở thích.

* Hỗ trợ phân loại travel style.

* Hỗ trợ tạo mô tả plan.

* Giải thích lý do đề xuất.

* Format kết quả cuối cùng theo JSON schema.

LLM không được:

* Tự bịa địa điểm.

* Tự bịa giá.

* Tự bịa giờ mở cửa.

* Tự bịa tọa độ.

* Tự tính khoảng cách.

* Tự tính thời gian di chuyển.

* Tự tạo place không tồn tại trong database.

### RAG

RAG chịu trách nhiệm:

* Tìm địa điểm phù hợp với yêu cầu user.

* Tìm địa điểm theo vibe / preference.

* Tìm review summary hoặc place summary.

* Trả về candidate places cho Itinerary Builder.

RAG không chịu trách nhiệm:

* Tạo plan hoàn chỉnh.

* Tối ưu route.

* Tính budget.

* Validate giờ mở cửa.

* Lưu dữ liệu.

---

# 4\. Backend vận hành như thế nào

## 4.1. Flow tạo travel plan

Flow tổng thể:

User Request  
→ Trip Input Validation  
→ Intent & Preference Parser  
→ Place Retrieval  
→ Place Ranking  
→ Itinerary Builder  
→ Route Calculation  
→ Budget Calculation  
→ Plan Validation  
→ LLM Plan Formatter  
→ Save Plan \+ Version  
→ Return Response

## 4.2. Chi tiết từng bước

### Step 1: Trip Input Validation

Frontend gửi request:

{  
  "destination": "Da Nang",  
  "startDate": "2026-07-01",  
  "endDate": "2026-07-03",  
  "peopleCount": 4,  
  "budget": 6000000,  
  "preferences": "Ăn local, thích biển, ít đi bộ, muốn cafe chill",  
  "travelStyle": "balanced"  
}

Backend validate:

* Destination không rỗng.

* Date hợp lệ.

* End date \>= start date.

* People count \> 0\.

* Budget \> 0\.

* Số ngày không quá giới hạn MVP.

MVP nên giới hạn:

Trip duration: 1–5 ngày  
People count: 1–10 người  
Plan options: 3 options  
Activities per day: 4–6 items

---

### Step 2: Intent & Preference Parser

Backend gọi LLM nhỏ hoặc parser rule-based để chuẩn hóa input.

Input:

Ăn local, thích biển, ít đi bộ, muốn cafe chill

Output:

{  
  "foodPreferences": \["local\_food", "seafood"\],  
  "activityPreferences": \["beach", "cafe", "chill"\],  
  "mobilityPreference": "low\_walking",  
  "pace": "medium",  
  "avoid": \[\]  
}

Nếu MVP chưa cần LLM ở bước này, có thể dùng keyword mapping trước.

---

### Step 3: Place Retrieval

Backend tìm candidate places từ database.

Retrieval sử dụng:

Hybrid RAG \= SQL Metadata Filter \+ Vector Search

SQL filter dùng cho điều kiện cứng:

* City.

* Category.

* Price level.

* Rating.

* Opening hours.

* Active status.

Vector search dùng cho điều kiện mềm:

* Chill.

* Local.

* Hidden gem.

* Family-friendly.

* Romantic.

* Low walking.

* Local food.

* Beach vibe.

Ví dụ:

**SELECT** \*  
**FROM** places  
**WHERE** city \= 'Da Nang'  
**AND** status \= 'active'  
**AND** price\_level **IN** ('cheap', 'medium')  
**AND** rating \>= 4.0;

Sau đó vector search trên place\_embeddings để tìm địa điểm hợp sở thích.

---

### Step 4: Place Ranking

Sau khi retrieve được candidate places, Backend chấm điểm lại.

Công thức MVP:

finalScore \=  
  preferenceMatchScore \* 0.35  
  \+ priceFitScore \* 0.20  
  \+ ratingScore \* 0.15  
  \+ areaFitScore \* 0.15  
  \+ categoryBalanceScore \* 0.15

Mục tiêu của ranking:

* Ưu tiên địa điểm khớp sở thích.

* Ưu tiên địa điểm vừa ngân sách.

* Ưu tiên rating tốt.

* Ưu tiên địa điểm cùng khu vực trong một ngày.

* Đảm bảo đủ category: ăn sáng, ăn trưa, tham quan, cafe, ăn tối.

---

### Step 5: Itinerary Builder

Đây là module quan trọng nhất.

Input:

{  
  "trip": {},  
  "rankedPlaces": \[\]  
}

Output:

{  
  "plans": \[  
    {  
      "style": "budget",  
      "days": \[\]  
    },  
    {  
      "style": "chill",  
      "days": \[\]  
    },  
    {  
      "style": "balanced",  
      "days": \[\]  
    }  
  \]  
}

Itinerary Builder chịu trách nhiệm ghép địa điểm thành lịch trình.

Rule MVP:

1. Mỗi ngày có 4–6 hoạt động.

2. Mỗi ngày cần có:

   * Breakfast hoặc morning food.

   * 1–2 attractions.

   * Lunch.

   * Cafe hoặc local experience.

   * Dinner.

3. Các điểm trong cùng một buổi nên gần nhau.

4. Không dùng lại cùng một địa điểm trong nhiều ngày, trừ khi user cố tình chọn.

5. Không xếp địa điểm ngoài giờ mở cửa.

6. Không vượt quá budget.

7. Phải có buffer time giữa các hoạt động.

8. Nếu không đủ địa điểm phù hợp, trả trạng thái NEED\_MORE\_PLACES.

Day structure:

Morning:  
\- Breakfast  
\- Attraction

Lunch:  
\- Restaurant

Afternoon:  
\- Attraction / Cafe / Local experience

Evening:  
\- Dinner  
\- Night activity nếu phù hợp

---

### Step 6: Route Calculation

Sau khi có draft itinerary, Backend gọi Routing Service.

MVP có thể dùng:

* Google Maps Directions API.

* Mapbox Directions API.

* OSRM.

* Hoặc PostGIS distance tạm thời nếu chưa tích hợp map API.

Routing Service nhận:

{  
  "fromPlaceId": "place\_001",  
  "toPlaceId": "place\_002",  
  "mode": "driving"  
}

Trả về:

{  
  "distanceKm": 3.5,  
  "durationMinutes": 12,  
  "mode": "driving"  
}

Route data được lưu cache để tránh gọi API nhiều lần.

---

### Step 7: Budget Calculation

Budget Service tính:

* Cost từng item.

* Cost từng ngày.

* Cost toàn plan.

* Cost per person.

* Budget usage percentage.

Ví dụ output:

{  
  "totalEstimatedCost": 5200000,  
  "costPerPerson": 1300000,  
  "budgetLimit": 6000000,  
  "budgetUsagePercent": 86.6,  
  "isOverBudget": **false**  
}

---

### Step 8: Plan Validation

Plan Validator kiểm tra:

* Có vượt budget không.

* Có item nào thiếu placeId không.

* Có duplicate place không.

* Có item ngoài giờ mở cửa không.

* Có travel time quá dài không.

* Có ngày nào quá dày không.

* Có ngày nào thiếu lunch/dinner không.

* Có route nào không tính được không.

Nếu lỗi nhẹ:

Backend tự sửa bằng rule.

Nếu lỗi nặng:

Gửi lại cho Itinerary Builder build lại.

Nếu vẫn lỗi:

{  
  "status": "FAILED\_TO\_BUILD\_PLAN",  
  "reason": "Not enough valid places for this destination and budget"  
}

---

### Step 9: LLM Plan Formatter

Sau khi Backend đã validate xong, LLM nhận draft plan sạch để format.

LLM input:

{  
  "validatedPlans": \[\],  
  "userPreferences": {},  
  "language": "vi"  
}

LLM output:

{  
  "plans": \[  
    {  
      "style": "budget",  
      "title": "Budget Local Food Plan",  
      "summary": "Lịch trình tiết kiệm, tập trung vào quán local và các điểm gần trung tâm.",  
      "days": \[\]  
    }  
  \]  
}

LLM chỉ được format và giải thích. Không được thêm địa điểm mới.

---

# 5\. Quản lý data

## 5.1. Các loại data chính

Hệ thống quản lý các nhóm data:

1. User data.

2. Trip data.

3. Room/member data.

4. Place data.

5. Place review data.

6. Place embedding data.

7. Route cache.

8. Plan data.

9. Plan version data.

10. AI request log.

11. Budget/expense data.

---

## 5.2. Place data

Place data là dữ liệu cốt lõi của hệ thống.

Nguồn dữ liệu:

* Crawl từ website.

* Google Places API.

* Admin nhập thủ công.

* User review trong tương lai.

Place data cần được chuẩn hóa thành structured data.

Ví dụ:

{  
  "name": "Bún Quậy Kiến Xây",  
  "city": "Phu Quoc",  
  "category": "restaurant",  
  "tags": \["local\_food", "seafood", "budget"\],  
  "priceLevel": "medium",  
  "estimatedCostMin": 50000,  
  "estimatedCostMax": 120000,  
  "rating": 4.4,  
  "latitude": 10.289,  
  "longitude": 103.984,  
  "openingHours": {},  
  "description": "Quán bún quậy nổi tiếng tại Phú Quốc...",  
  "status": "active"  
}

---

## 5.3. Place summary for embedding

Không embedding raw data lộn xộn.

Mỗi địa điểm cần có một field summary\_for\_embedding.

Ví dụ:

Bún Quậy Kiến Xây là quán ăn local nổi tiếng ở Phú Quốc, phù hợp cho nhóm bạn, khách du lịch thích món địa phương và hải sản. Mức giá trung bình, thường phù hợp cho bữa sáng hoặc bữa trưa. Không gian đông khách, trải nghiệm mang tính địa phương.

Embedding được tạo từ summary này.

---

## 5.4. Data ingestion pipeline

Flow crawl data:

Crawler  
→ Raw Place Data  
→ Data Cleaning  
→ Data Normalization  
→ Category Mapping  
→ Tag Extraction  
→ Price Normalization  
→ Location Geocoding  
→ Summary Generation  
→ Embedding Generation  
→ Store PostgreSQL

---

## 5.5. Data quality rules

Mỗi place cần có tối thiểu:

* Name.

* City.

* Category.

* Latitude.

* Longitude.

* Price level.

* Estimated cost.

* Description hoặc summary.

* Source.

* Status.

Nếu thiếu tọa độ:

Không được dùng cho plan có routing.

Nếu thiếu giá:

Có thể dùng nhưng budget confidence thấp.

Nếu thiếu giờ mở cửa:

Validator cần cảnh báo opening\_hour\_unknown.

---

# 6\. Build LLM AI với RAG

## 6.1. Kiến trúc AI MVP

MVP sử dụng:

Hybrid RAG \+ Backend Rule Engine \+ LLM Formatter

Không dùng full Agentic AI trong MVP.

Kiến trúc:

User Input  
→ Preference Parser  
→ Hybrid Retriever  
→ Place Ranker  
→ Itinerary Builder  
→ Route/Budget Validator  
→ LLM Formatter  
→ JSON Response

---

## 6.2. RAG dùng loại nào

MVP dùng:

Hybrid RAG

Bao gồm:

1. Metadata Filtering.

2. Vector Search.

3. Rule-based Ranking.

Chưa dùng:

* GraphRAG.

* MemoRAG.

* LoRA.

* CRAG.

* Web search fallback.

* Multi-agent autonomous planning.

---

## 6.3. RAG retrieval flow

Step 1: Parse destination, budget, preference.  
Step 2: SQL filter places by city, category, price, status.  
Step 3: Vector search by user preference.  
Step 4: Merge results.  
Step 5: Rank places.  
Step 6: Return top candidates to Itinerary Builder.

---

## 6.4. Prompt rule cho LLM

System prompt:

You are an AI Travel Planner.

Rules:  
1\. Use only places provided by Backend.  
2\. Do not invent places.  
3\. Do not invent price, distance, duration, rating or opening hours.  
4\. Do not calculate route by yourself.  
5\. Do not change placeId.  
6\. Return valid JSON only.  
7\. If provided data is insufficient, return NEED\_MORE\_PLACES.  
8\. Your role is to format, explain and refine the itinerary, not to create fake data.

---

## 6.5. JSON schema output

LLM phải trả về schema cố định:

{  
  "tripId": "string",  
  "plans": \[  
    {  
      "planId": "string",  
      "style": "budget | chill | balanced",  
      "title": "string",  
      "summary": "string",  
      "estimatedTotalCost": 0,  
      "estimatedCostPerPerson": 0,  
      "days": \[  
        {  
          "dayNumber": 1,  
          "date": "2026-07-01",  
          "areaFocus": "string",  
          "estimatedCost": 0,  
          "items": \[  
            {  
              "time": "08:00",  
              "placeId": "string",  
              "placeName": "string",  
              "activityType": "breakfast | sightseeing | lunch | cafe | dinner | night\_activity",  
              "description": "string",  
              "estimatedCost": 0,  
              "durationMinutes": 90,  
              "routeToNext": {  
                "distanceKm": 0,  
                "durationMinutes": 0,  
                "mode": "walking | driving | motorbike | public\_transport"  
              }  
            }  
          \]  
        }  
      \],  
      "warnings": \[\]  
    }  
  \]  
}

---

# 7\. Database design

Database đề xuất:

PostgreSQL \+ PostGIS \+ pgvector

PostgreSQL dùng cho relational data.

PostGIS dùng cho location query.

pgvector dùng cho semantic search.

---

## 7.1. Extensions

**CREATE** EXTENSION **IF** **NOT** **EXISTS** postgis;  
**CREATE** EXTENSION **IF** **NOT** **EXISTS** vector;  
**CREATE** EXTENSION **IF** **NOT** **EXISTS** "uuid-ossp";

---

## 7.2. Core tables

### users

**CREATE** **TABLE** users (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  email VARCHAR(255) **UNIQUE**,  
  phone VARCHAR(30) **UNIQUE**,  
  password\_hash TEXT,  
  full\_name VARCHAR(255),  
  avatar\_url TEXT,  
  status VARCHAR(30) **DEFAULT** 'active',  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  updated\_at TIMESTAMP **DEFAULT** NOW()  
);

---

### trips

**CREATE** **TABLE** trips (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  owner\_id UUID **REFERENCES** users(**id**),  
  title VARCHAR(255),  
  destination\_city VARCHAR(255) **NOT** **NULL**,  
  destination\_country VARCHAR(255) **DEFAULT** 'Vietnam',  
  start\_date DATE **NOT** **NULL**,  
  end\_date DATE **NOT** **NULL**,  
  people\_count INT **NOT** **NULL**,  
  budget\_total NUMERIC(14,2),  
  status VARCHAR(30) **DEFAULT** 'draft',  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  updated\_at TIMESTAMP **DEFAULT** NOW()  
);

---

### travel\_rooms

**CREATE** **TABLE** travel\_rooms (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  trip\_id UUID **REFERENCES** trips(**id**) **ON** **DELETE** **CASCADE**,  
  host\_id UUID **REFERENCES** users(**id**),  
  room\_code VARCHAR(50) **UNIQUE** **NOT** **NULL**,  
  invite\_url TEXT,  
  status VARCHAR(30) **DEFAULT** 'active',  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  updated\_at TIMESTAMP **DEFAULT** NOW()  
);

---

### room\_members

**CREATE** **TABLE** room\_members (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  room\_id UUID **REFERENCES** travel\_rooms(**id**) **ON** **DELETE** **CASCADE**,  
  user\_id UUID **REFERENCES** users(**id**),  
  **role** VARCHAR(30) **DEFAULT** 'member',  
  ready\_status BOOLEAN **DEFAULT** **FALSE**,  
  joined\_at TIMESTAMP **DEFAULT** NOW(),  
  **UNIQUE**(room\_id, user\_id)  
);

---

### member\_preferences

**CREATE** **TABLE** member\_preferences (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  trip\_id UUID **REFERENCES** trips(**id**) **ON** **DELETE** **CASCADE**,  
  user\_id UUID **REFERENCES** users(**id**),  
  budget\_preference NUMERIC(14,2),  
  travel\_style VARCHAR(50),  
  food\_preferences TEXT\[\],  
  activity\_preferences TEXT\[\],  
  avoid\_preferences TEXT\[\],  
  raw\_text TEXT,  
  parsed\_json JSONB,  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  updated\_at TIMESTAMP **DEFAULT** NOW(),  
  **UNIQUE**(trip\_id, user\_id)  
);

---

## 7.3. Place tables

### places

**CREATE** **TABLE** places (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  name VARCHAR(255) **NOT** **NULL**,  
  slug VARCHAR(255),  
  city VARCHAR(255) **NOT** **NULL**,  
  region VARCHAR(255),  
  country VARCHAR(255) **DEFAULT** 'Vietnam',  
  address TEXT,  
  latitude DOUBLE PRECISION **NOT** **NULL**,  
  longitude DOUBLE PRECISION **NOT** **NULL**,  
  geo\_point GEOGRAPHY(Point, 4326),  
  **category** VARCHAR(50) **NOT** **NULL**,  
  tags TEXT\[\],  
  price\_level VARCHAR(30),  
  estimated\_cost\_min NUMERIC(14,2),  
  estimated\_cost\_max NUMERIC(14,2),  
  rating NUMERIC(3,2),  
  review\_count INT **DEFAULT** 0,  
  opening\_hours JSONB,  
  best\_time\_to\_visit TEXT\[\],  
  suitable\_for TEXT\[\],  
  description TEXT,  
  summary\_for\_embedding TEXT,  
  **source** VARCHAR(50),  
  source\_url TEXT,  
  status VARCHAR(30) **DEFAULT** 'active',  
  last\_crawled\_at TIMESTAMP,  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  updated\_at TIMESTAMP **DEFAULT** NOW()  
);

Index:

**CREATE** **INDEX** idx\_places\_city **ON** places(city);  
**CREATE** **INDEX** idx\_places\_category **ON** places(**category**);  
**CREATE** **INDEX** idx\_places\_price\_level **ON** places(price\_level);  
**CREATE** **INDEX** idx\_places\_rating **ON** places(rating);  
**CREATE** **INDEX** idx\_places\_tags **ON** places **USING** GIN(tags);  
**CREATE** **INDEX** idx\_places\_geo\_point **ON** places **USING** GIST(geo\_point);

---

### place\_embeddings

**CREATE** **TABLE** place\_embeddings (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  place\_id UUID **REFERENCES** places(**id**) **ON** **DELETE** **CASCADE**,  
  embedding vector(1536),  
  embedding\_model VARCHAR(100),  
  content TEXT,  
  created\_at TIMESTAMP **DEFAULT** NOW()  
);

Index:

**CREATE** **INDEX** idx\_place\_embeddings\_vector  
**ON** place\_embeddings  
**USING** hnsw (embedding vector\_cosine\_ops);

---

### place\_reviews

**CREATE** **TABLE** place\_reviews (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  place\_id UUID **REFERENCES** places(**id**) **ON** **DELETE** **CASCADE**,  
  **source** VARCHAR(50),  
  author\_name VARCHAR(255),  
  rating NUMERIC(3,2),  
  content TEXT,  
  sentiment VARCHAR(30),  
  created\_at TIMESTAMP **DEFAULT** NOW()  
);

---

## 7.4. Plan tables

### trip\_plans

**CREATE** **TABLE** trip\_plans (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  trip\_id UUID **REFERENCES** trips(**id**) **ON** **DELETE** **CASCADE**,  
  style VARCHAR(30) **NOT** **NULL**,  
  title VARCHAR(255),  
  **summary** TEXT,  
  estimated\_total\_cost NUMERIC(14,2),  
  estimated\_cost\_per\_person NUMERIC(14,2),  
  total\_distance\_km NUMERIC(10,2),  
  total\_duration\_minutes INT,  
  status VARCHAR(30) **DEFAULT** 'draft',  
  selected BOOLEAN **DEFAULT** **FALSE**,  
  created\_by UUID **REFERENCES** users(**id**),  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  updated\_at TIMESTAMP **DEFAULT** NOW()  
);

---

### itinerary\_days

**CREATE** **TABLE** itinerary\_days (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  plan\_id UUID **REFERENCES** trip\_plans(**id**) **ON** **DELETE** **CASCADE**,  
  day\_number INT **NOT** **NULL**,  
  trip\_date DATE,  
  area\_focus VARCHAR(255),  
  estimated\_cost NUMERIC(14,2),  
  total\_distance\_km NUMERIC(10,2),  
  total\_duration\_minutes INT,  
  created\_at TIMESTAMP **DEFAULT** NOW()  
);

---

### itinerary\_items

**CREATE** **TABLE** itinerary\_items (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  day\_id UUID **REFERENCES** itinerary\_days(**id**) **ON** **DELETE** **CASCADE**,  
  place\_id UUID **REFERENCES** places(**id**),  
  order\_index INT **NOT** **NULL**,  
  start\_time TIME,  
  end\_time TIME,  
  activity\_type VARCHAR(50),  
  title VARCHAR(255),  
  description TEXT,  
  estimated\_cost NUMERIC(14,2),  
  duration\_minutes INT,  
  **locked** BOOLEAN **DEFAULT** **FALSE**,  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  updated\_at TIMESTAMP **DEFAULT** NOW()  
);

---

### item\_routes

**CREATE** **TABLE** item\_routes (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  from\_item\_id UUID **REFERENCES** itinerary\_items(**id**) **ON** **DELETE** **CASCADE**,  
  to\_item\_id UUID **REFERENCES** itinerary\_items(**id**) **ON** **DELETE** **CASCADE**,  
  from\_place\_id UUID **REFERENCES** places(**id**),  
  to\_place\_id UUID **REFERENCES** places(**id**),  
  **mode** VARCHAR(50),  
  distance\_km NUMERIC(10,2),  
  duration\_minutes INT,  
  provider VARCHAR(50),  
  raw\_response JSONB,  
  created\_at TIMESTAMP **DEFAULT** NOW()  
);

---

### plan\_versions

**CREATE** **TABLE** plan\_versions (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  plan\_id UUID **REFERENCES** trip\_plans(**id**) **ON** **DELETE** **CASCADE**,  
  version\_number INT **NOT** **NULL**,  
  change\_type VARCHAR(50),  
  changed\_by UUID **REFERENCES** users(**id**),  
  prompt TEXT,  
  **snapshot** JSONB **NOT** **NULL**,  
  created\_at TIMESTAMP **DEFAULT** NOW()  
);

---

## 7.5. AI logs

### ai\_requests

**CREATE** **TABLE** ai\_requests (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  trip\_id UUID **REFERENCES** trips(**id**),  
  user\_id UUID **REFERENCES** users(**id**),  
  request\_type VARCHAR(50),  
  model\_name VARCHAR(100),  
  prompt\_version VARCHAR(50),  
  input\_json JSONB,  
  retrieved\_context JSONB,  
  output\_json JSONB,  
  status VARCHAR(30),  
  error\_message TEXT,  
  latency\_ms INT,  
  token\_input INT,  
  token\_output INT,  
  created\_at TIMESTAMP **DEFAULT** NOW()  
);

Bảng này rất quan trọng để debug AI.

---

## 7.6. Route cache

**CREATE** **TABLE** route\_cache (  
  **id** UUID **PRIMARY** **KEY** **DEFAULT** uuid\_generate\_v4(),  
  from\_place\_id UUID **REFERENCES** places(**id**),  
  to\_place\_id UUID **REFERENCES** places(**id**),  
  **mode** VARCHAR(50),  
  distance\_km NUMERIC(10,2),  
  duration\_minutes INT,  
  provider VARCHAR(50),  
  raw\_response JSONB,  
  created\_at TIMESTAMP **DEFAULT** NOW(),  
  **UNIQUE**(from\_place\_id, to\_place\_id, **mode**)  
);

---

# 8\. Source code structure

Backend nên tổ chức theo module.

Ví dụ với NestJS:

src/  
 ├─ main.ts  
 ├─ app.module.ts  
 │  
 ├─ config/  
 │   ├─ database.config.ts  
 │   ├─ redis.config.ts  
 │   ├─ ai.config.ts  
 │   └─ map.config.ts  
 │  
 ├─ common/  
 │   ├─ decorators/  
 │   ├─ filters/  
 │   ├─ guards/  
 │   ├─ interceptors/  
 │   ├─ pipes/  
 │   ├─ utils/  
 │   └─ constants/  
 │  
 ├─ modules/  
 │   ├─ auth/  
 │   ├─ users/  
 │   ├─ trips/  
 │   ├─ travel-rooms/  
 │   ├─ preferences/  
 │   ├─ places/  
 │   ├─ planner/  
 │   ├─ routing/  
 │   ├─ budget/  
 │   ├─ ai/  
 │   └─ files/  
 │  
 ├─ database/  
 │   ├─ migrations/  
 │   ├─ seeds/  
 │   └─ prisma/  
 │  
 └─ workers/  
     ├─ place-crawler.worker.ts  
     ├─ embedding.worker.ts  
     └─ route-cache.worker.ts

---

## 8.1. AI module

modules/ai/  
 ├─ ai.module.ts  
 ├─ ai.service.ts  
 ├─ llm-client.service.ts  
 ├─ prompt-registry.service.ts  
 ├─ schemas/  
 │   ├─ plan-output.schema.ts  
 │   ├─ preference-output.schema.ts  
 │   └─ refinement-output.schema.ts  
 ├─ prompts/  
 │   ├─ system.prompt.ts  
 │   ├─ parse-preference.prompt.ts  
 │   ├─ format-plan.prompt.ts  
 │   └─ refine-plan.prompt.ts  
 └─ logs/  
     └─ ai-request-log.service.ts

---

## 8.2. Planner module

modules/planner/  
 ├─ planner.module.ts  
 ├─ planner.controller.ts  
 ├─ planner.service.ts  
 ├─ orchestrator/  
 │   └─ generate-plan.orchestrator.ts  
 ├─ builders/  
 │   ├─ itinerary-builder.service.ts  
 │   ├─ day-composer.service.ts  
 │   └─ time-slot-composer.service.ts  
 ├─ rankers/  
 │   └─ place-ranker.service.ts  
 ├─ validators/  
 │   ├─ plan-validator.service.ts  
 │   ├─ budget-validator.service.ts  
 │   ├─ opening-hour-validator.service.ts  
 │   └─ route-validator.service.ts  
 ├─ dto/  
 │   ├─ generate-plan.dto.ts  
 │   ├─ select-plan.dto.ts  
 │   └─ refine-plan.dto.ts  
 └─ schemas/  
     └─ itinerary.schema.ts

---

## 8.3. Places module

modules/places/  
 ├─ places.module.ts  
 ├─ places.controller.ts  
 ├─ places.service.ts  
 ├─ retrieval/  
 │   ├─ place-retriever.service.ts  
 │   ├─ hybrid-search.service.ts  
 │   ├─ vector-search.service.ts  
 │   └─ metadata-filter.service.ts  
 ├─ crawler/  
 │   ├─ place-crawler.service.ts  
 │   ├─ normalizer.service.ts  
 │   └─ embedding-generator.service.ts  
 ├─ dto/  
 └─ entities/

---

## 8.4. Routing module

modules/routing/  
 ├─ routing.module.ts  
 ├─ routing.service.ts  
 ├─ providers/  
 │   ├─ google-maps.provider.ts  
 │   ├─ mapbox.provider.ts  
 │   └─ osrm.provider.ts  
 ├─ cache/  
 │   └─ route-cache.service.ts  
 └─ dto/

---

## 8.5. Budget module

modules/budget/  
 ├─ budget.module.ts  
 ├─ budget.service.ts  
 ├─ budget-calculator.service.ts  
 ├─ dto/  
 └─ entities/

---

# 9\. Main API specification

## 9.1. Generate plans

POST /api/trips/:tripId/plans/generate

Request:

{  
  "destination": "Da Nang",  
  "startDate": "2026-07-01",  
  "endDate": "2026-07-03",  
  "peopleCount": 4,  
  "budget": 6000000,  
  "preferences": "Ăn local, thích biển, ít đi bộ, muốn cafe chill"  
}

Response:

{  
  "tripId": "trip\_001",  
  "plans": \[  
    {  
      "planId": "plan\_001",  
      "style": "budget",  
      "title": "Budget Local Plan",  
      "estimatedTotalCost": 4800000,  
      "days": \[\]  
    },  
    {  
      "planId": "plan\_002",  
      "style": "chill",  
      "title": "Chill Beach & Cafe Plan",  
      "estimatedTotalCost": 5600000,  
      "days": \[\]  
    },  
    {  
      "planId": "plan\_003",  
      "style": "balanced",  
      "title": "Balanced Discovery Plan",  
      "estimatedTotalCost": 5200000,  
      "days": \[\]  
    }  
  \]  
}

---

## 9.2. Select plan

POST /api/trips/:tripId/plans/:planId/select

---

## 9.3. Get plan detail

GET /api/trips/:tripId/plans/:planId

---

## 9.4. Refine plan

POST /api/trips/:tripId/plans/:planId/refine

Request:

{  
  "prompt": "Ngày 2 hơi dày, giảm bớt một địa điểm và thêm cafe chill buổi chiều",  
  "lockedItemIds": \["item\_001", "item\_002"\]  
}

---

# 10\. Generate Plan Orchestrator

Pseudo-flow:

**async** **function** generatePlans(input) {  
  validateTripInput(input);

  **const** parsedPreferences \= **await** ai.parsePreferences(input.preferences);

  **const** candidatePlaces \= **await** placeRetriever.retrieve({  
    destination: input.destination,  
    budget: input.budget,  
    preferences: parsedPreferences,  
    days: input.days  
  });

  **const** rankedPlaces \= **await** placeRanker.rank(candidatePlaces, {  
    preferences: parsedPreferences,  
    budget: input.budget  
  });

  **const** draftPlans \= **await** itineraryBuilder.buildThreePlans({  
    trip: input,  
    rankedPlaces  
  });

  **const** plansWithRoutes \= **await** routingService.enrichPlans(draftPlans);

  **const** plansWithBudget \= **await** budgetService.calculate(plansWithRoutes);

  **const** validatedPlans \= **await** planValidator.validate(plansWithBudget);

  **const** formattedPlans \= **await** ai.formatPlans(validatedPlans);

  **await** planRepository.save(formattedPlans);

  **await** aiRequestLog.save({  
    type: 'generate\_plan',  
    input,  
    output: formattedPlans  
  });

  **return** formattedPlans;  
}

---

# 11\. Error handling

## 11.1. Không đủ địa điểm

{  
  "status": "NEED\_MORE\_PLACES",  
  "message": "Không đủ địa điểm phù hợp với ngân sách và sở thích hiện tại."  
}

## 11.2. Không tính được route

{  
  "status": "ROUTE\_CALCULATION\_FAILED",  
  "message": "Không thể tính đường đi giữa một số địa điểm."  
}

## 11.3. Vượt budget

{  
  "status": "OVER\_BUDGET",  
  "message": "Không thể tạo plan phù hợp trong ngân sách hiện tại."  
}

## 11.4. LLM output sai schema

{  
  "status": "INVALID\_AI\_OUTPUT",  
  "message": "AI response does not match required schema."  
}

---

# 12\. Versioning

Hệ thống cần version hóa:

1. Prompt version.

2. Plan version.

3. Schema version.

4. AI model version.

Ví dụ:

prompt\_version \= format\_plan\_v1.0  
schema\_version \= itinerary\_schema\_v1  
model\_name \= gemini-3.1-flash-lite

Mỗi lần user chỉnh plan hoặc AI refine plan, hệ thống lưu snapshot vào plan\_versions.

---

# 13\. Kết luận kiến trúc

Trong MVP, hệ thống cần được xây theo hướng:

Backend-Orchestrated AI Planner

Không để LLM tự vận hành toàn bộ.

Phân tách trách nhiệm:

RAG \= tìm địa điểm phù hợp  
Backend \= ghép plan, tính route, tính budget, validate  
LLM \= parse preference, format output, giải thích plan  
Database \= nguồn dữ liệu thật  
Route API \= nguồn tính đường thật

Mục tiêu hoàn chỉnh của MVP:

User nhập yêu cầu chuyến đi  
→ Backend lấy địa điểm phù hợp  
→ Backend ghép thành 3 lịch trình  
→ Backend tính route và budget  
→ Backend validate  
→ LLM format kết quả  
→ User nhận 3 travel plans hoàn chỉnh

Đây là nền tảng đủ chắc để sau này mở rộng sang:

* Prompt-based refinement.

* Group voting.

* Real-time collaboration.

* Live location.

* Offline mode.

* Weather-aware planning.

* Event-aware planning.

* CRAG / web search fallback.

* LoRA router.
