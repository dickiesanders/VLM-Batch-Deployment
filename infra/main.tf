provider "aws" {
  region = var.region
}

###### IAM Roles ######

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_instance_role" {
  name               = "ecs_instance_role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_role" {
  name = "ecs_instance_role"
  role = aws_iam_role.ecs_instance_role.name
}

# Batch Service Role
data "aws_iam_policy_document" "batch_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "batch_service_role" {
  name               = "aws_batch_service_role"
  assume_role_policy = data.aws_iam_policy_document.batch_assume_role.json
}

resource "aws_iam_role_policy_attachment" "batch_service_role" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# ECS Task Execution Role (for container management)
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecs_task_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

# Attach the standard ECS Task Execution policy
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom Job Role (for your application)
resource "aws_iam_role" "batch_job_role" {
  name = "demo-batch-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

# IAM Policy for S3 Access
resource "aws_iam_policy" "batch_s3_policy" {
  name        = "batch-s3-access"
  description = "Allow Batch jobs to access S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      Resource = [
        "arn:aws:s3:::${var.s3_bucket}",
        "arn:aws:s3:::${var.s3_bucket}/*"
      ]
    }]
  })
}

# Attach Policy to Job Role
resource "aws_iam_role_policy_attachment" "batch_attach_s3" {
  role       = aws_iam_role.batch_job_role.name
  policy_arn = aws_iam_policy.batch_s3_policy.arn
}


###### Compute Environment (using default VPC) ######

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Create a security group that allows outbound internet access
resource "aws_security_group" "batch_sg" {
  name   = "batch_sg"
  vpc_id = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "batch-sg"
  }
}

resource "aws_batch_compute_environment" "batch_compute_env" {
  compute_environment_name = "demo-compute-environment"
  type                     = "MANAGED"
  service_role             = aws_iam_role.batch_service_role.arn # Role associated with Batch

  compute_resources {
    type                = "EC2"
    allocation_strategy = "BEST_FIT_PROGRESSIVE"

    instance_type = var.instance_type

    min_vcpus     = var.min_vcpus
    desired_vcpus = var.desired_vcpus
    max_vcpus     = var.max_vcpus

    security_group_ids = [aws_security_group.batch_sg.id]
    subnets            = data.aws_subnets.default.ids
    instance_role      = aws_iam_instance_profile.ecs_instance_role.arn # Role to roll up EC2 instances
  }

  depends_on = [aws_iam_role_policy_attachment.batch_service_role] # To prevent a race condition during environment deletion 
}

###### Job Queue ######

resource "aws_batch_job_queue" "batch_job_queue" {
  name     = "demo-job-queue"
  state    = "ENABLED"
  priority = 1
  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.batch_compute_env.arn
  }
}

###### Job Definition (with GPU support) ######

resource "aws_batch_job_definition" "batch_job_definition" {
  name = "demo-job-definition"
  type = "container"

  container_properties = jsonencode({
    image            = var.docker_image,
    jobRoleArn       = aws_iam_role.batch_job_role.arn,
    executionRoleArn = aws_iam_role.ecs_task_execution_role.arn,
    resourceRequirements = [
      {
        type  = "VCPU"
        value = "4" # g6.xlarge has 4 vCPUs
      },
      {
        type  = "MEMORY"
        value = "8000" # g6.xlarge has 16GB RAM
      },
      {
        type  = "GPU"
        value = "1" # Critical for g6.xlarge
      }
    ],
    environment = [
      {
        name  = "S3_BUCKET",
        value = var.s3_bucket
      },
      {
        name  = "S3_PREPROCESSED_IMAGES_DIR_PREFIX",
        value = var.preprocessed_images_dir_prefix
      },
      {
        name  = "S3_PROCESSED_DATASET_PREFIX",
        value = var.s3_processed_dataset_prefix
      }
    ]
  })
}
