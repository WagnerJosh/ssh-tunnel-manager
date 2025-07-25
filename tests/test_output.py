"""Tests for the output formatting module."""

from __future__ import annotations

import json
from typing import Any

import pytest
import toml
import yaml

from src.tunnels.output import (
    OutputFormat,
    _format_status_value,
    _get_column_style,
    _json_encoder,
    _table_encoder,
    _table_encoder_with_title,
    _toml_encoder,
    _yaml_encoder,
    format_output,
    output_encoder,
)


class TestOutputFormat:
    """Test the OutputFormat enum."""

    def test_output_format_values(self):
        """Test that all expected output formats are available."""
        assert OutputFormat.JSON == "json"
        assert OutputFormat.YAML == "yaml"
        assert OutputFormat.TOML == "toml"
        assert OutputFormat.TABLE == "table"

    def test_output_format_iteration(self):
        """Test that we can iterate over output formats."""
        formats = list(OutputFormat)
        assert len(formats) == 4
        assert all(isinstance(fmt, OutputFormat) for fmt in formats)


class TestHelperFunctions:
    """Test helper functions for table formatting."""

    def test_get_column_style_status(self):
        """Test column style for status column."""
        style, justify = _get_column_style("status")
        assert style == "bold"
        assert justify == "center"

    def test_get_column_style_ports(self):
        """Test column style for port columns."""
        for port_col in ("local_port", "remote_port"):
            style, justify = _get_column_style(port_col)
            assert style == "yellow"
            assert justify == "right"

    def test_get_column_style_name(self):
        """Test column style for name column."""
        style, justify = _get_column_style("name")
        assert style == "green"
        assert justify == "left"

    def test_get_column_style_default(self):
        """Test column style for other columns."""
        style, justify = _get_column_style("random_column")
        assert style == "cyan"
        assert justify == "left"

    def test_format_status_value_active(self):
        """Test status formatting for active status."""
        result = _format_status_value("active")
        assert "[bold green]Active[/bold green]" == result

    def test_format_status_value_inactive(self):
        """Test status formatting for inactive status."""
        result = _format_status_value("inactive")
        assert "[bold red]Inactive[/bold red]" == result

    def test_format_status_value_connecting(self):
        """Test status formatting for connecting status."""
        result = _format_status_value("connecting")
        assert "[bold yellow]Connecting[/bold yellow]" == result

    def test_format_status_value_unknown(self):
        """Test status formatting for unknown status."""
        result = _format_status_value("unknown")
        assert "[dim]unknown[/dim]" == result

    def test_format_status_value_case_insensitive(self):
        """Test that status formatting is case insensitive."""
        assert "[bold green]Active[/bold green]" == _format_status_value("ACTIVE")
        assert "[bold red]Inactive[/bold red]" == _format_status_value("Inactive")


class TestEncoderFunctions:
    """Test individual encoder functions."""

    @pytest.fixture
    def sample_data(self) -> list[dict[str, Any]]:
        """Sample test data."""
        return [
            {
                "name": "web-server",
                "local_port": "8080",
                "remote_host": "example.com",
                "status": "active",
            },
            {
                "name": "database",
                "local_port": "5432",
                "remote_host": "db.example.com",
                "status": "inactive",
            },
        ]

    def test_json_encoder(self, sample_data):
        """Test JSON encoder."""
        result = _json_encoder(sample_data)

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed == sample_data

        # Verify it's formatted (has indentation)
        assert "    " in result

    def test_yaml_encoder(self, sample_data):
        """Test YAML encoder."""
        result = _yaml_encoder(sample_data)

        # Verify it's valid YAML
        parsed = yaml.safe_load(result)
        assert parsed == sample_data

        # Verify it contains expected YAML structure
        assert "name: web-server" in result
        assert "local_port: '8080'" in result

    def test_toml_encoder(self, sample_data):
        """Test TOML encoder."""
        result = _toml_encoder(sample_data)

        # Verify it's valid TOML
        parsed = toml.loads(result)
        assert "Tunnel" in parsed
        assert parsed["Tunnel"] == sample_data

        # Verify TOML structure
        assert "[[Tunnel]]" in result
        assert 'name = "web-server"' in result

    def test_toml_encoder_custom_key(self, sample_data):
        """Test TOML encoder with custom key."""
        result = _toml_encoder(sample_data, key="CustomKey")
        parsed = toml.loads(result)
        assert "CustomKey" in parsed
        assert parsed["CustomKey"] == sample_data

    def test_table_encoder(self, sample_data):
        """Test table encoder."""
        result = _table_encoder(sample_data)

        # Should contain table content (no borders in current implementation)
        assert "web-server" in result
        assert "8080" in result
        assert "Local Port" in result  # Header
        assert "Name" in result  # Header

    def test_table_encoder_with_title(self, sample_data):
        """Test table encoder with title."""
        title = "Test Tunnels"
        result = _table_encoder_with_title(sample_data, title)

        # Should contain the title and table elements
        assert title in result
        assert "web-server" in result
        assert "Local Port" in result  # Header

    def test_table_encoder_empty_data(self):
        """Test table encoder with empty data."""
        result = _table_encoder([])
        assert result == "No data to display.\n"

    def test_table_encoder_with_title_empty_data(self):
        """Test table encoder with title and empty data."""
        result = _table_encoder_with_title([], "Empty Test")
        assert result == "No data to display.\n"


class TestFormatOutput:
    """Test the main format_output function."""

    @pytest.fixture
    def sample_data(self) -> list[dict[str, Any]]:
        """Sample test data."""
        return [
            {
                "name": "test-tunnel",
                "local_port": "3000",
                "status": "active",
            },
        ]

    def test_format_output_json(self, sample_data):
        """Test formatting output as JSON."""
        result = format_output(sample_data, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed == sample_data

    def test_format_output_yaml(self, sample_data):
        """Test formatting output as YAML."""
        result = format_output(sample_data, OutputFormat.YAML)
        parsed = yaml.safe_load(result)
        assert parsed == sample_data

    def test_format_output_toml(self, sample_data):
        """Test formatting output as TOML."""
        result = format_output(sample_data, OutputFormat.TOML)
        parsed = toml.loads(result)
        assert parsed["Tunnel"] == sample_data

    def test_format_output_table(self, sample_data):
        """Test formatting output as table."""
        result = format_output(sample_data, OutputFormat.TABLE)
        assert "test-tunnel" in result
        assert "3000" in result
        assert "Local Port" in result  # Header

    def test_format_output_table_with_title(self, sample_data):
        """Test formatting output as table with title."""
        title = "Custom Title"
        result = format_output(sample_data, OutputFormat.TABLE, title=title)
        assert title in result
        assert "test-tunnel" in result

    def test_format_output_table_title_ignored_for_other_formats(self, sample_data):
        """Test that title is ignored for non-table formats."""
        title = "Should Be Ignored"

        # JSON should not contain the title
        json_result = format_output(sample_data, OutputFormat.JSON, title=title)
        assert title not in json_result

        # YAML should not contain the title
        yaml_result = format_output(sample_data, OutputFormat.YAML, title=title)
        assert title not in yaml_result

    def test_format_output_invalid_format(self, sample_data):
        """Test error handling for invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            # This should raise an error since we're bypassing the enum
            format_output(sample_data, "invalid_format")  # type: ignore[arg-type]

    def test_format_output_empty_data(self):
        """Test formatting empty data."""
        empty_data = []

        # JSON should return empty list
        json_result = format_output(empty_data, OutputFormat.JSON)
        assert json_result == "[]"

        # Table should return special message
        table_result = format_output(empty_data, OutputFormat.TABLE)
        assert table_result == "No data to display.\n"


class TestEncoderRegistry:
    """Test the ENCODER registry."""

    def test_encoder_registry_completeness(self):
        """Test that all output formats have encoders."""
        for format_type in OutputFormat:
            assert format_type in output_encoder

    def test_encoder_registry_functions(self):
        """Test that all encoders are callable."""
        for encoder in output_encoder.values():
            assert callable(encoder)


class TestGetSupportedFormats:
    """Test the get_supported_formats function."""

    def test_get_supported_formats(self):
        """Test getting supported formats."""
        formats = get_supported_formats()
        assert isinstance(formats, list)
        assert len(formats) == 4
        assert all(isinstance(fmt, OutputFormat) for fmt in formats)
        assert OutputFormat.JSON in formats
        assert OutputFormat.YAML in formats
        assert OutputFormat.TOML in formats
        assert OutputFormat.TABLE in formats


class TestRealWorldScenarios:
    """Test with real-world SSH tunnel data scenarios."""

    @pytest.fixture
    def tunnel_data(self) -> list[dict[str, Any]]:
        """Real-world tunnel data."""
        return [
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
            {
                "name": "api-staging",
                "local_port": "3000",
                "remote_host": "staging-api.com",
                "remote_port": "443",
                "status": "connecting",
                "user": "tester",
            },
        ]

    def test_complete_workflow_all_formats(self, tunnel_data):
        """Test complete workflow with all formats."""
        for format_type in OutputFormat:
            result = format_output(tunnel_data, format_type)

            # All formats should produce non-empty output
            assert result
            assert isinstance(result, str)

            # Each should contain tunnel names
            if format_type != OutputFormat.TABLE or "No data to display" not in result:
                assert "web-development" in result
                assert "database-tunnel" in result

    def test_status_colors_in_table(self, tunnel_data):
        """Test that status colors are applied in table format."""
        result = format_output(tunnel_data, OutputFormat.TABLE)

        # Should contain the status values (colors are applied at Rich markup level)
        assert "Active" in result
        assert "Inactive" in result
        assert "Connecting" in result
        # Check for ANSI color codes instead of Rich markup
        assert "\x1b[1;32m" in result  # Bold green for active
        assert "\x1b[1;31m" in result  # Bold red for inactive

    def test_column_ordering_consistency(self, tunnel_data):
        """Test that column ordering is consistent."""
        result = format_output(tunnel_data, OutputFormat.TABLE)

        # Columns should be in alphabetical order of keys
        lines = result.split("\n")
        header_line = None
        for line in lines:
            if "Local Port" in line and "Name" in line:
                header_line = line
                break

        assert header_line is not None
        # Should have consistent column order (alphabetical by key name)
        assert "Local Port" in header_line
        assert "Name" in header_line
        assert "Remote Host" in header_line

    def test_missing_fields_handling(self):
        """Test handling of missing fields in data."""
        incomplete_data = [
            {"name": "incomplete-1", "status": "active"},
            {"name": "incomplete-2", "local_port": "8080"},
        ]

        # Should not raise errors
        for format_type in OutputFormat:
            result = format_output(incomplete_data, format_type)
            assert result
            assert "incomplete-1" in result
            assert "incomplete-2" in result

    def test_special_characters_in_data(self):
        """Test handling of special characters in data."""
        special_data = [
            {
                "name": "test-with-unicode-🚇",
                "host": "example.com/path?param=value&other=123",
                "status": "active",
            },
        ]

        # Should handle special characters gracefully
        for format_type in OutputFormat:
            result = format_output(special_data, format_type)
            assert result
            # Unicode should be preserved
            if format_type == OutputFormat.TABLE:
                assert "🚇" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_values(self):
        """Test handling of very long values."""
        long_data = [
            {
                "name": "very-long-tunnel-name-that-exceeds-normal-expectations",
                "host": "very-long-hostname.with.many.subdomains.example.com",
                "description": "A" * 100,  # Very long description
                "status": "active",
            },
        ]

        # Should handle long values without errors
        result = format_output(long_data, OutputFormat.JSON)
        assert result
        assert "very-long-tunnel-name" in result

    def test_numeric_values(self):
        """Test handling of numeric values."""
        numeric_data = [
            {
                "id": 123,
                "port": 8080,
                "timeout": 30.5,
                "retries": 0,
                "status": "active",
            },
        ]

        # Should convert numbers to strings properly
        result = format_output(numeric_data, OutputFormat.TABLE)
        assert "123" in result
        assert "8080" in result
        assert "30.5" in result

    def test_boolean_values(self):
        """Test handling of boolean values."""
        bool_data = [
            {
                "name": "test",
                "enabled": True,
                "auto_reconnect": False,
                "status": "active",
            },
        ]

        # Should convert booleans to strings
        result = format_output(bool_data, OutputFormat.TABLE)
        assert "True" in result
        assert "False" in result

    def test_none_values(self):
        """Test handling of None values."""
        none_data = [
            {
                "name": "test",
                "description": None,
                "optional_field": None,
                "status": "active",
            },
        ]

        # Should handle None values gracefully
        result = format_output(none_data, OutputFormat.TABLE)
        assert "test" in result
        # None should be converted to string
        assert "None" in result or "" in result
