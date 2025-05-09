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
  service_role             = aws_iam_role.batch_service_role.arn

  compute_resources {
    type                = "EC2"
    allocation_strategy = "BEST_FIT_PROGRESSIVE"

    instance_type = var.instance_type

    min_vcpus     = var.min_vcpus
    desired_vcpus = var.desired_vcpus
    max_vcpus     = var.max_vcpus

    security_group_ids = [aws_security_group.batch_sg.id]
    subnets            = data.aws_subnets.default.ids
    instance_role      = aws_iam_instance_profile.ecs_instance_role.arn

    launch_template {
      launch_template_id = aws_launch_template.batch_launch_template.id
      version            = aws_launch_template.batch_launch_template.latest_version
    }
  }

  depends_on = [aws_iam_role_policy_attachment.batch_service_role]
}

resource "aws_launch_template" "batch_launch_template" {
  name = "batch-launch-template"
  
  block_device_mappings {
    device_name = "/dev/xvda"
    
    ebs {
      volume_size = 100  # Increase this value as needed (in GB)
      volume_type = "gp3"
      delete_on_termination = true
    }
  }
  
  # Add a second volume for model storage
  block_device_mappings {
    device_name = "/dev/sdf"
    
    ebs {
      volume_size = 100  # Adjust size as needed for your models
      volume_type = "gp3"
      delete_on_termination = true
    }
  }

  user_data = base64encode(<<-EOF
Content-Type: multipart/mixed; boundary="==MYBOUNDARY=="
MIME-Version: 1.0

--==MYBOUNDARY==
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
# Wait for the EBS volume to be attached
while [ ! -e /dev/nvme1n1 ]; do
  echo "Waiting for EBS volume to be attached..." >> /var/log/user-data.log
  sleep 5
done

# Check if the volume is already formatted
if ! blkid /dev/nvme1n1; then
  # Format the volume
  echo "Formatting volume..." >> /var/log/user-data.log
  mkfs -t xfs /dev/nvme1n1
fi

# Create mount point
mkdir -p /mnt/data

# Add to fstab for persistence
echo "/dev/nvme1n1 /mnt/data xfs defaults 0 2" >> /etc/fstab

# Mount the volume
mount /mnt/data
echo "Volume mounted at /mnt/data" >> /var/log/user-data.log

# Create directories for cache
mkdir -p /mnt/data/huggingface_cache
mkdir -p /mnt/data/huggingface_home

# Set permissions
chmod 777 -R /mnt/data
echo "Directories created and permissions set" >> /var/log/user-data.log
--==MYBOUNDARY==--
EOF
  )
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

###### Job Definition (with GPU support and EFS volume) ######

# Create an EFS file system for persistent storage
resource "aws_efs_file_system" "model_storage" {
  creation_token = "model-storage"
  
  tags = {
    Name = "ModelStorage"
  }
}

# Create mount targets in each subnet
resource "aws_efs_mount_target" "model_storage_mount" {
  for_each = toset(data.aws_subnets.default.ids)
  
  file_system_id = aws_efs_file_system.model_storage.id
  subnet_id      = each.value
  security_groups = [aws_security_group.efs_sg.id]
}

# Security group for EFS
resource "aws_security_group" "efs_sg" {
  name        = "efs_sg"
  description = "Allow NFS traffic from Batch instances"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.batch_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Update the batch job definition to include the EFS volume
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
      },
      {
        name  = "TRANSFORMERS_CACHE",
        value = "/mnt/efs/huggingface_cache"
      },
      {
        name  = "HF_HOME",
        value = "/mnt/efs/huggingface_home"
      }
    ],
    volumes = [
      {
        name = "model-storage",
        efsVolumeConfiguration = {
          fileSystemId = aws_efs_file_system.model_storage.id,
          rootDirectory = "/"
        }
      }
    ],
    mountPoints = [
      {
        containerPath = "/mnt/efs",
        sourceVolume = "model-storage",
        readOnly = false
      }
    ]
  })

  depends_on = [aws_efs_mount_target.model_storage_mount]
}
