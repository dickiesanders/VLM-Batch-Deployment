# DeepSeek OCR Dashboard

Management dashboard for the DeepSeek OCR API.

## Features

- **Dashboard**: Usage overview and quick actions
- **Schemas**: Create and manage extraction schemas
- **Jobs**: Look up job status and results
- **Models**: Register and manage custom models (BYOM)
- **API Keys**: Configure authentication

## Quick Start

```bash
# Install dependencies
npm install

# Set environment variable
export NEXT_PUBLIC_API_URL=http://localhost:8080

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Configuration

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=https://your-api-url.com
```

## Deployment

### Vercel (Recommended)

```bash
vercel
```

### Docker

```bash
npm run build
docker build -t deepseek-ocr-dashboard .
docker run -p 3000:3000 deepseek-ocr-dashboard
```

## Pages

- `/` - Landing page
- `/dashboard` - Main dashboard with stats
- `/schemas` - Schema management (CRUD)
- `/jobs` - Job lookup and results
- `/models` - BYOM model registration
- `/api-keys` - API key configuration

## Tech Stack

- Next.js 14 (App Router)
- Tailwind CSS
- Lucide Icons
- TypeScript

## Future Enhancements

- Clerk authentication integration
- Usage analytics with charts
- Billing portal (Stripe)
- Team management
- Real-time job updates (WebSocket)
