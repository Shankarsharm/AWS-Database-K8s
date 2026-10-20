# ☁️ AWS 3-Tier Kubernetes Ecommerce Architecture

A production-grade, end-to-end 3-tier ecommerce application deployed on a Kubernetes (Minikube) cluster hosted on an AWS EC2 instance. This project demonstrates modern cloud-native principles including API Gateway routing, automated TLS provisioning, and external managed database integration.

## 🏗️ Architecture Overview

* **Compute:** AWS EC2 (Ubuntu 22.04) running a single-node Minikube Kubernetes cluster.
* **API Gateway & Ingress:** Kong API Gateway routing external traffic to microservices.
* **DNS & TLS:** `nip.io` wildcard DNS with automated Let's Encrypt HTTPS certificates managed by `cert-manager`.
* **Frontend Microservice:** Python (FastAPI) serving an interactive HTML/JS dashboard.
* **Backend Microservice:** Python (FastAPI) handling business logic and external connections.
* **Primary Database:** AWS RDS (PostgreSQL) for persistent order storage.
* **Caching Layer:** AWS ElastiCache (Redis) for high-speed read operations.

## 📁 Repository Structure
```text
aws-k8s-ecommerce-app/
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
└── k8s/
    ├── aws-deploy.yaml
    └── kong-ingress.yaml
```

## 📋 Prerequisites

1. **AWS EC2 Instance:** Ubuntu 22.04+ with Minikube, Docker, and `kubectl` installed.
2. **AWS RDS:** A PostgreSQL database instance in the same VPC.
3. **AWS ElastiCache:** A Redis cluster (Primary Writer Endpoint) in the same VPC.
4. **Security Groups:** 
   - `ec2-minikube-sg`: Allow Inbound TCP ports `22` (SSH), `80` (HTTP), `443` (HTTPS), and `8080` (Custom App Proxy) from `0.0.0.0/0`.
   - `db-backend-sg`: Allow Inbound TCP ports `5432` (Postgres) and `6379` (Redis) from the EC2 security group.

---

## 🚀 Step-by-Step Deployment Guide

### Step 1: Database Initialization
By default, AWS RDS provisions a `postgres` database, but our application requires a specific `ecommerce` database to function.

1. Connect to your EC2 instance via SSH.
2. Install the PostgreSQL client:
   ```bash
   sudo apt update && sudo apt install postgresql-client -y
   ```
3. Connect to your RDS instance using your master credentials:
   ```bash
   psql -h <YOUR_RDS_ENDPOINT> -U postgres -d postgres
   ```
4. Create the application database inside the prompt:
   ```sql
   CREATE DATABASE ecommerce;
   \q
   ```

### Step 2: Build the Docker Images Locally
To avoid pushing images to a public registry like DockerHub, we build the images directly inside the Minikube environment.

1. Point your shell to Minikube's Docker daemon:
   ```bash
   eval $(minikube docker-env)
   ```
2. Build the Backend Image:
   ```bash
   cd backend
   docker build -t app-backend:latest .
   ```
3. Build the Frontend Image:
   ```bash
   cd ../frontend
   docker build -t app-frontend:latest .
   ```

### Step 3: Configure Kubernetes Manifests
Update the deployment files to point to your specific AWS infrastructure.

1. **Edit `k8s/aws-deploy.yaml`**:
   Inject your specific AWS database endpoints into the backend pod's environment variables. *Note: Do not include the `:6379` port in the Redis host variable.*
   ```yaml
   env:
     - name: DB_HOST
       value: "database-1.xxxx.ap-south-1.rds.amazonaws.com"
     - name: REDIS_HOST
       value: "ecommerce-redis.xxxx.cache.amazonaws.com"
   ```

2. **Edit `k8s/kong-ingress.yaml`**:
   Update the `nip.io` hostnames to match your EC2 instance's public IP address.
   ```yaml
   spec:
     tls:
     - hosts:
       - shop.<YOUR_EC2_PUBLIC_IP>.nip.io
   ```

### Step 4: Deploy Core Services & App to Kubernetes
Ensure your cluster has Kong API Gateway and Cert-Manager installed. Then apply your application manifests:

```bash
kubectl apply -f k8s/aws-deploy.yaml
kubectl apply -f k8s/kong-ingress.yaml
```

Verify all pods are running successfully:
```bash
kubectl get pods
```

### Step 5: Expose the Application Gateway
To bypass Docker/Linux networking restrictions on the EC2 host (like root permission requirements for port 80), expose the Kong API Gateway proxy via port 8080:

```bash
# Run this in a dedicated terminal session or background it
kubectl port-forward --address 0.0.0.0 svc/kong-kong-proxy -n kong 8080:80
```

---

## 🧪 Testing & Validation

Open your web browser and navigate to your dynamic domain:
**`http://shop.<YOUR_EC2_PUBLIC_IP>.nip.io:8080`**

### 1. Test Write Operations (RDS + Redis)
1. In the **1. Checkout** section of the UI, submit a new order.
2. Watch the System Logs terminal. It will confirm: `[Backend] 🐘 Saved to RDS | ⚡ Cached in Redis` and return an Order ID.

### 2. Test Read Operations (Cache Hit)
1. Enter the generated Order ID into the **2. Fetch Order** section.
2. The logs will confirm the data was fetched instantly from the high-speed cache: `[Backend] Resolved from ElastiCache Redis ⚡`.

### 3. Test Database Fallback (Cache Miss / Resilience)
To prove the PostgreSQL fallback logic works in the event of a cache eviction or failure:
1. SSH into the EC2 instance in a new terminal.
2. Install Redis tools and connect to ElastiCache:
   ```bash
   sudo apt install redis-tools -y
   redis-cli -h <YOUR_ELASTICACHE_ENDPOINT> -p 6379
   ```
3. Flush the cache manually:
   ```bash
   ecommerce-redis> FLUSHALL
   ecommerce-redis> exit
   ```
4. Fetch the exact same Order ID again in the web dashboard.
5. The UI logs will dynamically change to confirm the data was safely recovered directly from the persistent database: `[Backend] Resolved from RDS PostgreSQL 🐘`.