locals {
  services = toset([
    "run.googleapis.com", "sqladmin.googleapis.com", "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com", "firebase.googleapis.com", "firebasehosting.googleapis.com",
    "cloudresourcemanager.googleapis.com", "iam.googleapis.com"
  ])
}
resource "google_project_service" "api" {
  for_each           = local.services
  service            = each.value
  disable_on_destroy = false
}
resource "google_service_account" "api" {
  account_id   = "spry-api"
  display_name = "Spry API runtime"
  depends_on   = [google_project_service.api]
}
resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "spry"
  format        = "DOCKER"
  depends_on    = [google_project_service.api]
}
resource "random_password" "database" {
  length  = 32
  special = false
}
resource "google_sql_database_instance" "postgres" {
  name                = "spry-postgres"
  region              = var.region
  database_version    = "POSTGRES_17"
  deletion_protection = true
  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 10
    ip_configuration { ipv4_enabled = true }
  }
  depends_on = [google_project_service.api]
}
resource "google_sql_database" "app" {
  name     = "meetings"
  instance = google_sql_database_instance.postgres.name
}
resource "google_sql_user" "app" {
  name     = "meetings"
  instance = google_sql_database_instance.postgres.name
  password = random_password.database.result
}
resource "google_secret_manager_secret" "database_url" {
  secret_id = "spry-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.api]
}
resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql+asyncpg://meetings:${random_password.database.result}@/meetings?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"
}
resource "google_secret_manager_secret_iam_member" "api_access" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}
resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}
resource "google_cloud_run_v2_service" "api" {
  name                = "spry-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true
  template {
    service_account = google_service_account.api.email
    scaling { min_instance_count = 0 }
    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.postgres.connection_name] }
    }
    containers {
      image = var.api_image
      ports { container_port = 8080 }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "CORS_ORIGINS"
        value = join(",", var.cors_origins)
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      resources {
        limits   = { cpu = "1", memory = "512Mi" }
        cpu_idle = true
      }
    }
  }
  depends_on = [google_project_service.api, google_secret_manager_secret_version.database_url, google_secret_manager_secret_iam_member.api_access, google_project_iam_member.api_cloudsql, google_sql_user.app, google_sql_database.app]
}
resource "google_firebase_project" "default" {
  provider   = google-beta
  project    = var.project_id
  depends_on = [google_project_service.api]
}
resource "google_firebase_hosting_site" "frontend" {
  provider   = google-beta
  project    = var.project_id
  site_id    = var.firebase_site_id
  depends_on = [google_firebase_project.default]
}
