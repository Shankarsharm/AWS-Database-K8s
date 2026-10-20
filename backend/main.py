import os
import psycopg2
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# AWS Endpoints injected via Kubernetes
DB_HOST = os.getenv("DB_HOST")
REDIS_HOST = os.getenv("REDIS_HOST")
DB_USER = "postgres"
DB_PASS = "password" # Update to your RDS password if different

def get_db():
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname="ecommerce")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, customer VARCHAR(50), item VARCHAR(100), amount INT)")
    return conn

def get_redis():
    return redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

class Order(BaseModel):
    customer: str
    item: str
    amount: int

@app.post("/api/orders")
def create_order(order: Order):
    conn = get_db()
    cache = get_redis()
    
    # 1. Write to RDS PostgreSQL
    with conn.cursor() as cur:
        cur.execute("INSERT INTO orders (customer, item, amount) VALUES (%s, %s, %s) RETURNING id", 
                   (order.customer, order.item, order.amount))
        order_id = cur.fetchone()[0]
    
    # 2. Cache in ElastiCache Redis
    cache.set(f"order:{order_id}", f"{order.customer} bought {order.item} for ${order.amount}")
    
    return {"message": "Order created securely", "order_id": order_id}

@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    cache = get_redis()
    
    # 1. Try Cache First (Fast)
    cached_data = cache.get(f"order:{order_id}")
    if cached_data:
        return {"source": "ElastiCache Redis ⚡", "data": cached_data}
    
    # 2. Fallback to Database (Slower)
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT customer, item, amount FROM orders WHERE id = %s", (order_id,))
        row = cur.fetchone()
        if row:
            data = f"{row[0]} bought {row[1]} for ${row[2]}"
            cache.set(f"order:{order_id}", data) # Lazy load into cache
            return {"source": "RDS PostgreSQL 🐘", "data": data}
    
    raise HTTPException(status_code=404, detail="Order not found")