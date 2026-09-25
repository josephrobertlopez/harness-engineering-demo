# Proposal: FX Conversion API Service (OPS-1432)

## Why

The billing team currently converts invoice amounts between currencies manually or via external API calls, which is slow and not integrated into their workflow. A dedicated internal FX conversion service will enable real-time currency conversion for invoice processing with pre-loaded rates, eliminating external dependencies and providing consistent, predictable performance.

## What Changes

- Add a stateless REST API endpoint (`GET /convert`) for currency conversion
- Load exchange rates from a checked-in rates.json file at startup (no runtime network calls)
- Provide precise decimal handling with banker's rounding for financial accuracy
- Implement health check endpoint for operational monitoring
- Dockerize the service for deployment on internal infrastructure
- Enforce strict input validation with specific HTTP error responses

## Capabilities

### New Capabilities

- **FX Conversion API**: REST endpoint to convert amounts between ISO 4217 currencies with in-memory rate loading, precise decimal arithmetic, and strict validation
- **Health Check Endpoint**: Simple operational health check for container orchestration
- **Dockerized Deployment**: Python 3.12 slim container with configurable port, non-root execution, and no external dependencies

## Impact

- **Scope**: Adds new REST API service and Docker image
- **Dependencies**: None (Python 3.12 standard library only)
- **Breaking Changes**: None (new feature)
- **Performance**: Sub-millisecond conversion latency (in-memory lookup)
- **Security**: Internal network only; no authentication required
- **Testing**: Must cover all response codes and edge cases for inputs, currencies, and error conditions
