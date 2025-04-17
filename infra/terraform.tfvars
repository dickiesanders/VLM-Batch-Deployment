# Compute resources
min_vcpus     = 0
desired_vcpus = 0
max_vcpus     = 8
instance_type = ["g6.xlarge"]

# Container
docker_image = "265890761777.dkr.ecr.eu-central-1.amazonaws.com/demo-invoice-structured-outputs"

## Env variables
s3_bucket                      = "demo-cdlc-invoice-parsing-batch-job"
preprocessed_images_dir_prefix = "invoices"
s3_processed_dataset_prefix    = "parsed_data.jsonl"
