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

    @staticmethod
    def init_session_table():
        """Tạo bảng travel_sessions và travel_room_events nếu chưa có."""
        try:
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS travel_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    state_data JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS travel_room_events (
                    id SERIAL PRIMARY KEY,
                    room_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Lỗi tạo bảng sessions/events: {e}")

    @staticmethod
    def save_session(session_id: str, state_data: dict):
        import json
        try:
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            json_str = json.dumps(state_data, ensure_ascii=False)
            
            cur.execute('''
                INSERT INTO travel_sessions (session_id, state_data, updated_at)
                VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
                ON CONFLICT (session_id) 
                DO UPDATE SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP;
            ''', (session_id, json_str))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Lỗi save_session: {e}")

    @staticmethod
    def load_session(session_id: str) -> dict:
        try:
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            cur.execute('SELECT state_data FROM travel_sessions WHERE session_id = %s;', (session_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return row[0]
            return None
        except Exception as e:
            print(f"Lỗi load_session: {e}")
            return None

    @staticmethod
    def get_all_sessions() -> list:
        try:
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            cur.execute('SELECT session_id, updated_at FROM travel_sessions ORDER BY updated_at DESC;')
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [{"session_id": r[0], "updated_at": r[1]} for r in rows]
        except Exception as e:
            print(f"Lỗi get_all_sessions: {e}")
            return []

    # --- GROUP ROOM EVENT SOURCING METHODS ---

    @staticmethod
    def append_event(room_id: str, user_id: str, event_type: str, payload: dict):
        import json
        try:
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            json_str = json.dumps(payload, ensure_ascii=False)
            
            cur.execute('''
                INSERT INTO travel_room_events (room_id, user_id, event_type, payload)
                VALUES (%s, %s, %s, %s::jsonb);
            ''', (room_id, user_id, event_type, json_str))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Lỗi append_event: {e}")

    @staticmethod
    def load_room_state(room_id: str) -> dict:
        """
        Rebuilds the state of a room by applying all events in chronological order.
        Last-write-wins policy.
        """
        try:
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            cur.execute('SELECT payload FROM travel_room_events WHERE room_id = %s ORDER BY id ASC;', (room_id,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            state = {}
            for row in rows:
                payload = row[0]
                if isinstance(payload, dict):
                    # For list-based history, we should properly append if it's a new message
                    if "chat_history" in payload and "chat_history" in state:
                        # Append new messages that aren't already in the state's history
                        new_msgs = payload["chat_history"]
                        current_msgs = state.get("chat_history", [])
                        # A simple way is to just overwrite since the app.py passes the full history array
                        state["chat_history"] = new_msgs
                    state.update(payload)
            return state
        except Exception as e:
            print(f"Lỗi load_room_state: {e}")
            return {}
            
    @staticmethod
    def get_all_rooms() -> list:
        try:
            conn = DatabaseManager.get_connection()
            cur = conn.cursor()
            cur.execute('SELECT DISTINCT room_id, MAX(created_at) as last_activity FROM travel_room_events GROUP BY room_id ORDER BY last_activity DESC;')
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [{"room_id": r[0], "last_activity": r[1]} for r in rows]
        except Exception as e:
            print(f"Lỗi get_all_rooms: {e}")
            return []
