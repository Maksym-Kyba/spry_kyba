variable "project_id" {
  type        = string
  description = "Existing Google Cloud project ID with billing enabled"
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "api_image" {
  type        = string
  description = "Artifact Registry image URI, built and pushed before deployment"
}
variable "firebase_site_id" {
  type        = string
  description = "Globally unique Firebase Hosting site ID"
}
variable "cors_origins" {
  type        = list(string)
  default     = []
  description = "Frontend origins allowed to access the API"
}
