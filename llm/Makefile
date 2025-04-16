

.PHONY: download-data
download-data:
	uv run huggingface-cli download mathieu1256/FATURA2-invoices --repo-type dataset --local-dir data

.PHONY: deploy 
deploy: ecr-login build tag push

ecr-login:
	@echo "[INFO] Logging in to ECR..."
	aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 265890761777.dkr.ecr.eu-central-1.amazonaws.com
	@echo "[INFO] ECR login successful"

build:
	@echo "[INFO] Building Docker image..."
	docker build -t demo-invoice-structured-outputs .
	@echo "[INFO] Build completed"

tag:
	@echo "[INFO] Tagging image for ECR..."
	docker tag demo-invoice-structured-outputs:latest 265890761777.dkr.ecr.eu-central-1.amazonaws.com/demo-invoice-structured-outputs:latest
	@echo "[INFO] Tagging completed"

push:
	@echo "[INFO] Pushing image to ECR..."
	docker push 265890761777.dkr.ecr.eu-central-1.amazonaws.com/demo-invoice-structured-outputs:latest
	@echo "[INFO] Push completed"
