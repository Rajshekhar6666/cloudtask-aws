# Security Group Rules Reference

This project uses the AWS account's **Default VPC** — no custom VPC/subnet setup is required.
Two security groups are created manually through the console and control all access.

## `meridian-ec2-sg` (attached to the EC2 instance)

| Type | Protocol | Port | Source | Purpose |
|---|---|---|---|---|
| HTTP | TCP | 80 | 0.0.0.0/0 (anywhere) | Lets anyone on the internet load the website |
| SSH | TCP | 22 | My IP (auto-detected by the console) | Lets only you connect for debugging |

## `meridian-rds-sg` (attached to the RDS database)

| Type | Protocol | Port | Source | Purpose |
|---|---|---|---|---|
| MYSQL/Aurora | TCP | 3306 | `meridian-ec2-sg` (the security group itself, not an IP) | Lets only the app server reach the database |

**Why the RDS rule points at a security group instead of an IP address:** IP-based rules break the moment
an instance is replaced or restarted with a new address. A security-group-to-security-group rule keeps
working automatically — this is the fix for the "instances suddenly stop connecting" problem that IP-based
rules cause.

The RDS instance itself has **Public access: No**, so even if the security group were briefly misconfigured,
the database still isn't reachable directly from the internet — only from resources inside the same VPC that
the security group explicitly allows.
