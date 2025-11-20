import axios, { AxiosInstance, AxiosError } from 'axios';
import FormData from 'form-data';
import * as fs from 'fs';
import * as path from 'path';
import {
  ClientConfig,
  ExtractRequest,
  ExtractResponse,
  BatchRequest,
  BatchResponse,
  JobStatus,
  Schema,
  CreateSchemaRequest,
  HealthResponse,
  APIKey,
  CreateKeyRequest,
  CreateKeyResponse,
  Team,
  TeamMember,
  AuditLog,
  AuditQueryParams,
} from './types';

export class DeepSeekOCRError extends Error {
  statusCode?: number;
  response?: any;

  constructor(message: string, statusCode?: number, response?: any) {
    super(message);
    this.name = 'DeepSeekOCRError';
    this.statusCode = statusCode;
    this.response = response;
  }
}

export class DeepSeekOCR {
  private client: AxiosInstance;
  private apiKey: string;

  constructor(config: ClientConfig) {
    this.apiKey = config.apiKey;
    this.client = axios.create({
      baseURL: config.baseUrl || 'http://localhost:8080',
      timeout: config.timeout || 120000,
      headers: {
        'X-API-Key': config.apiKey,
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const message = (error.response?.data as any)?.detail || error.message;
        throw new DeepSeekOCRError(
          message,
          error.response?.status,
          error.response?.data
        );
      }
    );
  }

  // Health
  async health(): Promise<HealthResponse> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // OCR Extraction
  async extract(request: ExtractRequest): Promise<ExtractResponse> {
    const payload: any = {
      prompt: request.prompt,
      max_tokens: request.maxTokens,
      temperature: request.temperature,
      model: request.model,
    };

    if (request.imageUrl) {
      payload.image_url = request.imageUrl;
    } else if (request.imageBase64) {
      payload.image_base64 = request.imageBase64;
    }

    if (request.schemaName) {
      payload.schema_name = request.schemaName;
    } else if (request.outputSchema) {
      payload.output_schema = request.outputSchema;
    }

    const response = await this.client.post('/ocr/extract', payload);
    return {
      success: response.data.success,
      content: response.data.content,
      structuredOutput: response.data.structured_output,
      usage: {
        promptTokens: response.data.usage.prompt_tokens,
        completionTokens: response.data.usage.completion_tokens,
        totalTokens: response.data.usage.total_tokens,
      },
      modelUsed: response.data.model_used,
      processingTimeMs: response.data.processing_time_ms,
    };
  }

  async extractFile(
    filePath: string,
    options?: Omit<ExtractRequest, 'imageUrl' | 'imageBase64'>
  ): Promise<ExtractResponse> {
    const imageBuffer = fs.readFileSync(filePath);
    const base64 = imageBuffer.toString('base64');
    return this.extract({
      ...options,
      imageBase64: base64,
    });
  }

  // Batch Processing
  async startBatch(request: BatchRequest): Promise<BatchResponse> {
    const payload: any = {
      source: request.source,
      file_pattern: request.filePattern,
      prompt: request.prompt,
      schema_name: request.schemaName,
      output_schema: request.outputSchema,
      webhook_url: request.webhookUrl,
      output_destination: request.outputDestination,
      max_concurrency: request.maxConcurrency,
      model: request.model,
    };

    const response = await this.client.post('/ocr/batch', payload);
    return {
      jobId: response.data.job_id,
      status: response.data.status,
      message: response.data.message,
    };
  }

  async getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await this.client.get(`/ocr/batch/${jobId}`);
    return {
      jobId: response.data.job_id,
      status: response.data.status,
      totalFiles: response.data.total_files,
      processedFiles: response.data.processed_files,
      failedFiles: response.data.failed_files,
      progress: response.data.progress,
      results: response.data.results,
      errors: response.data.errors,
      startedAt: response.data.started_at,
      completedAt: response.data.completed_at,
    };
  }

  async waitForJob(
    jobId: string,
    pollInterval: number = 2000,
    timeout: number = 3600000
  ): Promise<JobStatus> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const status = await this.getJobStatus(jobId);
      if (['completed', 'failed'].includes(status.status)) {
        return status;
      }
      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    throw new DeepSeekOCRError(`Job ${jobId} timed out after ${timeout}ms`);
  }

  // Schemas
  async createSchema(request: CreateSchemaRequest): Promise<Schema> {
    const response = await this.client.post('/schemas', {
      name: request.name,
      description: request.description,
      json_schema: request.jsonSchema,
    });
    return {
      name: response.data.name,
      description: response.data.description,
      jsonSchema: response.data.json_schema,
      version: response.data.version,
      createdAt: response.data.created_at,
      updatedAt: response.data.updated_at,
    };
  }

  async getSchema(name: string): Promise<Schema> {
    const response = await this.client.get(`/schemas/${name}`);
    return {
      name: response.data.name,
      description: response.data.description,
      jsonSchema: response.data.json_schema,
      version: response.data.version,
      createdAt: response.data.created_at,
      updatedAt: response.data.updated_at,
    };
  }

  async listSchemas(): Promise<Schema[]> {
    const response = await this.client.get('/schemas');
    return response.data.schemas.map((s: any) => ({
      name: s.name,
      description: s.description,
      jsonSchema: s.json_schema,
      version: s.version,
      createdAt: s.created_at,
      updatedAt: s.updated_at,
    }));
  }

  async deleteSchema(name: string): Promise<void> {
    await this.client.delete(`/schemas/${name}`);
  }

  // API Keys
  async createAPIKey(request: CreateKeyRequest): Promise<CreateKeyResponse> {
    const response = await this.client.post('/api-keys', {
      name: request.name,
      scopes: request.scopes,
      expires_days: request.expiresDays,
      rate_limit_rpm: request.rateLimitRpm,
      rate_limit_rpd: request.rateLimitRpd,
    });
    return {
      key: response.data.key,
      id: response.data.id,
      name: response.data.name,
      prefix: response.data.prefix,
      scopes: response.data.scopes,
      expiresAt: response.data.expires_at,
      createdAt: response.data.created_at,
    };
  }

  async listAPIKeys(): Promise<APIKey[]> {
    const response = await this.client.get('/api-keys');
    return response.data.keys;
  }

  async rotateAPIKey(keyId: string): Promise<CreateKeyResponse> {
    const response = await this.client.post(`/api-keys/${keyId}/rotate`);
    return {
      key: response.data.key,
      id: response.data.id,
      name: response.data.name,
      prefix: response.data.prefix,
      scopes: response.data.scopes,
      expiresAt: response.data.expires_at,
      createdAt: response.data.created_at,
    };
  }

  async revokeAPIKey(keyId: string): Promise<void> {
    await this.client.post(`/api-keys/${keyId}/revoke`);
  }

  // Teams
  async createTeam(name: string): Promise<Team> {
    const response = await this.client.post('/teams', { name });
    return response.data;
  }

  async listTeams(): Promise<Team[]> {
    const response = await this.client.get('/teams');
    return response.data.teams;
  }

  async getTeamMembers(teamId: string): Promise<TeamMember[]> {
    const response = await this.client.get(`/teams/${teamId}/members`);
    return response.data.members;
  }

  async inviteTeamMember(
    teamId: string,
    email: string,
    role: string = 'member'
  ): Promise<{ token: string; expiresAt: string }> {
    const response = await this.client.post(`/teams/${teamId}/invitations`, {
      email,
      role,
    });
    return {
      token: response.data.token,
      expiresAt: response.data.expires_at,
    };
  }

  // Audit
  async queryAuditLogs(params?: AuditQueryParams): Promise<AuditLog[]> {
    const queryParams: any = {};
    if (params?.action) queryParams.action = params.action;
    if (params?.userId) queryParams.user_id = params.userId;
    if (params?.resourceType) queryParams.resource_type = params.resourceType;
    if (params?.resourceId) queryParams.resource_id = params.resourceId;
    if (params?.startTime) queryParams.start_time = params.startTime.toISOString();
    if (params?.endTime) queryParams.end_time = params.endTime.toISOString();
    if (params?.success !== undefined) queryParams.success = params.success;
    if (params?.limit) queryParams.limit = params.limit;
    if (params?.offset) queryParams.offset = params.offset;

    const response = await this.client.get('/audit/logs', { params: queryParams });
    return response.data.logs;
  }

  async exportAuditLogs(
    format: 'json' | 'csv' = 'json',
    startTime?: Date,
    endTime?: Date
  ): Promise<string> {
    const params: any = { format };
    if (startTime) params.start_time = startTime.toISOString();
    if (endTime) params.end_time = endTime.toISOString();

    const response = await this.client.get('/audit/logs/export', { params });
    return response.data;
  }
}
