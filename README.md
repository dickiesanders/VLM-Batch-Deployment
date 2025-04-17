# VLM for Document structured extraction

In this project, we build a Batch inference job to extract data from reports and invoices using Vision Language Models (VLM) with vLLM.

The Batch inference is deployed and orchestrated in [AWS Batch](https://aws.amazon.com/fr/batch/).

This project is part of the Webinar we presented with [Julien Hurault](https://www.linkedin.com/in/julienhuraultanalytics/).

Webinar link: coming soon \
Article link: coming soon

Subscribe to the [Newsletter](https://medium.com/@jeremyarancio/subscribe).

## Quick start

The repository is organized as such:

```
.
├── src
│   └── llm
│       ├── __init__.py
│       ├── __main__.py
│       ├── parser           // Job module
│       └── settings.py      // Settings and Env variables
├── data
│   └── docs                 // Downloaded documents for testing 
├── infra                    // AWS Batch insfrastructure deployment
├── Dockerfile  
├── Makefile
├── NOTES.md                 // Technical notes
├── README.md
├── assets
├── notebooks                // Experimentations
├── scripts                  // Various scripts not used in package
├── pyproject.toml
└── uv.lock
```

The module is packaged with [uv](https://github.com/astral-sh/uv).
To install all the dependencies, run:

```bash
uv sync
```

To run the batch job:

1. Use the `.env.template` to create your own `.env` file.
2. You need to run the job within an environement with GPU such as L4, depending on the size of the model

Then run:

```bash
uv run run-batch-job
```

## Run online Batch inference

Deploy the module using Docker to AWS ECR with: 

```bash
make deploy ECR_ACCOUNT_ID=<YOUR-ECR-ACCOUNT-ID> 
```

NOTE: You may want to change the ECR repository (ECR_REPO_NAME) or the AWS region (AWS_REGION)

Then, deploy the Batch infrastructure on AWS using Terraform, run:

```bash
make aws-batch-apply
```

NOTE: Be sure to have Terraform installed.

Once the infrastructure is set up, you can launch a job using the `aws batch` cli command.

```bash
aws batch submit-job \
  --job-name <YOUR-JOB-NAME> \
  --job-queue demo-job-queue \
  --job-definition demo-job-definition
```

## Process overview

The Batch process looks like the following:

* The documents are loaded from S3 as images. You need to indicates 3 environment variables:
  * `S3_BUCKET`: the S3 bucket name
  * `S3_PREPROCESSED_IMAGES_DIR_PREFIX`: the directory name where the invoices are stored. It should be images and not PDFs.
  * `S3_PROCESSED_DATASET_PREFIX`: The path of the output dataset. Right now, the task only returns JSONL dataset (`.jsonl`).
* The model `MODEL_NAME` is loaded using **vLLM**. By default, we load *"Qwen/Qwen2.5-VL-3B-Instruct"*. But feel free to get any larger models if they fit into memory.
* vLLM is configured to return a structured output using `"GuidedDecoding"` by providing the expected schema with Pydantic. 
* Images are processed by vLLM and a `json` is extracted for each invoice. If the json decoding is not successful, an empty dict is returned instead.
* NOT IMPLEMENTED YET: Pydantic is used to validate the extracted jsons and default values are returned if field validation fails.
* The list of dicts, with an unique identifier (such as the S3 file path), is transformed into a usable dataset (here JSONL since there's no data type validation with Pydantic yet.)
* The dataset is finally exported to S3. Indicate where with the environment variable `S3_PROCESSED_DATASET_PREFIX`. Be sure to indicate the proper file format (`.jsonl` in this case.)

## Dataset

For this demo, we used synthetically generated invoices from this [dataset](https://huggingface.co/datasets/mathieu1256/FATURA2-invoices) on Hugging Face.

To download the full dataset: 

```bash
make download-data
```

There's also a script in `scripts/` folder to load a sample of images.
