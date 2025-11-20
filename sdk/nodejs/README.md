# DeepSeek OCR Node.js SDK

Official Node.js/TypeScript SDK for the DeepSeek OCR API.

## Installation

```bash
npm install @deepseek/ocr-sdk
```

## Quick Start

```typescript
import { DeepSeekOCR } from '@deepseek/ocr-sdk';

const client = new DeepSeekOCR({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.example.com',
});

// Extract text from image URL
const result = await client.extract({
  imageUrl: 'https://example.com/document.png',
  prompt: 'Extract all text from this document',
});

console.log(result.content);
```

## Features

- Full TypeScript support
- Real-time OCR extraction
- Batch processing with job tracking
- Schema management
- API key management
- Team management
- Audit log queries

## Usage Examples

### Extract from File

```typescript
const result = await client.extractFile('./invoice.pdf', {
  prompt: 'Extract invoice details',
  outputSchema: {
    type: 'object',
    properties: {
      invoiceNumber: { type: 'string' },
      total: { type: 'number' },
      date: { type: 'string' },
    },
  },
});

console.log(result.structuredOutput);
```

### Batch Processing

```typescript
// Start batch job
const batch = await client.startBatch({
  source: 's3://my-bucket/documents/',
  filePattern: '*.pdf',
  prompt: 'Extract text',
  webhookUrl: 'https://myapp.com/webhook',
});

console.log(`Job started: ${batch.jobId}`);

// Wait for completion
const status = await client.waitForJob(batch.jobId);
console.log(`Processed ${status.processedFiles} files`);
```

### Schema Management

```typescript
// Create schema
await client.createSchema({
  name: 'invoice',
  description: 'Invoice extraction schema',
  jsonSchema: {
    type: 'object',
    properties: {
      vendor: { type: 'string' },
      amount: { type: 'number' },
      date: { type: 'string' },
    },
    required: ['vendor', 'amount'],
  },
});

// Use schema in extraction
const result = await client.extract({
  imageUrl: 'https://example.com/invoice.png',
  schemaName: 'invoice',
});
```

### API Key Management

```typescript
// Create new key
const newKey = await client.createAPIKey({
  name: 'production-key',
  scopes: ['read', 'write'],
  expiresDays: 90,
});

console.log(`New key: ${newKey.key}`); // Store securely!

// Rotate key
const rotated = await client.rotateAPIKey(newKey.id);
console.log(`Rotated key: ${rotated.key}`);

// List keys
const keys = await client.listAPIKeys();
```

### Audit Logs

```typescript
// Query recent logs
const logs = await client.queryAuditLogs({
  action: 'ocr.extraction_completed',
  limit: 100,
});

// Export for compliance
const csvExport = await client.exportAuditLogs('csv',
  new Date('2024-01-01'),
  new Date()
);
```

## Error Handling

```typescript
import { DeepSeekOCR, DeepSeekOCRError } from '@deepseek/ocr-sdk';

try {
  const result = await client.extract({ imageUrl: '...' });
} catch (error) {
  if (error instanceof DeepSeekOCRError) {
    console.error(`API Error: ${error.message}`);
    console.error(`Status: ${error.statusCode}`);
  }
}
```

## Configuration

```typescript
const client = new DeepSeekOCR({
  apiKey: process.env.DEEPSEEK_API_KEY!,
  baseUrl: process.env.DEEPSEEK_API_URL || 'http://localhost:8080',
  timeout: 120000, // 2 minutes
});
```

## License

MIT
