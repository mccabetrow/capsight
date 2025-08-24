# 🔌 Webhook Integration Testing

## Quick Start

Test the n8n webhook integration with a production-grade valuation event:

```bash
# 1. Set up environment variables
cp .env.example .env
# Edit .env and set your WEBHOOK_SECRET

# 2. Run the webhook test
node test-webhook.mjs
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `N8N_WEBHOOK_URL` | n8n webhook endpoint URL | `https://walkerb.app.n8n.cloud/webhook/...` |
| `WEBHOOK_SECRET` | HMAC signing secret (32+ chars) | `your-secure-webhook-secret-here` |
| `CAPSIGHT_TENANT_ID` | Tenant identifier | `demo` |

## Test Output

**Success Example:**
```
✅ Webhook delivered successfully!
   Status: 200 OK
   Duration: 245ms
   Response: {"success":true,"id":"abc123"}
```

**Failure Example:**
```
❌ Failed to deliver after 5 attempts
   Error: HTTP 500: Internal Server Error
```

## Security Features

- **HMAC-SHA256 Signature**: Cryptographic authentication using `X-Capsight-Signature`
- **Idempotency Keys**: SHA-256 payload hash in `X-Payload-Hash` header
- **Request Tracing**: UUID-based `X-Request-Id` for debugging
- **Timestamp Validation**: ISO-8601 timestamp in `X-Timestamp`
- **Retry Logic**: Exponential backoff (0.5s → 8s) with 5 attempts max

## Payload Schema

The test sends a production-grade `valuation.upsert` event with:

```json
{
  "schema_version": "1.0",
  "type": "valuation.upsert",
  "tenant_id": "demo",
  "model": { "name": "valuation-blend", "version": "1.0.0" },
  "address": "2100 Logistics Pkwy, Dallas, TX",
  "current_value": { "point": 32500000, "confidence": 0.72 },
  "forecast_12m": { "point": 34400000, "confidence": 0.70 },
  "drivers": ["Rent momentum +1.8% q/q", "..."]
}
```

## Troubleshooting

**Connection Refused:**
```bash
# Check if URL is reachable
curl -I https://walkerb.app.n8n.cloud/webhook/450e72ce-45e9-4aa6-bb10-90ca044164c6
```

**Invalid Signature:**
- Verify `WEBHOOK_SECRET` matches n8n configuration
- Check that payload JSON formatting is consistent

**Timeout Issues:**
- n8n webhook may be processing slowly
- Check n8n execution logs for errors

## Integration with CapsightMVP

This test script validates the same webhook client used in production:

```typescript
// In production code
import { getWebhookClient } from './lib/webhook-client'

const webhookClient = getWebhookClient()
await webhookClient.send(payload, requestId)
```

The test script uses the same HMAC signing, retry logic, and payload format as the production webhook client.
