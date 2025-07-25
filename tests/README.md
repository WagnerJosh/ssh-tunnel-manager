# Tests for SSH Tunnel Manager

This directory contains the test suite for the SSH Tunnel Manager project, built using pytest.

## Overview

The test suite provides comprehensive coverage of the output formatting functionality, including:

- **Output Format Enum**: Tests for all supported output formats (JSON, YAML, TOML, TABLE)
- **Helper Functions**: Tests for column styling and status value formatting
- **Encoder Functions**: Individual tests for each output format encoder
- **Integration Tests**: End-to-end testing of the format_output function
- **Edge Cases**: Handling of empty data, special characters, and various data types
- **Real-world Scenarios**: Tests with realistic SSH tunnel data

## Test Structure

### Test Files

- `test_output.py` - Comprehensive tests for the output formatting module
- `__init__.py` - Package initialization

### Test Classes

1. **TestOutputFormat** - Tests the OutputFormat enum
2. **TestHelperFunctions** - Tests utility functions for table formatting
3. **TestEncoderFunctions** - Tests individual format encoders
4. **TestFormatOutput** - Tests the main format_output function
5. **TestEncoderRegistry** - Tests the encoder registry system
6. **TestGetSupportedFormats** - Tests format enumeration
7. **TestRealWorldScenarios** - Tests with realistic data
8. **TestEdgeCases** - Tests edge cases and error conditions

## Running Tests

### Basic Test Run

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_output.py

# Run specific test class
python -m pytest tests/test_output.py::TestOutputFormat

# Run specific test method
python -m pytest tests/test_output.py::TestOutputFormat::test_output_format_values
```

### Using the Test Runner Script

```bash
# Basic test run
python run_tests.py

# Run with coverage (requires coverage package)
python run_tests.py --coverage

# Show help
python run_tests.py --help
```

### Test Configuration

The project uses pytest configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Test Coverage

The test suite covers:

### Core Functionality
- ✅ All output formats (JSON, YAML, TOML, TABLE)
- ✅ Rich table formatting with colors and styling
- ✅ Status-based color coding
- ✅ Column styling and alignment
- ✅ Custom table titles
- ✅ Empty data handling

### Data Types
- ✅ String values
- ✅ Numeric values (integers, floats)
- ✅ Boolean values
- ✅ None/null values
- ✅ Unicode characters
- ✅ Special characters in URLs

### Edge Cases
- ✅ Empty datasets
- ✅ Missing fields in data
- ✅ Very long values
- ✅ Inconsistent data structures
- ✅ Invalid format types

### Error Handling
- ✅ Unsupported format errors
- ✅ Malformed data handling
- ✅ Type conversion errors

## Sample Test Data

Tests use realistic SSH tunnel data:

```python
sample_data = [
    {
        "name": "web-development",
        "local_port": "8080",
        "remote_host": "dev.example.com",
        "remote_port": "80",
        "status": "active",
        "user": "developer",
    },
    {
        "name": "database-tunnel",
        "local_port": "5432",
        "remote_host": "db.internal.com",
        "remote_port": "5432",
        "status": "inactive",
        "user": "dbadmin",
    },
]
```

## Adding New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test Structure

```python
class TestNewFeature:
    """Test new feature functionality."""

    @pytest.fixture
    def sample_data(self):
        """Provide test data."""
        return [...] 

    def test_basic_functionality(self, sample_data):
        """Test basic functionality."""
        result = function_under_test(sample_data)
        assert result is not None
        assert "expected_value" in result

    def test_edge_case(self):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### Best Practices

1. **Use descriptive test names** that explain what is being tested
2. **Group related tests** in classes
3. **Use pytest fixtures** for common test data
4. **Test both success and failure cases**
5. **Include docstrings** explaining the test purpose
6. **Keep tests independent** - each test should be able to run in isolation
7. **Use appropriate assertions** - be specific about what you're checking

## Dependencies

The test suite requires:

- `pytest>=8.3.5` - Testing framework
- `toml` - TOML parsing for testing TOML output
- `yaml` - YAML parsing for testing YAML output
- `rich` - Table formatting library

Optional dependencies:
- `coverage` - For test coverage reporting

## Continuous Integration

Tests are designed to run in CI environments with:

- Strict marker and configuration checking
- Short traceback format for cleaner output
- Quiet mode for less verbose CI logs
- Automatic test discovery

## Expected Output

When all tests pass, you should see output like:

```
=========================== test session starts ============================
collected 39 items

tests/test_output.py .......................................         [100%]

============================ 39 passed in 0.21s ============================
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the project is installed or PYTHONPATH includes the src directory
2. **Missing Dependencies**: Install test dependencies with `pip install -e ".[dev]"`
3. **Rich Table Issues**: Check that Rich is properly installed and console supports colors

### Debugging Tests

```bash
# Run with detailed output
python -m pytest -vv

# Run with Python debugger on failures
python -m pytest --pdb

# Show local variables in tracebacks
python -m pytest -l

# Stop on first failure
python -m pytest -x
```

## Contributing

When adding new functionality to the output module:

1. Write tests first (TDD approach)
2. Ensure all existing tests still pass
3. Add tests for new edge cases
4. Update this README if adding new test categories
5. Maintain test coverage above 90%

## Future Enhancements

Potential areas for additional testing:

- Performance tests for large datasets
- Memory usage tests
- Internationalization support
- Custom color scheme tests
- Table width and wrapping tests
- Export functionality tests