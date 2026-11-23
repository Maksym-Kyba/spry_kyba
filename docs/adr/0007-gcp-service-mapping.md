# ADR 0007: Spry core on Google Cloud

Status: proposed for Lab 9; no deployment performed. AWS stays operational.

## Decision

Use Firebase Hosting for the static React build, Cloud Run for the FastAPI container, Artifact Registry for its image, and a single-zone Cloud SQL for PostgreSQL instance in us-central1. Run Alembic explicitly against the empty database. The GCP Terraform root has its own HCP workspace; no state is shared with `infra/`.

| AWS piece | Decision for GCP | Reason and consequence |
| --- | --- | --- |
| S3 + CloudFront + WAF | Replace frontend with Firebase Hosting | Static HTTPS/CDN; review security controls separately, WAF is not carried over. |
| Lambda URL / FastAPI | Replace core API with Cloud Run | Same HTTP application, container without Lambda adapter, min instances zero. Current API has no token verification: keep IAM invoker private until authentication is implemented. |
| ECR | Artifact Registry | Regional Docker registry; image must be built and pushed before deployment. |
| Aurora PostgreSQL | Cloud SQL PostgreSQL db-f1-micro, 10 GiB SSD | Retains SQL, joins and migrations. It bills while running even with no requests and does not auto-pause like Aurora. |
| DynamoDB | Drop | Spry actually uses relational PostgreSQL; Firestore would require redesigning relations and queries. |
| Cognito + Google | Keep on AWS for now | Existing auth and parser tokens remain there; Cloud Run IAM does not accept those tokens automatically. Identity Platform is an eventual migration, not yet wired. |
| EventBridge Scheduler | Keep on AWS | Existing weekly reports remain on AWS; Cloud Scheduler is a future option. |
| SQS | Keep on AWS | Existing report queue remains; Cloud Tasks is a future closer analogue than Pub/Sub. |
| S3 event → Lambda | Keep on AWS | Existing report pipeline remains intact; Storage/Eventarc/Cloud Run is an alternative. |
| SES | Keep on AWS | No new provider or API key for the existing mailer; if migrated, use a provider such as SendGrid and keep its key in Secret Manager. |
| Bedrock | Keep on AWS | Agenda parser remains a separate Lambda; Vertex AI is a future alternative requiring application changes. |
| SSM / Secrets Manager | Secret Manager for GCP DB URL | Cloud Run runtime identity gets secret accessor; Terraform state also holds the generated password and must be access-controlled. |
| CloudWatch Logs | Cloud Logging | Cloud Run emits stdout/stderr; quotas and retention need review. |
| IAM roles | Dedicated service account + IAM | Grant Cloud SQL client and access only to the DB secret; no service-account key. |
| Terraform AWS provider | Separate google/google-beta root and state | Changes to GCP cannot be applied by the AWS root. |

## Alternatives and consequences

Stopping Cloud SQL outside classes reduces compute cost but needs scheduling/manual intervention and restarts; storage still bills. Firestore scales to zero but loses SQL/joins and needs a data-layer rewrite. Keeping Aurora on AWS avoids a new database but incurs cross-cloud latency, networking/security setup and transfer costs. Cloud SQL is chosen for a faithful lab migration, not as the cheapest idle solution. Min instances zero avoids idle Cloud Run compute, but cold starts remain. There is no public API invoker binding: making it public now would expose unauthenticated read/write endpoints, so Firebase-to-API production access requires a verified-token implementation or another protected proxy. Existing AWS sign-in, report and AI services are not moved.
