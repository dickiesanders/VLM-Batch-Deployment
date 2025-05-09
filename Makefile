.PHONY: download-data
download-data:
	uv run huggingface-cli download mathieu1256/FATURA2-invoices --repo-type dataset --local-dir data

AWS_PROFILE ?= slipify
AWS_REGION ?= us-east-1
ECR_REPO_NAME ?= demo-invoice-structured-outputs
ECR_URI = ${ECR_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}

.PHONY: deploy
deploy: check-ecr-repo ecr-login build tag push

	# Require ECR_ACCOUNT_ID (fail if not provided)
	ifndef ECR_ACCOUNT_ID
	$(error ECR_ACCOUNT_ID is not set. Please provide it, e.g., `make deploy ECR_ACCOUNT_ID=123456789012`)
	endif

check-ecr-repo:
	@echo "[INFO] Checking if ECR repository ${ECR_REPO_NAME} exists..."
	@if ! aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --profile ${AWS_PROFILE} --region ${AWS_REGION} >/dev/null 2>&1; then \
		echo "[INFO] Repository does not exist. Creating repository ${ECR_REPO_NAME}..."; \
		aws ecr create-repository --repository-name ${ECR_REPO_NAME} --profile ${AWS_PROFILE} --region ${AWS_REGION}; \
	else \
		echo "[INFO] Repository ${ECR_REPO_NAME} already exists."; \
	fi

ecr-login:
	@echo "[INFO] Logging in to ECR..."
	aws ecr get-login-password --region ${AWS_REGION} --profile ${AWS_PROFILE} | docker login --username AWS --password-stdin ${ECR_URI}
	@echo "[INFO] ECR login successful"

build:
	@echo "[INFO] Building Docker image..."
	docker build -t ${ECR_REPO_NAME} .
	@echo "[INFO] Build completed"

tag:
	@echo "[INFO] Tagging image for ECR..."
	docker tag ${ECR_REPO_NAME}:latest ${ECR_URI}:latest
	@echo "[INFO] Tagging completed"

push:
	@echo "[INFO] Pushing image to ECR..."
	docker push ${ECR_URI}:latest
	@echo "[INFO] Push completed"


.PHONY: aws-batch-apply terraform-init terraform-apply

aws-batch-apply: terraform-init terraform-apply

terraform-init:
	AWS_PROFILE=${AWS_PROFILE} terraform -chdir=infra init

terraform-apply:
	AWS_PROFILE=${AWS_PROFILE} terraform -chdir=infra apply