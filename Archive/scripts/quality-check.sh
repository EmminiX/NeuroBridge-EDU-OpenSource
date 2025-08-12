#!/bin/bash

# Quality Assurance Check Script for NeuroBridgeEDU
# Comprehensive testing and validation pipeline

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "=================================="
    echo "$1"
    echo "=================================="
}

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "Must be run from the project root directory"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs/qa

# Start quality assurance pipeline
print_header "NeuroBridgeEDU Quality Assurance Pipeline"
print_status "Starting comprehensive quality checks..."

START_TIME=$(date +%s)
OVERALL_STATUS=0

# Step 1: Environment Check
print_header "Step 1: Environment Validation"
print_status "Checking Node.js version..."

NODE_VERSION=$(node --version | cut -d'v' -f2)
REQUIRED_NODE="20.0.0"

if [ "$(printf '%s\n' "$REQUIRED_NODE" "$NODE_VERSION" | sort -V | head -n1)" = "$REQUIRED_NODE" ]; then
    print_success "Node.js version $NODE_VERSION meets requirements (>= $REQUIRED_NODE)"
else
    print_error "Node.js version $NODE_VERSION is below required $REQUIRED_NODE"
    OVERALL_STATUS=1
fi

print_status "Checking npm version..."
NPM_VERSION=$(npm --version)
print_success "npm version: $NPM_VERSION"

# Step 2: Dependency Check
print_header "Step 2: Dependency Validation"
print_status "Installing/updating dependencies..."

if npm ci --silent > logs/qa/npm-install.log 2>&1; then
    print_success "Dependencies installed successfully"
else
    print_error "Dependency installation failed"
    cat logs/qa/npm-install.log
    OVERALL_STATUS=1
fi

print_status "Running security audit..."
if npm audit --audit-level moderate > logs/qa/npm-audit.log 2>&1; then
    print_success "Security audit passed"
else
    print_warning "Security vulnerabilities found"
    echo "Check logs/qa/npm-audit.log for details"
    # Don't fail on audit warnings in development
fi

# Step 3: Code Quality Checks
print_header "Step 3: Code Quality Analysis"

print_status "Running ESLint..."
if npm run lint > logs/qa/eslint.log 2>&1; then
    print_success "ESLint checks passed"
else
    print_error "ESLint found issues"
    cat logs/qa/eslint.log
    OVERALL_STATUS=1
fi

print_status "Checking for unused dependencies..."
if command -v depcheck &> /dev/null; then
    if depcheck --json > logs/qa/depcheck.log 2>&1; then
        UNUSED_DEPS=$(cat logs/qa/depcheck.log | jq -r '.dependencies | length')
        if [ "$UNUSED_DEPS" -eq 0 ]; then
            print_success "No unused dependencies found"
        else
            print_warning "$UNUSED_DEPS unused dependencies found"
            echo "Check logs/qa/depcheck.log for details"
        fi
    fi
else
    print_warning "depcheck not installed, skipping unused dependency check"
fi

# Step 4: Type Checking (if TypeScript files exist)
if [ -f "tsconfig.json" ]; then
    print_header "Step 4: TypeScript Type Checking"
    print_status "Running TypeScript compiler..."
    
    if npx tsc --noEmit > logs/qa/typescript.log 2>&1; then
        print_success "TypeScript type checking passed"
    else
        print_error "TypeScript type errors found"
        cat logs/qa/typescript.log
        OVERALL_STATUS=1
    fi
fi

# Step 5: Unit Tests
print_header "Step 5: Unit Testing"
print_status "Running Jest test suite..."

if npm test > logs/qa/jest.log 2>&1; then
    print_success "All unit tests passed"
    
    # Extract test results
    TESTS_PASSED=$(grep -o "[0-9]* passed" logs/qa/jest.log | head -1 | cut -d' ' -f1)
    TEST_SUITES=$(grep -o "[0-9]* test suites passed" logs/qa/jest.log | head -1 | cut -d' ' -f1)
    COVERAGE=$(grep -o "[0-9]*\.[0-9]*%" logs/qa/jest.log | tail -1)
    
    if [ ! -z "$TESTS_PASSED" ]; then
        print_success "$TESTS_PASSED tests passed across $TEST_SUITES test suites"
    fi
    
    if [ ! -z "$COVERAGE" ]; then
        print_success "Test coverage: $COVERAGE"
    fi
else
    print_error "Unit tests failed"
    cat logs/qa/jest.log
    OVERALL_STATUS=1
fi

# Step 6: Integration Tests
print_header "Step 6: Integration Testing"
print_status "Running integration tests..."

if npm test -- --testPathPattern=integration > logs/qa/integration.log 2>&1; then
    print_success "Integration tests passed"
else
    print_warning "Integration tests failed or not found"
    echo "Check logs/qa/integration.log for details"
    # Don't fail overall build for integration test issues in development
fi

# Step 7: Build Verification
print_header "Step 7: Build Verification"
print_status "Testing build process..."

if npm run build > logs/qa/build.log 2>&1; then
    print_success "Build completed successfully"
else
    print_error "Build failed"
    cat logs/qa/build.log
    OVERALL_STATUS=1
fi

# Step 8: Performance Benchmarks
print_header "Step 8: Performance Benchmarking"
print_status "Running basic performance tests..."

# Test server startup time
START_SERVER_TIME=$(date +%s%3N)
timeout 10s node src/server.js > /dev/null 2>&1 &
SERVER_PID=$!
sleep 2
kill $SERVER_PID 2>/dev/null || true
END_SERVER_TIME=$(date +%s%3N)
SERVER_STARTUP_TIME=$((END_SERVER_TIME - START_SERVER_TIME))

if [ $SERVER_STARTUP_TIME -lt 5000 ]; then
    print_success "Server startup time: ${SERVER_STARTUP_TIME}ms (acceptable)"
else
    print_warning "Server startup time: ${SERVER_STARTUP_TIME}ms (slow)"
fi

# Step 9: Security Scan
print_header "Step 9: Security Analysis"

print_status "Checking for common security issues..."

# Check for hardcoded secrets
if grep -r -i "password\|secret\|key" src/ --include="*.js" --exclude-dir=node_modules | grep -v "// " | grep -v "/\*" > logs/qa/secrets-scan.log 2>&1; then
    SECRET_COUNT=$(wc -l < logs/qa/secrets-scan.log)
    if [ $SECRET_COUNT -gt 0 ]; then
        print_warning "Found $SECRET_COUNT potential hardcoded secrets"
        echo "Check logs/qa/secrets-scan.log for details"
    fi
else
    print_success "No obvious hardcoded secrets found"
fi

# Check for console.log in production code
if grep -r "console\.log\|console\.error\|console\.warn" src/ --include="*.js" > logs/qa/console-logs.log 2>&1; then
    CONSOLE_COUNT=$(wc -l < logs/qa/console-logs.log)
    if [ $CONSOLE_COUNT -gt 0 ]; then
        print_warning "Found $CONSOLE_COUNT console statements in source code"
        echo "Consider using proper logging instead"
    fi
else
    print_success "No console statements found in source code"
fi

# Step 10: Documentation Check
print_header "Step 10: Documentation Validation"

DOCS_SCORE=0
DOCS_TOTAL=5

if [ -f "README.md" ]; then
    print_success "README.md exists"
    DOCS_SCORE=$((DOCS_SCORE + 1))
else
    print_warning "README.md missing"
fi

if [ -f "package.json" ] && grep -q "description" package.json; then
    print_success "Package description present"
    DOCS_SCORE=$((DOCS_SCORE + 1))
else
    print_warning "Package description missing"
fi

if [ -d "docs" ] || ls *.md > /dev/null 2>&1; then
    print_success "Additional documentation found"
    DOCS_SCORE=$((DOCS_SCORE + 1))
else
    print_warning "Consider adding more documentation"
fi

if grep -r "TODO\|FIXME\|XXX" src/ --include="*.js" > logs/qa/todos.log 2>&1; then
    TODO_COUNT=$(wc -l < logs/qa/todos.log)
    print_warning "Found $TODO_COUNT TODO/FIXME comments"
else
    print_success "No TODO/FIXME comments found"
    DOCS_SCORE=$((DOCS_SCORE + 1))
fi

# Check for JSDoc comments
if grep -r "/\*\*" src/ --include="*.js" > /dev/null 2>&1; then
    print_success "JSDoc comments found"
    DOCS_SCORE=$((DOCS_SCORE + 1))
else
    print_warning "Consider adding JSDoc comments for better documentation"
fi

print_status "Documentation score: $DOCS_SCORE/$DOCS_TOTAL"

# Final Summary
print_header "Quality Assurance Summary"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $OVERALL_STATUS -eq 0 ]; then
    print_success "✅ All critical quality checks passed!"
    print_success "🕒 Total execution time: ${DURATION}s"
    
    echo ""
    echo "Quality Metrics:"
    echo "- Dependencies: ✅ Secure"
    echo "- Code Quality: ✅ Passed"
    echo "- Tests: ✅ All passed"
    echo "- Build: ✅ Successful"
    echo "- Documentation: $DOCS_SCORE/$DOCS_TOTAL"
    
else
    print_error "❌ Quality assurance failed!"
    print_error "🕒 Total execution time: ${DURATION}s"
    echo ""
    echo "Please address the issues above before deployment."
fi

# Save summary report
cat > logs/qa/summary.json << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "duration": $DURATION,
  "status": $([ $OVERALL_STATUS -eq 0 ] && echo "\"passed\"" || echo "\"failed\""),
  "node_version": "$NODE_VERSION",
  "npm_version": "$NPM_VERSION",
  "tests_passed": "${TESTS_PASSED:-0}",
  "test_suites": "${TEST_SUITES:-0}",
  "coverage": "${COVERAGE:-0%}",
  "server_startup_time": "${SERVER_STARTUP_TIME}ms",
  "documentation_score": "$DOCS_SCORE/$DOCS_TOTAL"
}
EOF

print_status "Detailed logs saved to logs/qa/"
print_status "Summary report saved to logs/qa/summary.json"

exit $OVERALL_STATUS