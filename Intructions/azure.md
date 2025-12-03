# **GitHub + Azure VM Setup**

# **🌟Introduction**

This is where we take your entire ML pipeline — extractor (Go), transformer & cleaner (Python), DuckDB, Streamlit UI, Prometheus, Grafana - and move it into a **professional workflow**.

Right now, your project lives only inside your Ubuntu VM. If that VM crashes or you lose access, everything disappears. Real engineers never rely on a single machine, they use:

* **Git** → to track every change
* **GitHub** → to store the project safely online
* **Cloud VMs** → to run the system from anywhere


Here is the **next section**, written in the same clear, student-friendly, concise style.



# **🤝1. What Are Git and GitHub?**

Before we start typing commands, let’s quickly understand the tools we’re using.
This will be short, simple, and practical.

## **⏳1.1 Git — Your Code’s “Time Machine”**

Git is a version control system.
Think of it like *save checkpoints* in a game:

* You can see what changed
* You can go back to older versions
* You can track exactly who did what
* You never lose progress by mistake

You will use Git to track every part of your pipeline — extractor, transformer, cleaner, Streamlit app, Docker files, etc.

**Key idea:**

> Git helps you manage your code as it grows, changes, and improves.


## **🏠1.2 GitHub — Your Online Code Home**

GitHub is a website that stores Git repositories online.
It is where almost every professional data engineer and developer stores their work.

GitHub lets you:

* Back up your project safely
* Work from any computer
* Collaborate with teammates
* Run automated tests and deployments
* Share your code with employers or other students

**Key idea:**

> GitHub keeps your project safe, organized, and easy to deploy.

# **📂2. GitHub Repository & Project Structure**


## **2.1 Create a New GitHub Repository**

Follow these steps:

1. Go to **[https://github.com](https://github.com)** and log in

2. Click the **+** icon (top-right) → **New repository**

3. Fill the details:

   * **Repository name**:
     `crash-pipeline`
     (or anything you like)
   * **Description**:
     “Full DE/ML pipeline (Extractor + Transformer + Cleaner + Streamlit + Docker)”
   * **DO NOT** add:
     * README
     * .gitignore
     * License
       (we’ll add these manually)

4. Click **Create repository**

You now have an empty GitHub repo ready to receive your full project.


## **2.2 Recommended Project Folder Structure**

Your pipeline has many components.
A clean structure helps you, your classmates, and future teammates instantly understand the project.

Use this layout:

```
Pipeline/
│
├── extractor/               # Go extractor (bronze layer)
├── transformer/             # Python transformer (silver layer)
├── cleaner/                 # Python cleaner (gold layer)
├── streamlit-app/           # Streamlit UI
├── docker-compose.yaml      # Runs all services
├── .env.sample              # Template for environment variables
├── .gitignore               # Files Git should NOT track
├── backfill.json            # DO NOT upload
├── streaming.json           # DO NOT upload
├── minio-data/              # DO NOT upload
├── prometheus_data/         # DO NOT upload
├── grafana_data/            # DO NOT upload
├── duckdb-data/             # DO NOT upload
└── README.md                # Overview of the project
```

This is **industry-standard**.
Every engineer should be able to navigate this instantly.

---

## **2.3 Create a Proper `.gitignore`**

You must prevent sensitive or unnecessary files from being committed.


> Indide your Ubuntu VM
Create a file:

```
Pipeline/.gitignore
```

Paste this inside:

```
# Python
# Python
__pycache__/
*.pyc
venv/

# Go
bin/
*.exe

# Environment + Secrets
.env
.env.local

# Data folders (should NEVER go to GitHub change accordingly)
minio-data/
prometheus_data/
grafana_data/
duckdb-data/

# Databases & Binary data
*.duckdb
*.wal
*.db

# Models
*.pkl
*.joblib

# Logs
*.log

# OS / Editor
.DS_Store
.vscode/
.idea/
```

Why this matters:

* `.env` must never go to GitHub
* DuckDB & WAL files can be huge and should stay local
* Model files (pkl/joblib) can get large and shouldn’t be versioned
* Grafana/Prometheus/MinIO data should stay on the VM

This keeps your repo clean and safe.


## **2.4 Write a Detailed README.md**

Your README is a **required deliverable**.
It must explain your entire project clearly, and it must include screenshots or recordings of your pipeline running.

Most hiring managers, recruiters, and engineers will ONLY look at your README—so this is where you show that you understand the pipeline end-to-end.

## **📌 What Your README MUST Include**

Make a readme that you can be proud of, you must ensure the README contains the following:

### **1. A clear explanation of your pipeline**

Explain:

* What problem your pipeline solves
* Which APIs/datasets you used
* How data moves through the system
* What the ML model predicts
* What the Streamlit app can do

This should be written in simple, understandable English.
Do not paste code here - explain the *concepts*.


### **2. A full walkthrough of each pipeline component**

For each part, write a short description of its purpose:

* **Extractor (Go)** → pulls raw crash/vehicle/people data into MinIO
* **Transformer (Python)** → merges and cleans into Silver CSVs
* **Cleaner (Python)** → applies cleaning logic and writes to DuckDB Gold
* **Streamlit app** → trains model, predicts outcomes, visualizes results
* **Docker Compose** → launches MinIO, Prometheus, Grafana, and Streamlit
* **Monitoring** → metrics exposed by your extractor/transformer/cleaner

Write 2–4 sentences per component.


### **3. High-quality screenshots or video demonstrations**

You MUST include screenshots or a short screen recording of:

* Running extractor
* Running transformer
* Running cleaner
* Streamlit app (home page, train model page, prediction page)
* DuckDB tables (shown in CLI or a notebook)
* Grafana dashboards showing metrics
* Prometheus target list (showing your services)

If you don’t have screenshots/video from earlier, **record them again now**.

This visual proof is extremely important.


### **4. An architecture diagram**

#### **Recommended diagram tools:**

* **Excalidraw** (free, simple): [https://excalidraw.com](https://excalidraw.com)
* **Mermaid Live Editor** (diagram-as-code): [https://mermaid.live](https://mermaid.live)
* **Draw.io / Diagrams.net** (very common): [https://app.diagrams.net](https://app.diagrams.net)
* **Canva** (clean and modern): [https://www.canva.com/](https://www.canva.com/)
* **Figma** (great for professional diagrams): [https://www.figma.com/](https://www.figma.com/)

Keep the diagram simple:

* Extractor → MinIO → Transformer → Cleaner → DuckDB → Streamlit
* Metrics → Prometheus → Grafana

This visual alone makes your README much more professional.


### **5. How to run your pipeline (step-by-step instructions)**

Write instructions for:

1. Cloning the repository
2. Creating `.env`
3. Setting up required folders
4. Running:

```
docker compose up -d
```

5. Accessing:

   * Streamlit (`http://localhost:8501`)
   * Grafana (`http://localhost:3000`)
   * Prometheus (`http://localhost:9090`)

You must explain running the whole system in **their own words**, not copying from instructors.


### **6. Any improvements or extra features you added**

Even small ones count:

* Extra ML features
* Additional metrics
* Data cleaning logic
* New Streamlit pages
* Custom dashboards
* Model comparison

These help show creativity and initiative.


### **7. Lessons learned / challenges section (short)**

Write a few bullet points about:

* What was difficult
* What you learned
* What you would improve if you had more time

This helps demonstrate understanding and reflection.

### **For saving/uploading images:**

* Put images inside a folder: `README-assets/`
* Then reference them in Markdown:

  ```
  ![screenshot](README-assets/extractor.png)
  ```


# **🐧3. Set Up Git on Your Ubuntu VM**

Before you can push your pipeline to GitHub, your VM needs Git installed and configured.
This section walks you through everything - even if you’ve never used Git before.


## **3.1 Install Git (if not installed already)**

Run this in your terminal:

```bash
sudo apt update
sudo apt install git -y
```

Check that it installed correctly:

```bash
git --version
```

If you see something like `git version 2.X.X`, you're good.


## **3.2 Configure Your Git Identity**

Git needs your name and email so your commits have an identity.

Run:

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@tamu.edu"
```

🔹 Use your **TAMU email** or the email linked to your GitHub account.
🔹 These values will appear in your GitHub commit history.

You can check your settings:

```bash
git config --list
```

## **3.3 Navigate to Your Project Folder**

Most students will have their project in the pipeline folder if not adjust accordingly:

```bash
cd ~/Pipeline
```
Confirm you're in the right place:

```bash
ls
```

You should see something similar to:

```
backfill.json   cleaner    docker-compose.yaml   extractor
minio-data/     transformer   grafana_data/   streamlit/
prometheus_data/  frontend/   duckdb-data/
```


## **3.4 Initialize Git in Your Project Folder**

This turns your project directory into a Git repository.

Run:

```bash
git init
```

You now have a hidden `.git` folder that tracks changes.

Check the status:

```bash
git status
```

At this point, Git will show many files as “untracked”.
This is normal — we will add only the correct files in the next steps.


## **3.5 Ensure Your `.gitignore` Is in Place**

Before adding ANY code to Git, make sure your `.gitignore` file exists 

This prevents you from accidentally uploading gigabytes of data or sensitive files.

Check it:

```bash
cat .gitignore
```

If you forgot to create it, stop and go back to Section 2.3.

## **3.6 Stage All Code Files (except ignored ones)**

Run:

```bash
git add .
```

Git will automatically ignore everything listed in `.gitignore`.

Verify what will be committed:

```bash
git status
```

You should see only code/config files — **no** large folders, **no** `.env`, **no** `.duckdb`, **no** data folders.

If something appears that shouldn’t be committed, add it to `.gitignore`, then run:

```bash
git reset <file>
```

## **3.7 Commit Your Project**

Now create your first commit:

```bash
git commit -m "Initial commit: full DE/ML pipeline"
```

This locks the current version of your project into Git.

Here is **Section 4 – Connecting Your VM to GitHub Using SSH Keys**, written step-by-step, detailed, but still simple and student-friendly.


# **🔐4. Connect Your VM to GitHub Using SSH Keys**

To push your code from your VM to GitHub, you need a **secure connection**.
The best way is using **SSH keys** — this lets your VM talk to GitHub without typing passwords.

This is the same method used by real companies and DevOps teams.

Follow the steps exactly.


## **4.1 Check if You Already Have SSH Keys**

Run:

```bash
ls ~/.ssh
```

If you see files like:

```
id_ed25519
id_ed25519.pub
```
Then you already have keys.
If not - we will create them.

(If you're unsure, just keep following the steps.)


## **4.2 Generate a New SSH Key Pair**

Run this command:

```bash
ssh-keygen -t ed25519 -C "your-email@tamu.edu"
```

When it asks for a file path:

```
Enter file in which to save the key (/home/user/.ssh/id_ed25519):
```

Just press **Enter**.

When it asks for a passphrase:

```
Enter passphrase (empty for no passphrase):
```

Press **Enter** again.

### After this, Git creates two files:

* `id_ed25519` → **private key** (do NOT share)
* `id_ed25519.pub` → **public key** (safe to share)


## **4.3 Copy Your Public Key**

Run:

```bash
cat ~/.ssh/id_ed25519.pub
```

This prints one long line starting with:

```
ssh-ed25519 AAAA...
```

**Copy the entire line** to your clipboard.


## **4.4 Add Your Key to GitHub**

1. Go to **[https://github.com](https://github.com)**
2. Click your profile → **Settings**
3. Left sidebar → **SSH and GPG keys**
4. Click **New SSH key**
5. Title:
   `Ubuntu VM`
6. Key type:
   **Authentication Key**
7. Paste your key into the box
8. Click **Add SSH key**

GitHub now allows your VM to push code without needing a password.

## **4.5 Test Your Connection**

Go back to your VM and run:

```bash
ssh -T git@github.com
```

You should see:

```
Hi <your-username>! You've successfully authenticated, but GitHub does not provide shell access.
```

If you see this message — congratulations!
Your VM is now securely connected to GitHub.


## **4.6 Add the GitHub Repo as Your “Remote”**

Now you need to tell your VM *which* GitHub repo to push to.

In your `~/Pipeline` folder, run:

```bash
git remote add origin git@github.com:<your-github-username>/<your-repo-name>.git
```

Example:

```bash
git remote add origin git@github.com:john-doe/crash-pipeline.git
```

Check it:

```bash
git remote -v
```

You should see your GitHub repo URL for `origin`.


## **4.7 Push Everything to GitHub**

Run:

```bash
git branch -M main
git push -u origin main
```

Your entire DE/ML pipeline is now safely uploaded to GitHub.

Refresh your GitHub repo — you should see all your folders (extractor, transformer, cleaner, streamlit, docker-compose, etc.) but **NOT**:

* `minio-data/`
* `grafana_data/`
* `prometheus_data/`
* `duckdb-data/`
* `.env`
* `.duckdb`/`.wal`
* large binary files

If any of these show up, your `.gitignore` is wrong — fix it and push again.

# ⚠️ **5. Azure: IMPORTANT — How to Create Your Account**

## 🚨 **READ THIS BEFORE YOU SIGN UP**

**Do NOT create your Azure for Students account directly with your university email.**
Many universities (including TAMU) have region restrictions that **BLOCK you from creating VMs in the popular regions** like **East US, West US, Central US**, etc.
If you create the account using your school email as the *main login*, Azure may **lock your subscription region**, which breaks all later steps in the project.

👉 **To avoid this problem, follow the instructions below EXACTLY.**

## **5.1 Correct Method: Use Your Personal Account → THEN Link Your School Email**

### **1. Open the Azure for Students page**

👉 [Azure for students](https://azure.microsoft.com/free/students)

### **2. Click “Start Free”**

### **3. Sign in with your *personal* Microsoft account**

✔ Gmail or Outlook personal account
❌ Do NOT use your `.edu` account here

### **4. Azure will ask for student verification**

Here you must enter your **school email** (e.g., `netid@tamu.edu`) — but only for verification.

✔ Your personal account = **login identity**
✔ Your school email = **verification identity**

This gives you:

* Full Azure for Students benefits
* **No region restrictions on VM creation**
* No credit card required
* $100 free credit

### **5. When verification succeeds**

You will see:

* **“You now have Azure for Students”**
* **$100 credit activated**
* VM creation allowed in multiple major regions


## **🔥 Why This Is SO IMPORTANT** 

If you accidentally sign up *using* your school email as the Azure account:

❌ You may NOT be able to create VMs in:

* East US
* West US
* Central US
* South Central US

❌ You may be restricted to slow or unusable regions
❌ You may get “Quota unavailable” or “Region not supported” errors
❌ You may have to wait days for Azure support to fix it
❌ You will not be able to complete your class project properly

**Using a personal account avoids ALL these problems.**


## **5.2 First Look at the Azure Portal**

**Goal of this step:**
You don’t need to become Azure experts, you just need to know where the things they care about live.


> When you go to `https://portal.azure.com`, this is your **control panel** for everything in Azure.

Have them do:

1. Go to [Azure Portal](https://portal.azure.com)
2. On the left/top, you should briefly locate:

   * **“Resource groups”**
   * **“Virtual machines”**
   * **“Cost Management + Billing”**


## **5.3 Create Your Azure Resource Group + Ubuntu VM**

In this part, you will create:

* A **Resource Group** (your project folder in Azure)
* An **Ubuntu Virtual Machine** (your cloud server)

Follow the instructions **exactly as written**.
Do **not** skip any step.


## **A. Create Your Ubuntu Virtual Machine**

Now you will create the actual Ubuntu VM where your pipeline will run.

This VM is your **remote Linux computer** in the cloud.


1. In the Azure portal search bar, type:
   **Virtual machines**

2. Click **Virtual machines**.

3. Click the **Create** button at the top.

4. Choose **Virtual machine**.

Azure will now open a multi-tab wizard.
You will fill out each tab.

## **Tab 1 — Basics**

### **Project details**

* **Subscription:**
  Select **Azure for Students**
 

* **Resource group:**
Keep it empty (so it autocreates)
### **Instance details**

* **Virtual machine name:**
  `crash-pipeline-vm`

* **Region:**
Choose a region that lets you choose the right sized machine(such as b2s or b2ls_v2 etc)
  *` West US 2` worked best during testing

* **Image:**
  From the dropdown, select:
  **Ubuntu Server 24.04 LTS – x64 Gen2**

### **Size (choose one)**

Click **Change size**.

You must choose one that uses less Cost/month, try to find a size thats under 35$ a month

Change the region to get more/less options

### **Administrator Account**

* **Authentication type:**
  Choose **SSH public key**

* **Username:**
  Type exactly:
  `azureuser`

### **SSH Key**

Under *SSH public key source*:

* Select **Generate new key pair** and select RSA SSH Format

* Name it:
  `azure_key`


## **Tab 2 — Disks**

Do **NOT** change anything.
Click **Next: Networking**.


## **Tab 3 — Networking**

Do **NOT** change anything.
Ensure especially:

* Public IP = **Enabled**
  (You need this to SSH later.)
  Click on **Create New** and give it a name and make it zone redundant  keeping the rest default

**Everything can stay as-is.**

Click **Review + create**.


After validation succeeds:

* Click **Create**


After you click Create , Azure will give you a file:

```
azure_key.pem
```

You MUST download this file.

You MUST keep it safe.

You MUST NOT lose it.

You MUST NOT share it with anyone.

This file is your private key to access your cloud server.

Wait for the deployment to finish (around 1–3 minutes).


## **B. Get Your VM’s Public IP**

On your VM’s Overview page, look for:

**Public IP Address or Primary NIC public IP**

It looks like:

```
52.176.140.23
```

Copy this — you will use it in the next step to SSH from your local machine into your cloud VM.


## **5.4 Connect to Your Azure VM Using SSH**

Now that your Azure VM is created, your next task is to **log into it** from your local laptop or desktop.
This is how you will control your cloud server just like any Linux machine.

You will use the private key file:

```
azure_key.pem
```

that you downloaded when creating the VM.

⚠️ **If you lose this file, you CANNOT access your VM.**
You must delete the VM and create a new one.

## **A. Connect to Your VM (SSH Command)**

In your terminal (Mac, Linux, WSL) or Bash (Windows), run:

```bash
ssh -i ./azure_key.pem azureuser@<YOUR_PUBLIC_IP>
```

Example:

```bash
ssh -i ./azure_key.pem azureuser@20.85.113.47
```

### **If this is your first time connecting**, SSH will ask:

```
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Type:

```
yes
```

Then press Enter.

If everything is correct, you will see a welcome banner like:

```
Welcome to Ubuntu 24.04 LTS
azureuser@crash-pipeline-vm:~$
```

This means:

🎉 **You are now inside your cloud VM.**


## **B. Verifying Inside the VM**

Once connected, run:

```bash
ls
```

You should see an empty home folder (since nothing is installed yet).

Check your OS version:

```bash
lsb_release -a
```

Check your username:

```bash
whoami
```

It must show:

```
azureuser
```


## **5.5 Prepare Your Azure VM**

At this point you are logged into your Azure VM as:

```
azureuser@crash-pipeline-vm:~$
```

Your goal in this section is to install all the required tools your pipeline needs to run:


## **A. Update Your VM**

Before installing anything, update the package list:

```bash
sudo apt update
sudo apt upgrade -y
```

This ensures your VM has the latest security patches and avoids weird errors.


## **B. Install Git**

Run:

```bash
sudo apt install git -y
```

Verify:

```bash
git --version
```

If you see a version number → Git is installed.


## **C. Install Docker**

Your pipeline uses Docker for MinIO, Streamlit, Prometheus, Grafana, etc.
You must install Docker first.

1. **Install prerequisite packages**
    ```bash
    sudo apt install apt-transport-https ca-certificates curl software-properties-common
    ```

2. **Add Docker’s official GPG key**
    ```bash
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    ```

3. **Set up the stable Docker repository**
    ```bash
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
      https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    ```

4. **Update the package index again**
    ```bash
    sudo apt update
    ```

5. **Install Docker Engine**
    ```bash
    sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

6. **Verify Docker Installation**
    ```bash
    sudo docker run hello-world
    ```

If Docker is correctly installed, you'll see a confirmation message displaying the successful run of the Docker test image.

## **🚨 Additional Setup: Managing Docker as a Non-root User**

To run Docker without needing `sudo`, add your user to the Docker group:

```bash
sudo usermod -aG docker ${USER}
newgrp docker
```

🔴 IMPORTANT:
You MUST log out and log back in for this change to apply.

To log out, run:

```bash
exit
```

Then reconnect:

```bash
ssh -i ~/azure_key.pem azureuser@<YOUR_PUBLIC_IP>
```

### **Verify Docker works**

```bash
docker ps
```

You should NOT see any permission errors.


## **D. Install Python + pip (Needed for transformer, cleaner, Streamlit)**

Run:


```bash
sudo apt install python3 python3-pip -y
```

Check versions:

```bash
python3 --version
pip3 --version
```


## **E. Install Go**

Azure usually has Go in the default repository:

```bash
sudo apt install golang -y
```

Verify:

```bash
go version
```

If this prints a version (e.g., go1.20 or go1.21) → you're set.


## **5.6 Clone Your GitHub Repository Onto the Azure VM**

Now that your Azure VM has Git, Docker, Python, and Go installed, the next step is to **download your entire pipeline code from GitHub into the VM**.

This is how your Azure machine will get the extractor, transformer, cleaner, docker-compose.yaml, and Streamlit app.

You will clone using **SSH**, which you already set up earlier.

Follow these instructions exactly.


## **A. Confirm SSH Access to GitHub Works on Your VM**


1. Ensure your SSH key exists:

```bash
ls ~/.ssh
```

You must see:

```
id_ed25519
id_ed25519.pub
```
if not go back up when you setup git keys for the local VM and create a new key for azurevm

2. Ensure your **public key** (`id_ed25519.pub`) is added to **GitHub → Settings → SSH keys**.

3. Ensure correct permissions:

```bash
chmod 600 ~/.ssh/id_ed25519
```

Run this inside your Azure VM:

```bash
ssh -T git@github.com
```

If SSH is correctly set up, you should see:

```
Hi <your-username>! You've successfully authenticated...
```

If you get “Permission denied (publickey)” → repeat the same setup you did for local VM(SSH keys)


## **B. Navigate to the Folder Where You Want Your Project**


## **C. Clone Your GitHub Repository**

Run:

```bash
git clone git@github.com:<your-username>/<your-repo>.git
```

Example:

```bash
git clone git@github.com:john-doe/crash-pipeline.git
```

**Important:**
You MUST use the **SSH URL** (`git@github.com:...`), not the HTTPS one.


## **D. Enter Your Project Folder**

Once cloning finishes, run:

```bash
cd <your-repo>
```

Example:

```bash
cd crash-pipeline
```

Verify contents:

```bash
ls
```

You should now see your folders, for example:

```
extractor-go/
transformer/
cleaner/
streamlit/
docker-compose.yaml
README.md
```

**If you see your entire code here — good job, your repo was cloned successfully.**

If your repo contains large folders like:

```
minio-data/
grafana_data/
duckdb-data/
prometheus_data/
```

STOP — your `.gitignore` is wrong.
You MUST fix it and re-push from your local VM.

## **E. Check Git Remote URL**

Run:

```bash
git remote -v
```

You MUST see the SSH remote:

```
origin  git@github.com:<your-username>/<repo>.git (fetch)
origin  git@github.com:<your-username>/<repo>.git (push)
```

If you see an HTTPS URL, fix it:

```bash
git remote set-url origin git@github.com:<your-username>/<repo>.git
```

## **5.7 Create Your `.env` File and Required Folders on the Azure VM**

Now that your code is inside the Azure VM, you need to prepare the **runtime environment** so your pipeline can start successfully.

Your `docker-compose.yaml` expects certain folders and environment files to exist.
If these are missing → Docker will fail to start.

## **A. Create Your `.env` File**

Inside your Azure VM, navigate to your project folder:

```bash
cd ~/crash-pipeline
```
(or whatever your repo name is)

Every project contains a `.env.sample` file.
This is your template.

### **Step 1 — Copy the sample file**

Run:

```bash
cp .env.sample .env
```

Now you have a real `.env` file that Docker will use.

### **Step 2 — Edit the `.env` file**

Open it with Nano:

```bash
nano .env
```

Fill in the required values:

* MinIO credentials
* MinIO endpoint
* Ports (if configured)

**IMPORTANT:**
Keep all values EXACTLY the same format as your working local VM.

When done, press:
```
CTRL + O  (write out)
Enter     (confirm)
CTRL + X  (exit)
```

⚠️ **Do NOT push `.env` to GitHub — it contains credentials.**
It stays only on your Azure VM.


## **B. Create All Required Folders**

Your pipeline uses several containers that expect persistent storage folders.

You must create them manually on your Azure VM.

Run these commands or simmilar based on your setup:

```bash
mkdir -p minio-data
mkdir -p prometheus_data
mkdir -p grafana_data
mkdir -p duckdb-data
```

This ensures:

* MinIO can store raw data
* Prometheus can store metrics
* Grafana can store dashboards
* DuckDB can store your Gold tables


## **C. Confirm the Folder Structure with the Ubuntu VM(local)**


## **D. Check Docker Compose for Folder Paths**

Open your `docker-compose.yaml`:

```bash
cat docker-compose.yaml
```

Look for sections like:

```
volumes:
  - ./minio-data:/data
  - ./grafana_data:/var/lib/grafana
  - ./prometheus_data:/prometheus
  - ./duckdb-data:/app/data
```

You MUST make sure:

1. The left side of each volume is a folder you created
2. Paths match exactly (case-sensitive)
3. Your `.env` file variables match what the compose file expects

If something does not match → fix it before continuing.



## **5.8 Fix Permissions for Persistent Storage**

Your Docker containers (especially MinIO, Grafana, and DuckDB) expect to read/write to specific folders.
Azure VMs sometimes assign restrictive permissions, which can cause containers to fail immediately.

You must fix permissions **before the first run**.



## **A. Go to your project folder**

```bash
cd ~/crash-pipeline
```

(Or whatever your repo name is.)


## **B. Ensure all required folders exist**

You should already have created these:

```bash
minio-data/
grafana_data/
prometheus_data/
duckdb-data/
```

Verify:

```bash
ls -d minio-data grafana_data prometheus_data duckdb-data
```

If any folder is missing, create it:

```bash
mkdir -p minio-data grafana_data prometheus_data duckdb-data
```

## **C. Assign Correct Ownership and Permissions**

### **1. Give ownership to the current user (azureuser)**

```bash
sudo chown -R $USER:$USER minio-data grafana_data prometheus_data duckdb-data
```

### **2. Give write permissions (required by Docker containers)**

```bash
chmod -R 755 minio-data grafana_data prometheus_data duckdb-data
```

### **3. Grafana requires *special* ownership**

Grafana runs as user **UID 472**, so you MUST assign grafana_data to that UID:

```bash
sudo chown -R 472:472 grafana_data
```

If you skip this step, Grafana will crash instantly with errors like:

```
permission denied
failed to write to disk
```

## **D. Confirm Folder Permissions**

Run:

```bash
ls -ld minio-data grafana_data prometheus_data duckdb-data
```

You should see readable/writable directories.


## **5.9 Open the Required Ports on Azure (You MUST Do This Before Running Anything)**

Azure VMs **block all incoming connections** except SSH (port 22).
This means NONE of your services — Streamlit, Grafana, Prometheus, MinIO — will be visible until you manually open the correct ports.

This step is REQUIRED.
If you skip it, your pipeline will appear “broken” even though it is running.

Follow these steps exactly.


## **A. Go to Your VM’s Networking Settings**

1. Go to the Azure Portal:
   👉 [https://portal.azure.com](https://portal.azure.com)

2. In the search bar at the top, type:
   **Virtual machines**

3. Click on your VM:
   `crash-pipeline-vm`

4. In the left-hand menu, click **Networking**

You are now on the page that controls which ports are open to the internet.


## **B. Add Inbound Port Rules for ALL Required Services**

Your project uses several web interfaces that require specific ports.

You will open these one by one.

Click the **“Add inbound port rule”** button.



## **1. Streamlit (port 8501)**

* **Destination port ranges:** `8501`
* **Protocol:** TCP
* **Action:** Allow
* **Priority:** 300
* **Name:** `streamlit`

Click **Add**.


## **2. Grafana (port 3000)**

* **Destination port ranges:** `3000`
* **Protocol:** TCP
* **Action:** Allow
* **Priority:** 301
* **Name:** `grafana`

Click **Add**.


## **3. Prometheus (port 9090)**

* **Destination port ranges:** `9090`
* **Protocol:** TCP
* **Action:** Allow
* **Priority:** 302
* **Name:** `prometheus`

Click **Add**.



## **5. MinIO Console (port 9001)**

* **Destination port ranges:** `9001`
* **Protocol:** TCP
* **Action:** Allow
* **Priority:** 304
* **Name:** `minio-console`

Click **Add**.


# **6. Any custom ports you use**

If you aren’t using custom ports, skip this step.


Do NOT delete or modify port 22.
If you remove 22, you will lose access to your VM and must recreate it.

## **Security Note**

These ports are meant for:

* Classroom projects
* Learning how cloud VMs work
* Temporary systems

In real production systems, these ports would be protected behind firewalls and authentication.

# **📘 Assignment: Full Pipeline Verification on Azure VM**

Your job is to prove that your Azure VM runs the **exact same end-to-end pipeline** as your local VM.


## **1. Start your full pipeline on Azure**

Start all services exactly as you did locally.
Make sure every container starts without errors.

## **2. Verify all services load in the browser**

Using your VM public IP, confirm:

* Streamlit (port 8501) opens and all features work
* Grafana (port 3000) loads and dashboards work
* Prometheus (port 9090) loads and shows metrics
* MinIO (port 9000/9001) loads and shows buckets/files

If any service fails to load → fix ports or container config.


## **3. Run a complete pipeline execution (Run #1)**

Trigger a full ETL + ML pipeline run:

* Extractor pulls data into MinIO
* Transformer produces cleaned data
* Cleaner updates DuckDB Gold
* Streamlit loads your model and predicts

Check that the behavior matches your local VM.

## **4. Run a second full pipeline execution (Run #2)**

Repeat the entire pipeline again.

Confirm:

* Incremental updates work
* No duplicated or missing files
* Gold tables persist
* ML predictions still work

This proves your cloud pipeline is stable.


## **5. Inspect and compare logs**

Check logs from:

* Extractor
* Transformer
* Cleaner
* Streamlit
* Prometheus

Make sure no unexpected errors appear.
Note any differences from local runs.



## **6. Confirm persistent storage works**

Verify that after both runs:

* MinIO keeps your raw/silver files
* DuckDB Gold data stays intact
* Grafana dashboards persist
* Prometheus still holds metrics

If anything resets on restart → fix your volume setup.



## **7. Document everything in your README**

Your README must include:

* Short summary of your Azure setup
    * VM configuration
    * Ports opened
    * Folder structure
    * Any differences from local

If you want to improve your portfolio, record a **30–60 second video** showing your pipeline running live on Azure or take generous photos.


## **Deliverables**

Submit:

* **Updated README.md** with screenshots
* **Evidence of 2 complete pipeline runs on Azure**
* **Short explanation comparing local vs cloud behavior**