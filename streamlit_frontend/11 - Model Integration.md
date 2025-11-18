# 📌 **Model Integration & “ML Model” Tab Instructions**

### 1️⃣ **Where to put your `.pkl` in the Streamlit project**

1. Inside your Streamlit app repository, create an `artifacts` folder (if it doesn’t already exist).
2. Copy your generated model file (for example `pipeline_calibrated.pkl`) into that folder.
3. Decide on a **fixed path** relative to the app (for example:
   `artifacts/pipeline_calibrated.pkl`) and **use that consistently** in your app code.


### 2️⃣ **Model loading: what your app must do** 

In your Streamlit code, you must implement a single **model loading helper** with the following behavior:

1. It takes a **file path** to the `.pkl` artifact (for example, a constant like `MODEL_ARTIFACT_PATH` at the top of your file).

2. It opens the file and unpickles it.

3. It must be cached using Streamlit’s caching mechanism so the model is only loaded once per session and not reloaded on every interaction.

If model loading fails, the app must show a visible error message in the UI instead of crashing.


### 3️⃣ **DuckDB connection & feature preparation**

In the same app:

1. Implement a **DuckDB connection helper** that:

   * Connects to your **gold DuckDB file** (for example `/data/gold/gold.duckdb` or the path defined in your docker/docker-compose setup).
   * Reuses the same connection for all queries in the app.
   * Is cached so it isn’t re-opened on every interaction.

2. Implement a **feature preparation helper** that:

   * Accepts a `DataFrame` loaded from DuckDB or from an external file.

### 4️⃣ **Adding the **Model** tab to the dashboard**

Your Streamlit app must add a new tab called **“Model”** alongside the existing ones (Home, Data Management, EDA, Reports, etc.).

Inside the **Model** tab you must implement three main sections:

1. **Model Summary**
2. **Data Selection**
3. **Prediction & Metrics**


### 5️⃣ **Section 1 – Model Summary**

In the **Model** tab, at the top:

1. Load the model artifact using your model-loading helper.
2. Display a short **summary block** that includes at least:

   * The class name of the outer model object (should be `CalibratedClassifierCV`).
   * The class name of the underlying estimator (the pipeline the calibrator wraps).
   * The current decision threshold that will be used to convert probabilities to class labels.
3. Add a brief **description** summarizing the expected input:

   * Clearly state that the model expects the feature columns listed earlier (categoricals + numerics).
   * State that one-hot encoding and numerical preprocessing are handled **inside** the pipeline, so the app must pass **raw columns** with the correct names, not manually encoded matrices.

If you change the feature set in your training notebook, you are responsible for updating this description so it doesn’t lie.


### 6️⃣ **Section 2 – Data Selection**

In the **Model** tab, the second block must allow the user to choose **which data** to run through the model.

You must support **three modes**:

1. **Gold table (full or sample)**
2. **Test data (held-out from training)**

#### 6.1 Gold table mode

* Provide an input for **maximum number of rows** to score (for example 5,000 by default, with an upper limit).
* Provide a date filter section:

  * Two date inputs: **start date** and **end date** for filtering.
  * An input for **maximum number of rows**.
* Load the result into a `DataFrame` and display the number of rows and a preview.


#### 6.2 Test data mode

* This mode is for evaluating the model on the **test data**.

* You must:

  * Provide a **file upload control** so the user can upload their own test file at runtime.

  * Clearly state and enforce the **allowed file types** for test data:

    * **CSV (`.csv`)** – allowed for **custom test data**.

  * Reject any other file extensions and show a **clear error message** if the user tries to use an unsupported type instead of silently failing.

  * Load the selected file into a DataFrame once it passes the file-type check.

  * Verify that the loaded DataFrame has:

    * The **same feature columns** that the trained pipeline expects (the ones used during training).

  * After loading, display:

    * The **number of rows** loaded.
    * A **small preview** (head) so the user can visually confirm that the data looks correct.


### 7️⃣ **Section 3 – Prediction & Metrics**

Once data is successfully loaded and shown, the Model tab must **Run predictions**

#### 7.1 Show core model metrics

You must distinguish between:

* **Static metrics**: the official metrics from your ***training notebook*** on the held-out test set.
* **Live metrics**: metrics computed in the streamlit app.

# 🧾 **Assignment: Model Findings Report (Written for Your Boss, Not Your Professor)**

### **🔍 Scenario**

You’re the data analyst on a crash-risk analytics project. Your “boss” (non-technical manager) has given you two tasks:

1. **Build a model** that predicts a crash-related outcome (your chosen label).
2. **Explain what the model is telling us** in normal language so leadership can decide what to do.

You’ve already trained the model and integrated it into the **Model** tab of your Streamlit dashboard. Now you owe your boss a **clear, concise written report** that uses:

* The **metrics and outputs in the Model tab**.
* Screenshots/tables/figures exported from your own tools as **evidence**.

This is not a “lab write-up”. This is you justifying your work to someone who can shut the project down if they aren’t convinced.


### **🎯 Goals**

By the end of this assignment, you must:

* Write a **2–3 page report** that:

  * Explains what the model is doing.
  * Shows **where it works and where it fails**, with proof.
  * Ends with **specific recommendations** to your boss.

If you dump raw metrics with no explanation, expect a bad grade.

You are **not** allowed to invent metrics or claim numbers that do not come from your tools.


### 📑 **Report Structure (Required Sections)**

Your report must have the following sections. Use these headings.

#### **1. Executive Summary**

Write this as if your boss will only read this section.

Include:

* **What problem** you modeled.
* **What the model can and cannot do** in plain English.
* A summary of performance.
* **1–2 clear recommendations**.

#### **2. Problem & Data Context**

No formulas here. Just enough context so your boss understands what “the model” is looking at.

#### **3. Model & Threshold Overview**

Summarize the model:

* **Model type:**
  
* **Decision threshold:**

If you can’t explain your threshold in plain English, you’re not in control of your model.


#### **4. Performance Findings (Using Test Metrics)**

Use the **test metrics** shown in the Model tab as your primary evidence on model quality.

* Is this performance **good enough** for the use case?
* What’s the trade-off?


#### **5. Business Insights & Implications**

Using your model outputs and metrics, answer:

1. **Who or what is the model flagging?**

   * Are there certain conditions (night vs. day, weather, speed limits, alignment, etc.) where the model finds many high-risk cases?
   * Which segments or situations show up frequently among predicted positives?

2. **What are the consequences of errors?**

   * Given your current threshold and metrics:

     * Approximate how many **missed high-risk crashes** (false negatives) you’d expect per 1,000 crashes.
     * Approximate how many **false alarms** (false positives) you’d expect per 1,000 crashes.
   * Use real numbers from your live evaluation or test set as examples.

3. **Is the model actionable?**

   * Based on the above, is it reasonable to:

     * Use the model to prioritize inspections / patrols?
     * Use it as a triage filter for analysts?
     * Or is it still a research prototype?

Back every claim with **numbers from your metrics** or **counts from your scored data**. If you make a claim without evidence, it doesn’t count.

### **📦 Deliverables**

**Written report** (PDF, 2–3 pages)