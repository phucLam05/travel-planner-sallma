import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from urllib.parse import urlparse

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Dữ liệu có thêm tọa độ (vĩ độ, kinh độ)
MOCK_DATABASE = [
    # Khách sạn
    {
        "id": "h1", "name": "Mường Thanh Luxury Đà Nẵng", "category": "hotel",
        "description": "Khách sạn 5 sao sát biển Mỹ Khê, view đẹp, hồ bơi vô cực.",
        "price": 2000000, "lat": 16.0594, "lng": 108.2435, "rating": 4.8
    },
    {
        "id": "h2", "name": "Furama Resort Danang", "category": "hotel",
        "description": "Khu nghỉ dưỡng đẳng cấp, sang trọng bậc nhất, phù hợp nghỉ dưỡng gia đình.",
        "price": 4500000, "lat": 16.0366, "lng": 108.2497, "rating": 4.9
    },
    {
        "id": "h3", "name": "Avora Hotel", "category": "hotel",
        "description": "Khách sạn 3 sao, ngay trung tâm sông Hàn, tiện di chuyển.",
        "price": 600000, "lat": 16.0683, "lng": 108.2235, "rating": 4.3
    },
    {
        "id": "h4", "name": "San Marino Boutique Danang", "category": "hotel",
        "description": "Khách sạn boutique đẹp, giá cả hợp lý, đi bộ ra biển.",
        "price": 850000, "lat": 16.0601, "lng": 108.2422, "rating": 4.5
    },
    {
        "id": "h5", "name": "Memory Hostel", "category": "hotel",
        "description": "Homestay giá rẻ bình dân, thiết kế hoài cổ, trung tâm.",
        "price": 150000, "lat": 16.0655, "lng": 108.2250, "rating": 4.2
    },

    # Điểm tham quan
    {
        "id": "a1", "name": "Bà Nà Hills", "category": "attraction",
        "description": "Khu du lịch trên núi với Cầu Vàng nổi tiếng, công viên giải trí Fantasy Park.",
        "price": 900000, "lat": 15.9984, "lng": 107.9868, "rating": 4.7
    },
    {
        "id": "a2", "name": "Bán đảo Sơn Trà & Chùa Linh Ứng", "category": "attraction",
        "description": "Ngắm cảnh biển, tượng Phật Bà Quan Âm lớn nhất Việt Nam.",
        "price": 0, "lat": 16.1026, "lng": 108.2758, "rating": 4.8
    },
    {
        "id": "a3", "name": "Ngũ Hành Sơn", "category": "attraction",
        "description": "Hệ thống 5 ngọn núi đá vôi, hang động, chùa chiền linh thiêng.",
        "price": 40000, "lat": 16.0022, "lng": 108.2618, "rating": 4.6
    },
    {
        "id": "a4", "name": "Phố cổ Hội An", "category": "attraction",
        "description": "Di sản văn hóa thế giới, cách Đà Nẵng 30km, thả đèn hoa đăng. Kiến trúc cổ kính.",
        "price": 120000, "lat": 15.8794, "lng": 108.3283, "rating": 4.9
    },
    {
        "id": "a5", "name": "Cầu Rồng (Đà Nẵng)", "category": "attraction",
        "description": "Biểu tượng của Đà Nẵng, phun lửa và nước vào cuối tuần.",
        "price": 0, "lat": 16.0610, "lng": 108.2272, "rating": 4.7
    },
    {
        "id": "a6", "name": "Chợ Hàn", "category": "attraction",
        "description": "Chợ truyền thống sầm uất, nơi mua sắm đặc sản làm quà.",
        "price": 0, "lat": 16.0682, "lng": 108.2248, "rating": 4.4
    },
    {
        "id": "a7", "name": "Công viên Châu Á (Asia Park)", "category": "attraction",
        "description": "Khu vui chơi giải trí, vòng quay mặt trời Sun Wheel.",
        "price": 200000, "lat": 16.0396, "lng": 108.2278, "rating": 4.5
    },

    # Nhà hàng
    {
        "id": "r1", "name": "Hải sản Năm Đảnh", "category": "restaurant",
        "description": "Hải sản tươi ngon, giá bình dân, luôn đông khách.",
        "price": 250000, "lat": 16.1042, "lng": 108.2460, "rating": 4.5
    },
    {
        "id": "r2", "name": "Mì Quảng Bà Mua", "category": "restaurant",
        "description": "Quán mì Quảng lâu đời, đậm đà hương vị miền Trung.",
        "price": 50000, "lat": 16.0526, "lng": 108.2144, "rating": 4.3
    },
    {
        "id": "r3", "name": "Chè sầu Liên", "category": "restaurant",
        "description": "Món tráng miệng đặc trưng Đà Nẵng, béo ngậy vị sầu riêng.",
        "price": 30000, "lat": 16.0588, "lng": 108.2110, "rating": 4.6
    },
    {
        "id": "r4", "name": "Bánh xèo Bà Dưỡng", "category": "restaurant",
        "description": "Bánh xèo miền Trung giòn rụm, nước chấm ngon xuất sắc.",
        "price": 70000, "lat": 16.0605, "lng": 108.2163, "rating": 4.7
    },
    {
        "id": "r5", "name": "Nhà hàng Không Gian Xưa", "category": "restaurant",
        "description": "Không gian truyền thống, sang trọng, ẩm thực đậm chất Việt Nam.",
        "price": 400000, "lat": 16.0653, "lng": 108.2037, "rating": 4.4
    }
]

def create_database_if_not_exists():
    result = urlparse(DATABASE_URL)
    username = result.username
    password = result.password
    hostname = result.hostname
    port = result.port
    db_name = result.path[1:]

    try:
        # Kết nối vào database mặc định 'postgres' để tạo db mới
        conn = psycopg2.connect(
            dbname='postgres',
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Đang tạo Database '{db_name}'...")
            cur.execute(f"CREATE DATABASE {db_name}")
            
        cur.close()
        conn.close()
        print(f"Database '{db_name}' đã sẵn sàng.")
    except Exception as e:
        print(f"Không thể tự động tạo Database (có thể đã tồn tại hoặc sai tài khoản): {e}")

def init_db():
    create_database_if_not_exists()
    
    print("Kết nối vào database travel_db...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Bật extension pgvector...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()

    register_vector(conn)

    print("Tạo bảng places...")
    cur.execute("""
        DROP TABLE IF EXISTS places;
        CREATE TABLE places (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255),
            category VARCHAR(50),
            description TEXT,
            price NUMERIC,
            lat NUMERIC,
            lng NUMERIC,
            rating NUMERIC,
            embedding vector(3072)
        );
    """)
    conn.commit()

    print("Khởi tạo Embeddings từ Google Gemini...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")

    print("Đang nạp dữ liệu vào Database...")
    for item in MOCK_DATABASE:
        text_to_embed = f"{item['name']} - {item['category']} - {item['description']}"
        vector = embeddings.embed_query(text_to_embed)

        cur.execute(
            """
            INSERT INTO places (id, name, category, description, price, lat, lng, rating, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (item["id"], item["name"], item["category"], item["description"], 
             item["price"], item["lat"], item["lng"], item.get("rating", 0), vector)
        )
    
    conn.commit()
    cur.close()
    conn.close()
    print("Khởi tạo và Seed DB thành công hoàn toàn!")

if __name__ == "__main__":
    init_db()
