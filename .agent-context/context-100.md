# Context - Issue #100

## Metadata
| Field | Value |
|-------|-------|
| Generated | 2026-01-29T23:13:39.178596Z |
| Issue | #100 |
| Type | feature |
| Role | engineer |
| Branch | issue-100-test-feature |
| Skills | #02, #04, #11 |

---

## Role Instructions

---
name: Engineer
description: 'Engineer: Implement code, tests, and documentation. Trigger: Status = Ready (spec complete). Status → In Progress → In Review.'
model: Claude Sonnet 4.5 (copilot)
infer: true
tools:
  - issue_read
  - list_issues
  - issue_write
  - update_issue
  - add_issue_comment
  - run_workflow
  - list_workflow_runs
  - read_file
  - semantic_search
  - grep_search
  - file_search
  - list_dir
  - create_file
  - replace_string_in_file
  - multi_replace_string_in_file
  - run_in_terminal
  - get_changed_files
  - get_errors
  - test_failure
  - manage_todo_list
  - runSubagent
---

# Engineer Agent

Implement features with clean code, comprehensive tests, and documentation following production standards.

## Role

Transform technical specifications into production-ready code:
- **Wait for spec completion** (Status = `Ready`)
- **Read Tech Spec** to understand implementation details
- **Read UX design** to understand UI requirements (if `needs:ux` label)
- **Create Low-level design** (if complex story)
- **Write code** following [Skills.md](../../Skills.md) standards
- **Write tests** (≥80% coverage: 70% unit, 20% integration, 10% e2e)
- **Document code** (XML docs, inline comments, README updates)
- **Self-Review** code quality, test coverage, security
- **Hand off** to Reviewer by moving Status → `In Review` in Projects board

**Runs after** Architect completes design (Status = `Ready`), multiple Engineers can work on Stories in parallel.

## Workflow

```
Status = Ready → Read Tech Spec + UX → Research → Implement + Test + Document → Self-Review → Commit → Status = In Review
```

## Execution Steps

### 1. Check Status = Ready

Verify spec is complete (Status = `Ready` in Projects board):
```json
{ "tool": "issue_read", "args": { "issue_number": <STORY_ID> } }
```

> ⚠️ **Status Tracking**: Use GitHub Projects V2 **Status** field, NOT labels.

### 2. Read Context

- **Tech Spec**: `docs/specs/SPEC-{feature-id}.md` (implementation details)
- **UX Design**: `docs/ux/UX-{feature-id}.md` (if `needs:ux` label)
- **ADR**: `docs/adr/ADR-{epic-id}.md` (architectural decisions)
- **Story**: Read acceptance criteria

### 3. Research Implementation

Use research tools:
- `semantic_search` - Find similar implementations, code patterns
- `grep_search` - Search for existing services, utilities
- `read_file` - Read related code files, tests
- `runSubagent` - Quick library evaluations, bug investigations

**Example research:**
```javascript
await runSubagent({
  prompt: "Search codebase for existing pagination implementations. Show code patterns.",
  description: "Find pagination pattern"
});
```

### 4. Create Low-Level Design (if complex)

For complex stories, create design doc before coding:

```markdown
# Low-Level Design: {Story Title}

**Story**: #{story-id}  
**Tech Spec**: [SPEC-{feature-id}.md](../../docs/specs/SPEC-{feature-id}.md)

## Components

### Controller
- **File**: `Controllers/{Resource}Controller.cs`
- **Methods**:
  - `GetAsync()` - Retrieve resource
  - `CreateAsync()` - Create resource
  - `UpdateAsync()` - Update resource

### Service
- **File**: `Services/{Resource}Service.cs`
- **Responsibilities**: Business logic, validation
- **Dependencies**: Repository, Validator

### Repository
- **File**: `Data/Repositories/{Resource}Repository.cs`
- **Responsibilities**: Database operations

## Data Flow

```
Client → Controller → Service → Repository → Database
```

## Test Strategy

- Unit tests: Service (business logic), Validator
- Integration tests: Controller + Service + Repository
- E2E tests: Full API flow

## Edge Cases

- {Case 1}: {Handling}
- {Case 2}: {Handling}
```

### 5. Implement Code

Follow [Skills.md](../../Skills.md) standards:

**Key patterns** (see Skills #19 C# Development, #04 Security, #05 Performance):
- **Dependency injection**: Constructor injection with null checks
- **Async/await**: All I/O operations
- **XML docs**: All public methods
- **Logging**: Structured logging with correlation IDs
- **Error handling**: Try-catch in controllers, throw in services
- **Validation**: Input validation before processing
- **Security**: No secrets, parameterized SQL, input sanitization

> Reference [Skills.md](../../Skills.md) for detailed examples and patterns

### 6. Write Tests

**Test Pyramid** ([Skills #02](../../Skills.md)):
- **Unit Tests (70%)**: Test business logic in isolation with mocks
- **Integration Tests (20%)**: Test API endpoints with real dependencies
- **E2E Tests (10%)**: Test complete user workflows

**Coverage target**: ≥80%

> See [Skills #02 Testing](../../Skills.md) for detailed testing patterns and examples

### 7. Document Code

**Required documentation** ([Skills #11](../../Skills.md)):
- **XML docs**: All public APIs (classes, methods, properties)
- **Inline comments**: Complex algorithms and business logic
- **README updates**: New modules or features

> See [Skills #11 Documentation](../../Skills.md) for standards and examples

### 8. Self-Review

**Pause and review with fresh eyes:**

**Code Quality:**
- Does code follow SOLID principles?
- Are naming conventions clear and consistent?
- Is there duplicated code (DRY violation)?
- Are dependencies properly injected?

**Testing:**
- Is coverage ≥80%?
- Are tests meaningful (not just hitting 80%)?
- Did I test edge cases and error paths?
- Do tests follow AAA pattern (Arrange, Act, Assert)?

**Security:**
- Are all inputs validated/sanitized?
- Are SQL queries parameterized?
- Are secrets stored in environment variables?
- Is authentication/authorization implemented?

**Performance:**
- Are I/O operations async?
- Did I add appropriate indexes?
- Is caching used where appropriate?
- Are N+1 query problems avoided?

**Documentation:**
- Do XML docs explain "why", not just "what"?
- Are complex algorithms commented?
- Is README updated?

**If issues found during reflection, fix them NOW before handoff.**

### 9. Run Tests

```bash
# Run all tests
dotnet test

# Check coverage
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=opencover

# Verify ≥80%
```

### 10. Commit Changes

```bash
git add .
git commit -m "feat: implement {feature} (#<STORY_ID>)

- Added ResourceController with CRUD operations
- Implemented ResourceService with business logic
- Created unit tests (75% coverage)
- Created integration tests (API endpoints)
- Updated README with setup instructions"
git push
```

### 11. Completion Checklist

Before handoff, verify:
- [ ] Code implemented following [Skills.md](../../Skills.md)
- [ ] Low-level design created (if complex)
- [ ] Unit tests written (70% of test budget)
- [ ] Integration tests written (20% of test budget)
- [ ] E2E tests written (10% of test budget)
- [ ] Test coverage ≥80%
- [ ] XML docs on all public APIs
- [ ] Inline comments for complex logic
- [ ] README updated
- [ ] Security checklist passed (no secrets, SQL parameterized)
- [ ] All tests passing
- [ ] No compiler warnings
- [ ] Code committed with proper message
- [ ] Story Status updated to "In Review" in Projects board

---

## Tools & Capabilities

### Research Tools

- `semantic_search` - Find code patterns, similar implementations
- `grep_search` - Search for specific functions, classes
- `file_search` - Locate source files, tests
- `read_file` - Read existing code, tests, configs
- `runSubagent` - Code pattern research, library comparisons, bug investigations

### Code Editing Tools

- `create_file` - Create new files
- `replace_string_in_file` - Edit existing code
- `multi_replace_string_in_file` - Batch edits (efficient for multiple files)

### Testing Tools

- `run_in_terminal` - Run tests, build, linting
- `get_errors` - Check compilation errors
- `test_failure` - Get test failure details

---

## 🔄 Handoff Protocol

### Step 1: Capture Context

Run context capture script:
```bash
# Bash
./.github/scripts/capture-context.sh engineer <STORY_ID>

# PowerShell
./.github/scripts/capture-context.ps1 -Role engineer -IssueNumber <STORY_ID>
```

### Step 2: Update Status to In Review

```json
// Update Status to "In Review" via GitHub Projects V2
// Status: In Progress → In Review
```

### Step 3: Trigger Next Agent (Automatic)

Agent X (YOLO) automatically triggers Reviewer workflow within 30 seconds.

**Manual trigger (if needed):**
```json
{
  "tool": "run_workflow",
  "args": {
    "owner": "jnPiyush",
    "repo": "AgentX",
    "workflow_id": "run-reviewer.yml",
    "ref": "master",
    "inputs": { "issue_number": "<STORY_ID>" }
  }
}
```

### Step 4: Post Handoff Comment

```json
{
  "tool": "add_issue_comment",
  "args": {
    "owner": "jnPiyush",
    "repo": "AgentX",
    "issue_number": <STORY_ID>,
    "body": "## ✅ Engineer Complete\n\n**Deliverables:**\n- Code: Commit <SHA>\n- Tests: X unit, Y integration, Z e2e\n- Coverage: {percentage}%\n- Documentation: README updated\n\n**Next:** Reviewer triggered"
  }
}
```

---

## 🔒 Enforcement (Cannot Bypass)

### Before Starting Work

1. ✅ **Verify prerequisite**: Parent Epic has Tech Spec (Status = Ready after Architect)
2. ✅ **Validate Tech Spec exists**: Check `docs/specs/SPEC-{feature-id}.md`
3. ✅ **Validate UX exists** (if `needs:ux` label): Check `docs/ux/UX-{feature-id}.md`
4. ✅ **Read story**: Understand acceptance criteria

### Before Updating Status to In Review

1. ✅ **Run validation script**:
   ```bash
   ./.github/scripts/validate-handoff.sh <issue_number> engineer
   ```
   **Checks**: Code committed, tests exist, coverage ≥80%

2. ✅ **Complete self-review checklist** (document in issue comment):
   - [ ] Low-level design created (if complex story)
   - [ ] Code quality (SOLID principles, DRY, clean code)
   - [ ] Test coverage (≥80%, unit + integration + e2e)
   - [ ] Documentation completeness (XML docs, inline comments)
   - [ ] Security verification (no secrets, SQL injection, XSS)
   - [ ] Error handling (try-catch, validation, logging)
   - [ ] Performance considerations (async, caching, queries)

3. ✅ **Capture context**:
   ```bash
   ./.github/scripts/capture-context.sh <issue_number> engineer
   ```

4. ✅ **All tests passing**: `dotnet test` exits with code 0

### Workflow Will Automatically

- ✅ Block if Tech Spec not present (Architect must complete first)
- ✅ Validate artifacts exist (code, tests, docs) before routing to Reviewer
- ✅ Post context summary to issue
- ✅ Trigger Reviewer workflow (<30s SLA)

### Recovery from Errors

If validation fails:
1. Fix the identified issue (failing tests, low coverage, missing docs)
2. Re-run validation script
3. Try handoff again (workflow will re-validate)

---

## References

- **Workflow**: [AGENTS.md](../../AGENTS.md) § Agent Roles
- **Standards**: [Skills.md](../../Skills.md) → All 18 skills

---

**Version**: 2.2 (Restructured)  
**Last Updated**: January 21, 2026


---

## Issue Details

### Title
Issue #100

### Description
No description available. Add details to Git notes.

### Labels
`type:feature`

### Status
spawned

---

## Dependencies

No dependencies specified.

---

## Acceptance Criteria

- [ ] No acceptance criteria specified

---

## Relevant Skills

### Skill #02: Testing

---
name: testing
description: 'Language-agnostic testing strategies including test pyramid (70% unit, 20% integration, 10% e2e), testing patterns, and 80%+ coverage requirements.'
---

# Testing

> **Purpose**: Language-agnostic testing strategies ensuring code quality and reliability.  
> **Goal**: 80%+ coverage with 70% unit, 20% integration, 10% e2e tests.  
> **Note**: For language-specific examples, see [C# Development](../csharp/SKILL.md) or [Python Development](../python/SKILL.md).

---

## Test Pyramid

```
        /\
       /E2E\      10% - Few (expensive, slow, brittle)
      /------\
     / Intg   \   20% - More (moderate cost/speed)
    /----------\
   /   Unit     \ 70% - Many (cheap, fast, reliable)
  /--------------\
```

**Why**: Unit tests catch bugs early, run fast, provide precise feedback. E2E tests validate workflows but are slow and flaky.

---

## Unit Testing

### Arrange-Act-Assert (AAA) Pattern

```
Test Structure:
  1. Arrange - Set up test data and dependencies
  2. Act - Execute the code being tested
  3. Assert - Verify the expected outcome

Example:
  test "calculateTotal returns sum of item prices":
    # Arrange
    cart = new ShoppingCart()
    cart.addItem(price: 10.00)
    cart.addItem(price: 25.00)
    
    # Act
    total = cart.calculateTotal()
    
    # Assert
    assert total == 35.00
```

### Test Naming Convention

```
Pattern: methodName_scenario_expectedBehavior

Examples:
  - getUser_validId_returnsUser
  - processPayment_invalidAmount_throwsError
  - calculateDiscount_newUser_applies10PercentOff
  - sendEmail_networkFailure_retriesThreeTimes
```

### Mocking Dependencies

**Mocking Pattern:**
```
test "getUser calls database with correct ID":
  # Arrange - Create mock
  mockDatabase = createMock(Database)
  mockDatabase.when("findById", 123).returns({id: 123, name: "John"})
  
  service = new UserService(mockDatabase)
  
  # Act
  user = service.getUser(123)
  
  # Assert
  assert user.name == "John"
  mockDatabase.verify("findById", 123).wasCalledOnce()
```

**Mocking Libraries by Language:**
- **.NET**: Moq, NSubstitute, FakeItEasy
- **Python**: unittest.mock, pytest-mock
- **Node.js**: Sinon, Jest mocks
- **Java**: Mockito, EasyMock
- **PHP**: PHPUnit mocks, Prophecy

### Test Data Builders

**Builder Pattern for Complex Objects:**
```
class UserBuilder:
  function withId(id):
    this.id = id
    return this
  
  function withEmail(email):
    this.email = email
    return this
  
  function build():
    return new User(this.id, this.email, ...)

# Usage in tests
test "createOrder requires valid user":
  user = new UserBuilder()
    .withId(123)
    .withEmail("test@example.com")
    .build()
  
  order = createOrder(user, items)
  assert order.userId == 123
```

---

## Integration Testing

### Test Database Interactions

**Integration Test Pattern:**
```
test "saveUser persists to database":
  # Arrange
  testDatabase = createTestDatabase()  # In-memory or test DB
  repository = new UserRepository(testDatabase)
  user = {email: "test@example.com", name: "Test User"}
  
  # Act
  savedUser = repository.save(user)
  retrievedUser = repository.findById(savedUser.id)
  
  # Assert
  assert retrievedUser.email == "test@example.com"
  
  # Cleanup
  testDatabase.cleanup()
```

**Test Database Strategies:**
- **In-Memory Database** - Fast, isolated (SQLite, H2)
- **Docker Container** - Real database, disposable
- **Test Database** - Separate instance, reset between tests
- **Transactions** - Rollback after each test

### Test API Endpoints

**HTTP API Integration Test:**
```
test "POST /users creates new user":
  # Arrange
  client = createTestClient(app)
  userData = {
    email: "newuser@example.com",
    name: "New User"
  }
  
  # Act
  response = client.post("/users", body: userData)
  
  # Assert
  assert response.status == 201
  assert response.body.email == "newuser@example.com"
  assert response.body.id exists
```

---

## End-to-End (E2E) Testing

### Browser Automation

**E2E Test Pattern:**
```
test "user can complete checkout flow":
  # Arrange
  browser = launchBrowser()
  page = browser.newPage()
  
  # Act
  page.goto("https://example.com")
  page.click("#add-to-cart-button")
  page.goto("/checkout")
  page.fill("#email", "user@example.com")
  page.fill("#credit-card", "4242424242424242")
  page.click("#place-order-button")
  
  # Assert
  page.waitForSelector(".order-confirmation")
  orderNumber = page.textContent(".order-number")
  assert orderNumber isNotEmpty
  
  # Cleanup
  browser.close()
```

**E2E Testing Tools:**
- **Playwright** - Modern, multi-browser
- **Cypress** - Developer-friendly, fast
- **Selenium** - Industry standard, widely supported
- **Puppeteer** - Chrome/Chromium focused

### E2E Best Practices

- Run E2E tests in CI/CD pipeline
- Use test data factories for consistent state
- Implement retry logic for flaky tests
- Run in parallel to reduce execution time
- Use unique test user accounts
- Clean up test data after runs

---

## Test Coverage

### Coverage Metrics

```
Coverage Types:
  - Line Coverage: % of code lines executed
  - Branch Coverage: % of if/else branches taken
  - Function Coverage: % of functions called
  - Statement Coverage: % of statements executed

Target: 80%+ overall coverage
```

**Coverage Tools by Language:**
- **.NET**: Coverlet, dotCover
- **Python**: coverage.py, pytest-cov
- **Node.js**: Istanbul (nyc), Jest
- **Java**: JaCoCo, Cobertura
- **PHP**: PHPUnit --coverage

### What to Test

**✅ Always Test:**
- Business logic and algorithms
- Data transformations
- Validation rules
- Error handling paths
- Edge cases and boundary conditions
- Security-critical code

**❌ Don't Test:**
- Third-party library internals
- Framework code
- Simple getters/setters (unless logic involved)
- Configuration files
- Auto-generated code

---

## Testing Best Practices

### Write Testable Code

**Testable Code Characteristics:**
```
✅ Single Responsibility Principle
✅ Dependency Injection
✅ Pure Functions (no side effects)
✅ Small, focused methods
✅ Minimal global state
✅ Clear interfaces

❌ Tightly coupled code
❌ Hidden dependencies
❌ God classes
❌ Hard-coded dependencies
❌ Static methods everywhere
```

### Test Fixtures

**Setup and Teardown:**
```
class UserServiceTests:
  # Run once before all tests
  beforeAll():
    testDatabase.connect()
  
  # Run before each test
  beforeEach():
    testDatabase.clear()
    seedTestData()
  
  # Run after each test
  afterEach():
    testDatabase.clear()
  
  # Run once after all tests
  afterAll():
    testDatabase.disconnect()
  
  test "getUser returns correct user":
    # Test uses clean database state
    user = service.getUser(1)
    assert user.name == "Test User"
```

### Parameterized Tests

**Data-Driven Testing:**
```
testCases = [
  {input: 0, expected: 0},
  {input: 1, expected: 1},
  {input: -1, expected: -1},
  {input: 100, expected: 100}
]

for each testCase in testCases:
  test "abs({testCase.input}) returns {testCase.expected}":
    result = abs(testCase.input)
    assert result == testCase.expected
```

---

## Test Organization

### Test File Structure

```
Project Structure:
  src/
    services/
      UserService
      PaymentService
    repositories/
      UserRepository
  
  tests/
    unit/
      services/
        UserService.test
        PaymentService.test
      repositories/
        UserRepository.test
    integration/
      api/
        UserEndpoints.test
        PaymentEndpoints.test
    e2e/
      checkout/
        CheckoutFlow.test
```

### Test Naming

**Descriptive Test Names:**
```
✅ Good:
  - test_getUser_withValidId_returnsUser
  - test_processPayment_whenInsufficientFunds_throwsError
  - test_calculateDiscount_forNewUser_applies10PercentOff

❌ Bad:
  - test1
  - testGetUser
  - testPayment
```

---

## Continuous Testing

### Run Tests in CI/CD

**CI Pipeline:**
```yaml
steps:
  1. Checkout code
  2. Install dependencies
  3. Run linter
  4. Run unit tests
  5. Run integration tests
  6. Generate coverage report
  7. Fail if coverage < 80%
  8. Run E2E tests (optional, can be separate pipeline)
```

### Test Automation

- Run tests on every commit
- Block PRs if tests fail
- Run tests in parallel for speed
- Retry flaky tests automatically
- Generate test reports
- Track test metrics over time

---

## Common Testing Pitfalls

| Issue | Problem | Solution |
|-------|---------|----------|
| **Flaky tests** | Tests pass/fail randomly | Fix timing issues, use retries, improve test isolation |
| **Slow tests** | Test suite takes too long | Parallelize, use in-memory DBs, mock external services |
| **Brittle tests** | Tests break with minor changes | Test behavior not implementation, use stable selectors |
| **Over-mocking** | Too many mocks, tests don't catch real bugs | Balance mocks with integration tests |
| **Under-testing** | Low coverage, bugs slip through | Follow test pyramid, aim for 80%+ coverage |
| **Untestable code** | Hard to write tests | Refactor for dependency injection, smaller functions |

---

## Testing Frameworks

**Unit Testing:**
- **.NET**: xUnit, NUnit, MSTest
- **Python**: pytest, unittest
- **Node.js**: Jest, Mocha, Vitest
- **Java**: JUnit, TestNG
- **PHP**: PHPUnit

**Integration Testing:**
- **API Testing**: REST Assured, Supertest, Postman/Newman
- **Database Testing**: Testcontainers, DbUnit

**E2E Testing:**
- **Browser**: Playwright, Cypress, Selenium, Puppeteer
- **Mobile**: Appium, Detox

---

## Resources

**Testing Guides:**
- [Test Pyramid - Martin Fowler](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Testing Best Practices](https://testingjavascript.com)
- [Google Testing Blog](https://testing.googleblog.com)

**Books:**
- "xUnit Test Patterns" by Gerard Meszaros
- "The Art of Unit Testing" by Roy Osherove
- "Growing Object-Oriented Software, Guided by Tests" by Steve Freeman

---

**See Also**: [Skills.md](../../../../Skills.md) • [AGENTS.md](../../../../AGENTS.md)

**Last Updated**: January 27, 2026


---

### Skill #04: Security

---
name: security
description: 'Language-agnostic production security practices covering OWASP Top 10, input validation, injection prevention, authentication/authorization, and secrets management.'
---

# Security

> **Purpose**: Language-agnostic security practices to protect against common vulnerabilities.  
> **Focus**: Input validation, injection prevention, authentication, secrets management.  
> **Note**: For language-specific implementations, see [C# Development](../../development/csharp/SKILL.md) or [Python Development](../../development/python/SKILL.md).

---

## OWASP Top 10 (2025)

1. **Broken Access Control** - Authorization failures, privilege escalation
2. **Cryptographic Failures** - Weak encryption, exposed secrets
3. **Injection** - SQL, NoSQL, command, LDAP injection
4. **Insecure Design** - Missing security controls in architecture
5. **Security Misconfiguration** - Default configs, unnecessary features enabled
6. **Vulnerable Components** - Outdated dependencies with known CVEs
7. **Authentication Failures** - Weak passwords, broken session management
8. **Software/Data Integrity** - Unsigned updates, insecure CI/CD
9. **Logging/Monitoring Failures** - Missing audit logs, delayed detection
10. **Server-Side Request Forgery (SSRF)** - Unvalidated URLs, internal network access

---

## Input Validation

### Validate All User Input

**Validation Pattern:**
```
1. Define validation rules (required, format, length, range)
2. Validate at API boundary BEFORE processing
3. Return clear, actionable error messages
4. Reject invalid data immediately
```

**Example Validation Rules:**
```yaml
email:
  required: true
  format: email
  max_length: 255

username:
  required: true
  min_length: 3
  max_length: 20
  pattern: "^[a-zA-Z0-9_]+$"
  message: "Only letters, numbers, and underscores"

age:
  required: true
  minimum: 13
  maximum: 120

url:
  format: url
  allowed_protocols: ["https"]
```

**Validation Libraries by Language:**
- **.NET**: FluentValidation, DataAnnotations
- **Python**: Pydantic, Marshmallow, Cerberus
- **Node.js**: Joi, Yup, Validator.js
- **Java**: Hibernate Validator, Bean Validation
- **PHP**: Respect\Validation, Symfony Validator

### Sanitize HTML Content

**HTML Sanitization Strategy:**
```
1. Define allowlist of safe tags (p, br, strong, em, a)
2. Define allowlist of safe attributes per tag
3. Remove all disallowed tags and attributes
4. Encode special characters in text content
5. Remove JavaScript event handlers (onclick, onerror, etc.)
```

**HTML Sanitization Libraries:**
- **.NET**: HtmlSanitizer (Ganss.Xss)
- **Python**: bleach, html5lib
- **Node.js**: DOMPurify, sanitize-html
- **Java**: OWASP Java HTML Sanitizer
- **PHP**: HTML Purifier

**Never Trust User HTML:**
- Strip all `<script>` tags
- Remove `javascript:` URLs
- Block `data:` URLs unless specifically needed
- Remove inline event handlers

---

## Injection Prevention

### SQL Injection

**❌ NEVER concatenate SQL queries:**
```sql
-- VULNERABLE - Attacker can inject SQL
query = "SELECT * FROM users WHERE email = '" + userInput + "'"
-- Injection: ' OR '1'='1' --
```

**✅ ALWAYS use parameterized queries:**
```sql
-- SAFE - Parameters separated from query
query = "SELECT * FROM users WHERE email = ?"
parameters = [userInput]

-- Or named parameters
query = "SELECT * FROM users WHERE email = @email"
parameters = {email: userInput}
```

**Parameterization Methods:**
- **Prepared Statements** - Precompile query, bind parameters
- **ORM Query Builders** - Use framework methods (WHERE, SELECT, etc.)
- **Stored Procedures** - Accept parameters, never concatenate inside
- **Parameterized APIs** - Use library's parameter binding

**Why This Works:**
- Parameters sent separately from SQL structure
- Database treats parameters as data, not executable code
- No string interpolation = no injection opportunity

### NoSQL Injection

**MongoDB Example (Vulnerable):**
```javascript
// VULNERABLE
db.users.find({username: userInput, password: userInput})
// Attacker input: {$gt: ""}
```

**Safe Approach:**
```javascript
// SAFE - Validate types and sanitize
db.users.find({
  username: {$eq: String(userInput)},  // Force string type
  password: {$eq: String(userInput)}
})
```

### Command Injection

**❌ NEVER pass user input to shell:**
```bash
# VULNERABLE
system("ping -c 1 " + userInput)
# Injection: 127.0.0.1; rm -rf /
```

**✅ Use safe APIs:**
- Use language-specific safe APIs (subprocess with array args)
- Validate input against strict allowlist
- Avoid shell execution entirely when possible
- Use libraries designed for the task (file operations, network calls)

---

## Authentication

### Password Storage

**❌ NEVER store plain text passwords:**
```
users:
  - username: john
    password: "MyPassword123"  # VULNERABLE
```

**✅ ALWAYS hash passwords with salt:**
```
users:
  - username: john
    password_hash: "$2b$12$xyz..."  # bcrypt hash with salt
```

**Password Hashing Algorithm Recommendations:**
1. **Argon2** (Best) - Winner of Password Hashing Competition
2. **bcrypt** (Good) - Industry standard, widely supported
3. **scrypt** (Good) - Memory-hard function
4. ❌ **SHA-256/MD5/SHA-1** (BAD) - Too fast, vulnerable to rainbow tables

**Password Hashing Pattern:**
```
function hashPassword(plainPassword):
    workFactor = 12  # Cost parameter (higher = slower = more secure)
    salt = generateRandomSalt()  # Unique per password
    hash = BCRYPT.hash(plainPassword, salt, workFactor)
    return hash  # Format: $algorithm$workFactor$salt$hash

function verifyPassword(plainPassword, storedHash):
    return BCRYPT.verify(plainPassword, storedHash)
```

**Password Requirements:**
- Minimum 8 characters (12+ recommended)
- No maximum length (allow passphrases)
- Check against common password lists
- Implement rate limiting on login attempts

### JWT Authentication

**Token Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id",
    "username": "john",
    "roles": ["user", "admin"],
    "iat": 1642531200,
    "exp": 1642534800
  },
  "signature": "..."
}
```

**JWT Best Practices:**
- Use strong signing algorithm (HS256, RS256)
- Set short expiration time (15-60 minutes)
- Store secret key in environment variables
- Validate issuer, audience, expiration
- Use refresh tokens for long-lived sessions
- Invalidate tokens on logout (token blacklist)

**JWT Validation Checklist:**
- ✅ Verify signature
- ✅ Check expiration time
- ✅ Validate issuer and audience
- ✅ Ensure algorithm matches expected
- ✅ Check token format and structure

---

## Authorization

### Role-Based Access Control (RBAC)

**Authorization Pattern:**
```
Roles:
  - Admin: Full access to all resources
  - Editor: Can create/edit content
  - Viewer: Read-only access

Permissions:
  - users:create
  - users:read
  - users:update
  - users:delete

Role-Permission Mapping:
  Admin: [users:*, posts:*, settings:*]
  Editor: [posts:create, posts:update, posts:read]
  Viewer: [posts:read]
```

**Authorization Check Pattern:**
```
function authorize(user, requiredPermission):
    userPermissions = getAllPermissions(user.roles)
    return userPermissions.contains(requiredPermission)

function handleDeleteUser(request, userId):
    currentUser = authenticate(request)
    
    if not authorize(currentUser, "users:delete"):
        return 403 Forbidden
    
    deleteUser(userId)
    return 204 No Content
```

### Attribute-Based Access Control (ABAC)

**Resource Ownership Pattern:**
```
function canEdit(user, post):
    # User can edit if they are:
    # 1. The post owner, OR
    # 2. An admin
    return post.authorId == user.id OR user.roles.contains("Admin")
```

---

## Secrets Management

### Environment Variables

**❌ NEVER hardcode secrets:**
```json
{
  "database": {
    "password": "SuperSecret123"  // VULNERABLE - in source control
  },
  "apiKeys": {
    "stripe": "sk_live_abcd1234"  // VULNERABLE - exposed
  }
}
```

**✅ Use environment variables:**
```
Configuration:
  database:
    password: ${DB_PASSWORD}  # From environment
  apiKeys:
    stripe: ${STRIPE_API_KEY}  # From environment
```

**Environment Variable Best Practices:**
- Never commit secrets to source control
- Use different secrets per environment (dev/staging/prod)
- Rotate secrets regularly
- Audit secret access logs
- Use secrets management service for production

### Secrets Management Services

**Cloud Providers:**
- **AWS**: AWS Secrets Manager, Parameter Store
- **Azure**: Azure Key Vault
- **GCP**: Google Secret Manager
- **HashiCorp**: Vault

**Access Pattern:**
```
1. Application authenticates with cloud provider (IAM role/managed identity)
2. Request secret by name/ID
3. Secret returned encrypted in transit
4. Cache secret in memory (not disk)
5. Rotate secrets without redeploying application
```

---

## HTTPS / TLS

### Enforce HTTPS Everywhere

**Security Headers:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: no-referrer-when-downgrade
```

**TLS Configuration:**
- Use TLS 1.2 or 1.3 (disable TLS 1.0, 1.1)
- Use strong cipher suites
- Enable HSTS (HTTP Strict Transport Security)
- Use valid certificates from trusted CA
- Implement certificate pinning for mobile apps

---

## Security Checklist

**Before Production:**
- [ ] All user input validated and sanitized
- [ ] SQL queries use parameterized statements
- [ ] Passwords hashed with bcrypt/Argon2
- [ ] Secrets in environment variables or vault
- [ ] HTTPS enforced with HSTS
- [ ] Security headers configured
- [ ] Authentication and authorization implemented
- [ ] Rate limiting on authentication endpoints
- [ ] CORS configured restrictively
- [ ] Dependencies scanned for vulnerabilities
- [ ] Sensitive data encrypted at rest
- [ ] Security audit logs enabled
- [ ] Error messages don't leak sensitive info
- [ ] File uploads validated and scanned
- [ ] API endpoints have input size limits

---

## Common Vulnerabilities

| Vulnerability | Attack | Prevention |
|---------------|--------|------------|
| **SQL Injection** | `' OR '1'='1` | Parameterized queries |
| **XSS** | `<script>alert(1)</script>` | HTML sanitization, CSP |
| **CSRF** | Forged cross-site request | CSRF tokens, SameSite cookies |
| **Path Traversal** | `../../etc/passwd` | Validate paths, use allowlist |
| **XXE** | XML external entity | Disable external entities |
| **Insecure Deserialization** | Malicious serialized object | Validate before deserializing |
| **Open Redirect** | `?redirect=evil.com` | Validate redirect URLs |

---

## Resources

**Security Standards:**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org)
- [CWE Top 25](https://cwe.mitre.org/top25/)

**Tools:**
- **Dependency Scanning**: Snyk, Dependabot, OWASP Dependency-Check
- **SAST**: SonarQube, CodeQL, Semgrep
- **DAST**: OWASP ZAP, Burp Suite
- **Secrets Scanning**: GitGuardian, TruffleHog, git-secrets

---

**See Also**: [Skills.md](../../../../Skills.md) • [AGENTS.md](../../../../AGENTS.md)

**Last Updated**: January 27, 2026



---

### Skill #11: Documentation

---
name: documentation
description: 'Language-agnostic documentation patterns including inline docs, README structure, API documentation, and code comments best practices.'
---

# Documentation

> **Purpose**: Write clear, maintainable documentation for code and APIs.  
> **Goal**: Self-documenting code, useful comments, comprehensive READMEs.  
> **Note**: For implementation, see [C# Development](../csharp/SKILL.md) or [Python Development](../python/SKILL.md).

---

## Documentation Hierarchy

```
Documentation Pyramid:

        /\
       /API\        External API docs (OpenAPI/Swagger)
      /------\
     / README \     Project documentation
    /----------\
   / Inline Docs\   Function/class documentation
  /--------------\
 /  Code Quality  \ Self-documenting code (naming, structure)
/------------------\

Best Code = Minimal comments needed
```

---

## Self-Documenting Code

### Code Should Explain WHAT

```
❌ Bad: Needs comment to understand
  # Check if user can access
  if u.r == 1 or u.r == 2:
    return True

✅ Good: Self-explanatory
  if user.role == Role.ADMIN or user.role == Role.MODERATOR:
    return True

✅ Better: Extract to function
  if user.hasModeratorPermissions():
    return True
```

### Names Should Be Descriptive

```
Variables:
  ❌ d, tmp, data, x
  ✅ daysSinceLastLogin, userCount, orderTotal

Functions:
  ❌ process(), handle(), do()
  ✅ calculateShippingCost(), validateEmailFormat(), sendWelcomeEmail()

Classes:
  ❌ Manager, Handler, Processor, Helper
  ✅ OrderRepository, EmailValidator, PaymentGateway
```

---

## Inline Documentation

### When to Document

```
✅ DOCUMENT:
  - Public APIs (functions, classes exposed to others)
  - Complex algorithms (why this approach)
  - Non-obvious behavior (edge cases, gotchas)
  - Business rules (why this validation)
  - Workarounds (link to issue/bug)

❌ DON'T DOCUMENT:
  - Obvious code (// increment counter)
  - Implementation details that might change
  - What the code does (code shows that)
```

### Documentation Template

```
Function Documentation Structure:

  Brief one-line description.

  Longer description if needed. Explain the purpose,
  not the implementation.

  Parameters:
    paramName: Description of parameter
    
  Returns:
    Description of return value
    
  Raises/Throws:
    ExceptionType: When this exception is thrown
    
  Example:
    code example showing usage
```

### Examples

```
Good Documentation:

  """
  Calculate shipping cost based on weight and destination.
  
  Uses zone-based pricing with a base rate plus per-kg charge.
  International shipments have additional customs handling fee.
  
  Args:
    weight_kg: Package weight in kilograms (must be positive)
    destination: ISO 3166-1 country code (e.g., "US", "GB")
    
  Returns:
    Shipping cost in USD
    
  Raises:
    ValueError: If weight is negative or zero
    InvalidDestinationError: If country code is not supported
    
  Example:
    >>> calculate_shipping(2.5, "US")
    15.99
  """
```

---

## Comments

### When to Use Comments

```
Use Comments For:

1. WHY, not WHAT
   # Using binary search because list is sorted and frequently queried
   index = binarySearch(sortedList, target)

2. Complex business logic
   # Discount applies only to first-time customers who
   # ordered within 30 days of account creation (PROMO-2024-Q1)
   if isEligibleForNewUserDiscount(user):

3. Warnings and gotchas
   # WARNING: This API has a rate limit of 100 req/min
   # See: https://api.example.com/docs/rate-limits
   
4. TODO with context
   # TODO(ticket-123): Refactor when payment v2 API is available
   
5. References
   # Algorithm from: https://en.wikipedia.org/wiki/Example
```

### Comment Anti-Patterns

```
❌ Redundant Comments:
  i = i + 1  # Increment i by 1

❌ Outdated Comments:
  # Returns the user's email
  function getUserName():  # Actually returns name now

❌ Commented-Out Code:
  # old_method()
  # another_old_method()
  new_method()

❌ Noise Comments:
  ###################################
  # BEGIN USER PROCESSING SECTION   #
  ###################################
```

---

## README Structure

### Essential Sections

```markdown
# Project Name

One-paragraph description of what this project does.

## Features

- Feature 1: Brief description
- Feature 2: Brief description

## Quick Start

Minimal steps to get running:

```bash
git clone <repo>
cd project
./setup.sh
./run.sh
```

## Installation

### Prerequisites

- Requirement 1 (version)
- Requirement 2 (version)

### Steps

1. Install dependencies
2. Configure environment
3. Run migrations

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | Database connection | localhost |

## Usage

Show common use cases with code examples.

## API Reference

Link to API documentation or brief overview.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License - see [LICENSE](LICENSE)
```

### README Best Practices

```
✅ DO:
  - Start with what the project does
  - Show working code examples
  - Keep installation steps minimal
  - Include troubleshooting for common issues
  - Update when features change

❌ DON'T:
  - Start with badges and shields
  - Assume knowledge of your stack
  - Skip the "why" of the project
  - Include outdated examples
```

---

## API Documentation

### OpenAPI/Swagger

```
API Documentation Should Include:

Endpoint Information:
  - HTTP method and path
  - Description of what it does
  - Authentication requirements

Request:
  - Path parameters
  - Query parameters
  - Request body schema
  - Example request

Response:
  - Status codes and meanings
  - Response body schema
  - Example responses

Errors:
  - Error codes
  - Error messages
  - How to handle
```

### API Documentation Example

```yaml
/users/{userId}:
  get:
    summary: Get user by ID
    description: |
      Retrieves detailed information about a specific user.
      Requires authentication. Users can only access their own data
      unless they have admin role.
    parameters:
      - name: userId
        in: path
        required: true
        schema:
          type: integer
        description: Unique user identifier
    responses:
      200:
        description: User found
        content:
          application/json:
            example:
              id: 123
              email: user@example.com
              name: John Doe
      404:
        description: User not found
      403:
        description: Access denied
```

---

## Architecture Documentation

### Architecture Decision Records (ADRs)

```
ADR Template:

# ADR-001: Use PostgreSQL for Primary Database

## Status
Accepted

## Context
We need a database that supports complex queries, transactions,
and can handle our expected load of 10K requests/second.

## Decision
We will use PostgreSQL 16 as our primary database.

## Consequences
### Positive
- ACID compliance
- Rich query capabilities
- Strong community support

### Negative
- Requires more operational expertise than managed NoSQL
- Vertical scaling limitations

## Alternatives Considered
- MongoDB: Rejected due to transaction requirements
- MySQL: PostgreSQL has better JSON support
```

### When to Write ADRs

```
Write ADR For:
  - Technology choices (database, framework, cloud provider)
  - Architecture patterns (microservices vs monolith)
  - Security decisions (auth strategy, encryption)
  - Integration approaches (sync vs async)
  - Breaking changes to existing patterns
```

---

## Documentation Tools

| Type | Tools |
|------|-------|
| **API Docs** | OpenAPI/Swagger, Postman, Redoc |
| **Code Docs** | DocFX, Sphinx, JSDoc, Typedoc |
| **Architecture** | C4 Model, Mermaid, PlantUML |
| **Wiki/Guides** | Notion, Confluence, GitBook, MkDocs |
| **Diagrams** | Draw.io, Lucidchart, Excalidraw |

---

## Best Practices Summary

| Practice | Description |
|----------|-------------|
| **Code first** | Write self-documenting code before adding comments |
| **Document why** | Explain intent, not mechanics |
| **Keep updated** | Wrong docs are worse than no docs |
| **Examples** | Show, don't just tell |
| **Audience** | Write for the reader, not yourself |
| **Minimal** | Document what's needed, no more |
| **Accessible** | Store docs near the code |
| **Versioned** | Docs in repo, not external wikis |

---

**See Also**: [API Design](.github/skills/architecture/api-design/SKILL.md) • [C# Development](../csharp/SKILL.md) • [Python Development](../python/SKILL.md)


---

## References

No references specified.

---

## Execution Checklist

- [ ] Review this context completely
- [ ] Generate execution plan
- [ ] Pass pre-flight validation
- [ ] Execute work
- [ ] Pass handoff validation (DoD)
- [ ] Update status

---

*Generated by ContextWeave v0.1.0*
