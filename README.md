# Building a Concurrent Data Orchestration Pipeline Using Amazon EMR and Apache Livy
This code demonstrates the architecture featured on the AWS Big Data blog (<link>)
which creates a concurrent data pipeline by using Amazon EMR and Apache Livy. This pipeline is orchestrated by Apache Airflow.

## LinkedIn Job Monitor

An hourly monitor that checks LinkedIn for new **Senior Data Engineer** roles and sends alerts.

### What it watches

| Profile | Criteria |
|---------|----------|
| `remote_india` | Remote roles, title matches senior/sr/lead/principal/staff data engineer, location India |
| `kochi` | Similar data-engineer titles in Kochi, Kerala |
| `trivandrum` | Similar data-engineer titles in Thiruvananthapuram (Trivandrum), Kerala |

Only **new** postings (not seen in a previous run) trigger alerts.

### Run once (manual or cron)

```bash
export PYTHONPATH=/path/to/repo
python3 -m job_monitor.monitor
# or
./scripts/run_job_monitor.sh
```

### Run hourly with systemd

```bash
sudo cp -r . /opt/job-monitor
sudo cp scripts/job-monitor.{service,timer} /etc/systemd/system/
# Optional: create /etc/job-monitor/env with alert variables (see below)
sudo systemctl daemon-reload
sudo systemctl enable --now job-monitor.timer
```

### Run hourly with Airflow

Enable the DAG `linkedin_senior_data_engineer_monitor` in Airflow (schedule: every 1 hour).

### Alert configuration

Set these environment variables on the host running the monitor:

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Incoming Slack webhook URL |
| `ALERT_EMAIL_TO` | Recipient email address |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default `587`) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `SMTP_FROM` | From address (defaults to `SMTP_USER`) |
| `JOB_MONITOR_STATE_FILE` | Path to JSON state file (default: `data/seen_jobs.json`) |

If no alert channel is configured, new jobs are logged to stdout only.

> **Note:** Slack MCP in Cursor requires separate IDE authentication. For automated alerts, use `SLACK_WEBHOOK_URL` or email.
