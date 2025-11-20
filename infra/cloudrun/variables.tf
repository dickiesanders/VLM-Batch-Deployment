variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region (must support Cloud Run GPU)"
  type        = string
  default     = "us-central1"
}

variable "model_name" {
  description = "VLM model to use for OCR"
  type        = string
  default     = "deepseek-ai/deepseek-vl2-tiny"
}

variable "gpu_memory_utilization" {
  description = "GPU memory utilization (0-1)"
  type        = string
  default     = "0.85"
}

variable "max_model_len" {
  description = "Maximum model context length"
  type        = string
  default     = "4096"
}

variable "storage_bucket" {
  description = "GCS bucket for storing results"
  type        = string
}

variable "image_tag" {
  description = "Container image tag"
  type        = string
  default     = "latest"
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 5
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to the API"
  type        = bool
  default     = false
}
