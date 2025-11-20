/**
 * DeepSeek OCR SDK Types
 */

export interface ClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export interface ExtractRequest {
  imageUrl?: string;
  imageBase64?: string;
  prompt?: string;
  schemaName?: string;
  outputSchema?: Record<string, any>;
  maxTokens?: number;
  temperature?: number;
  model?: string;
}

export interface ExtractResponse {
  success: boolean;
  content: string;
  structuredOutput?: Record<string, any>;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  modelUsed: string;
  processingTimeMs: number;
}

export interface BatchRequest {
  source: string;
  filePattern?: string;
  prompt?: string;
  schemaName?: string;
  outputSchema?: Record<string, any>;
  webhookUrl?: string;
  outputDestination?: string;
  maxConcurrency?: number;
  model?: string;
}

export interface BatchResponse {
  jobId: string;
  status: string;
  message: string;
}

export interface JobStatus {
  jobId: string;
  status: string;
  totalFiles: number;
  processedFiles: number;
  failedFiles: number;
  progress: number;
  results?: any[];
  errors?: any[];
  startedAt?: string;
  completedAt?: string;
}

export interface Schema {
  name: string;
  description?: string;
  jsonSchema: Record<string, any>;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateSchemaRequest {
  name: string;
  description?: string;
  jsonSchema: Record<string, any>;
}

export interface HealthResponse {
  status: string;
  modelLoaded: boolean;
  modelName?: string;
  gpuAvailable: boolean;
}

export interface APIKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  createdAt: string;
  expiresAt?: string;
  lastUsedAt?: string;
  isActive: boolean;
}

export interface CreateKeyRequest {
  name: string;
  scopes?: string[];
  expiresDays?: number;
  rateLimitRpm?: number;
  rateLimitRpd?: number;
}

export interface CreateKeyResponse {
  key: string;
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  expiresAt?: string;
  createdAt: string;
}

export interface Team {
  id: string;
  name: string;
  createdAt: string;
}

export interface TeamMember {
  userId: string;
  email: string;
  role: string;
  joinedAt: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  tenantId: string;
  userId?: string;
  resourceType?: string;
  resourceId?: string;
  success: boolean;
  errorMessage?: string;
}

export interface AuditQueryParams {
  action?: string;
  userId?: string;
  resourceType?: string;
  resourceId?: string;
  startTime?: Date;
  endTime?: Date;
  success?: boolean;
  limit?: number;
  offset?: number;
}
