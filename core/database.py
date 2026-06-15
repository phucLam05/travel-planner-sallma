import os
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_db")

class DatabaseManager:
    """
    Quản lý kết nối DB và thực hiện Hybrid Search (Vector + SQL Filter)
    """
    
    @staticmethod
    def get_connection():
        conn = psycopg2.connect(DATABASE_URL)
        register_vector(conn)
        return conn

    @staticmethod
    def hybrid_search(category: str, query: str, limit: int = 5) -> list:
        """
        Tìm kiếm kết hợp: Lọc theo category trước, sau đó tìm kiếm vector gần nhất với câu query.
        """
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
            query_vector = embeddings.embed_query(query)
            
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            
            # Sử dụng pgvector <-> operator (L2 distance)
            sql = """
                SELECT id, name, description, price, lat, lng, rating
                FROM places
                WHERE category = %s
                ORDER BY embedding <-> %s::vector
                LIMIT %s;
            """
            
            cur.execute(sql, (category, query_vector, limit))
            rows = cur.fetchall()
            
            results = []
            for r in rows:
                results.append({
                    "id": r[0],
                    "name": r[1],
                    "description": r[2],
                    "price": float(r[3]),
                    "lat": float(r[4]),
                    "lng": float(r[5]),
                    "rating": float(r[6])
                })
                
            cur.close()
            conn.close()
            return results
        except Exception as e:
            print(f"Database error: {e}")
            return []
