import logging
import os
import pwd
import socket

from grpc import insecure_channel

LOG = logging.getLogger(__name__)


class RpcClient:
    """
    Wrapper to GRPC api to setup an RPC client.

    Arguments:
        host:
            host string for RPC server to connect to.
        port:
            TCP port for RPC server to connect to.
        stubs_map:
            name:stub item maps, used to instantiate and attach (generated) stubs to current client instance
            e.g. if a {"foo": FooServiceStub} map is provided, methods of the Foo service can be accessed through a client.foo.xxx call
    """

    def __init__(self, host: str, port: int, stubs_map: dict = None, client_api_version: int = None, timeout: float = None, name: str = None):
        # Prepare metadata for RPC calls
        self.metadata = self.get_metadata(name)

        # Create channel
        LOG.debug(f"Initializing RPC client for {host}:{port}")
        channel = insecure_channel(f"{host}:{port}")

        # Handle stubs hooking
        all_stubs = dict(stubs_map) if stubs_map is not None else {}
        for name, typ in all_stubs.items():
            LOG.debug(f"Adding {name} stub to client")
            setattr(self, name, typ(channel))

        # TODO Handle API check if client version is provided

        LOG.debug(f"RPC client ready for {host}:{port}")

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 1))
            out = s.getsockname()[0]
        except Exception:  # pragma: no cover
            out = ""
        finally:
            s.close()
        return out

    def get_user(self):
        # Resolve user
        uid = os.getuid()
        try:
            # Try from pwd
            user = pwd.getpwuid(uid).pw_name
        except Exception:  # pragma: no cover
            # Not in pwd database, just keep UID
            user = f"{uid}"
        return user

    def get_metadata(self, name: str):
        # Resolve all metadata
        return (("client", name if name is not None else ""), ("user", self.get_user()), ("host", socket.gethostname()), ("ip", self.get_ip()))
