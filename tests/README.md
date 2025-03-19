# State of Mika SDK Tests

This directory contains tests for the State of Mika SDK.

## Test Files

- `test_claude_integration.py`: Unit tests for the Claude adapter integration
- `test_end_to_end.py`: End-to-end integration test simulating the complete flow from LLM request to result
- `run_tests.py`: Test runner script that executes both test modules and displays results

## Running Tests

### Option 1: Using the test runner script

From the project root directory, run:

```bash
./run_tests.sh
```

This will:
1. Activate the virtual environment if present
2. Verify you're in the project root
3. Run all the tests
4. Generate a test_results.log file with detailed logs

### Option 2: Running tests directly

You can also run the tests directly with Python:

```bash
# Run all tests using the test runner
python tests/run_tests.py

# Run only the Claude integration tests
python -m unittest tests/test_claude_integration.py

# Run only the end-to-end test
python -m tests.test_end_to_end
```

## Test Output

The test output includes:
- Detailed logging of each step in the process
- Success/failure status for each test
- Execution time for end-to-end tests
- Overall test summary with pass percentages

All logs are also written to `test_results.log` in the current directory.

## Creating New Tests

When creating new tests:
1. Add your test file to this directory
2. Import your test module in `run_tests.py` if you want it included in the automated test runner
3. Follow the existing pattern of detailed logging to maintain consistency 