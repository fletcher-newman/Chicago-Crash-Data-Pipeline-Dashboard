# **CI/CD for Your Advanced Data Engineering Pipeline**

# 🌟 **Section 1 — Introduction**

Welcome to the final stage of your full end-to-end project.
You’ve already built an impressive system:

* 🟢 **Local pipeline** (Go Extractor → Transformer → Cleaner → DuckDB → Streamlit)
* 🔵 **Azure VM replica of the local setup**
* 🟣 **GitHub repository with all pipeline code**
* 🟠 **Docker Compose managing services**

Now we add the last missing piece:

## 🚀 **CI/CD — The Automation Layer**

CI/CD is how real engineering teams ship code **reliably**, **safely**, and **without manual intervention** every time they push changes.

This notebook teaches CI/CD **step by step**, in a way that fits your exact pipeline.

## 🎯 **Why You Need CI/CD Now**

Without CI/CD, your workflow probably looks like this:

1. Edit code locally
2. `git push`
3. SSH to Azure
4. Pull the code
5. Rebuild containers
6. Restart everything
7. Pray it works 🤞

CI/CD fixes this by turning all of those steps into **automatic checks** and **automatic deployment**.

CI/CD means:

* When you push code → GitHub checks it.
* When checks pass → GitHub deploys it.
* If something breaks → GitHub stops it before it reaches Azure.

## ⚙️ **CI/CD in Simple Terms**

### 🔧 **CI = Continuous Integration**

This means GitHub automatically:

* Pulls your code
* Builds it (Go + Python parts)
* Runs basic tests or checks
* Validates your Docker Compose file
* Ensures nothing *obviously* broken goes to Azure

If CI fails → **Do NOT deploy.**

If CI passes → **Safe to deploy.**

### 🚚 **CD = Continuous Delivery / Deployment**

While CI checks code, **CD deploys code**.

For your project, CD means:

* Whenever you push to **main** (or a “release” branch):

  * GitHub opens an SSH session into your Azure VM
  * Pulls the latest code
  * Rebuilds your pipeline
  * Restarts the services
  * Runs a tiny smoke check (e.g., Streamlit health page)

This ensures:

> Your Azure VM always runs the latest working version — automatically.

No more manual deployments.
No more “I forgot to restart the container.”


## 🔍 **Where CI/CD Fits in *Your* Architecture**

Your pipeline looks like this:

* 🟤 **Bronze (Extractor)** → MinIO
* 🟡 **Silver (Transformer)** → MinIO
* 🟢 **Gold (Cleaner)** → DuckDB
* 🔵 **ML + Streamlit UI**
* 🔐 **Azure VM running everything with Docker Compose**
* 🐙 **GitHub repo tracking all code**

Everything remains clean, predictable, and automatic.


# 🌈 **Section 2 — Understanding GitHub Actions**

GitHub Actions is the engine that will power your entire CI/CD pipeline.
Before we write any YAML or build any workflows.

## 🚀 **2.1 What Is GitHub Actions?**

GitHub Actions is a **built-in automation platform** inside GitHub.

Every time you:

* push code
* create a branch
* open a pull request
* publish a release

GitHub can automatically run tasks **for you**.

Think of it as:

> A free robot inside your repo that runs your scripts every time something changes.

## 🧩 **2.2 Core Concepts**

There are only **4 concepts** you truly need to understand:


## 🟦 **1. Workflows**

A workflow = **a complete automation file**.

Located in:

```
.github/workflows/
```

Example:

```
ci.yml
deploy.yml
docker-build.yml
```

Each file is a separate automation.

In this course, you’ll create **two main workflows**:

* `ci.yml` → checks your code
* `deploy.yml` → deploys to Azure


## 🟩 **2. Jobs**

A job = **a set of steps that run in sequence**.

Example jobs you will build:

* `build-extractor` (Go)
* `test-transformer` (Python)
* `validate-docker-compose`
* `deploy-to-azure`

Each job runs in its own clean environment.


## 🟧 **3. Steps**

A step = **one command inside a job**.

Examples:

* Install Go / Python
* run Go build
* run docker compose config
* SSH to Azure server

Steps run one after another **inside the same job container**.


## 🟨 **4. Runners**

A runner = **a virtual machine where your workflow runs**.

There are two types:

### 🖥️ **GitHub-Hosted Runner**

* Free Linux VM
* Temporary (deleted after your workflow finishes)
* **Most common** for CI
* Perfect for this course

### 🏡 **Self-Hosted Runner**

* You install a runner on your own server
* More power, more control
* We *don’t* need this yet

For this entire unit, you will use:

```
runs-on: ubuntu-latest
```

## 🧪 **2.3 How Workflows Are Triggered**

Workflows run when certain **events** happen.

Examples:

### 🟦 On every push:

```yaml
on:
  push:
    branches: ["*"]
```

### 🟩 On pull request:

```yaml
on:
  pull_request:
```

### 🟧 On push to main only:

```yaml
on:
  push:
    branches: ["main"]
```

### 🟨 On a schedule (cron jobs):

```yaml
on:
  schedule:
    - cron: "0 12 * * *"   # every day at 12pm
```

For your project:

* CI runs → on *every push*
* CD runs → ONLY when `main` is updated

This prevents accidental deployments.


## 📦 **2.4 What GitHub Actions Actually DOES for You**

**On push:**

1. GitHub spins up a temporary Linux VM
2. Your repo is cloned
3. Your code is built, tested, validated
4. Results show up under “Actions” tab
5. Workflow VM is deleted

**On deploy:**

1. GitHub spins up VM
2. SSH into Azure
3. Pulls latest code
4. Rebuilds Docker
5. Restarts pipeline

Your Azure VM stays untouched except during deployment.

# 🌟 **Section 3 — Planning Your CI Workflow**

Before we write any GitHub Actions YAML, we need a **clear plan**.

A CI pipeline should NEVER be random.
It must be designed around:

* your project structure
* your languages (Go + Python)
* your Docker setup
* your Azure deployment


## 🎯 **3.1 Goal of CI**

Your CI must check:

* the project builds
* the code imports
* dependencies install
* Docker Compose is valid
* basic pipeline entrypoints work normally

If CI fails → **CD must NOT run.**


## 🔍 **3.2 The CI Workflow Structure**

Your CI workflow should have **3 major jobs**:


## 🟦 **Job 1 — Code Quality & Build Checks**

This job ensures your languages actually run.

### This will check:

* Go extractor can **compile**
* Python modules can **import**
* `requirements.txt` can install packages

## 🟩 **Job 2 — Docker Compose Configuration Check**

This job ensures your multi-container setup is valid.

### This will check:

* Dockerfile syntax
* That container dependencies are logically correct
* No YAML indentation issues


## 🟧 **Job 3 — Light Functional Sanity Check**

We don’t need to run the entire pipeline on GitHub’s VM.
But we do need a **basic sanity test**.


This catches mistakes like:

* wrong relative paths
* missing environment variables
* missing folders
* missing .env.example files


## 🛑 **3.3 What You SHOULD NOT Test in CI**

We often over-test and slow CI down.

Here’s what **we DO NOT run** in CI:

* MinIO
* RabbitMQ
* Full extractor end-to-end API call
* Full transformer processing
* DuckDB writes
* Streamlit UI server

Why?

Because CI should be:

* **fast**
* **easy to debug**
* **cheap** (GitHub minutes cost money)
* **reliable** (no API throttling or timeout failures)

We test only what matters most:
**Does the code run, and does the system start?**


## 🖌️ **3.4 Visual Layout of CI**

```
              ┌───────────────────────┐
              │       Git Push        │
              └────────────┬──────────┘
                           ▼
            ┌──────────────────────────────┐
            │        CI WORKFLOW           │
            └──────────────────────────────┘
                │                  │
                │                  │
                ▼                  ▼
          ┌──────────────┐   ┌──────────────┐
          │  Code Build  │   │ Docker Checks│
          │  (Go+Python) │   │  Compose OK  │
          └──────────────┘   └──────────────┘
                  │                 │
                  └────────┬────────┘
                           ▼
                    ┌────────────────┐
                    │  Sanity Tests  │
                    │  (Imports etc) │
                    └──────┬─────────┘
                           ▼
                    ┌────────────────┐
                    │   CI PASSED    │
                    └────────────────┘
```

# 🌈 **Section 4 — Building Your CI Workflow File**

In this section, **you** are going to build your own CI workflow file.


## **4.1 Create the CI Workflow File**

You **must** create a workflow file in this exact folder:

1. In your repo, create the folders (if they don’t exist):

```text
.github/workflows/
```

2. Inside `workflows`, create a file:

```text
ci.yml
```

> 📝 From now on, everything you write goes inside `ci.yml`.



## **4.2 Add Basic Workflow Header + Trigger**

At the very top of `ci.yml`, you need two things:

1. A **name** (anything readable)
2. An **on:** block that tells GitHub **when** to run CI

* Give the workflow a short name like `"CI Pipeline"` or `"Advanced DE CI"`.
* Configure it to run:

    * on **every push**

You’ll need something like:

```yaml
name: <your workflow name>

on:
  push:
    branches: ["*"]
```

## **4.3 Define Job 1: Build & Validate Code**

Now you’ll define your **first job** called something like `build` or `build-and-validate`.

This job will:

* Check out the code
* Install Go
* Build your Go extractor
* Install Python
* Install dependencies
* Test Python imports

### **4.3.1 Job Skeleton**

Inside `jobs:`, add your first job:

```yaml
jobs:
  build:
    name: <friendly name for job>
    runs-on: ubuntu-latest

    steps:
      # you will add steps here
```

### **4.3.2 Add “Checkout Code” Step**

Every job needs to **download your repo** into the runner.

Inside `steps:`, add a step that uses `actions/checkout`.

* Add a step with a name like `"Checkout repository"`
* Use the official GitHub action `actions/checkout@v4` (or v3)

**Hint:**

```yaml
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
```


### **4.3.3 Add Go Setup + Build Step**

Now we want CI to confirm your **Go extractor** actually builds.

   
1. Add a step that:

   * Uses `actions/setup-go`
   * Sets a Go version (e.g., `"1.22"`)

2. Add a **build step** that:

   * `cd` into your extractor folder (whatever you named it)
   * Runs `go mod tidy`
   * Runs `go build ./...`

**You must:**

* Use the correct folder name (e.g., `extractor`, `go-extractor`, etc.)
* Use the correct main file name if needed (`main.go`, etc.)

### **4.3.4 Add Python Setup + Requirements Install**

Next, check that Python and your dependencies install correctly.


1. Add a step to set up Python (e.g., 3.11) using `actions/setup-python`.
2. Add a step that runs:

```bash
pip install -r requirements.txt
```

**You must:**

* Ensure `requirements.txt` actually exists at the repo root
* Adjust the path if it’s inside a folder (e.g., `app/requirements.txt`)

### **4.3.5 Add Python Import Test Step**

Finally, make sure your main Python modules **import without errors**.


* Add a step that runs **at least two** import checks from each service, like:

```bash
python -c "import <your_transformer_module>"
python -c "import <your_cleaner_module>"
```

**You must:**

* Use the correct module names based on your project layout

## **4.4 Define Job 2: Docker Validation**

Now you’ll add a second job to validate your **Docker services and Docker Compose file** using only:

* `docker compose build`
* `docker compose config`
* (optionally) `docker compose up` in a lightweight way

This job should:

* Run **after** Job 1
* Make sure your services **can build**
* Make sure your Docker Compose file is **valid YAML and wiring**


### **4.4.1 Job Skeleton**

Under `jobs:` (next to `build`, not inside it), define another job:

```yaml
  docker-validation:
    name: <friendly name>
    runs-on: ubuntu-latest
    needs: build

    steps:
      # steps come here
```

### **4.4.2 Add Checkout Step**

Same as before, the runner needs your code.

Add this as your **first step** inside `steps:`:

```yaml
      - name: Checkout repository
        uses: actions/checkout@v4
```

Without this, `docker compose` won’t find your files.

### **4.4.3 Add `docker compose build` Checks**

1. Decide which services you want to validate:

   * e.g., `extractor`, `transformer`, `cleaner`, `streamlit`, etc.
2. Use `docker compose build` with those service names.

**Example pattern (you must adapt service names to match your `docker-compose.yml`):**

```yaml
      - name: Build key services with docker compose
        run: |
          docker compose -f docker-compose.yml build extractor
          docker compose -f docker-compose.yml build transformer
          docker compose -f docker-compose.yml build cleaner
          docker compose -f docker-compose.yml build streamlit
```

Hints:

* Service names must match **exactly** what you used under `services:` in `docker-compose.yml`.
* If you named them differently (e.g., `ml-ui` instead of `streamlit`), update the names.


### **4.4.4 Add Docker Compose File Validation**

Now we make sure the **compose file itself** is valid:

* YAML is correct
* All references resolve properly
* No obvious config issues

👉 Add a step that runs `docker compose config`:

```yaml
      - name: Validate docker-compose.yml
        run: |
          docker compose -f docker-compose.yml config
```


> 💡 This is like a **“lint”** for your Docker Compose file. If your YAML is broken or a variable is missing, it’ll fail here.



## **4.5 Define Job 3: Sanity Check** 

This job does **quick, safe checks** that your entrypoints still work, without running the full pipeline.

Examples:

* Run `go run main.go --help` inside extractor
* Import `transformer` and print a message
* Import `cleaner` and print a message

### **4.5.1 Job Skeleton**

Add a third job:

```yaml
  sanity-check:
    name: <friendly name>
    runs-on: ubuntu-latest
    needs: docker-validation

    steps:
      # steps here
```

### **4.5.2 Add Checkout Step**

Same as before:

```yaml
      - name: Checkout repository
        uses: actions/checkout@v4
```


### **4.5.3 Add 2–3 Sanity Tests**

Now you decide what to test lightly.

👉 Choose at least **two** of the following:

1. **Extractor test**

   * `cd` into your extractor directory
   * Run something like: `go run main.go --help`

2. **Transformer import test**

   * Use a short inline Python script to import your transformer

3. **Cleaner import test**

   * Same idea for cleaner

**Hint pattern for inline Python:**

```yaml
      - name: Transformer import test
        run: |
          python - <<EOF
          import <your_transformer_module>
          print("Transformer imported successfully")
          EOF
```

## **4.6 View CI Runs on GitHub**

After you push:

1. Go to your GitHub repo
2. Click the **“Actions”** tab
3. Click on your workflow name
4. Open the latest run
5. Click each job (`build`, `docker-validation`, `sanity-check`) to see logs

## **4.7 📚 Suggested Resources**

* **Workflow Syntax (GitHub Docs)**
  [https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions)
  → Full reference for writing workflow YAML files.

* **actions/checkout**
  [https://github.com/actions/checkout](https://github.com/actions/checkout)
  → Lets your workflow pull your repository into the runner.

* **actions/setup-python**
  [https://github.com/actions/setup-python](https://github.com/actions/setup-python)
  → Installs Python versions inside GitHub Actions.

* **actions/setup-go**
  [https://github.com/actions/setup-go](https://github.com/actions/setup-go)
  → Installs Go toolchain for building your extractor.

* **Runner Images (What’s preinstalled?)**
  [https://github.com/actions/runner-images](https://github.com/actions/runner-images)
  → Lists all tools available in the `ubuntu-latest` GitHub runner.

* **Starter Workflows**
  [https://github.com/actions/starter-workflows](https://github.com/actions/starter-workflows)
  → Example GitHub Actions workflows you can learn from.



# 🌈 **Section 5 — Setting Up GitHub Secrets for Deployment**


In this part, you will set up the **secure credentials** that GitHub Actions needs to log into your Azure VM and deploy your code.


### 🔐 **What You Are Setting Up**

You will add the following secrets to your GitHub repository:

| Secret Name       | Description                                              |
| ----------------- | -------------------------------------------------------- |
| **AZURE_HOST**    | The public IP address of your Azure VM                   |
| **AZURE_USER**    | The username you use to SSH (e.g., `azureuser`)          |
| **AZURE_SSH_KEY** | Your **private SSH key**         |
| **PROJECT_PATH**  | The folder on your Azure VM where your project is stored |

These secrets allow GitHub Actions to SSH into your VM and deploy your pipeline.

### **Open Your GitHub Repository**

1. Go to your repository on GitHub.
2. Click on the **Settings** tab (top-right).


### **Open Secrets Panel**

Inside Settings:

1. On the left sidebar, click **“Secrets and variables”**
2. Then click **“Actions”**
3. Then click the **“New repository secret”** button

You will repeat this process for EACH secret.

### **Add `AZURE_HOST`**

1. Click **“New repository secret”**
2. For **Name**, type:

```
AZURE_HOST
```

3. For **Value**, paste **your Azure VM public IP**
   (Example: `20.122.41.75` — yours will be different)

4. Click **Add secret**


### **Add `AZURE_USER`**

1. Click **“New repository secret”**
2. For **Name**, type:

```
AZURE_USER
```

3. For **Value**, enter your SSH username
   Example:

```
azureuser
```

4. Click **Add secret**


### **Add `AZURE_SSH_KEY`**

### You **must** paste your **private key**, NOT the `.pub` file.

### Instructions:

1. On your VM, open a terminal.
2. Run:

```
cat ~/.ssh/id_rsa
```

or if you use a `.pem` key:

```
cat key.pem
```

3. Copy **everything**, including:

```
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

4. Back in GitHub:

* Click **New repository secret**
* Name it:

```
AZURE_SSH_KEY
```

* Paste the entire private key into **Value**
* Click **Add secret**

### **❗ Warning :**

* DO NOT paste your `.pub` key
* DO NOT modify the key
* DO NOT add quotes or backticks
* DO NOT commit your key to the repo


### **Add `PROJECT_PATH`**

This tells GitHub where your code is stored on your Azure VM.

You must SSH into your VM and run:

```
pwd
```

Example output:

```
/home/azureuser/myproject
```

Use this as the value.

### In GitHub:

1. New repository secret
2. Name:

```
PROJECT_PATH
```

3. Value:

```
/home/<your-user>/<your-project-folder>
```

4. Add secret



# 🌈 **Section 5.1 — Creating the Deployment Workflow File (`deploy.yml`)**

Now that your GitHub Secrets are fully set up, you are ready to **create the deployment workflow file**.

This file will live inside:

```
.github/workflows/deploy.yml
```

This workflow controls **WHEN** deployment happens and sets the foundation for the actual deployment steps you’ll write later.


**You are NOT connecting to your VM yet.**
This section only sets up the structure.


### **Create the Workflow File**

Inside your repository:

1. Navigate to the `.github` folder
2. Create a folder named `workflows` (if it doesn’t exist)
3. Inside it, create a new file:

```
deploy.yml
```

Make sure:

* Name is correct (`deploy.yml`)
* It is inside `.github/workflows/`

If your folders are wrong → GitHub won’t detect it.

### **Give Your Workflow a Name**

At the very top of `deploy.yml`, add a simple, clear name.

Example (choose your own wording):

```yaml
name: Deploy to Azure VM
```

This is what shows up in GitHub Actions.


### **Add the Trigger**

You MUST configure deployment to run **only** when the `main` branch changes.

Add this block:

```yaml
on:
  push:
    branches:
      - main
```


### **Start the Job Structure**

Next, create the basic structure for your deployment job.

Add this under `on:`:

```yaml
jobs:
  deploy:
    name: Deploy Pipeline to Azure
    runs-on: ubuntu-latest

    steps:
      # You will fill this in next part
```

This creates:

* a **job** named `deploy`
* running on a GitHub-hosted Ubuntu VM
* containing a `steps:` section (currently empty)

You will fill in steps (SSH, git pull, compose builds, etc.) later.


### ⛔ **Do NOT Add Any SSH or Docker Steps Yet**

Right now, your file should ONLY contain:

* name
* trigger
* job header
* empty steps block

The actual deployment commands will be added **after this part**.


### **Validate Your Structure**

Your `deploy.yml` should now look like this:

```yaml
name: Deploy to Azure VM

on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy Pipeline to Azure
    runs-on: ubuntu-latest

    steps:
      # Steps will be added in the next section
```

Make sure indentation is correct.

YAML breaks easily if spacing is wrong.


### **Commit and Push**

1. Save the file
2. Commit the file:
3. Open GitHub → Actions
4. You should now see:

“Deploy to Azure VM” (workflow created but skipped / idle)


# 🌈 **Section 5.2 — Linking CD to CI**


You’ve already:

* Built a **CI workflow** (`ci.yml`)
* Created a **CD workflow skeleton** (`deploy.yml`)

Now you will **connect them logically** using GitHub’s protections, so:

You will do this using **Branch Protection Rules** on GitHub.

### **Open Your Repo Settings**

1. Go to your repository on GitHub.
2. Click the **Settings** tab (top of the page).


### **Go to Branch Protection Rules**

Inside Settings:

1. On the left sidebar, click **“Branches”**
2. You will see a section called **“Branch protection rules”**
3. Click **“Add branch protection rule”**


###  **Target the `main` Branch**

You are going to protect the `main` branch (your production branch).

1. In **“Branch name pattern”**, type:

```
main
```

This rule will now apply to the `main` branch only.


### **Enable “Require Status Checks to Pass”**

Scroll down to the section called:

> **✔ Require status checks to pass before merging**

1. Check the box: **Require status checks to pass before merging**
2. A list of available checks will appear (these are from your CI workflow).

Look for the CI workflow you created earlier.
* Whatever `name:` you gave your CI workflow in `ci.yml`

3. Select your CI workflow’s **status checks**.

If it shows individual jobs (e.g., `build`, `docker-validation`, `sanity-check`), you can:

* Either select the **overall workflow**, or
* Select the **critical job(s)** you want to require



### **Save the Rule**

Scroll to the bottom and click:

> **“Create”** or **“Save changes”**

Now your `main` branch is protected.



### **🧪 Quick Test** 

1. Make a small change on a branch that **breaks CI on purpose**

   * e.g., introduce a syntax error or bad import
2. Open a Pull Request into `main`
3. Wait for CI to run
4. Confirm:

   * CI fails ❌
   * GitHub shows a message like:

     > “Merging is blocked — 1 or more checks have not passed”
5. Fix the mistake
6. Push again
7. CI turns green ✅
8. You are now allowed to merge


# 🌈 **Section 5.3 — Adding SSH Setup to the Deploy Job (Connecting to Your Azure VM)**

Right now your `deploy.yml` has:

* a name
* a trigger (`on: push → main`)
* a `deploy` job with `runs-on: ubuntu-latest`
* an empty `steps:` block

In this part, you will:

1. Load the secrets you created (`AZURE_HOST`, `AZURE_USER`, `AZURE_SSH_KEY`, `PROJECT_PATH`)
2. Create an SSH key file on the GitHub runner
3. Confirm the runner can theoretically connect to your VM


### **Attach Secrets as Environment Variables in the `deploy` Job**

Open `.github/workflows/deploy.yml`.

Find your `deploy` job. It should look like:

```yaml
jobs:
  deploy:
    name: Deploy Pipeline to Azure
    runs-on: ubuntu-latest

    steps:
      # Steps will be added in the next section
```

You now need to **add an `env:` block** to this job so it has access to your secrets.

👉 Modify your job to include:

```yaml
  deploy:
    name: Deploy Pipeline to Azure
    runs-on: ubuntu-latest

    env:
      AZURE_HOST: ${{ secrets.AZURE_HOST }}
      AZURE_USER: ${{ secrets.AZURE_USER }}
      AZURE_SSH_KEY: ${{ secrets.AZURE_SSH_KEY }}
      PROJECT_PATH: ${{ secrets.PROJECT_PATH }}

    steps:
      # Steps will be added in the next section
```


### **Add a Step to Create the SSH Key File**

Now you will turn `AZURE_SSH_KEY` (the environment variable) into an actual key file (`key.pem`) that the `ssh` command can use.

Inside the `steps:` list, add this as your **first real step**:

```yaml
    steps:
      - name: Set up SSH key
        run: |
          echo "$AZURE_SSH_KEY" > key.pem
          chmod 600 key.pem
```

### What this does:

* `echo "$AZURE_SSH_KEY" > key.pem`
  Takes the private key from the environment variable and writes it into a file named `key.pem`.

* `chmod 600 key.pem`
  Sets the correct permissions (only the owner can read/write).
  SSH will **refuse** to use the key if permissions are too open.

> 🔐 You are not exposing your key; the runner is temporary and the key is loaded from GitHub Secrets each run.


### **Add a Debug Step to Print the Host/User**

You can add a quick debug step to confirm that your secrets are being read correctly (without revealing the key).

Right after the SSH key setup step, add:

```yaml
      - name: Debug connection info (no secrets)
        run: |
          echo "Will try to connect to $AZURE_USER@$AZURE_HOST"
          echo "Project path on VM: $PROJECT_PATH"
```

This helps you:

* Confirm the values are not empty
* Confirm the environment hookup works

GitHub will print these in the Actions logs.


### **🔍 At This Point, Your `deploy` Job Should Look Like:**

Don’t copy-paste blindly; just compare structure:

```yaml
jobs:
  deploy:
    name: Deploy Pipeline to Azure
    runs-on: ubuntu-latest

    env:
      AZURE_HOST: ${{ secrets.AZURE_HOST }}
      AZURE_USER: ${{ secrets.AZURE_USER }}
      AZURE_SSH_KEY: ${{ secrets.AZURE_SSH_KEY }}
      PROJECT_PATH: ${{ secrets.PROJECT_PATH }}

    steps:
      - name: Set up SSH key
        run: |
          echo "$AZURE_SSH_KEY" > key.pem
          chmod 600 key.pem

      - name: Debug connection info (no secrets)
        run: |
          echo "Will try to connect to $AZURE_USER@$AZURE_HOST"
          echo "Project path on VM: $PROJECT_PATH"

      # Next: you'll add a real SSH command in the next part
```

Again: indentation matters a LOT in YAML. Keep it clean.



# 🌈 **Section 5.4 — Add the SSH Deploy Step (Pull Code + Docker Compose on Azure)**

In this part, you will:

* Add **one SSH step** to your `deploy` job
* That step will:

  * SSH into your Azure VM
  * Go to your project folder
  * Pull the latest code from GitHub
  * Rebuild and restart your Docker Compose stack

### **Add the SSH Deploy Step**

Open `.github/workflows/deploy.yml` and find your `steps:` block.

Right **after** the “Debug connection info” step, add a new step like this:

```yaml
      - name: Deploy latest version on Azure VM
        run: |
          ssh -i key.pem -o StrictHostKeyChecking=no "$AZURE_USER@$AZURE_HOST" "
            cd \"$PROJECT_PATH\" && \
            git pull && \
            docker compose pull && \
            docker compose build && \
            docker compose down && \
            docker compose up -d
          "
```

### **What this does:**

Inside the quotes, this runs **on your Azure VM**:

1. `cd "$PROJECT_PATH"`
   → Go into your project folder (where `docker-compose.yml` lives).

2. `git pull`
   → Fetch the latest code from your GitHub repo.

3. `docker compose pull`
   → Pull newer images if you’re using any from Docker Hub.

4. `docker compose build`
   → Rebuild your local images (extractor, transformer, etc.) based on your latest code.

5. `docker compose down`
   → Stop and remove the currently running containers.

6. `docker compose up -d`
   → Start everything again in the background (detached).

### **Why `-o StrictHostKeyChecking=no`?**

This flag:

```bash
-o StrictHostKeyChecking=no
```

tells SSH:

> “Don’t ask interactive questions about trusting this host. Just connect.”


### **Commit and Push**

After adding the deploy step:

Since this workflow triggers on **push to `main`**, you now have two options:

* If you pushed to a **feature branch** → open a PR, merge into `main`, CD runs
* If you pushed directly to `main`  → CD runs immediately

### **Watch the Deployment in GitHub Actions**

1. Go to your repo on GitHub
2. Click the **Actions** tab
3. Click your **“Deploy to Azure VM”** workflow
4. Open the latest run

You should see steps like:

* Set up SSH key
* Debug connection info
* Deploy latest version on Azure VM


### **Verify on the Azure VM**

SSH into your VM manually and check:

```bash
cd $PROJECT_PATH
docker compose ps
docker compose logs 
```

You should see:

* Containers rebuilt recently
* Services running (STATUS = “Up”)
* New behavior if you changed your app code


# 🌈 **Section 5.5 — HTTP Smoke Test After Deployment**

In this part, you’ll add a **single step** to your `deploy.yml` that:

* SSHes into your Azure VM
* Calls the **HTTP health URLs** for your services
* Fails the deployment if any service is not healthy

Because you already use Prometheus/Grafana, each service should have **some HTTP endpoint** like `/health`, `/metrics`, `/ready`, etc.


### **List Your Health URLs**

First, you must decide which URLs you want to check.

On your VM (or from your notes), list the health endpoints. Examples (you must fill in your real ones):

* Streamlit UI:
  `http://localhost:8501/health`
* Extractor service:
  `http://localhost:8001/health` or `/metrics`
* Transformer service:
  `http://localhost:8002/health`
* Cleaner service:
  `http://localhost:8003/health`
* MinIO (already has one):
  `http://localhost:9000/minio/health/ready`

👉 **You must:**

* Decide the exact URL + port for each critical service
* Write them down in your notebook (this is your smoke test checklist)


### **Add a Single HTTP Smoke Test Step to `deploy.yml`**

Open `.github/workflows/deploy.yml` and find your `deploy` job.

You should already have:

* SSH key step
* Debug step
* Deploy step that does: `git pull`, `docker compose … up -d`

Right **after** the deploy step, add this **HTTP smoke test** step:

```yaml
      - name: Smoke test – HTTP health checks
        run: |
          ssh -i key.pem -o StrictHostKeyChecking=no "$AZURE_USER@$AZURE_HOST" '
            set -e

            cd "$PROJECT_PATH"

            echo "🔍 Checking Streamlit health..."
            curl -f http://localhost:8501/health

            echo "🔍 Checking Extractor health..."
            curl -f http://localhost:8001/health

            echo "🔍 Checking Transformer health..."
            curl -f http://localhost:8002/health

            echo "🔍 Checking Cleaner health..."
            curl -f http://localhost:8003/health

            echo "✅ All HTTP health checks passed."
          '
```


### **What this does:**

* `ssh -i key.pem ...` → logs into your VM
* `cd "$PROJECT_PATH"` → goes to your project folder (optional, but consistent)
* `set -e` → “if any command fails, stop and exit with error”
* Each `curl -f ...`:

  * Makes an HTTP request to the service
  * Fails the whole step if:

    * status code is 4xx or 5xx
    * the service is not reachable

If one service is **down or broken**, this step fails → your deployment run is marked ❌.


### **Commit and Push**

Once you’ve customized all URLs push them to your ```.github/workflows/deploy.yml```

Trigger CD by:

* Merging a PR into `main`, or
* Pushing a small change directly to `main` (less ideal, but works)

### **Inspect the Smoke Test Output in GitHub Actions**

Go to:

* **Actions → Deploy to Azure VM → Latest run**

Open the step:

> `Smoke test – HTTP health checks`

You should see something like:

```text
🔍 Checking Streamlit health...
<some response, but curl is quiet if OK>

🔍 Checking Extractor health...
...

✅ All HTTP health checks passed.
```

If something fails, you might see:

```text
curl: (7) Failed to connect to localhost port 8002: Connection refused
Error: Process completed with exit code 7.
```

That tells you exactly which service is unhealthy.


# 📝 **Final CI/CD Assignment**

Your job is to prove that your **entire CI/CD pipeline works end-to-end**:

Local → GitHub → CI → Merge → CD → Azure → Smoke Test → Working Pipeline


## 🧪 **PART 1 — CI Validation**

###  **Make a small, safe change**

(e.g., update README or add a comment)

### **Push to a new branch**

```
git checkout -b ci-test
git commit -m "CI test"
git push --set-upstream origin ci-test
```

### **Open a Pull Request into `main`**

### **Wait for CI to finish**

All jobs must pass:

* build
* docker-validation
* sanity-check

### 📸 **Screenshot #1**

PR page showing **all CI checks passed**.


## 🚀 **PART 2 — CD Deployment**

### **Merge the PR into `main`**

(Merge allowed only if CI passed.)

### **CD workflow should run automatically**

It should show green checks for:

* SSH setup
* Deploy step
* HTTP smoke test

### 📸 **Screenshot #2**

Actions → Successful CD run
Include the smoke test output.


## 🖥️ **PART 3 — Verify Deployment on Azure**

SSH into your VM:

```
ssh <AZURE_USER>@<AZURE_HOST> -i <your-private-key>
cd <PROJECT_PATH>
docker compose ps
```

All services should be **Up**.


### 📸 **Screenshot #3**

Your VM terminal showing `docker compose ps`



##  📔**Reflection Section**

Write short, clear answers in **2–4 sentences each**.
This entire section must be submitted along with your screenshots.

**1. Which 3 CI checks are MOST critical for your project and why?**

**2. What broke first in your CI pipeline, and how did you fix it?**
(Be specific: import issue, build error, Docker path, indentation, etc.)

**3. Why should deployment run *only* when the `main` branch is updated?**

**4. What would happen if you accidentally pasted your *public key* instead of your private key into `AZURE_SSH_KEY`?**

**5. Why must the SSH key be given permission `600`?**

**6. Why do we load secrets using `${{ secrets.NAME }}` instead of hardcoding values into the workflow?**

**7. After your first successful deploy, what commands did GitHub actually run on your VM via SSH?**

**8. What improvement would you add to your deploy step in the future?**

**9. Why is the HTTP smoke test more reliable than “container is running”?**

**10. How does the HTTP health check catch issues that Docker cannot?**

