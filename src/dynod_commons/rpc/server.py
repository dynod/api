import logging
from concurrent import futures
from typing import Callable

from grpc import server

from dynod_commons.api import ResultCode
from dynod_commons.utils import DynodError

LOG = logging.getLogger(__name__)


class RpcServer:
    """
    Wrapper to GRPC api to setup an RPC server.

    Arguments:
        port:
            TCP port to be used by the RPC server.
        hook_servicers:
            function which will be called back to hook RPC servicers for this RPC server instance.
            Signature:
                def hook_servicers(server: grpc.server)
    """

    def __init__(self, port: int, hook_servicers: Callable):
        self.__port = port
        LOG.debug(f"Starting RPC server on port {self.__port}")

        # Create server instance
        # TODO: add configuration item for parallel workers
        self.__server = server(futures.ThreadPoolExecutor(max_workers=30))

        # Delegate servicers hooking
        hook_servicers(self.__server)

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
