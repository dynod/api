import inspect
import logging
import traceback
from concurrent import futures
from typing import Callable

from grpc import server

import dynod_commons
from dynod_commons.api import Empty, InfoApiVersion, MultiServiceInfo, Result, ResultCode, ServiceInfo
from dynod_commons.api.info_pb2_grpc import InfoServiceServicer, add_InfoServiceServicer_to_server
from dynod_commons.rpc.trace import trace_buffer, trace_rpc
from dynod_commons.utils import DynodError

LOG = logging.getLogger(__name__)


class RpcMethod:
    def __init__(self, name: str, manager: object, return_type: object, info: ServiceInfo):
        self.manager_method = getattr(manager, name)
        self.return_type = return_type
        self.info = info

    def server_call(self, request, context):
        LOG.debug(trace_rpc(True, request, context=context))

        try:
            # Verify API version
            metadata = {k: v for k, v in context.invocation_metadata()}
            if "api_version" in metadata:
                client_version = int(metadata["api_version"])
                if client_version > self.info.current_api_version:
                    raise DynodError(
                        f"Server current API version ({self.info.current_api_version}) is too old for client API version ({client_version})",
                        rc=ResultCode.ERROR_API_SERVER_TOO_OLD,
                    )
                elif client_version < self.info.supported_api_version:
                    raise DynodError(
                        f"Client API version ({client_version}) is too old for server supported API version ({self.info.current_api_version})",
                        rc=ResultCode.ERROR_API_CLIENT_TOO_OLD,
                    )

            # Ok, delegate to manager
            result = self.manager_method(request)

        except Exception as e:
            # Something happened during the RPC execution

            # Extract RC if this was a known error
            rc = e.rc if isinstance(e, DynodError) else ResultCode.ERROR

            # Special case if operation just returns a Result object
            r = Result(code=rc, msg=str(e), stack="".join(traceback.format_tb(e.__traceback__)))
            result = r if self.return_type == Result else self.return_type(r=r)

        LOG.debug(trace_rpc(False, result, context=context))
        return result


class RpcServicer:
    """
    Generic servicer implementation, that:
     * logs method calls
     * checks api version
     * routes method to provided manager
    """

    def __init__(self, servicer_stub: object, manager: object, info: ServiceInfo):
        # Fake the stub methods
        for n in filter(lambda x: not x.startswith("__") and callable(getattr(servicer_stub, x)), dir(servicer_stub)):
            sig = inspect.signature(getattr(manager, n))
            return_type = sig.return_annotation
            LOG.debug(f" >> add method {n} (returns {return_type.__name__})")
            setattr(self, n, RpcMethod(n, manager, return_type, info).server_call)


class RpcServer(InfoServiceServicer):
    """
    Wrapper to GRPC api to setup an RPC server.

    Arguments:
        port:
            TCP port to be used by the RPC server.
        get_servicers:
            function which will be called back to hook RPC servicers for this RPC server instance.
            Signature:
                def get_servicers() -> list(tuple(info: ServiceInfo, add_method: callable, stub: object, manager: object))
            where:
                *info* is a ServiceInfo object holding API information for this servicer
                *add_method* is the GRPC generated method to add the servicer to the server instance
                *stub* is the GRPC generated object instance for this servicer
                *manager* is an object instance to which delegating method calls for this service
    """

    def __init__(self, port: int, get_servicers: Callable):
        self.__port = port
        LOG.debug(f"Starting RPC server on port {self.__port}")

        # Create server instance
        # TODO: add configuration item for parallel workers
        self.__server = server(futures.ThreadPoolExecutor(max_workers=30))

        # To be able to answer to "get info" rpc
        servicers = [
            (
                ServiceInfo(
                    name=InfoServiceServicer.__name__,
                    version=dynod_commons.__version__,
                    current_api_version=InfoApiVersion.INFO_API_CURRENT,
                    supported_api_version=InfoApiVersion.INFO_API_SUPPORTED,
                ),
                add_InfoServiceServicer_to_server,
                InfoServiceServicer(),
                self,
            )
        ]

        # Get servicers
        servicers.extend(get_servicers())

        # Register everything
        self.__info = []
        for info, method, stub, manager in servicers:
            LOG.debug(f"Registering service in RPC server: {trace_buffer(info)}")

            # Remember info
            self.__info.append(info)

            # Register servicer in RPC server
            method(RpcServicer(stub, manager, info), self.__server)

        # Setup port and start
        try:
            self.__server.add_insecure_port(f"[::]:{self.__port}")
        except Exception as e:
            msg = f"Failed to start RPC server on port {self.__port}: {e}"
            LOG.error(msg)
            raise DynodError(msg, rc=ResultCode.ERROR_SUBPROCESS_FAILED)
        self.__server.start()
        LOG.debug(f"RPC server started on port {self.__port}")

    def shutdown(self):
        """
        Shuts down this RPC server instance
        """

        # Stop server and wait for termination
        LOG.debug(f"Shutting down RPC server on port {self.__port}")
        self.__server.stop(None)
        self.__server.wait_for_termination()
        LOG.debug(f"RPC server shut down on port {self.__port}")

    def get(self, request: Empty) -> MultiServiceInfo:
        # Just build message from stored info
        return MultiServiceInfo(items=self.__info)
