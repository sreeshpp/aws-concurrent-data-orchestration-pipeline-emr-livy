# Building a Concurrent Data Orchestration Pipeline Using Amazon EMR and Apache Livy
This code demonstrates the architecture featured on the AWS Big Data blog (<link>)
which creates a concurrent data pipeline by using Amazon EMR and Apache Livy. This pipeline is orchestrated by Apache Airflow.

## Local LinkedIn Job Agent

A **local background agent** that checks LinkedIn every hour and alerts you when new jobs appear. No Airflow or cloud setup required — it runs on your machine.

### What it watches

| Profile | Criteria |
|---------|----------|
| `remote_india` | Remote Senior Data Engineer roles (and similar titles) in India |
| `kochi` | Similar data-engineer titles in Kochi, Kerala |
| `trivandrum` | Similar data-engineer titles in Thiruvananthapuram (Trivandrum) |

Only **new** postings trigger alerts. State is stored locally at `~/.local/share/job-monitor/`.

### Quick start

```bash
chmod +x scripts/job-agent

# Optional: copy and edit local config
mkdir -p ~/.config/job-monitor
cp config.env.example ~/.config/job-monitor/config.env

# Run a single check now
./scripts/job-agent run-once

# Start the local agent (checks every 1 hour in the background)
./scripts/job-agent start

# Check status / stop
./scripts/job-agent status
./scripts/job-agent stop
```

### Local alerts (default)

When new jobs are found, the agent:

1. Shows a **desktop notification** (Linux: `notify-send`, macOS: native notification)
2. Appends details to **`~/.local/share/job-monitor/alerts.log`**
3. Logs activity to **`~/.local/share/job-monitor/agent.log`**

### Optional: Slack or email

Add to `~/.config/job-monitor/config.env`:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
# or
ALERT_EMAIL_TO=you@example.com
SMTP_HOST=smtp.gmail.com
SMTP_USER=you@example.com
SMTP_PASSWORD=your-app-password
```

### Alternative deployments

| Method | When to use |
|--------|-------------|
| **Local agent** (`./scripts/job-agent start`) | Default — runs on your laptop/desktop |
| systemd timer (`scripts/job-monitor.timer`) | Linux server without keeping a process running |
| Airflow DAG (`dags/linkedin_job_monitor_dag.py`) | If you already use Airflow in this repo |

## Resume Analysis Chatbot Agent

An **LLM-powered chatbot** that analyzes resumes. Upload a PDF or text resume, then ask questions about strengths, skill gaps, ATS keywords, tailoring for roles, and interview prep.

A sample resume is included at `data/sample_resume.pdf`.

### Quick start

```bash
pip install -r requirements-resume-agent.txt

# Optional: configure API key
mkdir -p ~/.config/resume-agent
cp config-resume-agent.env.example ~/.config/resume-agent/config.env
# Edit config.env and set ANTHROPIC_API_KEY

# Launch the chatbot
./scripts/resume-agent
```

Open the URL shown in the terminal (default `http://localhost:8501`).

### Supported providers

| Provider | Config |
|----------|--------|
| **Anthropic** (default) | `ANTHROPIC_API_KEY`, optional `ANTHROPIC_BASE_URL` |
| **AWS Bedrock** | `RESUME_AGENT_PROVIDER=bedrock`, `RESUME_AGENT_MODEL`, `AWS_REGION` |

### Example questions

- "Give me an overall assessment of this resume."
- "What skills are missing for a Senior Data Engineer role?"
- "Compare this resume against this job description: …"
- "Suggest stronger bullet points for the most recent role."
