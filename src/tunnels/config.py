"""The application configuration."""

from __future__ import annotations

import logging
import os
import pathlib
from functools import cached_property
from pathlib import Path
from typing import Any, NamedTuple, Self

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, FilePath, model_validator
from pydantic.v1.utils import deep_update
from pydantic_settings import BaseSettings

log = logging.getLogger(__name__)

XDG_CONFIG_HOME: Path = Path(
    os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config",
)


class ConfigFileLoader(BaseSettings):
    """A base class for loading configuration from a file."""

    config: FilePath | None = Field(
        default=XDG_CONFIG_HOME / Path("tunnels/config.yaml"),
        description="The configuration file to use.",
    )

    @classmethod
    def load(cls) -> Self:
        """Load the configuration from the configuration file.

        Returns:
            Config: The loaded configuration
        """
        load_dotenv()
        cli = cls()
        if not cli.config:
            return cli
        cfg = yaml.safe_load(pathlib.Path(cli.config).read_text(encoding="utf-8"))
        return cls.model_validate(deep_update(cfg, cli.model_dump(exclude_unset=True)))


class Dynamic(BaseModel, frozen=True):
    """Specifies a local 'dynamic' application-level port forwarding configuration.

    Setting this will create a SOCKS proxy on the local machine. Currently only
    SOCKS4 and SOCKS5 are supported, where ssh acts as a SOCKS server.

    Args:
        bind_address (str, optional): Specifies the interface to bind the outgoing
            connection to.  Ann explicit bind_address may be used to bind the
            connection to a specific address.  The bind_address of `localhost`
            indicates that the listening port be bound for local use only, while
            an `empty address` (`None`) or `*` indicates that the port should be
            available from all interfaces. Defaults to `None`.
        port (int): Specifies the port number to use on the local machine.
    """

    bind_address: str | None = Field(default=None)
    port: int

    @cached_property
    def address(self) -> str:
        """The dynamic forwarding address, specified by the config.

        Essentially, this creates `-D [bind_address:]port`. If a bind_address
        is specified, it will be included in the address, otherwise only the
        port will be returned.

        Returns:
            str: The address for the dynamic forwarding.
        """
        if self.bind_address:
            return f"[{self.bind_address}:]{self.port}"
        return str(self.port)


class Local(BaseModel, frozen=True):
    """Specifies a local port or socket to forward to the given remote.

    Important Notes:
        * Forwarding of privileged ports is only allowed for the superuser.
        * To specify `ipv6` addresses, enclose the address in square brackets.

    Specifies that connections to the given TCP port or Unix socket on the local
    (client) host are to be forwarded to the given host and port, or Unix socket,
    on the remote side.

    See `man ssh` for more information.

    Args:
        port (int, optional): A TCP port to forward to the remote host.
            Defaults to `None`.
        local_socket (str, optional): A Unix socket to forward to the remote host.
            Defaults to `None`.
        host (str | None): The host to forward the local port to. Defaults to `None`.
        remote_socket (str | int): The remote socket to forward the local socket to.
            Defaults to `None`.
        host_port (int | None): The port on the host to forward the local port to.
            Defaults to `None`.
        bind_address (str, optional): Specifies the interface to bind the outgoing
            connection to. An explicit bind_address may be used to bind the connection
            to a specific address. The bind_address of `localhost` indicates that the
            listening port be bound for local use only, while an `empty address`
            (`None`) or `*` indicates that the port should be available from all
            interfaces. Defaults to `None`.
    """

    port: int | None = Field(
        default=None,
        description="The local port to forward",
    )
    local_socket: str | None = Field(
        default=None,
        description="The local socket to forward",
    )
    host: str | None = Field(
        default=None,
        description="The host to forward the local port to",
    )
    remote_socket: str | None = Field(
        default=None,
        description="The remote socket to forward the local socket to",
    )
    host_port: int | None = Field(
        default=None,
        description="The port on the host to forward the local port to",
    )
    bind_address: str | None = Field(
        default=None,
        description="The interface to bind the outgoing connection to",
    )

    @property
    def bind(self) -> str | None:
        """The bind address for the local forwarding.

        Returns:
            str: The bind address for the local forwarding.
        """
        return None if not self.bind_address else f"[{self.bind_address}:]"

    def _combinations(self) -> list[tuple[str | int | None, ...]]:
        return [
            (self.local_socket, self.remote_socket),
            (self.local_socket, self.host, self.host_port),
            (self.port, self.host, self.host_port),
            (self.port, self.remote_socket),
            (self.bind, self.port, self.host, self.host_port),
            (self.bind, self.port, self.remote_socket),
        ]

    @model_validator(mode="after")
    def _validate_all_input(self: Self) -> Self:
        # Get the one combination where no values are None
        valid = [combo for combo in self._combinations() if all(combo)]
        if not valid or len(valid) > 1:
            msg: str = "Invalid combination of values. Please check the configuration."
            raise ValueError(msg)
        return self

    @cached_property
    def address(self) -> str:
        """The local forwarding address, specified by the config.

        Essentially, this creates the following address:
        ```
        -L [bind_address:]port:host:hostport
        -L [bind_address:]port:remote_socket
        -L local_socket:host:hostport
        -L local_socket:remote_socket
        ```
        depending on the values configured in the model.

        Returns:
            str: The address for the local forwarding.
        """
        valid_entry = next(combo for combo in self._combinations() if all(combo))
        return ":".join(str(x) for x in valid_entry if x)


class Tunnel(BaseModel):
    """A tunnel configuration."""

    name: str
    group: str | None = Field(default=None, description="The group of the tunnel")
    hostname: str = Field(..., description="The hostname of the tunnel")
    dynamic: Dynamic | None = Field(default=None)
    local: Local | None = Field(default=None)

    def name_tag(self) -> str:
        """Return a constructed name tag for the tunnel.

        Returns:
            str: The name tag for the tunnel.
        """
        return self.name.replace(" ", "-").casefold().lower()


class TunnelGroup(BaseModel):
    """A group of tunnels."""

    name: str = Field(..., description="The name of the group")
    tunnels: list[Tunnel] = Field(
        default_factory=list,
        description="The tunnels in the group",
    )


class Config(ConfigFileLoader):
    """The configuration for the tunnels application."""

    tunnels: list[Tunnel] = Field(default_factory=list)
    groups: list[TunnelGroup] | None = Field(default_factory=list)


class Settings(NamedTuple):
    """The application settings."""

    configuration: Config
    global_options: dict[str, Any]


settings: Settings = Settings(
    configuration=Config.load(),
    global_options={"output": None},
)

if __name__ == "__main__":
    import rich

    rich.print(settings)
