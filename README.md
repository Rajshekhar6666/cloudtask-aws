# Meridian Goods — Highly Available Multi-Tier Cloud-Native Application

**Case Study:** Design and Deployment of a Highly Available, Multi-Tier Cloud-Native Application using the AWS Well-Architected Framework
**Submitted by:** Rajshekhar — Roll No. 2400290120198
**Repository:** https://github.com/Rajshekhar6666/cloudtask-aws

Meridian Goods is a small e-commerce product catalog (browse, search, filter by category, add/edit/delete products) deployed on AWS as a 2-tier application:

| Tier | AWS Service | Purpose |
|---|---|---|
| App | 1x EC2 instance | Runs the Flask application |
| Data | Amazon RDS (MySQL) | Stores products and categories |

This deployment is done **entirely through the AWS Management Console** — no command-line tools, no Infrastructure-as-Code required. See [`docs/console_deployment_guide.docx`](docs/console_deployment_guide.docx) for a complete click-by-click walkthrough written for someone who has never used AWS before, and [`docs/case_study_report.pdf`](docs/case_study_report.pdf) for the full write-up against the AWS Well-Architected Framework pillars.

---

## Repository structure

```
2400290120198_RAJSHEKHAR/
├── app/                          # Flask application source
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── templates/
│   └── static/
├── infra/
│   ├── ec2-user-data.sh          # Bootstrap script pasted into the EC2 launch wizard
│   └── security-group-rules.md   # Exact security group rules used
├── diagrams/
│   └── architecture.svg / .png
├── screenshots/                  # Deployment evidence
├── docs/
│   ├── case_study_report.pdf
│   └── console_deployment_guide.docx
└── README.md
```

---

## Quick summary of how it's deployed

Full detail with exact click paths is in `docs/console_deployment_guide.docx` — this is just the short version:

1. Create two security groups in the EC2 console: `meridian-ec2-sg` (allows HTTP from anywhere, SSH from your IP) and `meridian-rds-sg` (allows MySQL only from `meridian-ec2-sg`).
2. Create a MySQL database in the RDS console, free-tier template, `Public access: No`, attached to `meridian-rds-sg`.
3. Once the database shows **Available**, copy its endpoint.
4. Open `infra/ec2-user-data.sh`, replace the placeholder DB endpoint/password with your real values.
5. Launch an EC2 instance (Amazon Linux 2023, t2.micro), attach `meridian-ec2-sg`, and paste the edited script into the **User data** field under Advanced details.
6. Wait a few minutes, then open the instance's public IP address in a browser — the app installs and starts itself automatically.
7. When you're done testing and have your screenshots, **terminate the EC2 instance and delete the RDS database** to avoid any charges.

---

## Why this design (brief)

- **No custom VPC needed** — the account's Default VPC already has a working Internet Gateway and route table, which removes the single biggest source of "why isn't this connecting" problems for a first AWS deployment.
- **Security groups reference each other, not IP addresses** — the RDS security group allows traffic from the EC2 security group by ID, not from an IP. This keeps working even if the EC2 instance is stopped/restarted and gets a new IP, which is the actual root cause behind most "it randomly stopped connecting" issues.
- **RDS is not publicly accessible** — it only accepts connections from inside the VPC, and only from the app tier's security group specifically.
- **No NAT Gateway** — not needed, since RDS never requires outbound internet access, and skipping it avoids an hourly charge that isn't free-tier eligible.

---

## Testing

- **Load the site:** open `http://<EC2-public-IP>/` in a browser — the catalog homepage should load with sample products.
- **Health check:** open `http://<EC2-public-IP>/healthz` — should return `{"status": "ok", "db": "reachable"}`.
- **Functional test:** add a product via "List a product", confirm it appears on the homepage; edit and delete it and confirm the changes persist.
- **Security boundary test:** confirm the RDS endpoint is not reachable directly from your own laptop (it should time out) — only the EC2 instance can reach it.

---

## Cleaning up (important on free tier)

1. EC2 console → Instances → select your instance → **Instance state → Terminate instance**
2. RDS console → Databases → select your database → **Actions → Delete** (uncheck "create final snapshot", type `delete me` to confirm)
3. Optionally, EC2 console → Security Groups → delete `meridian-ec2-sg` and `meridian-rds-sg` once nothing uses them

Full detail on every step, including exact screenshots to take, is in `docs/console_deployment_guide.docx`.
