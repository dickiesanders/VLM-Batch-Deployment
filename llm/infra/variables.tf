variable "region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "eu-central-1"
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
