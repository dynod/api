import logging

from pytest_multilog import TestHelper

from dynod_commons.api import Empty, LoggerStatus, ResultCode
from dynod_commons.api.logs_pb2_grpc import LogsServiceServicer, LogsServiceStub, add_LogsServiceServicer_to_server
from dynod_commons.rpc import RpcClient, RpcServer
from dynod_commons.utils import DynodError


class SampleLog(LogsServiceServicer):
    def list(self, request: Empty, context) -> LoggerStatus:  # NOQA: A003
        logging.info("In SampleLog.list!!!")
        return LoggerStatus()


class TestRpcServer(TestHelper):
    def sample_register(self, server):
        add_LogsServiceServicer_to_server(SampleLog(), server)

    @property
    def worker_index(self):
        # TODO: move this up to pytest-multilog
        worker = self.worker
        return int(worker[2:]) if worker.startswith("gw") else 0

    @property
    def rpc_port(self) -> int:
        return 52100 + self.worker_index

    def dummy_call(self):
        # Try a dummy call
        client = RpcClient("127.0.0.1", self.rpc_port, {"logs": LogsServiceStub})
        s = client.logs.list(Empty())
        assert s.r.code == ResultCode.OK

    def test_server1(self):
        # Start server
        srv = RpcServer(self.rpc_port, self.sample_register)
        self.dummy_call()

        # Shutdown server
        srv.shutdown()

    def test_server2(self):
        # Start server
        srv = RpcServer(self.rpc_port, self.sample_register)
        self.dummy_call()

        # Shutdown server
        srv.shutdown()

    def test_server_forbidden_port(self):
        # Try to use a system port
        try:
            RpcServer(22, self.sample_register)
            raise AssertionError("Shouldn't get here")
        except DynodError as e:
            assert e.rc == ResultCode.ERROR_SUBPROCESS_FAILED
