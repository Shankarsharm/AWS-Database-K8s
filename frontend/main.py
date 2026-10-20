from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
def serve_dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AWS 3-Tier Dashboard</title>
        <style>
            body { font-family: system-ui; background: #f0f2f5; padding: 2rem; }
            .container { max-width: 800px; margin: auto; }
            .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            button { background: #ff9900; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }
            input { padding: 8px; margin-right: 10px; border: 1px solid #ccc; border-radius: 4px; }
            #terminal { background: #1e1e1e; color: #00ff00; padding: 15px; font-family: monospace; border-radius: 8px; min-height: 200px; max-height: 300px; overflow-y: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>☁️ AWS Production Practice Dashboard</h2>
            
            <div class="card">
                <h3>1. Checkout (Writes to RDS & Redis)</h3>
                <input id="customer" placeholder="Your Name" value="Shankar">
                <input id="item" placeholder="Product" value="MacBook Pro">
                <input id="amount" type="number" placeholder="Price" value="2000">
                <button onclick="createOrder()">Submit Order</button>
            </div>

            <div class="card">
                <h3>2. Fetch Order (Test Cache Hit vs DB Hit)</h3>
                <input id="orderId" placeholder="Order ID" type="number">
                <button onclick="fetchOrder()">Lookup Order</button>
                <p style="color: #666; font-size: 0.9em;">Notice how the first request fetches from PostgreSQL, and subsequent requests fetch instantly from ElastiCache.</p>
            </div>

            <div class="card">
                <h3>System Logs</h3>
                <div id="terminal">Initializing architecture...<br></div>
            </div>
        </div>

        <script>
            function log(msg) {
                const term = document.getElementById('terminal');
                term.innerHTML += msg + '<br>';
                term.scrollTop = term.scrollHeight;
            }

            async function createOrder() {
                const customer = document.getElementById('customer').value;
                const item = document.getElementById('item').value;
                const amount = document.getElementById('amount').value;
                
                log(`[API Gateway] POST /api/orders`);
                const res = await fetch('/api/orders', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({customer, item, amount: parseInt(amount)})
                });
                const data = await res.json();
                log(`[Backend] 🐘 Saved to RDS | ⚡ Cached in Redis | ID: ${data.order_id}`);
                document.getElementById('orderId').value = data.order_id;
            }

            async function fetchOrder() {
                const orderId = document.getElementById('orderId').value;
                if(!orderId) return alert('Enter an Order ID');
                
                log(`[API Gateway] GET /api/orders/${orderId}`);
                const res = await fetch('/api/orders/' + orderId);
                const data = await res.json();
                
                if(data.source) {
                    log(`[Backend] Resolved from ${data.source} => ${data.data}`);
                } else {
                    log(`[Backend] Error: ${data.detail}`);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)