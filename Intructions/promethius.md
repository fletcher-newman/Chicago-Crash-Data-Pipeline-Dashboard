# 📘 **Monitoring & Observability for the Crash Pipeline**

### **Prometheus + Grafana + Exporters (RabbitMQ, MinIO) + Pipeline Metrics**

## 🏁 **1. Introduction**

Modern data pipelines must be **observable** — meaning you can see:

* How many jobs ran
* How long they took
* Whether queues are backing up
* Whether buckets are filling
* Whether transformations or cleaners are failing
* Whether UI usage is spiking

Without monitoring, the pipeline silently fails.
With **Prometheus + Grafana**, you get **live metrics, dashboards, alerts, and complete transparency**.

## 🔍 **2. What is Prometheus?**

Prometheus is the **metrics engine** of our monitoring setup.
Think of it like a *live spreadsheet* that keeps updating itself every few seconds.

It continuously asks each service in your pipeline:

> “How are you doing right now? Got any new numbers for me?”

And each service responds through a simple `/metrics` endpoint.

### 📌 What Prometheus Does

* ⏱️ **Pulls metrics** from Extractor, Transformer, Cleaner, Streamlit
* 🧮 Stores the values as **time-series data** (numbers tracked over time)
* 🔎 Lets Grafana graph those numbers however you want

Prometheus = **collector + storage** for all your monitoring data.


## 🧪 **What Do Metrics Look Like?**

Metrics are just labelled numbers. For example:

* `extractor_rows_fetched_total 12000`
* `transformer_rows_output_total 8975`
* `cleaner_nulls_fixed_total 302`
* `ml_inference_latency_seconds 0.14`

These numbers tell the story of your pipeline’s behavior.


## 🔢 **Types of Prometheus Metrics**

### **1. Counter (🔼 goes up only)**

Use for things you count: rows processed, errors, jobs completed.

### **2. Gauge (🔼🔽 goes up AND down)**

Use for values that change: queue size, bucket sizes, row counts.

### **3. Histogram (📊 grouped buckets)**

Use for timings or sizes: ETL stage durations, ML prediction latency.

## 🎯 **Why Prometheus Matters for This Pipeline**

Your pipeline has many points of failure:

* Extractor might fetch 0 rows
* Transformer might take too long
* Cleaner might drop too many rows
* RabbitMQ may back up
* MinIO might run out of space
* Streamlit model accuracy may drop silently

Prometheus gives you **truth, history, and visibility**.
Grafana will help you visualize it next.


## 🎨 **3. What is Grafana?**

Now that Prometheus is collecting all your metrics, we need a way to **see** them.
That’s where **Grafana** comes in.

Think of Grafana as:

> 🖼️ **The visual dashboard layer for your pipeline’s health.**

If Prometheus is the database storing all your numbers →
Grafana is the tool that turns those numbers into **beautiful, readable charts**.


## 🌈 **What Grafana Lets You Do**

### 📊 1. Build Dashboards

You can create panels like:

* ETL duration graphs
* Queue size heatmaps
* Row processing trends
* ML accuracy over time
* Storage usage gauges

### 🧠 2. Combine Metrics Across Services

Example:

* Extractor duration (from Extractor service)
* Rows dropped (from Cleaner)
* Queue depth (from RabbitMQ)
* MinIO bucket size

All in **one dashboard**.

### 🚨 3. Create Alerts

You can tell Grafana:

> “Notify me if Cleaner takes more than 5 seconds.”

Or:

> “Alert me if Extractor outputs zero rows.”

This is exactly how production teams detect failures instantly.

### 🎛️ 4. Explore Prometheus Data Easily

Grafana has a built-in editor for writing Prometheus queries without needing to memorize syntax.

## 🖥️ **How Grafana Fits Into Our Pipeline**

Here is your monitoring flow:

```
Extractor / Transformer / Cleaner / Streamlit
                ↓ expose metrics
            Prometheus (collector)
                ↓ stores numbers
              Grafana (UI)
```

* Prometheus scrapes your `/metrics` endpoints.
* Grafana reads those metrics from Prometheus.
* You build dashboards to **see everything clearly**.


## 🏗️ **5. Installing Prometheus + Grafana**

Now that you understand *why* monitoring matters, let’s set up the two main tools that will power all your metrics and dashboards.

This step is simple — you're just adding two new services (Prometheus + Grafana) to your existing `docker-compose.yml`.

## 📦 **Prometheus Service (Metrics Collector)**

Add this block to your `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus
  container_name: prometheus
  user: "${UID}:${GID}" 
  ports:
    - "9090:9090"   # Prometheus UI
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    - ./prometheus_data:/prometheus
  restart: unless-stopped 
```

### 📝 What this does

* **Runs Prometheus** inside a container
* **Exposes the UI at:** [http://localhost:9090](http://localhost:9090)
* **Loads your config file:** `monitoring/prometheus.yml`

You will fill that file with **scrape targets** (services to monitor) in the next section.

---

## 🎨 **Grafana Service (Dashboard UI)**

Add this block below Prometheus:

```yaml
grafana:
  image: grafana/grafana
  container_name: grafana
  user: "${UID}:${GID}" 
  ports:
    - "3000:3000"   # Grafana UI
  volumes:
    - ./grafana_data:/var/lib/grafana
  depends_on:
    - prometheus
  restart: unless-stopped
```

### 📝 What this does

* Launches **Grafana**, the dashboard tool
* Exposes it at: [http://localhost:3000](http://localhost:3000)
* Ensures Prometheus starts **first** so the datasource is available

### 🔑 Default login

* **Username:** `admin`
* **Password:** `admin`

(You'll change this later if you want.)


## 📝 **6. Creating the Prometheus Configuration (`prometheus.yml`)**

Now that Prometheus is running as a service, it still doesn’t know **who** to scrape.
We teach it that using a config file: `monitoring/prometheus.yml`.

Think of this file as a **contact list** of all the services Prometheus should talk to.


### 📂 Step 1 — Create the config file

In your project, create the folder and file:

```bash
mkdir monitoring
nano monitoring/prometheus.yml   # or use VS Code / any editor
```


### ⚙️ Step 2 — Add a basic Prometheus config

Start with this:

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "extractor"
    static_configs:
      - targets: ["extractor:8000"]

  - job_name: "transformer"
    static_configs:
      - targets: ["transformer:8000"]

  - job_name: "cleaner"
    static_configs:
      - targets: ["cleaner:8000"]
```

We will add RabbitMQ, MinIO, and Streamlit later.


### 🧠 What this file is saying 

* `scrape_interval: 5s`

  * 👉 "Every 5 seconds, go and collect metrics from all the services I list below."

* `job_name: "extractor"`

  * This is just a label so you can later filter metrics by job in Prometheus/Grafana.

* `targets: ["extractor:8000"]`

  * Inside the Docker network, Prometheus will call:

    * `http://extractor:8000/metrics`
  * That means:

    * The **service name** must be `extractor` in `docker-compose.yml`
    * The **metrics HTTP server inside that container** must listen on port `8000`

> 🔴 Important: The port in `targets` must match whatever port your service actually exposes metrics on.
> If you choose a different port (e.g., `9100`), update it **both** in the code and here.


## ⚙️ **7. Adding Prometheus Metrics to Each Pipeline Component**

Now that Prometheus knows *where* to scrape from, we need to make sure each service actually **exposes metrics**.

For your pipeline, the three core ETL services are:

* **Extractor** (Go)
* **Transformer** (Python)
* **Cleaner** (Python)

Each one should expose its own `/metrics` endpoint so Prometheus can collect useful information.

This section teaches students exactly **what** to track and **why** it matters—without overwhelming them.


## 📦 Step 1 — Install Prometheus Client Libraries

### 🐍 Python Services (Transformer, Cleaner)

Run inside the service environment:

```bash
pip install prometheus-client
```

### 🐹 Go Service (Extractor)

Use:

```go
import "github.com/prometheus/client_golang/prometheus"
import "github.com/prometheus/client_golang/prometheus/promhttp"
```

## 🎯 Step 2 — Metrics You MUST Add to *Each* Service

You should treat every service as its **own monitored component**.

For each stage (**Extractor, Transformer, Cleaner**), add:

### **1. Service uptime**

Shows if the container restarted or crashed.

### **2. Run/Request count**

How many times this service executed its main job.

### **3. Error count (4xx/5xx or failures)**

Tells you when the service is failing silently.

### &#x20;**4. Latency of each run**

How long a full Extract/Transform/Clean cycle takes.

### **5. Rows processed**

Very important for data pipelines — lets you catch missing or duplicated data.

### **6. Duration of each major function**

Example:

* time spent fetching API data (Extractor)
* time spent cleaning nulls (Cleaner)
* time spent writing outputs (Transformer)

### **7. Success vs failure counters**

Lets you quickly see whether a stage is stable.

## 🧰 Step 3 — How Students Will Implement Metrics

We’re keeping it simple:

### 👨‍💻 Extractor (Go)

Use the official `prometheus/client_golang` package to:

* register counters
* create timing histograms
* expose `/metrics` via `promhttp.Handler()`

### 🐍 Transformer & Cleaner (Python)

Use the `prometheus_client` package to:

* define counters/gauges/histograms
* start a small metrics HTTP server (e.g., `start_http_server(8000)`)


## 🐇 **8. RabbitMQ Monitoring Exporter**

RabbitMQ does not expose Prometheus metrics by default — you need an exporter container.

Add to **docker-compose.yml**:

```yaml
rabbitmq-exporter:
  image: kbudde/rabbitmq-exporter
  ports:
    - "9419:9419"
  environment:
    RABBIT_URL: http://rabbitmq:15672
    RABBIT_USER: guest
    RABBIT_PASSWORD: guest
  depends_on:
    - rabbitmq
  restart: unless-stopped

```
### 🧠 What this does

* Connects to RabbitMQ’s management API (`15672`)
* Converts its internal stats → Prometheus metrics
* Exposes them at `:9419/metrics`

Add to `prometheus.yml`:

```yaml
- job_name: 'rabbitmq'
  static_configs:
    - targets: ['rabbitmq-exporter:9419']
```
That’s all — Prometheus will now scrape queue health every 5 seconds.

Include metrics like:

* **Messages published**
* **Messages consumed**
* **Messages unacked**
* **Queue length**
* **Worker failures**
* **Processing rate**



## 🗄️ **9. MinIO Monitoring**

MinIO already exposes Prometheus metrics natively — no exporter required.

You only need to enable the Prometheus endpoint in MinIO.

Add to MinIO env inside docker compose file :

```yaml
MINIO_PROMETHEUS_AUTH_TYPE: public
```
This tells MinIO:

> “Expose the Prometheus metrics endpoint without requiring authentication.”
Prometheus config:

```yaml
- job_name: 'minio'
  metrics_path: '/minio/v2/metrics/cluster'
  static_configs:
    - targets: ['minio:9000']
```

Metrics to be included:

* **Number of objects per bucket**
* **Total size of objects**
* **Upload/download operations**
* **Latency of MinIO API calls**


## 🖥️ **10. Streamlit UI Monitoring**

Your Streamlit ML UI must expose:

* App uptime (is the app running?)
* Model quality: accuracy, precision, recall
* Prediction latency (how long a prediction takes)


Add atleast 3-5 more metrics(whichever you feel useful).

These are custom metrics you  will expose using:

```python
from prometheus_client import Counter, Gauge, Histogram
```

## 🚨 **11. Prometheus Alerts**

Everything so far has been **dashboards** – you open Grafana and *look* at metrics.
Alerts flip this around:

> 🛎️ **"Tell me when something bad happens, even if I’m not watching."**

Prometheus can evaluate alert rules on your metrics and mark them as **firing** when a condition is true for some time.

This section gives you a simple, student-friendly way to add **two example alerts**:

* One for **Extractor failures**
* One for **slow Cleaner runs**

You can treat this as a **bonus/extension** if you’re new to PromQL.

## 🧩 Step 1 — Tell Prometheus Where Alert Rules Live

In your `monitoring/prometheus.yml`, add:

```yaml
rule_files:
  - alerts.yml
```

This means:

> "In addition to scraping metrics, also load alert rules from `monitoring/alerts.yml`."

## 📂 Step 2 — Create `monitoring/alerts.yml`

Create the file:

```bash
nano monitoring/alerts.yml
```

Then add alert rules.

### ⚠️ Example 1: Extractor Failures

Goal: **Alert if the extractor has any failures in the last 5 minutes.**

```yaml
- alert: ExtractorFailures
  expr: increase(extractor_jobs_failed_total[5m]) > 0
  for: 2m
  labels:
    severity: warning
  annotations:
    message: "Extractor failing recently"
```

🔍 Breakdown:

* `increase(extractor_jobs_failed_total[5m]) > 0`

  * Look at the counter `extractor_jobs_failed_total` over the last 5 minutes.
  * If it increased by more than 0 → at least one failure happened.
* `for: 2m`

  * Only fire the alert if this condition stays true for 2 minutes.
* `severity: warning`

  * You can use this label later in Alertmanager / dashboards.

> ✅ For this to work, you must already be exposing a `extractor_jobs_failed_total` counter in your extractor service.

### 🐢 Example 2: Cleaner Too Slow

Goal: **Alert if the Cleaner is taking too long**

```yaml
- alert: CleanerTooSlow
  expr: histogram_quantile(0.95, sum(rate(cleaner_latency_seconds_bucket[5m])) by (le)) > 5
  for: 2m
```

🔍 Breakdown:

* `cleaner_latency_seconds_bucket` is the histogram you should expose for cleaner run time.
* `rate(...[5m])` looks at how it changes over 5 minutes.
* `sum(... by (le))` aggregates buckets to prepare for quantile.
* `histogram_quantile(0.95, ...) > 5` means:

  * "The 95th percentile latency is more than 5 seconds."
* `for: 2m` means it has to stay slow for 2 minutes before alerting.

This is a standard pattern for latency alerts.

## 🎓 How you can Extend This 

You have to design **your own alert** based on:

* ML accuracy dropping below a threshold
* RabbitMQ queue size getting too large
* MinIO free space getting too low
* ETL rows processed suddenly dropping to zero

just seeing alerts in the Prometheus UI (`Alerts` tab) is enough.

## 📈 **12. Building Dashboards in Grafana**

Now that Prometheus is scraping all your metrics, it’s time to turn those numbers into **visual dashboards** in Grafana.

Dashboards are where everything comes together: ETL, storage, queues, and ML — all in one place.

### 🧭 Step 1 — Open Grafana

In your browser, go to:

```text
http://localhost:3000
```

Login using the default credentials:

* **Username:** `admin`
* **Password:** `admin`

(You may be asked to change the password — you can keep it simple for local use.)

### 🔗 Step 2 — Add Prometheus as a Data Source

1. Click **“Connections” → “Add new connection” → Prometheus**

2. Set the URL to:

   ```text
   http://prometheus:9090
   ```

   (This uses the **Docker service name** `prometheus`.)

3. Click **Save & Test**.
   You should see a green **“Data source is working”** message.

Now Grafana can query all metrics scraped by Prometheus.

### 🧩 Step 3 — Create 3 Dashboards

You will build **three dashboards**, each focusing on a different part of the system:


Each dashboard should use metrics you already exposed.

### The below metrics are just a starter, use the right metrics according to the prometheus code.

You can also add extras if you see fit 

## 📊 Dashboard 1 — ETL Overview

This dashboard answers:

> "How is the pipeline itself behaving?"

Create panels for at least:

* ⏱️ **Extract duration**
* ⏱️ **Transform duration**
* ⏱️ **Clean duration**
* 🔢 **Rows in / rows out** for each stage
* ⚠️ **Error counts** (per service)
* 🕒 **Last pipeline run time**

➡️ **Plus:** add **one extra panel** using a **custom ETL metric you designed**
(e.g., rows dropped, retries, nulls fixed, etc.).


## 📦 Dashboard 2 — Storage & Queue Health

This dashboard answers:

> "Is storage okay? Are queues backing up?"

### 🐇 RabbitMQ panels

* Queue size (messages ready)
* Messages published vs consumed
* Unacked messages (if available)

### 🗄️ MinIO panels

* Object count per bucket (Bronze / Silver)
* Bucket size (total bytes used)

### 🧮 DuckDB panels

* Final row count in Gold table
* DuckDB file size (using your Cleaner metric)

➡️ **Plus:** add **one panel** based on any **custom metric of your choice**
(e.g., free disk space, bucket growth rate, queue depth threshold).


## 🤖 Dashboard 3 — ML Performance

This dashboard answers:

> "Is the model healthy and fast?"

Include panels for:

* 📈 **Model accuracy** (or main metric you track)
* 🏋️ **Training duration**
* 🔢 **Inference count** (how many predictions)
* 🕒 **Last-trained timestamp**

➡️ **Plus:** add **one panel using YOUR custom ML metric**, such as:

* Prediction latency (p95)
* Precision / recall
* Error rate
* Model version usage

## 🔄 **13. Rebuild and Verify the Entire Pipeline**

After adding metrics, exporters, and new services (Prometheus, Grafana, RabbitMQ exporter, etc.), it’s a good idea to do a **clean rebuild** so everything picks up the latest changes.

### 🧱 Step 1 — Rebuild & Restart

Run these commands from the root of your project:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```


### ✅ Step 2 — Verify Metrics Endpoints

Open these URLs in your browser or with `curl` to make sure everything is exposing metrics correctly.

🔁 Use the ports you actually chose for each service.

* **Extractor metrics** → [http://localhost:8000/metrics](http://localhost:8000/metrics)
* **Transformer metrics** → [http://localhost:8000/metrics](http://localhost:8001/metrics)
* **Cleaner metrics** → [http://localhost:8000/metrics](http://localhost:8002/metrics)
* **Streamlit metrics (if separate)** → [http://localhost:8000/metrics](http://localhost:8003/metrics)
* **RabbitMQ exporter** → [http://localhost:9419/metrics](http://localhost:9419/metrics)
* **MinIO metrics** → [http://localhost:9000/minio/v2/metrics/cluster](http://localhost:9000/minio/v2/metrics/cluster)
* **Prometheus UI** → [http://localhost:9090](http://localhost:9090)
* **Grafana UI** → [http://localhost:3000](http://localhost:3000)

If you see a page full of text starting with things like `# HELP` and `# TYPE`, that means your metrics endpoint is working.

Inside Prometheus, go to **Status → Targets** and confirm all jobs are **UP**.


## 🏁 Final Goal 

By the end of this assignment, you should be able to open Grafana and immediately see:

* 🚀 How each ETL stage is performing (duration, rows, errors)
* 📦 Whether RabbitMQ or MinIO is slowing things down
* 🧮 Whether DuckDB (Gold) is growing as expected over time
* 🤖 How your ML model behaves across training and inference
* 🧠 Whether your **custom metrics** actually add useful insight

If you can:

* Run the pipeline end-to-end,
* See live metrics in Prometheus,
* Read clear dashboards in Grafana,
* And explain what each dashboard tells you about the system,

…then your monitoring & observability layer is complete. 🎉

You’ve just built the kind of visibility that real data engineering and ML teams rely on every day in production systems.

Good luck!


# **📦 Assignment Submission Requirements**

Submit the following as a **single `.zip` file**:

🖼️ **1. Screenshots of All 3 Grafana Dashboards**

Make sure each screenshot clearly shows:

* Dashboard title (ETL Overview, Storage & Queue Health, ML Performance)
* All required panels
* Your **custom metric panel** included in each dashboard

📄 **2. Your `prometheus.yml` Configuration File**

✍️ **3. Short Reflection Write-Up (5–8 Sentences)**

Answer the following:

* **Which custom metric was your favorite and why?**
* **What did you learn about your pipeline from the dashboards?**
* **Did any metric reveal performance issues or surprises?**
* **What improvement would you make next time?**
