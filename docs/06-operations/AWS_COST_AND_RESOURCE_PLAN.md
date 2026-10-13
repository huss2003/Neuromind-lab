# AWS cost and resource plan

Measured on 2026-10-13 through the connected AWS role. Prices below are **estimates from memory for ap-south-1 and must be checked in the AWS pricing page before anything is created.** Nothing has been provisioned.

## What the account actually is
* Account `757968055032`, role `AccountFullAccessRole`, inside an AWS Organization.
* **Free plan, ACTIVE, remaining credit $100.00, plan expires 2027-04-13** (about 6 months). On a Free plan, charges stop when the credit is used up or the plan ends; the account does not bill a card. That is an automatic spending cap, and upgrading to a paid plan removes it.
* Month-to-date cost: $0.00. No S3 buckets.
* A Service Control Policy **explicitly denies**: EC2 (including `Describe*`), ECS, ECR, SQS, SNS, Lambda, CloudWatch, SSM, Secrets Manager, IAM alias listing. It is the same in `us-east-1`, `eu-west-1` and `ap-south-1`.
* **Allowed in the tests:** STS, S3 (list), CloudFront (list), Cost Explorer, Budgets (list, empty), Free Tier plan state. Creating things in them has not been tested.

## Budget arithmetic
$100 over 4.5 months is $22/month; over the 6-month plan life, $16.6/month. **Target ceiling: $15/month**, leaving margin.

| Item | Est. $/month | Notes |
|---|---|---|
| S3 for lecture videos (10 GB stored) | 0.25 | about $0.025/GB-month |
| CloudFront delivery (first 1 TB/month is free on the AWS always-free allowance, if the plan applies it) | 0–3 | video minutes watched × bitrate decides it; 100 learners × 5 h × 1.5 GB/h ≈ 750 GB worst case |
| **Subtotal that can be built in this account today** | **~0–3.5** | |
| (If EC2 were allowed) `t4g.micro` on-demand | ~6.1 | $0.0084/h × 730 |
| (If EC2 were allowed) 20 GB gp3 + public IPv4 | ~1.6 + 3.65 | a public IPv4 now costs about $0.005/h |
| (If EC2 were allowed) total grader host | **~11.4** | about $57 over 5 months |

Avoid: NAT Gateway (about $32/month), load balancers (about $16/month+), Fargate always-on, CloudWatch detailed logs, data egress from the grader.

## What I did **not** do
* Created no AWS resource, budget, IAM user or key.
* Did not set a billing alert: it needs a notification email address, which I will not send to AWS without your OK. Command to run once you confirm (Budgets is permitted): a $15 monthly cost budget with 50/80/100% email alerts.

## Recommendations
1. **Keep the API and the database where they are** (Vercel, Supabase). Moving them to AWS gains nothing and the SCP blocks most of the compute options.
2. **Use S3 + CloudFront for lecture video only**, with a private bucket and CloudFront origin access control, after you confirm the SCP does not also deny bucket creation (untested).
3. **Run the grading worker on a Docker host you control** until an AWS admin lifts the SCP. Everything needed is in `grader/worker.py`.
4. If you upgrade the plan to unlock EC2, first set a Budgets alert: from then on, credits are not a hard cap.

## Cleanup and after the credits end
* Free plan: resources stop being usable when credits or the plan end; export video from S3 first.
* Inventory (empty today): tag every resource `project=neuromind`. Cleanup = delete the bucket contents and bucket, then the CloudFront distribution (disable first).
