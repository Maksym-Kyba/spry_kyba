output "cloud_run_url" { value = google_cloud_run_v2_service.api.uri }
output "cloud_sql_connection_name" { value = google_sql_database_instance.postgres.connection_name }
output "artifact_repository" { value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}" }
output "firebase_site_url" { value = "https://${google_firebase_hosting_site.frontend.site_id}.web.app" }
