# 🌆 **Introduction — Chicago Crash ETL Dashboard**

Welcome, data engineers! 🚀
In this project, you’ll build a **Streamlit dashboard** that becomes the **command center** for the **Chicago Crash ETL pipeline** — a real-world, multi-stage data flow that automates everything from pulling crash data to producing clean, analytics-ready datasets.

By the end, you’ll have a **fully interactive web app** that lets anyone run, monitor, and analyze the ETL process — all with the click of a button. 🖱️✨


## ⚙️ What’s Already Built (Backend Summary)

You’re not starting from scratch — the backend pipeline is already operational!
Here’s what’s available for you:

| Stage              | What It Does                                                                     | Where Data Lives                           |
| :----------------- | :------------------------------------------------------------------------------- | :----------------------------------------- |
| 🧩 **Extractor**   | Pulls 3 APIs (`crashes`, `people`, `vehicles`), gzips them, and uploads to MinIO | `raw-data/crash/<corrid>/`                 |
| 🔄 **Transformer** | Merges JSONs into one CSV                                                        | `transform-data/crash/<corrid>/merged.csv` |
| 🧹 **Cleaner**     | Cleans and upserts into DuckDB                                                   | `gold.duckdb` (local)                      |

Each run is isolated by its **corrid**, so you can track and manage them independently.


### 🎨 **Build the Streamlit Frontend**

Streamlit is perfect for this kind of dashboard — it’s **Python-based**, **interactive**, and can be deployed easily.
You’ll use it to create six main tabs/pages:

| Section                | Purpose                                                                                                    | Example UI Component(s)                                                               |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 🏠 **Home**            | Label overviews (Crash Type, Hit & Run, Fatality Risk) and **Container Health**                            | Info cards + links to EDA/Reports, health status chips                                |
| 🧰 **Data Management** | MinIO delete **by folder** or **by bucket**; Gold (DuckDB) **wipe file**; **Quick Peek**                   | Bucket/prefix inputs + **I confirm** checkbox + preview; table list + row counts      |
| 🔍 **Data Fetcher**    | Fetch data via **Streaming** (since N days) or **Backfill** (date range) with **dynamic columns from API** | `st.tabs(["Streaming","Backfill"])`, multiselect populated from `/api/schema/columns` |
| ⏰ **Scheduler**        | Automate streaming/backfill runs (cron-style)                                                     | Cron text + presets + enable/disable toggle                                           |
| 📊 **EDA**             | Explore cleaned Gold tables per label                                                                      | preview, summary stats, charts                                        |
| 📑 **Reports**         | Pipeline summaries, latest crash dates, run history, CSV download                                          | Metric cards, tables, download button                                                 |

Your dashboard will talk to the backend using **REST API calls**, which you’ll handle with Python’s `requests` library or Streamlit’s built-in `st.button()` + `st.spinner()` interactions.



## 🧭 Navigation Layout

Tabs :

```
🏠 Home | 🧰 Data Management | 📡 Data Fetcher | ⏰ Scheduler | 📊 EDA | 📑 Reports
```


The dashboard will be divided into **six main pages (tabs)**. Each page will perform a specific role in managing, visualizing, and reporting pipeline activity.



## 🏠 1. Home Tab

### 🎯 Purpose

A simple landing page that orients users to the available **ML labels/pipelines** and shows **container health** at a glance..

### 🧱 Components to include


### A) **Label Overview Cards** 

Display a card, include a short description of your pipeline, the label it predicts, key features used, a subset of source columns pulled, class imbalance notes (and how you handled it), data grain/filters, and any leakage caveats.

### **Below is the starter snippet, Add few more whichever you feel needed**:

#### <Emoji + Pipeline Name>  <!-- e.g., 🚦 Crash Type -->
**Label predicted:** `<label_col>`  •  **Type:** `<binary | multiclass>`  •  **Positive class/Classes:** `<define clearly>`

**Pipeline (1–2 lines):**
“We built a model to predict `<label>` using context like `<3–5 key signals>`.”

**Key features (why they help):**
- `<feature_1>` — why it matters
- `<feature_2>` — why it matters
- `<feature_3>` — why it matters
- *(add as needed)*

**Source columns (subset):**
- `crashes`: `<col_a>`, `<col_b>`, `<col_c>`
- `vehicles`: `<col_x>`, `<col_y>` *(if used)*
- `people`: `<col_p>` *(if used)*

**Class imbalance:**
- Positives: `<count or %>` | Negatives: `<count or %>` | Ratio: `~1:<k>`
- Handling: `<none | class_weight | resampling | thresholding | PR-curve focus>`

**Data grain & filters:**
- One row = `<crash | crash+vehicle | crash+person>`
- Window: `<dates or since_days>`
- Filters: `<e.g., drop null geo, city-limits only>`

**Leakage/caveats:**
- `<any IDs or post-outcome fields dropped, mapping columns not used as features, etc.>`

**Gold table:** `<gold_table_name>`  <!-- e.g., gold_crash_type -->


### B) **Container Health Section**

Create small colored **status cards** showing the health of all containers:

* 🟢 MinIO
* 🟢 RabbitMQ
* 🟢 Extractor
* 🟢 Transformer
* 🟢 Cleaner

You can get their status from the backend API (e.g., `/api/health`).
Each card should show:
`✅ Running` or `❌ Not Responding`.


## 🧰 2. Data Management Tab

Centralized admin for storage and warehouse housekeeping. You can delete data in **MinIO** and reset **Gold (DuckDB)**. A lightweight **Quick Peek** helps you sanity-check a few rows from Gold.

### 🧱 Components

### **A) MinIO Browser & Delete**

**Purpose**  
Manage objects in object storage. Remove either a specific **folder (prefix)** or an entire **bucket**.

### 1) Delete **by Folder (Prefix)**

**Inputs**
- **Bucket** (dropdown): `raw-data` | `transform-data`
- **Prefix** (text): e.g., `crash/<corrid>/`
- **I confirm** (checkbox)
- Disable **Delete Folder** until **Preview** has run and **I confirm** is checked.

**Preview (Dry-run)**
- Click **Preview** to see **folders**.

**Action Flow**
1. Run **Preview** to verify scope.  
2. Check **I confirm**.  
3. Click **Delete Folder**.


### 2) Delete **by Bucket**

**Inputs**
- **Bucket** (dropdown)
- **I confirm** (checkbox)
- Disable **Delete Bucket** until **I confirm** is checked.  


**Action Flow**
1. Check **I confirm**.  
2. Click **Delete Bucket** (backend empties objects, then deletes bucket).


### **B) Gold Admin (DuckDB)**

**Purpose**  
Reset or inspect the analytical warehouse stored in `gold.duckdb`.

**Inputs**
- **I confirm** (checkbox) for destructive 
- Disable **Wipe** until **I confirm** is checked.

**Preview**
- **Status Card** shows: DB path, total rows, and per-table row counts.

**Action Flow**
1. To fully reset, choose **Wipe Gold DB (ENTIRE FILE)**.  
2. Check **I confirm**.  
3. Click **Wipe Gold DB** (removes on-disk file and recreates an empty DB).


### **C) Quick Peek (Gold — sanity view)**

**Purpose**  
Confirm that cleaned data looks sane by viewing **columns (with types)** and a small set of **sample rows**. This is a light check, **not** EDA.

**Inputs**

- **Columns**: Multiselect (if empty, auto-select up to **8** left-most columns).
- **Rows (limit)**: Slider (10–200; default **50**).

**Action Flow** 
1. Select a handful of **columns** you care about (label + top features + a couple context fields).  
2. Set **Rows (limit)** to ~**50**.  
3. Click **Preview** to render sample rows.  


## 🔍 3. Data Fetcher Page

This page handles **data retrieval from APIs** before cleaning.
It has **two subtabs**: **Streaming** and **Backfill**.

### 🧱 Components

Use Streamlit’s `st.tabs()` inside this page:

```python
tabs = st.tabs(["Streaming", "Backfill"])
```

### 🔁 Common Sections (applies to **Streaming** & **Backfill**)

### Enrichment Columns

* Adding extra fields from people and vehicles datasets.
* **Controls:**

  * ✅ **Include Vehicles**

    * **Select all vehicle columns** (toggle)
    * **Vehicles: columns to be fetched** (multiselect)
  * ✅ **Include People**

    * **Select all people columns** (toggle)
    * **People: columns to be fetched** (multiselect)
* **Behavior:**

  * Column options are **loaded dynamically from the backend schema** (by calling the openAPI and filtering the columns and storing them in cache, no hardcoding).
  * This dynamic behavior lets the UI change with any change in schema of the enrichment datasets(vehicles and people)
  * **Select all** simply pre-selects everything for that dataset.

### UI elements and Actions

* **Preview JSON** (expander)

  * Shows the **exact request body** that will be published (mode + window + selected columns).
  * Use this to sanity-check corrid, dates/times, and the final column lists.
* **Publish to RabbitMQ**

  * Queues the fetch job with the current selections.
  * Shows a success/error **Status** message after submission.
* **Reset form**

  * Clears selections and returns controls to their defaults (e.g., Since Days = 30).
* **Status**

  * Displays the latest outcome (queued/failed) and any helpful message for the user.

### i. 📡 Streaming Subtab

**Purpose**
Fetch only **recent** crash data (last N days) and **choose the columns to be fetched** so requests stay small and focused.

**Header & CorrID**

* **Mode:** `streaming`
* **corrid (auto):** shown, read-only

**Window**

* **Since days** (default **30**)


### ii. 🕰️ Backfill Subtab

**Purpose**
Fetch data for a **historical date/time range** and **choose the columns to be fetched**.

**Header & CorrID**

* **Mode:** `backfill`
* **corrid (auto):** shown, read-only

**Backfill window**

* **Start date**, **End date**
* **Start time**, **End time**



## ⏰ 4. Scheduler Tab

**Purpose:**
Automate the pipeline so it runs regularly (like every day or week).

### 🧱 Components

* **Select Frequency:**

  * Daily
  * Weekly
  * Custom cron string (advanced)
* **Time Picker:** When should the run start (e.g., 9:00 AM)
* **Config Type:** `streaming`
* **Create Schedule Button** → triggers `/api/schedule`
* **Active Schedules Table:** shows all current schedules (cron, config, last run time).

  * Include delete icon to remove schedule.



## 📊 5. EDA Tab

**Purpose:**
Provide exploratory analysis of the cleaned data in DuckDB (`gold.duckdb`).

### 🧱 Components

1. **Summary Statistics**

   * Row count, missing values
   * Min, max, mean (numeric columns)
   * Top categories (categorical columns)
2. **Visualizations**

    * **Histogram: `posted_speed_limit`**

      * *Crash Type:* Compare distributions for top types (e.g., Rear End vs Turning). Insight: Rear End often peaks at 30–35 mph streets.
      * *Hit & Run:* Overlay 0/1 groups. Insight: Hit-and-run may skew toward mid-speed arterials (e.g., 30–40 mph).

    * **Bar chart: `weather_condition`**

      * *Crash Type:* Counts by weather, colored/faceted by crash_type. Insight: Rear End higher in “Wet/Light Rain”; Sideswipe in “Clear”.
      * *Hit & Run:* Rate = hits/total by weather. Insight: Slightly higher rates in “Dark + Rain/Snow”.

    * **Line chart: `crash_hour`**

      * *Crash Type:* Counts by hour (optionally separate lines for top types). Insight: Turning/Angle spike during PM commute.
      * *Hit & Run:* Hit-and-run rate by hour. Insight: Rate rises late night (e.g., after 10 PM).

    * **Pie chart: `crash_day_of_week`**

      * *Crash Type:* Share of each day by crash_type (or separate pies per type). Insight: Weekend mix shifts toward Angle/Turning at entertainment areas.
      * *Hit & Run:* Share of hit-and-run by weekday. Insight: Slight weekend uptick in hit-and-run proportion.
    Here are more **visualization types** with quick **examples** for both **crash_type** and **hit_and_run_i**:

    * **Heatmap: hour × day-of-week**

      * *Crash Type:* Count heatmap; see commute patterns (Mon–Fri 16–19).
      * *Hit & Run:* Rate heatmap (hits/total). Late-night weekends glow.
.

## 📑 6. Reports Tab

**Purpose:**
Show summarized metrics and health of the ETL process over time.

### 🧱 Components

### Summary Cards (at a glance)

* **Total runs completed**
* **Latest corrid** (click-to-copy)
* **Gold row count** (current)
* **Latest data date fetched** *(max crash date currently in Gold)*
* **Last run timestamp** *(ended_at of most recent run, local time)*

### Latest Run Summary (most recent corrid)

* **Config used** (streaming/backfill; window or dates)
* **Start / End time** (local time)
* **Rows processed** (show per table if available)
* **Errors / Warnings** (collapsed list with counts)
* **Artifacts** (links: request JSON, logs, sample outputs if exposed)

### Download Reports

* **CSV / PDF** buttons to export:

  * **Run history**: corrid, mode, window, rows, status, started/ended
  * **Gold snapshot**: table, row count, latest data date
  * **Errors summary**: corrid, type, message counts

# 📝 Assignment — Dashboard Proof & Enhancements

Prove your end-to-end pipeline works and that you can extend the EDA. Submit concise screenshots + one downloaded report.

### ✅ What to Submit (Checklist)

1. **Home Page (1 screenshot)**

   * Must show:

     * **Label overview cards** (your chosen outcome highlighted)
     * **Container Health** cards with statuses visible (MinIO, RabbitMQ, Extractor, Transformer, Cleaner)

2. **Data Fetcher in Action (1 screenshot)**

   * One screenshot of **Streaming** or **Backfill** **after Publish**, with the **Status** message visible (success or error) and the **corrid** shown.
   * If you use Enrichment: include the **columns to be fetched** selections in frame.

3. **Data Management Functioning (1–2 screenshots)**

   * **MinIO by Folder**: show the **Preview (dry-run)** result (count/keys visible) and the **I confirm** checkbox **enabled** (you do **not** need to actually delete in the screenshot).
   * **Gold Admin**: show the **Status Card** (DB path + table counts). If you performed a wipe, show the **post-wipe** state (Tables: 0 · Rows: 0).

4. **EDA — Add 10+ New Visualizations (10+ screenshots)**

   * Add **at least 10** additional visuals **beyond** the defaults. Mix chart types (e.g., histogram, bar, line, box, heatmap, stacked bar, donut/pie, hex/point map, violin, scatter with jitter, treemap, bump chart for hourly ranks, etc.).
   * Each screenshot must show:

     * The **chart title** describing the view (e.g., “Hit & Run Rate by Weather”)
     * The **selected label/table** (e.g., `gold_hit_and_run`)
     * Any key filter/encoding choices (e.g., “rate = hits/total”) in a tiny subtitle or caption.

5. **Reports — Downloaded Report (1 file + screenshot)**

   * Download either the **Run history CSV** or the **PDF** report from the Reports tab.
   * Submit the **file** and a **screenshot** of the Reports page with **Summary Cards** visible (must include **Latest data date fetched** and **Last run timestamp**).

6. **Single **PDF** with Briefs**

    If you prefer, compile your screenshots into **one PDF** and include a short write-up under **each** image:

    * **What is shown?** (feature/step/result)
    * **Why it matters?** (1 line)
    * **Issues faced (if any) & how you handled them.**
    * **Outcome** (fixed/not fixed; next step).

You must still include **one downloaded report file** ( `report.pdf`) alongside the PDF.


### 🧭 Guidance & Acceptance Criteria

* **Visibility:** All screenshots must be readable (no cropped corners, no overlapping dialogs).
* **Freshness:** **Last run timestamp** and **Latest data date fetched** should align with your recent run (within your chosen window).
* **EDA Variety:** Your 10+ visuals should **not** be trivial duplicates; use at least **5 distinct chart types** and highlight insights specific to your label (e.g., late-night spike for hit-and-run, speed-bin patterns for crash type).
* **Safety:** For Data Management, it’s enough to show **Preview + I confirm enabled**. Do not actually delete shared class data unless instructed.
* **Clarity:** Give each EDA chart a 1-line **insight caption** (e.g., “Hit-and-run rate increases after 22:00 on weekends”). You can add captions directly under the chart.

### 📦 Submission Format

* Create a folder named:
  `outcome_firstname_lastname_dashboard_proof_<yyyy-mm-dd>`
* Include:

  * `home.png`
  * `fetch_status_streaming.png` (or `fetch_status_backfill.png`)
  * `minio_preview.png`, `gold_status.png`
  * `eda_01.png` … `eda_10.png` (add more if you have them)
  * `report_screenshot.png`
  * `report.pdf` (downloaded from Reports tab)
  * All the images with description in the pdf apart from the report
* Zip the folder

## 🎥 Optional Video Walkthrough (Alternative Submission)

Prefer showing instead of screenshotting everything? You may submit a **single video** that walks through the entire dashboard.

### What the video must cover (in order)

1. **Home** — label overview cards and **Container Health**.
2. **Data Fetcher** — run either **Streaming** or **Backfill**, then show the **Status** with the corrid visible.
3. **Data Management** —

   * **MinIO (by Folder)**: show **Preview (dry-run)** and the **I confirm** checkbox enabled (no need to actually delete).
   * **Gold Admin**: show the **Status Card** (DB path + table counts), or post-wipe state if you performed one.
4. **EDA** — briefly tour **at least 10 additional visualizations** you added (titles visible + one-line insight each).
5. **Reports** — show the **Summary Cards** (including **Latest data date fetched** and **Last run timestamp**) and demonstrate downloading one report (CSV or PDF).

### Recording guidelines

* **Length:** 5–8 minutes.
* **Audio:** Narrate what you’re doing and call out key results (e.g., “corrid appears here… rows processed > 0…”).

### What it replaces

* The video can **replace all required screenshots**.
* You must still **upload one downloaded report file** (PDF).

### How to submit
* Provide the actual file or provide a view-only link with download enabled for the video 
* Include the **report file(pdf)** in the same submission package.
* Zip both the video and the report pdf.

### Reflection segment (required for video and screenshots in pdf)

Add **1–2 minutes** or a few lines at the end on **what was different this time vs last semester’s DAEN 328** when you built a Streamlit app.

This can be used as a starting point or Template.

* **Architecture/process:** schema-driven column selection, preview→publish flow, corrid tracking.
* **Safety/UX:** dry-run previews, “I confirm” gates, clearer status/errors.
* **EDA depth:** outcome-aware visuals, rates (e.g., hits/total), better labeling.
* **Automation/reporting:** scheduler mindset (if used), artifacts, Reports tab.

