import logging
import os
import pwd
import socket
import time

from grpc import RpcError, StatusCode, insecure_channel

from dynod_commons.api import InfoApiVersion
from dynod_commons.api.info_pb2_grpc import InfoServiceStub
from dynod_commons.rpc.trace import trace_rpc

LOG = logging.getLogger(__name__)


# Utility class to handle stub retry
# i.e. permissive stub that allows server to be temporarily unavailable
class RetryStub:
    class RetryMethod:
        def __init__(self, name: str, stub, timeout: float, metadata: tuple):
            self.m_name = name
            self.s_name = stub.__class__.__name__
            self.stub = stub
            self.timeout = timeout
            self.metadata = metadata

        def retry_call(self, request):
            LOG.debug(trace_rpc(True, request, method=f"{self.s_name}.{self.m_name}"))
            first_try = time.time()

            # Loop to handle retries
            while True:
                try:
                    # Call real stub method, with metadata
                    result = getattr(self.stub, self.m_name)(request, metadata=self.metadata)
                    break
                except RpcError as e:
                    if e.code() == StatusCode.UNAVAILABLE and self.timeout is not None and (time.time() - first_try) < self.timeout:
                        # Server is not available, and timeout didn't expired yet: sleep and retry
                        time.sleep(0.5)
                        LOG.debug(f"<RPC> >> {self.s_name}.{self.m_name}... (retry)")
                    else:
                        # Timed out or any other reason: raise exception
                        LOG.error(f"<RPC> >> {self.s_name}.{self.m_name} error: {str(e)}")
                        raise e

            LOG.debug(trace_rpc(False, result, method=f"{self.s_name}.{self.m_name}"))
            return result

    def __init__(self, real_stub, timeout: float, metadata: tuple):
        # Fake the stub methods
        for n in filter(lambda x: not x.startswith("__") and callable(getattr(real_stub, x)), dir(real_stub)):
            setattr(self, n, RetryStub.RetryMethod(n, real_stub, timeout, metadata).retry_call)


class RpcClient:
    """
    Wrapper to GRPC api to setup an RPC client.

    Arguments:
        host:
            host string for RPC server to connect to.
        port:
            TCP port for RPC server to connect to.
        stubs_map:
            name:(stub,api_version) item maps, used to instantiate and attach (generated) stubs to current client instance
            e.g. if a {"foo": (FooServiceStub,1)} map is provided, methods of the Foo service can be accessed through a client.foo.xxx call
        timeout:
            timeout for unreachable server (in seconds; default: 60)
        name:
            client name, which will appear in server logs
    """

    def __init__(self, host: str, port: int, stubs_map: dict, timeout: float = 60, name: str = ""):
        # Prepare metadata for RPC calls
        shared_metadata = [("client", name), ("user", self.get_user()), ("host", socket.gethostname()), ("ip", self.get_ip())]

        # Create channel
        LOG.debug(f"Initializing RPC client for {host}:{port}")
        channel = insecure_channel(f"{host}:{port}")

        # Handle stubs hooking
        all_stubs = {"info": (InfoServiceStub, InfoApiVersion.INFO_API_CURRENT)}
        all_stubs.update(stubs_map)
        for name, typ_n_ver in all_stubs.items():
            typ, ver = typ_n_ver
            metadata = list(shared_metadata)
            if ver is not None:
                metadata.append(("api_version", str(ver)))
            LOG.debug(f"Adding {name} stub to client (api version: {ver})")
            setattr(self, name, RetryStub(typ(channel), timeout, tuple(metadata)))

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
