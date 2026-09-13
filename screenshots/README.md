# Deployment Screenshots — what to capture

Save these in this folder using these exact filenames. The console deployment guide
tells you exactly when to take each one as you go.

1. `01-security-groups.png` — EC2 Console → Security Groups, showing both `meridian-ec2-sg` and `meridian-rds-sg` in the list
2. `02-rds-creating.png` — RDS Console → Databases, showing your database while status is "Creating"
3. `03-rds-available.png` — RDS Console → Databases, showing your database with status "Available", with the endpoint visible
4. `04-ec2-launch-userdata.png` — the EC2 launch wizard's "Advanced details" section, showing your edited user-data script pasted in (fine to blur out the password)
5. `05-ec2-running.png` — EC2 Console → Instances, showing your instance state "Running" with its public IP visible
6. `06-app-running.png` — your browser showing the Meridian Goods homepage loaded via the EC2 public IP
7. `07-healthz-check.png` — your browser showing `/healthz` returning `{"status": "ok", "db": "reachable"}`
8. `08-add-product-test.png` — your browser showing a product you added yourself through the "List a product" form

Once you're done, terminate the EC2 instance and delete the RDS database (see the README) so you don't get charged for idle resources.
