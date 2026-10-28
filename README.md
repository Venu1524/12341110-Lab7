# Lab 7: Proximity Search API

A high-performance geospatial proximity search web API that recommends the 10 closest locations on a 1×1 grid network matching a requested category within a specified circular search radius.

---

## Lab 9: Docker Quick Start (One-Command Full-Stack)

Containerise and run the entire multi-service stack with a single command:
```bash
docker compose up --build -d
```

### Accessing the Stack
- **Unified Web & API Gateway (Nginx):** [http://localhost:8080/](http://localhost:8080/)
- **Proximity Search API Endpoint:** [http://localhost:8080/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15](http://localhost:8080/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15)
- **Direct Backend API:** [http://localhost:5000/health](http://localhost:5000/health)
- **Inspect Services:** `docker compose ps`
- **View Integration Test Suite Output:** `docker compose logs tester`
- **Stop Stack:** `docker compose down`

---

## Local Development (Without Docker)

### 1. Run the API Server

Using Flask (recommended):
```bash
# Windows
.\.venv\Scripts\python.exe app.py

# Or standard python (if flask is installed)
python app.py
```

Using Zero-Dependency Standalone Server (uses Python standard library):
```bash
python standalone_server.py
```
The server will be running on `http://127.0.0.1:5000` (and `0.0.0.0:5000`).

---

### 2. Test the API

Run the comprehensive automated test suite:
```bash
.\.venv\Scripts\python.exe test_api.py
```

Test manually using `curl`:
```bash
curl -X GET "http://127.0.0.1:5000/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15"
```

Expected output:
```json
[5051, 4949, 5053, 5251, 4751, 5149, 5047, 4551, 4748, 5154]
```

Or open `http://127.0.0.1:5000/` in any browser to use the interactive visual query testing console!

---

## Obtaining the API Link for Submission

### Active Live Deployment: Ubuntu Container
The API is deployed and actively running inside your Ubuntu container:
- **SSH Target:** `ssh -p 2292 student@10.1.75.79`
- **Container Port:** `6000`
- **Port Mapping Formula:** `6000 + 2292 - 2000 = 6292`
- **Active API Base Endpoint:** `http://10.1.75.79:6292/search/`
- **Interactive UI Console:** `http://10.1.75.79:6292/`
- **Sample Live Query:**
  ```text
  http://10.1.75.79:6292/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15
  ```

---

### Alternative Options


### Method A: Instant Public Tunnel (Zero Setup)
With the server running on port 5000, open a separate terminal window and run:
```bash
ssh -R 80:localhost:5000 a.pinggy.io
```
Pinggy immediately outputs a live public HTTPS URL:
```
https://<subdomain>.a.pinggy.link/search/
```
You can use this exact link for your assignment submission:
`https://<subdomain>.a.pinggy.link/search/`

*(Alternative tunnel: `ssh -R 80:localhost:5000 serveo.net`)*

---

### Method B: Free Cloud Hosting (Permanent Link)
You can deploy for free to **Render.com** or **Railway.app**:
1. Push this folder to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Lab 7 Proximity Search API"
   git branch -M main
   git remote add origin https://github.com/<your-username>/lab7-proximity-search.git
   git push -u origin main
   ```
2. Log into [Render.com](https://render.com) and click **New + -> Web Service**.
3. Select your GitHub repository.
4. Settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. Render generates a permanent public link:
   `https://<service-name>.onrender.com/search/`

---

## Submission Files Checklist
- **API Link:** Your live public URL (e.g. `https://<subdomain>.a.pinggy.link/search/` or `https://<app>.onrender.com/search/`)
- **Report:** Submit `Lab7_Report.pdf` (or `REPORT.md`)
