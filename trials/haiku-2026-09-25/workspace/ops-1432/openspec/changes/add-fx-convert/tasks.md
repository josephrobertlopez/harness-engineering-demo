# Tasks: FX Conversion API Service

## 1. Core Conversion Endpoint

- [x] 1.1 Write test: Valid conversion (USD to EUR)
- [x] 1.2 Write test: Invalid amount (missing parameter)
- [x] 1.3 Write test: Invalid amount (not a number)
- [x] 1.4 Write test: Invalid amount (NaN or Infinity)
- [x] 1.5 Write test: Invalid amount (negative)
- [x] 1.6 Write test: Invalid amount (> 1,000,000,000,000)
- [x] 1.7 Write test: Unknown currency (from or to missing)
- [x] 1.8 Write test: Unknown currency (code not in rates)
- [x] 1.9 Write test: Non-GET HTTP method returns 405
- [x] 1.10 Write test: Query parameter order independence
- [x] 1.11 Write test: Trailing slash on /convert endpoint

## 2. Rate Loading and Data

- [x] 2.1 Write test: Service reads rates.json at startup
- [x] 2.2 Write test: No network calls made during conversion
- [x] 2.3 Write test: New rates used after redeployment
- [x] 2.4 Write test: Cross-rate conversion through USD (GBP to EUR)
- [x] 2.5 Create rates.json with sample FX data

## 3. Response Format and Precision

- [x] 3.1 Write test: Response JSON has exactly required fields
- [x] 3.2 Write test: Response JSON has no additional fields
- [x] 3.3 Write test: Monetary values are strings, not JSON numbers
- [x] 3.4 Write test: Banker's rounding (ROUND_HALF_EVEN) applied
- [x] 3.5 Write test: Amounts displayed with 2 decimal places
- [x] 3.6 Write test: Rates displayed with 6 decimal places
- [x] 3.7 Write test: Rate field uses unrounded rate from file

## 4. Error Handling

- [x] 4.1 Write test: Unknown path returns 404 not_found
- [x] 4.2 Write test: POST to unknown path returns 404
- [x] 4.3 Write test: All error responses include Content-Type JSON header

## 5. Health Check Endpoint

- [x] 5.1 Write test: GET /healthz returns 200 ok
- [x] 5.2 Write test: GET /healthz/ (with trailing slash) returns 200

## 6. Docker Configuration

- [x] 6.1 Write test: Dockerfile uses FROM python:3.12-slim
- [x] 6.2 Write test: Default port is 8080
- [x] 6.3 Write test: PORT environment variable overrides default
- [x] 6.4 Write test: Container process runs as non-root user
- [x] 6.5 Write test: No pip-installed packages in image
- [x] 6.6 Write test: No apt-installed packages beyond base image

## 7. Integration and Deployment

- [x] 7.1 Write integration test: Service starts and serves requests
