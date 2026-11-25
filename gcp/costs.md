# Lab 9 Part 3 — monthly cost comparison

No-GCP-account route. Prices are USD, no tax, on-demand, 730 hours/month, AWS us-east-1 and GCP us-central1. Calculator evidence and manual adjustments for each profile are listed below. This is the **core**, excluding unchanged AWS Cognito, report/SES and Bedrock features, taxes, extras, and paid backup or cross-cloud transfer; it is not a full account bill. Calculators were checked on 26 November 2026. AWS share links expire after one year.

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

## Calculator evidence and manual portions

Every row uses the regions, 100 ms request duration, memory, monthly database storage, idle/active assumptions and shared free tiers stated above. AWS Lambda free tier: 1 million requests and 400,000 GB-seconds; Google Cloud Run: 2 million requests, 180,000 vCPU-seconds and 360,000 GiB-seconds. These are shared allowances, assumed fully available to this workload. Firebase Hosting, CloudFront, logs and other small services remain manual $0 assumptions for every row.

| Profile | AWS calculator evidence | Google calculator evidence | Manual portions and limits |
| --- | --- | --- | --- |
| Nobody | No saved idle estimate | [Idle: 0 requests, $9.37/month](https://cloud.google.com/products/calculator/estimate-preview/CiRkZjFiZjAwZS1iOTZkLTRkNzYtOTI5MC00MTliYTY1ZWE3ZTMQAQ%3D%3D) | AWS idle Aurora $0.10 storage and $0 compute/Lambda are manual; Google Firebase and logging are manual. |
| Class demos | [Lambda: 72,000 requests, $0](https://calculator.aws/#/estimate?id=3beee64fc921d1cb011ee656484cddc18ee9ad81); [Aurora: $1.30](https://calculator.aws/#/estimate?id=2cd6c5b885dec41d9037eba175705a6adb6e3d57) | [Nearest preset: 100,000 requests, $9.62 before CPU/memory free allowances](https://cloud.google.com/products/calculator/estimate-preview/CiRhNmQ0NWM0MS0xMmEzLTRhOWEtOTRmZC1kZjcwZTA3MTEyZjIQAQ%3D%3D) | The Aurora link also contains **office** Lambda, not demo Lambda; use the separate demo Lambda link. Google uses 100,000 instead of 72,000 requests; exact Cloud Run and free-tier adjustment are manual. |
| Office hours | [Aurora + Lambda: $10.66](https://calculator.aws/#/estimate?id=cf494a53d6726930ab1d6cfd3de01d3721a2e282) | [Nearest preset: 760,417 requests, $11.29 before CPU/memory free allowances](https://cloud.google.com/products/calculator/estimate-preview/CiRlMTY4NTY1Yy04N2Q0LTQwMTktYjI0Mi0xOTM3M2U1MTZlYzgQAQ%3D%3D) | Google uses 760,417 instead of 633,600 requests; exact Cloud Run and free-tier adjustment are manual. |
| Busy all month | [Lambda: 2,628,000 requests, $0.33](https://calculator.aws/#/estimate?id=0c35a33e0cb4e54314455674edc06f1612108b8d); Aurora $43.90 was checked in the calculator but no link was saved | [Nearest preset: 2.5 million requests, $15.88 before CPU/memory free allowances](https://cloud.google.com/products/calculator/estimate-preview/CiQwZmQ5MjZiMS0xMWY1LTQ3MmUtYjUzOS1iNWI0YTBkMmZiNWIQAQ%3D%3D) | AWS total combines separately checked Aurora and Lambda. Google uses 2.5 million instead of 2.628 million requests; exact Cloud Run and free-tier adjustment are manual. |

For AWS demo and office, the calculator models time-varying capacity as a **monthly average**, respectively 0.5 × 20 / 730 = 0.01369863 ACU and 0.5 × 176 / 730 = 0.120547945 ACU. These are calculator inputs for an arithmetic average, not deployable Aurora minimum capacity settings. The form required at least 13 monthly baseline and peak I/O operations, which round to $0.00; the model otherwise omits I/O. Both estimates disable RDS Proxy and Database Insights. For busy, the earlier calculator check used 0.5 ACU for all 730 hours and 1 GB. Each saved AWS estimate covers only its listed components, not the complete cloud bill.

Google's calculator offers request-count presets rather than the exact three active counts. The saved examples use 1 vCPU, 512 MiB, 100 ms, concurrency 1 and minimum instances 0. The summaries include the request free allowance but charge CPU and memory usage without the free compute allowances used in the table above; those allowances and exact request counts are applied manually. Therefore the calculator's $9.62, $11.29 and $15.88 are evidence for the **nearby inputs**, not the final totals in the profile table. Cloud SQL, registry and Secret Manager are present in each linked Google estimate; Firebase and Cloud Logging are not.

To reproduce, use the [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator) with Iowa, Cloud SQL PostgreSQL Enterprise shared-core db-f1-micro, zonal, 730 h, 10 GiB SSD and the Cloud Run settings above. In the [AWS Pricing Calculator](https://calculator.aws/), select Aurora Standard Serverless v2 in N. Virginia, 1 GB storage and the average ACUs above; select Lambda x86, 512 MB, 100 ms and the exact request count with free tier enabled.

Sources: [Cloud SQL](https://cloud.google.com/sql/pricing?hl=en), [Cloud Run](https://cloud.google.com/run/pricing), [Firebase Hosting](https://firebase.google.com/pricing/), [Artifact Registry](https://cloud.google.com/artifact-registry/pricing), [Secret Manager](https://cloud.google.com/security/products/secret-manager), [Aurora](https://aws.amazon.com/rds/aurora/pricing/), [Lambda](https://aws.amazon.com/lambda/pricing/).
