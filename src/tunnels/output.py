"""Output formatting for the command."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

import toml
import yaml
from pydantic import BaseModel
from rich.console import Console, RenderableType
from rich.table import Table

from tunnels.status import StatusEntry

if TYPE_CHECKING:
    from collections.abc import Callable

type JustifyMethod = Literal["default", "left", "center", "right", "full"]


class OutputFormat(StrEnum):
    """The output format for the command."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    TABLE = "table"


def _get_column_style(header: str) -> tuple[str, JustifyMethod]:
    """Get the style and justification for a column header."""
    if header in {"local_port", "remote_port"}:
        header = "port"
    default: tuple[str, JustifyMethod] = ("cyan", "left")
    styles: dict[str, tuple[str, JustifyMethod]] = {
        "status": ("bold", "center"),
        "port": ("yellow", "right"),
        "name": ("green", "left"),
    }
    return styles.get(header, default)


def _format_status_value(value: str) -> str:
    """Format status values with appropriate colors."""
    formats: dict[str, str] = {
        "active": "[bold green]Active[/]",
        "inactive": "[bold red]Inactive[/]",
        "connecting": "[bold yellow]Connecting[/]",
    }
    return formats.get(value.lower(), f"[dim]{value}[/]")


def _create_table(data: list[BaseModel], title: str | None = None) -> Table:
    """Create a rich table with proper styling."""
    table = Table(
        show_header=True,
        header_style="bold yellow dim",
        show_lines=True,
        box=None,
        title=title,
        title_justify="left",
        title_style="bold cyan",
        expand=True,
    )

    model: list[dict[str, Any]] = [entry.model_dump(mode="json") for entry in data]

    for header in model:
        column_title = header.replace("_", " ").title()
        style, justify = _get_column_style(header)
        table.add_column(column_title, style=style, justify=justify)

    for header, value in model.items():
        table.add_column(column_title, style=style, justify=justify)
        row_values = []
        for header in all_keys:
            value = str(item.get(header, ""))
            if header == "status":
                value = _format_status_value(value)
            row_values.append(value)
        table.add_row(*row_values)

    return table


def _table_encoder(data: list[StatusEntry]) -> str:
    """Encode the data as a rich table format with status-based styling."""
    if not data:
        return "No data to display.\n"

    return _create_table(data)


def _json_encoder(data: list[StatusEntry]) -> str:
    """Encode the data as formatted JSON."""
    return json.dumps(
        [entry.model_dump(mode="json", by_alias=True) for entry in data],
        indent=4,
    )


def _yaml_encoder(data: list[StatusEntry]) -> str:
    """Encode the data as YAML."""
    return yaml.safe_dump(
        [entry.model_dump(mode="json", by_alias=True) for entry in data],
        default_flow_style=False,
        sort_keys=False,
    )


def _toml_encoder(data: list[StatusEntry], key: str = "Tunnel") -> str:
    """Encode the data as TOML."""
    return toml.dumps(
        {
            key: [entry.model_dump(mode="json", by_alias=True) for entry in data],
        },
    )


def _table_encoder_with_title(
    data: list[StatusEntry],
    title: str | None = None,
) -> RenderableType:
    """Encode the data as a rich table format with optional title."""
    if not data:
        return "No data to display.\n"

    return _create_table(data, title)


ENCODER: dict[OutputFormat, Callable[[list[StatusEntry]], RenderableType]] = {
    OutputFormat.JSON: _json_encoder,
    OutputFormat.YAML: _yaml_encoder,
    OutputFormat.TOML: _toml_encoder,
    OutputFormat.TABLE: _table_encoder,
}


def format_output(
    data: list[dict[str, Any]],
    format_type: OutputFormat,
    title: str | None = None,
) -> RenderableType:
    """Format the output data according to the specified format.

    Args:
        data: List of dictionaries containing the data to format
        format_type: The desired output format
        title: Optional title for table format (ignored for other formats)

    Returns:
        Formatted string representation of the data

    Raises:
        ValueError: If the format type is not supported
    """
    if format_type not in ENCODER:
        supported_formats = ", ".join(OutputFormat)
        error_msg = (
            f"Unsupported format '{format_type}'. "
            f"Supported formats: {supported_formats}"
        )
        raise ValueError(error_msg)

    # Use custom table encoder with title if format is TABLE and title is provided
    if format_type == OutputFormat.TABLE and title is not None:
        return _table_encoder_with_title(data, title)

    encoder = ENCODER[format_type]
    return encoder(data)


def get_supported_formats() -> list[OutputFormat]:
    """Get a list of all supported output formats.

    Returns:
        List of supported OutputFormat values
    """
    return list(OutputFormat)


if __name__ == "__main__":
    sample_data = [
        {"name": "Tunnel1", "status": "active", "local_port": 8080, "remote_port": 80},
        {
            "name": "Tunnel2",
            "status": "inactive",
            "local_port": 9090,
            "remote_port": 90,
        },
    ]

    formatted_output = format_output(
        sample_data,
        OutputFormat.TABLE,
    )
    print(formatted_output)
    formatted_output = format_output(
        sample_data, OutputFormat.TABLE, title="Sample Tunnels"
    )
    print(formatted_output)

    formatted_json = format_output(sample_data, OutputFormat.JSON)
    print(formatted_json)

    formatted_yaml = format_output(sample_data, OutputFormat.YAML)
    print(formatted_yaml)
    formatted_toml = format_output(sample_data, OutputFormat.TOML)
    print(formatted_toml)
