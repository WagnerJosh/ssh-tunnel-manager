"""Output formatting for the command."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal, Sequence

import rich.box
import toml
import yaml
from pydantic import BaseModel
from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Callable

type JustifyMethod = Literal["default", "left", "center", "right", "full"]
"""A type alias for justification methods used in rich tables."""

type EncoderData = Sequence[type[BaseModel]] | list[dict[str, Any]]

"""A type alias for the data that can be encoded by the encoder."""

type Encoder = Callable[[EncoderData, Sequence[str] | None], RenderableType]
"""A type alias for the encoder function that takes data and optional columns."""


class OutputFormat(StrEnum):
    """The output format for the command."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    TABLE = "table"
    PANEL = "panel"


default_table: Table = Table(
    show_header=True,
    header_style="bold yellow dim",
    show_lines=False,
    box=rich.box.ROUNDED,
    title_justify="left",
    title_style="bold cyan",
    expand=True,
)

borderless_table: Table = Table(
    show_header=True,
    header_style="bold yellow dim",
    show_lines=False,
    box=None,
    title_justify="left",
    title_style="bold cyan",
    expand=True,
)


def _get_column_style(header: str) -> tuple[str, JustifyMethod]:
    """Get the style and justification for a column header.

    Args:
        header: The column header name

    Returns:
        tuple[str, JustifyMethod]: A tuple containing the style and justification method
    """
    if header in {"local_port", "remote_port"}:
        header = "port"
    default: tuple[str, JustifyMethod] = ("dim", "left")
    styles: dict[str, tuple[str, JustifyMethod]] = {
        "status": ("bold", "left"),
        "port": ("yellow", "right"),
        "name": ("green", "left"),
        "proxy": ("cyan", "center"),
        "item": ("cyan", "left"),
        "details": ("dim", "left"),
    }
    return styles.get(header, default)


def _format_status_value(value: str) -> str:
    """Format status values with appropriate colors.

    Args:
        value: The status value to format

    Returns:
        str: A formatted string with color styling based on the status value.
    """
    formats: dict[str, str] = {
        "running": "[bold green]Running[/]",
        "inactive": "[bold red]Inactive[/]",
        "connecting": "[bold dim]Connecting[/]",
    }
    return formats.get(value.lower(), f"[dim]{value}[/]")


def _standardize_data(
    input_data: EncoderData,
    /,
    columns: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Standardize the input data to a list of dictionaries or dict.

    Args:
        input_data: List of dictionaries, Pydantic models, or dict to standardize
        columns: Optional list of column names to include in the output

    Returns:
        list[dict[str, Any]] | dict[str, Any]: A standardized list of dictionaries
            or dict with the specified columns.
    """
    model: list[dict[str, Any]] = []
    for entry in input_data:
        data: dict[str, Any] = {}
        if isinstance(entry, BaseModel):
            data = entry.model_dump(mode="json", by_alias=True)
        else:
            data = entry.copy()
        if columns:
            data = {key: data[key] for key in columns if key in data}
        model.append(data)

    return model


def _create_table(
    data: EncoderData,
    columns: Sequence[str] | None = None,
    *,
    title: str | None = None,
    table_: Table = default_table,
) -> RenderableType:
    """Create a rich table with proper styling.

    Args:
        data: List of dictionaries containing the data to format
        columns: Optional list of column names to include in the output
        title: Optional title for the table
        table_: The Table object to use for formatting. Defaults to `default_table`.

    Returns:
        Table: A rich Table object containing the formatted data.
    """
    table_.rows.clear()
    table_.columns.clear()
    if title:
        table_.title = title

    model: list[dict[str, Any]] = _standardize_data(
        data,
        columns=columns,
    )

    if not model or not model[0]:
        return table_
    header_keys: list[str] = []
    for key in model[0]:
        header_keys.append(key)
        column_title = key.replace("_", " ").title()
        style, justify = _get_column_style(key)
        table_.add_column(column_title, style=style, justify=justify)

    for row in model:
        row_values = []
        for key in header_keys:
            v = str(row.get(key, ""))
            row_values.append(v if key != "status" else _format_status_value(v))
        table_.add_row(*row_values)
    return table_


def _table_encoder(
    data: EncoderData,
    columns: list[str] | None = None,
    *,
    table_: Table = default_table,
) -> RenderableType:
    """Encode the data as a rich table format with status-based styling.

    Args:
        data: List of dictionaries containing the data to format
        columns: Optional list of column names to include in the output
        table_: The Table object to use for formatting. Defaults to `default_table`.

    Returns:
        Table: A rich Table object containing the formatted data.
    """
    return _create_table(data, table_=table_, columns=columns)


def _panel_encoder(
    data: EncoderData,
    columns: Sequence[str] | None = None,
    title: str | None = None,
) -> RenderableType:
    """Encode the data as a rich table format with status-based styling.

    Args:
        data: List of dictionaries containing the data to format
        columns: Optional list of column names to include in the output
        title: Optional title override for the panel

    Returns:
        Panel: A rich Panel object containing the formatted table
    """
    panel_title = f"[bold]{title}" if title else "[bold]Active Tunnels"

    # Add color based on VPN status if present
    if title:
        if "NOT SET" in title:
            panel_title = f"[bold yellow]{title}"
        elif "Cisco" in title and "Enabled" in title:
            panel_title = f"[bold green]{title}"
        elif "unusual" in title.lower():
            panel_title = f"[bold yellow]{title}"
        elif "Ivanti" in title or "Lab" in title:
            panel_title = f"[bold cyan]{title}"
        elif "Disconnected" in title and "Proxy: Set" in title:
            panel_title = f"[bold yellow]{title}"
        elif "Disconnected" in title:
            panel_title = f"[bold red]{title}"

    return Panel(
        _create_table(data, table_=borderless_table, columns=columns),
        title=panel_title,
        title_align="left",
        border_style="dim",
    )


def _json_encoder(data: EncoderData, columns: list[str] | None = None) -> str:
    """Encode the data as formatted JSON.

    Args:
        data: List of dictionaries or dict containing the data to format
        columns: Optional list of column names to include in the output

    Returns:
        str: A string representation of the data in JSON format.
    """
    standardized = _standardize_data(data, columns=columns)
    return json.dumps(standardized, indent=2)


def _yaml_encoder(data: EncoderData, columns: list[str] | None = None) -> str:
    """Encode the data as YAML.

    Args:
        data: List of dictionaries or dict containing the data to format
        columns: Optional list of column names to include in the output

    Returns:
        str: A string representation of the data in YAML format.
    """
    standardized = _standardize_data(data, columns=columns)
    return yaml.safe_dump(
        standardized,
        default_flow_style=False,
        sort_keys=False,
    )


def _toml_encoder(
    data: EncoderData,
    columns: list[str] | None = None,
    key: str = "Tunnel",
) -> str:
    """Encode the data as TOML.

    Args:
        data: List of dictionaries or dict containing the data to format
        columns: Optional list of column names to include in the output
        key: The key under which the data will be stored in the TOML output.
            Defaults to "Tunnel" (ignored if data is already a dict)

    Returns:
        str: A string representation of the data in TOML format.
    """
    standardized = _standardize_data(data, columns=columns)
    return toml.dumps({key: standardized})


def _table_encoder_with_title(
    data: EncoderData,
    columns: Sequence[str] | None = None,
    title: str | None = None,
) -> RenderableType:
    """Encode the data as a rich table format with optional title.

    Args:
        data: List of dictionaries containing the data to format
        columns: Optional list of column names to include in the output
        title: Optional title for the table

    Returns:
        RenderableType: A rich Table object with the formatted data and title
    """
    return _create_table(data, columns=columns, title=title)


output_encoder: dict[OutputFormat, Encoder] = {
    OutputFormat.JSON: _json_encoder,
    OutputFormat.YAML: _yaml_encoder,
    OutputFormat.TOML: _toml_encoder,
    OutputFormat.TABLE: _table_encoder,
    OutputFormat.PANEL: _panel_encoder,
}
"""The mapping of output formats to their respective encoders."""


def format_output(
    data: EncoderData,
    format_: OutputFormat,
    columns: Sequence[str] | None = None,
    title: str | None = None,
) -> RenderableType:
    """Format the output data according to the specified format.

    Args:
        data: List of dictionaries containing the data to format
        format_: The desired output format
        columns: Optional list of column names to include in the output
        title: Optional title for table/panel formats

    Returns:
        Formatted string representation of the data

    Raises:
        ValueError: If the format type is not supported
    """
    if format_ not in output_encoder:
        msg = f"Unsupported format '{format_}'. Supported:[{', '.join(OutputFormat)}]"
        raise ValueError(msg)

    # Use custom table encoder with title if format is TABLE and title is provided
    if format_ == OutputFormat.TABLE and title is not None:
        return _table_encoder_with_title(data, columns=columns, title=title)

    # Use panel encoder with title if format is PANEL and title is provided
    if format_ == OutputFormat.PANEL and title is not None:
        return _panel_encoder(data, columns=columns, title=title)

    encoder: Encoder = output_encoder[format_]
    return encoder(data, columns)


if __name__ == "__main__":
    import rich

    sample_data = [
        {
            "name": "Tunnel1",
            "status": "active",
            "local_port": 8080,
            "remote_port": 80,
            "test": True,
        },
        {
            "name": "Tunnel2",
            "status": "inactive",
            "local_port": 9090,
            "remote_port": 90,
            "test": True,
        },
    ]

    formatted_output = format_output(sample_data, OutputFormat.TABLE)
    rich.print(formatted_output)
    formatted_output = format_output(
        data=sample_data,
        format_=OutputFormat.TABLE,
        columns=["name", "status", "local_port"],
        title="Sample Tunnels",
    )
    rich.print(formatted_output)

    formatted_output = format_output(sample_data, OutputFormat.PANEL)
    rich.print(formatted_output)
    formatted_output = format_output(
        sample_data,
        OutputFormat.PANEL,
        title="Sample Tunnels",
    )
    rich.print(formatted_output)
    formatted_json = format_output(sample_data, OutputFormat.JSON)
    rich.print(formatted_json)

    formatted_yaml = format_output(sample_data, OutputFormat.YAML)
    rich.print(formatted_yaml)
    formatted_toml = format_output(sample_data, OutputFormat.TOML)
    rich.print(formatted_toml)
    formatted_toml = format_output([], OutputFormat.TABLE)
    rich.print(formatted_toml)
    formatted_toml = format_output([], OutputFormat.TABLE, title="Empty Table")
    rich.print(formatted_toml)
    formatted_toml = format_output([], OutputFormat.PANEL)
    rich.print(formatted_toml)
    formatted_toml = format_output([], OutputFormat.JSON)
    rich.print(formatted_toml)
    formatted_toml = format_output([], OutputFormat.YAML)
    rich.print(formatted_toml)
    formatted_toml = format_output([], OutputFormat.TOML)
    rich.print(formatted_toml)
