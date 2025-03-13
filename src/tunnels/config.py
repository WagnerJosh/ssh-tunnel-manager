from __future__ import annotations

import pathlib
import shlex
import shutil
from pathlib import Path
from typing import Self

import yaml
from dotenv import load_dotenv
from pydantic import AliasChoices, BaseModel, Field, FilePath
from pydantic.v1.utils import deep_update
from pydantic_settings import BaseSettings, CliApp


class ConfigFileLoader(BaseSettings):
    """A base class for loading configuration from a file"""

    config: FilePath | None = Field(
        default=Path("config.yaml"),
        description="The configuration file to use.",
    )

    @classmethod
    def load(cls) -> Self:
        load_dotenv()
        cli = cls()
        if not cli.config:
            return cli
        cfg = yaml.safe_load(pathlib.Path(cli.config).read_text(encoding="utf-8"))
        return cls.model_validate(deep_update(cfg, cli.model_dump(exclude_unset=True)))


class Dynamic(BaseModel):
    bind_address: str | None = Field(default=None)
    port: int

    def address(self) -> str:
        if self.bind_address:
            return f"[{self.bind_address}:]{self.port}"
        return str(self.port)


class Local(BaseModel):
    port: int | str = Field(validation_alias=AliasChoices("port", "local_socket"))
    host: str | int = Field(validation_alias=AliasChoices("host", "remote_socket"))
    host_port: int | None = Field(default=None)
    bind_address: str | None = Field(default=None)

    def address(self) -> str:
        addr = []
        if self.host_port:
            addr.append(self.host_port)
        addr.extend([self.host, self.port])
        address = ":".join(str(x) for x in addr if x)
        if self.bind_address:
            return f"[{self.bind_address}:]{address}"
        return address


class Tunnel(BaseModel):
    """A tunnel configuration"""

    name: str = Field(..., description="The name of the tunnel")
    hostname: str = Field(..., description="The hostname of the tunnel")
    dynamic: Dynamic | None = Field(default=None)
    local: Local | None = Field(default=None)


_default_cmd: str | None = shutil.which("ssh") or "ssh"


def create_tunnel_cmd(
    tun: Tunnel,
    *,
    name_tag: bool = True,
    ssh_cmd: str = _default_cmd,
) -> list[str]:
    """Create the command to start a tunnel"""
    base_cmd = [ssh_cmd, "-f", "-N", "-n"]
    if tun.dynamic:
        base_cmd.extend(["-D", f"{tun.dynamic.address()}"])
    elif tun.local:
        base_cmd.extend(["-L", tun.local.address()])
    base_cmd.append(tun.hostname)
    if name_tag:
        name = tun.name.replace(" ", "-").casefold().lower()
        base_cmd.extend(["-o", f"Tag=tunnels-{name}"])
    base_cmd.append("-o")
    base_cmd.append("ExitOnForwardFailure=yes")
    base_cmd.append("-o")
    base_cmd.append("ServerAliveInterval=30")
    base_cmd.append("-o")
    base_cmd.append("ServerAliveCountMax=5")

    cmd = " ".join(base_cmd)
    return shlex.split(cmd)


class TunnelGroup(BaseModel):
    """A group of tunnels"""

    name: str = Field(..., description="The name of the group")
    tunnels: list[Tunnel] = Field(
        default_factory=list, description="The tunnels in the group"
    )


class Config(ConfigFileLoader):
    """The configuration for the tunnels application"""

    tunnels: list[Tunnel] | None = Field(default_factory=list)
    groups: list[TunnelGroup] | None = Field(default_factory=list)


if __name__ == "__main__":
    from rich import print as rprint

    settings = Config.load()
    rprint(settings)
    for tunnel in settings.tunnels if settings.tunnels else []:
        rprint(create_tunnel_cmd(tunnel))
    for group in settings.groups if settings.groups else []:
        for tunnel in group.tunnels:
            rprint(create_tunnel_cmd(tunnel))
