---
description: 'DevOps & CI/CD: GitHub Actions, YAML pipelines, deployment strategies, and release automation'
---

# DevOps & CI/CD

> **Purpose**: Production-ready CI/CD pipelines using GitHub Actions for automated build, test, and deployment.  
> **Audience**: DevOps Engineers building deployment automation and release workflows.  
> **Standard**: Follows GitHub Actions best practices and cloud-native deployment patterns.

---

## Quick Reference

| Need | Solution | Pattern |
|------|----------|---------|
| **Continuous Integration** | Build & test on PR | `on: pull_request` + `jobs: build, test` |
| **Continuous Deployment** | Auto-deploy on merge | `on: push: branches: [main]` |
| **Manual Deployment** | Workflow dispatch with inputs | `on: workflow_dispatch` + `inputs:` |
| **Environment Management** | GitHub Environments | `environment: production` |
| **Secret Management** | GitHub Secrets | `${{ secrets.AZURE_CREDENTIALS }}` |
| **Deployment Strategy** | Blue-green, canary, rolling | Deployment slots or traffic shifting |
| **Rollback** | Previous version restoration | Keep last N releases, quick revert |

---

## GitHub Actions Fundamentals

### Workflow Structure

```yaml
name: CI/CD Pipeline  # Descriptive workflow name

on:  # Trigger events
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:  # Manual trigger
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'
        type: choice
        options:
          - dev
          - staging
          - production

env:  # Global environment variables
  NODE_VERSION: '18'
  DOTNET_VERSION: '8.0.x'

jobs:
  build:  # Job name
    name: Build Application  # Display name
    runs-on: ubuntu-latest  # Runner OS
    timeout-minutes: 15  # Prevent runaway jobs
    
    permissions:  # GITHUB_TOKEN permissions
      contents: read
      packages: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4  # Pin version, not @main
        with:
          fetch-depth: 0  # Full history for semantic versioning
      
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}
      
      - name: Restore dependencies
        run: dotnet restore
      
      - name: Build
        run: dotnet build --no-restore --configuration Release
      
      - name: Test
        run: dotnet test --no-build --configuration Release --verbosity normal
      
      - name: Publish
        run: dotnet publish --no-build --configuration Release --output ./publish
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: app-package
          path: ./publish
          retention-days: 7
```

---

## CI Pipeline Patterns

### Pattern 1: Basic CI (Build + Test)

```yaml
name: Continuous Integration

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main, develop ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        dotnet-version: [ '8.0.x' ]
        os: [ ubuntu-latest, windows-latest ]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup .NET ${{ matrix.dotnet-version }}
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ matrix.dotnet-version }}
      
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.nuget/packages
          key: ${{ runner.os }}-nuget-${{ hashFiles('**/*.csproj') }}
          restore-keys: |
            ${{ runner.os }}-nuget-
      
      - name: Restore
        run: dotnet restore
      
      - name: Build
        run: dotnet build --no-restore
      
      - name: Test
        run: dotnet test --no-build --logger "trx" --results-directory ./TestResults
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ matrix.os }}
          path: ./TestResults/*.trx
```

### Pattern 2: CI with Code Quality

```yaml
name: CI with Quality Checks

on:
  pull_request:
    branches: [ main ]

jobs:
  quality:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      
      # Build and Test
      - name: Build
        run: dotnet build
      
      - name: Test with coverage
        run: dotnet test /p:CollectCoverage=true /p:CoverageReportsFormat=opencover
      
      # Code Quality
      - name: Run linter
        run: dotnet format --verify-no-changes --verbosity diagnostic
      
      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
      
      # Security Scanning
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: csharp
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v3
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
      
      - name: Dependency Review
        uses: actions/dependency-review-action@v4
        if: github.event_name == 'pull_request'
      
      # Coverage Report
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.opencover.xml
          fail_ci_if_error: true
```

### Pattern 3: Monorepo CI (Path Filtering)

```yaml
name: Monorepo CI

on:
  pull_request:
    paths:
      - 'src/api/**'
      - 'src/web/**'
      - '.github/workflows/**'

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      api-changed: ${{ steps.filter.outputs.api }}
      web-changed: ${{ steps.filter.outputs.web }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Detect changes
        uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            api:
              - 'src/api/**'
            web:
              - 'src/web/**'
  
  build-api:
    needs: detect-changes
    if: needs.detect-changes.outputs.api-changed == 'true'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      - name: Build API
        run: |
          cd src/api
          dotnet build
  
  build-web:
    needs: detect-changes
    if: needs.detect-changes.outputs.web-changed == 'true'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      - name: Build Web
        run: |
          cd src/web
          npm ci
          npm run build
```

---

## CD Pipeline Patterns

### Pattern 1: Simple CD (Dev Environment)

```yaml
name: Deploy to Dev

on:
  push:
    branches: [ develop ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: development
      url: https://myapp-dev.azurewebsites.net
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      
      - name: Build and publish
        run: dotnet publish -c Release -o ./publish
      
      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v3
        with:
          app-name: myapp-dev
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE_DEV }}
          package: ./publish
      
      - name: Health check
        run: |
          sleep 30  # Wait for app to start
          curl -f https://myapp-dev.azurewebsites.net/health || exit 1
      
      - name: Notify success
        if: success()
        run: echo "[SUCCESS] Deployed to dev environment"
      
      - name: Notify failure
        if: failure()
        run: echo "[ERROR] Deployment to dev failed"
```

### Pattern 2: CD with Approval Gate (Production)

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*.*.*'  # Trigger on version tags
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy'
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      
      - name: Build and publish
        run: dotnet publish -c Release -o ./publish
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: production-package
          path: ./publish
  
  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.azurewebsites.net
    
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: production-package
          path: ./publish
      
      - name: Login to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy to production slot
        uses: azure/webapps-deploy@v3
        with:
          app-name: myapp-prod
          slot-name: staging  # Deploy to staging slot first
          package: ./publish
      
      - name: Run smoke tests
        run: |
          curl -f https://myapp-prod-staging.azurewebsites.net/health || exit 1
          curl -f https://myapp-prod-staging.azurewebsites.net/health/ready || exit 1
      
      - name: Swap slots (Blue-Green)
        uses: azure/CLI@v2
        with:
          inlineScript: |
            az webapp deployment slot swap \
              --name myapp-prod \
              --resource-group myapp-rg \
              --slot staging \
              --target-slot production
      
      - name: Verify production
        run: |
          sleep 30
          curl -f https://myapp.azurewebsites.net/health || exit 1
      
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
```

### Pattern 3: Canary Deployment

```yaml
name: Canary Deployment

on:
  workflow_dispatch:
    inputs:
      canary-percentage:
        description: 'Canary traffic percentage'
        required: true
        default: '10'
        type: choice
        options:
          - '10'
          - '25'
          - '50'
          - '100'

jobs:
  deploy-canary:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build application
        run: dotnet publish -c Release -o ./publish
      
      - name: Deploy canary version
        uses: azure/webapps-deploy@v3
        with:
          app-name: myapp-prod
          slot-name: canary
          package: ./publish
      
      - name: Set traffic routing
        uses: azure/CLI@v2
        with:
          inlineScript: |
            az webapp traffic-routing set \
              --name myapp-prod \
              --resource-group myapp-rg \
              --distribution canary=${{ inputs.canary-percentage }}
      
      - name: Monitor canary (10 minutes)
        run: |
          echo "[INFO] Monitoring canary deployment for 10 minutes..."
          sleep 600
          # In real scenario, check metrics from Application Insights
      
      - name: Canary validation
        run: |
          # Check error rate, response time, etc.
          echo "[INFO] Validating canary metrics..."
          # If metrics are good, proceed. Otherwise, rollback.
      
      - name: Promote to 100% or rollback
        run: |
          # This would be automated based on metrics
          echo "[INFO] Canary validation successful. Ready to promote."
```

---

## Deployment Strategies

### Blue-Green Deployment

**Use Case**: Zero-downtime deployment with instant rollback capability

```yaml
# Deploy to blue (staging) slot
- name: Deploy to blue environment
  uses: azure/webapps-deploy@v3
  with:
    app-name: myapp
    slot-name: blue  # Staging slot
    package: ./publish

# Run tests on blue
- name: Test blue environment
  run: |
    curl -f https://myapp-blue.azurewebsites.net/health || exit 1

# Swap blue <-> green (production)
- name: Swap to production
  run: |
    az webapp deployment slot swap \
      --name myapp \
      --resource-group rg \
      --slot blue \
      --target-slot production

# Monitor for 5 minutes
- name: Monitor production
  run: |
    sleep 300
    curl -f https://myapp.azurewebsites.net/health || exit 1

# Rollback if needed
- name: Rollback on failure
  if: failure()
  run: |
    az webapp deployment slot swap \
      --name myapp \
      --resource-group rg \
      --slot blue \
      --target-slot production
```

### Rolling Deployment

**Use Case**: Gradual update across instances

```yaml
- name: Rolling update
  uses: azure/webapps-deploy@v3
  with:
    app-name: myapp
    package: ./publish
    # Azure handles rolling update automatically
    # Instances updated one at a time

- name: Verify each instance
  run: |
    # Check all instances are healthy
    for i in {1..5}; do
      curl -f https://myapp.azurewebsites.net/health || exit 1
      sleep 10
    done
```

### Recreate Deployment

**Use Case**: Stateful apps or database migrations

```yaml
- name: Stop application
  run: az webapp stop --name myapp --resource-group rg

- name: Run database migrations
  run: dotnet ef database update

- name: Deploy new version
  uses: azure/webapps-deploy@v3
  with:
    app-name: myapp
    package: ./publish

- name: Start application
  run: az webapp start --name myapp --resource-group rg
```

---

## Environment Management

### GitHub Environments Configuration

```yaml
# In workflow file
jobs:
  deploy:
    environment:
      name: production
      url: https://myapp.com
    
    # Environment protection rules (configured in GitHub UI):
    # - Required reviewers (manual approval)
    # - Wait timer (delay before deployment)
    # - Branch restrictions (only main can deploy)
```

### Environment-Specific Variables

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    
    steps:
      - name: Deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}  # Per-environment secret
          API_KEY: ${{ vars.API_KEY }}  # Per-environment variable
        run: |
          echo "Deploying to ${{ inputs.environment }}"
          echo "Database: $DATABASE_URL"
```

### Multi-Environment Deployment

```yaml
name: Deploy to Multiple Environments

on:
  workflow_dispatch:
    inputs:
      environments:
        description: 'Environments to deploy'
        required: true
        type: choice
        options:
          - 'dev'
          - 'staging'
          - 'production'
          - 'all'

jobs:
  deploy:
    strategy:
      matrix:
        environment: ${{ fromJSON(
          inputs.environments == 'all' && '["dev","staging","production"]' ||
          format('["{0}"]', inputs.environments)
        ) }}
    
    runs-on: ubuntu-latest
    environment: ${{ matrix.environment }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to ${{ matrix.environment }}
        run: |
          echo "Deploying to ${{ matrix.environment }}"
          # Deployment logic here
```

---

## Secret Management

### Using GitHub Secrets

```yaml
steps:
  - name: Login to Azure
    uses: azure/login@v2
    with:
      creds: ${{ secrets.AZURE_CREDENTIALS }}
  
  - name: Set environment variables
    env:
      DATABASE_PASSWORD: ${{ secrets.DB_PASSWORD }}
      API_KEY: ${{ secrets.API_KEY }}
    run: |
      # Secrets are masked in logs
      echo "Connecting to database..."
      # Never echo secrets directly
```

### Service Principal Authentication

```yaml
# Create service principal (run once)
# az ad sp create-for-rbac --name "myapp-github-actions" \
#   --role contributor \
#   --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
#   --sdk-auth

steps:
  - name: Azure Login with Service Principal
    uses: azure/login@v2
    with:
      creds: ${{ secrets.AZURE_CREDENTIALS }}
      # Secret format:
      # {
      #   "clientId": "<client-id>",
      #   "clientSecret": "<client-secret>",
      #   "subscriptionId": "<subscription-id>",
      #   "tenantId": "<tenant-id>"
      # }
```

### Azure Key Vault Integration

```yaml
steps:
  - name: Login to Azure
    uses: azure/login@v2
    with:
      creds: ${{ secrets.AZURE_CREDENTIALS }}
  
  - name: Get secrets from Key Vault
    uses: azure/get-keyvault-secrets@v1
    with:
      keyvault: "myapp-keyvault"
      secrets: |
        DatabasePassword
        ApiKey
        StorageAccountKey
    id: keyvault-secrets
  
  - name: Use secrets
    env:
      DB_PASSWORD: ${{ steps.keyvault-secrets.outputs.DatabasePassword }}
      API_KEY: ${{ steps.keyvault-secrets.outputs.ApiKey }}
    run: |
      echo "Secrets retrieved from Key Vault"
```

---

## Health Checks & Monitoring

### Health Check Endpoints

```yaml
steps:
  - name: Wait for deployment
    run: sleep 30
  
  - name: Liveness check
    run: |
      curl -f https://myapp.azurewebsites.net/health || exit 1
  
  - name: Readiness check
    run: |
      curl -f https://myapp.azurewebsites.net/health/ready || exit 1
  
  - name: Deep health check
    run: |
      response=$(curl -s https://myapp.azurewebsites.net/health/ready)
      echo "$response" | jq -e '.status == "Healthy"' || exit 1
```

### Smoke Tests

```yaml
- name: Run smoke tests
  run: |
    # Test critical endpoints
    curl -f https://myapp.azurewebsites.net/api/products || exit 1
    curl -f https://myapp.azurewebsites.net/api/orders || exit 1
    
    # Test authentication
    TOKEN=$(curl -s -X POST https://myapp.azurewebsites.net/api/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username":"test","password":"test"}' | jq -r '.token')
    
    [ -n "$TOKEN" ] || exit 1
    
    # Test authenticated endpoint
    curl -f -H "Authorization: Bearer $TOKEN" \
      https://myapp.azurewebsites.net/api/user/profile || exit 1
```

### Workflow Notifications

```yaml
jobs:
  notify-start:
    runs-on: ubuntu-latest
    steps:
      - name: Notify deployment start
        uses: 8398a7/action-slack@v3
        with:
          status: custom
          text: 'Deployment to production started'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  
  deploy:
    needs: notify-start
    runs-on: ubuntu-latest
    # ... deployment steps ...
  
  notify-result:
    needs: deploy
    runs-on: ubuntu-latest
    if: always()
    
    steps:
      - name: Notify success
        if: needs.deploy.result == 'success'
        uses: 8398a7/action-slack@v3
        with:
          status: success
          text: 'Production deployment successful!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
      
      - name: Notify failure
        if: needs.deploy.result == 'failure'
        uses: 8398a7/action-slack@v3
        with:
          status: failure
          text: 'Production deployment failed!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Rollback Strategies

### Automated Rollback Workflow

```yaml
name: Rollback Deployment

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to rollback'
        required: true
        type: choice
        options:
          - dev
          - staging
          - production
      version:
        description: 'Version to rollback to (optional, defaults to previous)'
        required: false

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    
    steps:
      - name: Login to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Get previous deployment
        id: previous
        run: |
          # Get previous deployment from Azure or GitHub Releases
          PREVIOUS_TAG=$(gh release list --limit 2 --json tagName --jq '.[1].tagName')
          echo "tag=$PREVIOUS_TAG" >> $GITHUB_OUTPUT
      
      - name: Checkout previous version
        uses: actions/checkout@v4
        with:
          ref: ${{ inputs.version || steps.previous.outputs.tag }}
      
      - name: Build previous version
        run: dotnet publish -c Release -o ./publish
      
      - name: Deploy previous version
        uses: azure/webapps-deploy@v3
        with:
          app-name: myapp-${{ inputs.environment }}
          package: ./publish
      
      - name: Verify rollback
        run: |
          sleep 30
          curl -f https://myapp-${{ inputs.environment }}.azurewebsites.net/health || exit 1
      
      - name: Notify rollback
        run: |
          echo "[WARNING] Rolled back to version: ${{ inputs.version || steps.previous.outputs.tag }}"
```

### Blue-Green Rollback

```yaml
- name: Instant rollback (swap slots back)
  if: failure()
  uses: azure/CLI@v2
  with:
    inlineScript: |
      az webapp deployment slot swap \
        --name myapp \
        --resource-group rg \
        --slot blue \
        --target-slot production
```

---

## Performance Optimization

### Caching Dependencies

```yaml
steps:
  - name: Cache NuGet packages
    uses: actions/cache@v4
    with:
      path: ~/.nuget/packages
      key: ${{ runner.os }}-nuget-${{ hashFiles('**/*.csproj') }}
      restore-keys: |
        ${{ runner.os }}-nuget-
  
  - name: Cache npm packages
    uses: actions/cache@v4
    with:
      path: ~/.npm
      key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
      restore-keys: |
        ${{ runner.os }}-npm-
```

### Parallel Jobs

```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        run: dotnet test --filter Category=Unit
  
  test-integration:
    runs-on: ubuntu-latest
    steps:
      - name: Run integration tests
        run: dotnet test --filter Category=Integration
  
  deploy:
    needs: [test-unit, test-integration]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        run: echo "Both test jobs passed, deploying..."
```

### Concurrency Control

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true  # Cancel old runs

jobs:
  deploy:
    concurrency:
      group: production-deployment
      cancel-in-progress: false  # Don't cancel production deployments
```

---

## Security Best Practices

### Least Privilege Permissions

```yaml
permissions:
  contents: read  # Only what's needed
  packages: write
  pull-requests: write

jobs:
  build:
    permissions:
      contents: read  # Override at job level if needed
```

### Security Scanning

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload Trivy results to GitHub Security
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-results.sarif'
```

### Pin Action Versions

```yaml
# ❌ DON'T use floating tags
- uses: actions/checkout@main

# ✅ DO pin to specific version
- uses: actions/checkout@v4

# ✅ BEST: Pin to commit SHA for security
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
```

---

## Reusable Workflows

### Creating Reusable Workflow

```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      app-name:
        required: true
        type: string
    secrets:
      azure-credentials:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Azure
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ inputs.app-name }}
          publish-profile: ${{ secrets.azure-credentials }}
```

### Using Reusable Workflow

```yaml
# .github/workflows/deploy-production.yml
name: Deploy Production

on:
  push:
    tags: ['v*']

jobs:
  call-reusable-workflow:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
      app-name: myapp-prod
    secrets:
      azure-credentials: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE_PROD }}
```

---

## Troubleshooting

### Debug Workflow

```yaml
- name: Enable debug logging
  run: |
    echo "::debug::Debug message"
    echo "::notice::Notice message"
    echo "::warning::Warning message"
    echo "::error::Error message"

# Enable debug logs in workflow runs:
# Settings → Secrets → Add ACTIONS_STEP_DEBUG = true
```

### Workflow Validation

```bash
# Install actionlint
# brew install actionlint (Mac)
# go install github.com/rhysd/actionlint/cmd/actionlint@latest

# Validate workflows
actionlint .github/workflows/*.yml
```

---

## Best Practices Summary

### DO ✅

1. **Pin action versions** - Use specific versions, not `@main`
2. **Use caching** - Cache dependencies to speed up builds
3. **Implement health checks** - Validate deployments automatically
4. **Use environments** - Leverage GitHub Environments for protection rules
5. **Fail fast** - Exit on first error to save time
6. **Use semantic versioning** - Tag releases as v1.2.3
7. **Monitor workflow duration** - Optimize slow workflows
8. **Use matrix strategy** - Test across multiple versions/OS
9. **Set timeouts** - Prevent runaway jobs
10. **Document workflows** - Add comments explaining complex logic

### DON'T ❌

1. **Don't hardcode secrets** - Always use GitHub Secrets
2. **Don't use personal tokens** - Use service principals
3. **Don't skip tests** - Always run tests before deployment
4. **Don't deploy without health checks** - Validate success
5. **Don't use latest tags** - Pin to specific versions
6. **Don't ignore security** - Run security scans
7. **Don't deploy directly to prod** - Use staging first
8. **Don't forget rollback** - Always have a rollback plan
9. **Don't commit artifacts** - Use artifact storage
10. **Don't leave debug enabled** - Disable after troubleshooting

---

## Common Patterns

### Full CI/CD Template

```yaml
name: Full CI/CD Pipeline

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

env:
  DOTNET_VERSION: '8.0.x'

jobs:
  # 1. Code Quality & Security
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run linter
        run: dotnet format --verify-no-changes
      - name: Security scan
        uses: github/codeql-action/analyze@v3
  
  # 2. Build & Test
  build:
    needs: quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}
      - name: Build
        run: dotnet build
      - name: Test
        run: dotnet test
      - name: Publish
        run: dotnet publish -c Release -o ./publish
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: app
          path: ./publish
  
  # 3. Deploy to Dev (auto)
  deploy-dev:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: app
      - name: Deploy to dev
        run: echo "Deploy to dev"
  
  # 4. Deploy to Production (tags only, with approval)
  deploy-prod:
    needs: build
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: app
      - name: Deploy to production
        run: echo "Deploy to production"
      - name: Create release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
```

---

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [Security Hardening Guide](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Azure Deploy Actions](https://github.com/marketplace?query=azure+deploy)
- [Awesome Actions](https://github.com/sdras/awesome-actions)

---

**Last Updated**: February 5, 2026
