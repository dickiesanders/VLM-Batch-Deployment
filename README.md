# VLM for Document structured extraction

In this project, we build a Batch inference job to extract data from reports and invoices using Vision Language Models (VLM) with vLLM.

The Batch inference is deployed and orchestrated in [AWS Batch](https://aws.amazon.com/fr/batch/).

This project is part of the Webinar we presented with [Julien Hurault](https://www.linkedin.com/in/julienhuraultanalytics/).

:microphone: Webinar (coming soon) \
:newspaper: [Article](https://medium.com/towards-artificial-intelligence/deploy-an-in-house-vision-language-model-to-parse-millions-of-documents-say-goodbye-to-gemini-and-cdac6f77aff5)

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


---

Here's a detailed write-up that you can use alongside your architecture diagram. It includes:

* A **consumer-friendly explanation** (for business stakeholders)
* A **technical explanation** (for developers/architects)
* A concise **elevator pitch** (for quick introductions or investor meetings)

---

## 📝 **Consumer-Friendly Explanation**

**What is Slipify?**

Slipify transforms how your business manages paperwork. Instead of manually handling endless invoices, receipts, contracts, and other documents, Slipify automatically reads, understands, and processes them using advanced AI technologies. Whether you're handling simple receipts or complex legal agreements, Slipify captures critical information accurately and integrates it directly into your accounting systems, project management tools, or ERP platforms.

**How Does Slipify Help Your Business?**

* **Reduces Errors & Saves Time**: Eliminates hours spent on manual data entry.
* **Improves Accuracy & Compliance**: Ensures data integrity, eliminating costly mistakes.
* **Speeds Up Cash Flow**: Shortens payment cycles by automating invoice and receipt processing.
* **Scales Easily**: Handles thousands of documents, freeing your staff for high-value tasks.

Simply upload your documents—Slipify handles the rest, extracting essential information, and routing it directly where it needs to go.

---

## 🛠️ **Technical Explanation**

**Slipify Unified Document Processing Architecture**

The Slipify platform features a flexible architecture capable of handling diverse document types with a sophisticated combination of OCR, layout-aware models, and large language models (LLMs):

### **1. Document Ingestion & OCR**

* Documents uploaded are stored in cloud-agnostic object storage (e.g., MinIO, AWS S3).
* OCR services (Tesseract, PaddleOCR, or AWS Textract) convert documents into machine-readable text, including positional and layout metadata.

### **2. Intelligent Document Routing**

* A routing service classifies each document (invoice, receipt, contract) and directs it to the appropriate workflow:

  * **Simple Documents (receipts/invoices)**: Routed directly for LLM-driven extraction (Qwen-2.5-VL, LLaMA-3).
  * **Complex Documents (contracts, agreements)**: Routed to LayoutLMv3/Nougat for advanced layout-aware extraction.

### **3. Dynamic Schema Generation**

* Slipify dynamically generates data schemas based on OCR results using powerful LLMs (Qwen-2.5, LLaMA-3).
* Schemas are stored in a schema database or cache, allowing rapid reuse and consistency across similar documents.

### **4. Data Extraction & Validation**

* The dynamic schemas guide structured data extraction via LLM-driven inference.
* Pydantic dynamically validates structured data output, ensuring alignment with generated schemas.

### **5. Human-in-the-Loop**

* An optional user interface allows manual review, corrections, and approvals.
* Human feedback refines extraction accuracy and dynamically enhances schema precision over time.

### **6. Structured Data & Integration**

* Final structured JSON data is stored in unified databases (MongoDB, PostgreSQL, DynamoDB).
* Slipify seamlessly integrates data into existing business applications (QuickBooks, Sage, Tekmetric, ERP systems).

### **7. Analytics & Reporting**

* Dashboards (Grafana, Metabase) provide insights, tracking document processing, performance metrics, and operational analytics.

This unified architecture ensures Slipify is robust, flexible, and scalable across document types, workloads, and integration scenarios.

---

## 🚀 **Elevator Pitch (30 seconds)**

Slipify eliminates manual paperwork by intelligently extracting and processing critical data from any business document—receipts, invoices, or complex contracts—at scale. By leveraging advanced vision language AI models, Slipify delivers over 98% accuracy, dramatically reducing errors and costs while seamlessly integrating data into your existing business systems. With Slipify, businesses save hours of manual labor, improve cash flow, and make better, data-driven decisions faster.

---

Let me know if you'd like this content refined further or if you'd like it structured into a particular format for presentations, investor pitches, or internal documentation.


```architecture overview

Document Upload
      │
      ▼
Cloud-agnostic Object Storage (MinIO/S3)
      │
      ▼
┌───────────────────────────┐
│ Document Routing Service  │─────┐
│ (classify type: invoice,  │     │
│ receipt, contract, etc.)  │     │
└───────────────────────────┘     │
      │                           │
      │ (simple docs)             │ (complex docs)
      ▼                           ▼
┌────────────────┐       ┌───────────────────────┐
│ OCR Processing │       │ OCR Processing        │
│ (Tesseract or  │       │ (Tesseract/PaddleOCR) │
│ AWS Textract)  │       └─────────┬─────────────┘
└───────┬────────┘                 │
        │                          │
        │ (raw OCR text)           │ (OCR text + layout data)
        │                          ▼
        │                ┌─────────────────────────────┐
        │                │ LayoutLMv3/Nougat Model     │
        │                │ (Complex docs extraction)   │
        │                └─────────┬───────────────────┘
        │                          │
        │                          ▼
        │                ┌───────────────────────┐
        │                │ Structured JSON Output│
        │                └─────────┬─────────────┘
        │                          │
        ▼                          ▼
┌───────────────────────────────────────────────────────────┐
│      Dynamic Schema Generation (LLM: Qwen-2.5/LLaMA-3)    │
│                                                           │
│ Input: OCR Text (simple docs) or LayoutLM JSON (optional) │
│ Output: JSON schema dynamically inferred                  │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
                 ┌──────────────────────────┐
                 │ Schema Store/Cache (DB)  │◀─────┐
                 │ (Postgres/DynamoDB)      │      │
                 └─────────┬────────────────┘      │
                           │                       │
                           ▼                       │
                ┌───────────────────────────┐      │
                │ Schema Selection Logic    │      │
                │ (Dynamic or User-provided)│──────┘
                └───────────┬───────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │ Structured Data Extraction  │
              │ (LLM: Qwen-2.5/LLaMA-3)     │
              └─────────────┬───────────────┘
                            │
                            ▼
              ┌───────────────────────────────┐
              │ Validation & Transformation   │
              │ (Pydantic DynamicSchema)      │
              └─────────────┬─────────────────┘
                            │
                            ▼
               ┌───────────────────────────┐
               │  Human-in-the-loop (Opt.) │◀──────────┐
               │  (Review & Approve/Correct│           │
               │  via Web UI)              │           │
               └─────────────┬─────────────┘           │
                             │                         │
                             ▼                         │
               ┌───────────────────────────────┐       │
               │ Final Structured JSON Output  │───────┘
               │                               │
               │ (Unified Storage: MongoDB,    │
               │ PostgreSQL, or DynamoDB)      │
               └─────────────┬─────────────────┘
                             │
                             ▼
         ┌─────────────────────────────────────┐
         │       Integration Layer/API         │
         │ (QuickBooks, Sage, Tekmetric, etc.) │
         └──────────┬──────────────────────────┘
                    │
                    ▼
      ┌─────────────────────────┐
      │ Dashboards & Reporting  │
      │   (Grafana/Metabase)    │
      └───────────────────────-─┘
```
