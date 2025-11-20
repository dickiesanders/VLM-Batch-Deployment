# Google Cloud Run with GPU support for DeepSeek OCR API

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "run" {
  service = "run.googleapis.com"
}

resource "google_project_service" "artifactregistry" {
  service = "artifactregistry.googleapis.com"
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "ocr_api" {
  location      = var.region
  repository_id = "deepseek-ocr-api"
  format        = "DOCKER"
  description   = "DeepSeek OCR API container images"

  depends_on = [google_project_service.artifactregistry]
}

# Service account for Cloud Run
resource "google_service_account" "ocr_api" {
  account_id   = "deepseek-ocr-api"
  display_name = "DeepSeek OCR API Service Account"
}

# Grant Storage access for results
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.ocr_api.email}"
}

# Cloud Run service with GPU
resource "google_cloud_run_v2_service" "ocr_api" {
  name     = "deepseek-ocr-api"
  location = var.region

  template {
    service_account = google_service_account.ocr_api.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/deepseek-ocr-api/api:${var.image_tag}"

      resources {
        limits = {
          cpu    = "8"
          memory = "32Gi"
          "nvidia.com/gpu" = "1"
        }
        cpu_idle = false  # Keep CPU allocated for GPU workloads
      }

      env {
        name  = "MODEL_NAME"
        value = var.model_name
      }

      env {
        name  = "GPU_MEMORY_UTILIZATION"
        value = var.gpu_memory_utilization
      }

      env {
        name  = "MAX_MODEL_LEN"
        value = var.max_model_len
      }

      env {
        name  = "STORAGE_BUCKET"
        value = var.storage_bucket
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 60
        timeout_seconds       = 30
        period_seconds        = 10
        failure_threshold     = 10
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds = 30
      }
    }

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # GPU configuration
    node_selector {
      accelerator = "nvidia-l4"
    }

    timeout = "300s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.run]
}

# Allow unauthenticated access (or configure IAM for authenticated access)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ocr_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Output the service URL
output "service_url" {
  value       = google_cloud_run_v2_service.ocr_api.uri
  description = "URL of the deployed OCR API"
}

output "artifact_registry" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/deepseek-ocr-api"
  description = "Artifact Registry repository for container images"
}
