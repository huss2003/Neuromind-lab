# AWS setup instructions (owner steps) — budget ceiling $15/month

Decision recorded 2026-10-13: the Supabase key and passwords are **not** being rotated for now (owner decision). The risk stays open in the readiness report.

## 0. How I can reach AWS
My only AWS access is the **AWS connector** (the same sign-in as before). Pasting an access key into chat will not work with those tools, and I do not have the AWS CLI here. So the safe route is: you sign the connector into the right account/role, or you run a template I give you in **AWS CloudShell** (no credentials leave your account).

## 1. Pick the account (the blocker)
The current account (757968055032) sits under an organization policy that denies EC2, ECS, SQS, Lambda, CloudWatch, SSM and Secrets Manager. Check: AWS Console → EC2 → Instances. If you see "explicit deny in a service control policy", this account cannot host the grader.
* Option A: ask the organization admin to allow EC2 in `ap-south-1`.
* Option B: create a **new standalone AWS account** (it gets its own Free-plan credit) and use that.
* Option C: skip AWS compute; run `grader/worker.py` on a Docker machine you control. AWS then holds only video (S3/CloudFront).

## 2. Spending guardrails (do these first, 5 minutes)
1. Billing → **Budgets** → Create budget → Cost budget, monthly, **$15**. Alerts at 50%, 80% and 100% of actual cost, plus 100% of forecast, sent to your email.
2. Billing → Billing preferences → turn on Free Tier usage alerts and invoice/credit alerts.
3. Keep the account on the **Free plan**: charges stop when the credit ($100, expires 2027-04-13) is used up or ends. Upgrading to a paid plan removes that cap; if you ever do, the budget alert becomes your only protection.
4. Do not create: NAT Gateway (~$32/month), load balancers (~$16/month+), Elastic IPs that sit unused, RDS, always-on Fargate.

## 3. What I would build (about $11–13/month)
| Resource | Setting | Est. $/month |
|---|---|---|
| 1 EC2 instance | `t4g.micro` (ARM, 1 GB), Amazon Linux 2023, region `ap-south-1`, 20 GB gp3 | ~6.1 + 1.6 |
| Public IPv4 | needed for outbound-only internet; **no inbound rules at all** | ~3.7 |
| Instance settings | IMDSv2 required, metadata hop limit 1 (containers cannot reach it), no instance role, termination protection off, tag `project=neuromind` | 0 |
| Worker | Docker + `grader/worker.py` as a systemd service; polls the API over HTTPS; `--network none` sandbox | 0 |
| S3 (optional, video) | private bucket, block public access, CloudFront with origin access control | ~0.3 + egress |

Estimated total about $11.4 for the worker alone. Video through CloudFront can exceed the remaining ~$3.6 if many learners watch: 100 learners × 5 hours × ~1.5 GB/hour is up to ~750 GB. Until video usage is measured, keep video where it is (or use a low bitrate and a CloudFront price class limited to India/Asia). Prices are estimates; verify on the AWS pricing page.

## 4. Least-privilege IAM for me (if you choose a deployer user/role)
Create an IAM user or role `neuromind-deployer` with **no** IAM, Organizations or Billing-write rights. Policy (adjust the account id):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["ec2:RunInstances"], "Resource": "*",
     "Condition": {"StringEquals": {"aws:RequestedRegion": "ap-south-1"},
                   "StringLikeIfExists": {"ec2:InstanceType": ["t4g.micro", "t4g.small"]}}},
    {"Effect": "Allow", "Action": ["ec2:Describe*", "ec2:CreateTags", "ec2:CreateSecurityGroup", "ec2:AuthorizeSecurityGroupEgress",
     "ec2:RevokeSecurityGroupEgress", "ec2:DeleteSecurityGroup", "ec2:StopInstances", "ec2:StartInstances", "ec2:TerminateInstances",
     "ec2:ModifyInstanceMetadataOptions"], "Resource": "*", "Condition": {"StringEquals": {"aws:RequestedRegion": "ap-south-1"}}},
    {"Effect": "Allow", "Action": ["s3:*"], "Resource": ["arn:aws:s3:::neuromind-*", "arn:aws:s3:::neuromind-*/*"]},
    {"Effect": "Allow", "Action": ["cloudfront:*"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["budgets:ViewBudget", "ce:Get*"], "Resource": "*"}
  ]
}
```
No `iam:*`, so a leaked key cannot create admins. Delete the access key when we finish.

## 5. What I will need from you
1. Which option in section 1 you chose (A, B or C).
2. Either (a) the connector re-signed into the chosen account, or (b) your OK for me to write a CloudFormation template for you to run in CloudShell.
3. The email for budget alerts (only if you want me to create the budget instead of you).
4. A `GRADER_WORKER_TOKEN` you generate yourself (`openssl rand -hex 32`) and place in the worker host and in the Vercel API project. Do not send it to me.

## 6. After setup (my part)
Bootstrap the worker, set `GRADER_MODE=queue` on the API, run the staging drills (restart API, kill worker mid-job, duplicate result, dead-letter), measure queue wait and grading time, and update the readiness report with real numbers.
