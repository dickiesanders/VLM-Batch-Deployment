variable "region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "min_vcpus" {
  description = "Minimum number of vCPUs for Batch compute environment"
  type        = number
}

variable "max_vcpus" {
  description = "Maximum number of vCPUs for Batch compute environment"
  type        = number
}
variable "desired_vcpus" {
  description = "vCPUs to initially provision"
  type        = number
}

variable "docker_image" {
  description = "Docker image for the Batch job"
  type        = string
}

variable "instance_type" {
  description = "List of instance for batch jobs."
  type        = list(string)
}

variable "s3_bucket" {
  description = "S3 bucket where the data processing is performed. Environment variable"
  type        = string
}

variable "preprocessed_images_dir_prefix" {
  description = "S3 folder where images are stored. Environment variable."
  type        = string
}

variable "s3_processed_dataset_prefix" {
  description = "S3 folder where extracted data is stored. Environment variable."
  type        = string
}

variable "model_name" {
  description = "The name of the model to use"
  type        = string
  default     = "Qwen/Qwen2.5-VL-7B-Instruct"
}

variable "gpu_memory_utilisation" {
  description = "GPU memory utilization"
  type        = string
  default     = "0.9"
}

variable "max_num_seqs" {
  description = "Maximum number of sequences"
  type        = string
  default     = "4"
}

variable "max_model_len" {
  description = "Maximum model length"
  type        = string
  default     = "4096"
}

variable "max_tokens" {
  description = "Maximum tokens"
  type        = string
  default     = "4096"
}

variable "temperature" {
  description = "Temperature for generation"
  type        = string
  default     = "0"
}

variable "hf_token" {
  description = "Hugging Face API token for accessing gated models"
  type        = string
  default     = ""
  sensitive   = true  # Mark as sensitive to prevent it from showing in logs
}