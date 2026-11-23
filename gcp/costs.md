# Lab 9 Part 3 — monthly cost comparison

No-GCP-account route. The Google Cloud Pricing Calculator was used to check the idle Cloud SQL and Cloud Run core: [idle estimate](https://cloud.google.com/products/calculator/estimate-preview/CiQ1NGVjOGY3NS1lZmQ0LTRjNjktYjAyMC0zYjM0MWQzNzJlZTkQAQ%3D%3D), $9.37/month. Firebase, AWS and the three non-idle profiles below are estimates calculated from the official list-price pages, not calculator exports. Prices USD, no tax, on-demand, 730 hours/month, AWS us-east-1 and GCP us-central1. This is the **core**, excluding the unchanged AWS Cognito, report/SES and Bedrock features, taxes, extras, and any paid backup or cross-cloud transfer; it is not a full account bill.

Assumptions: Firebase static assets <10 GB and <360 MB/day; CloudFront usage inside its selected free allowance; registry ≤0.5 GiB and six active secret versions or fewer; logging and requests inside free quotas except where shown. AWS Aurora Standard has 1 GB storage, 0.5 ACU while awake, then pauses; 5-minute idle tails and database I/O are omitted. GCP Cloud SQL is single-zone db-f1-micro with 10 GiB SSD running all 730 hours for every profile. Cloud Run request billing, min 0, 1 vCPU/0.5 GiB. In active windows assume one API request per second, 100 ms billed duration, no concurrency; idle means zero requests. Lambda uses 0.5 GiB and 100 ms. Free tiers are shared across applicable account/project usage; other usage may consume them. Frontend egress above the quota, cold starts and outbound network add costs.

| Piece | AWS (Lab 4, Stage 2) | Google Cloud (this lab) |
| --- | ---: | ---: |
| Frontend + CDN + HTTPS | $0, assumed within CloudFront free allowance | $0, Firebase Hosting free quota |
| API, idle | $0, Lambda | $0, Cloud Run scales to zero |
| Database compute | $0 while Aurora is paused | $7.67 = 730 × $0.0105 |
| Database storage | $0.10 = 1 GB × $0.10 | $1.70 = 10 GiB × 730 h × $0.000232877 |
| Registry, secrets, logs | $0 assumed within quotas; actual usage varies | $0 within stated quotas |
| **Total idle** | **$0.10/month** | **$9.37/month** |

| Profile | Active hours | Requests | AWS DB compute | AWS API | AWS total | GCP DB compute + disk | Cloud Run | GCP total | Cheaper |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Nobody | 0 | 0 | $0.00 | $0.00 | $0.10 | $9.37 | $0.00 | $9.37 | AWS |
| Class demos (10 × 2 h) | 20 | 72,000 | $1.20 | $0.00 | $1.30 | $9.37 | $0.00 | $9.37 | AWS |
| Office hours (8 h × 22) | 176 | 633,600 | $10.56 | $0.00 | $10.66 | $9.37 | $0.00 | $9.37 | GCP |
| Busy all month | 730 | 2,628,000 | $43.80 | $0.33 | $44.23 | $9.37 | $2.24 | $11.60 | GCP |

AWS total includes $0.10 storage; its busy Lambda request cost is (2.628M − 1M) × $0.20/M = $0.3256, while assumed 131,400 GB-seconds are below the 400,000 free. Cloud Run busy uses 262,800 vCPU-seconds, 131,400 GiB-seconds and 2.628M requests: (262,800 − 180,000) × $0.000024 + (2.628M − 2M) × $0.40/M = $2.2384. Other profiles are below these free quotas. Prices rounded only for display; totals computed before rounding. The model does not measure real latency or usage.

The decisive line is database compute: Aurora can pause and is cheaper for little traffic; fixed Cloud SQL compute is cheaper than 0.5 ACU kept active long enough. On GCP, leaving Cloud SQL running and provisioned storage allocated after the demo is the analogous cost trap; stopping compute still leaves storage charges. If Cloud SQL is stopped for the entire month, its 10 GiB SSD is still about $1.70, without compute.

Reproduce in the [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator): select Iowa, Cloud SQL PostgreSQL Enterprise shared-core db-f1-micro, zonal, 730 h, 10 GiB SSD; Cloud Run request-based 1 vCPU/0.5 GiB, min 0 and requests/duration above; add Firebase, Artifact Registry and Secret Manager within their free usage. Repeat the active-hours inputs and compare [AWS Pricing Calculator](https://calculator.aws/) Aurora Standard 0.5 ACU active hours, 1 GB, Lambda 512 MiB and request counts. The shared calculator link covers idle Cloud SQL and Cloud Run only; the remaining profiles and services need calculator cross-checking. The calculator presents request counts as presets, so the exact profile counts above were calculated from official rates.

Sources: [Cloud SQL](https://cloud.google.com/sql/pricing?hl=en), [Cloud Run](https://cloud.google.com/run/pricing), [Firebase Hosting](https://firebase.google.com/pricing/), [Artifact Registry](https://cloud.google.com/artifact-registry/pricing), [Secret Manager](https://cloud.google.com/security/products/secret-manager), [Aurora](https://aws.amazon.com/rds/aurora/pricing/), [Lambda](https://aws.amazon.com/lambda/pricing/).
