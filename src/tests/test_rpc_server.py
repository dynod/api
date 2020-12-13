import logging

import pytest
from grpc import RpcError, StatusCode
from pytest_multilog import TestHelper

import dynod_commons
from dynod_commons.api import Empty, InfoApiVersion, LoggerConfig, LoggerStatus, LogsApiVersion, LogStop, ResultCode
from dynod_commons.api.logs_pb2_grpc import LogsServiceServicer, LogsServiceStub, add_LogsServiceServicer_to_server
from dynod_commons.rpc import RpcClient, RpcServer, RpcServiceDescriptor
from dynod_commons.utils import DynodError


class SampleLog(LogsServiceServicer):
    def list(self, request: Empty) -> LoggerStatus:  # NOQA: A003
        logging.info("In SampleLog.list!!!")
        return LoggerStatus()

    def update(self, request) -> LoggerStatus:
        # Error sample
        raise DynodError("sample error", rc=ResultCode.ERROR_RESOURCE_UNKNOWN)


class TestRpcServer(TestHelper):
    @property
    def sample_register(self) -> list:
        return [RpcServiceDescriptor(dynod_commons, LogsApiVersion, SampleLog(), add_LogsServiceServicer_to_server)]

    @pytest.fixture
    def sample_server(self):
        # Start server
        srv = RpcServer(self.rpc_port, self.sample_register)

        # Yield to test
        yield

        # Shutdown server
        srv.shutdown()

    @pytest.fixture
    def client(self, sample_server):
        # Setup RPC client
        yield RpcClient("127.0.0.1", self.rpc_port, {"logs": (LogsServiceStub, LogsApiVersion.LOGS_API_CURRENT)}, name="pytest")

    @property
    def rpc_port(self) -> int:
        return 52100 + self.worker_index

    def test_server(self, client):
        # Normal call
        s = client.logs.list(Empty())
        assert s.r.code == ResultCode.OK

    def test_exceptions(self, client):
        # Error call
        s = client.logs.update(LoggerConfig())
        assert s.r.code == ResultCode.ERROR_RESOURCE_UNKNOWN

    def test_server_forbidden_port(self):
        # Try to use a system port
        try:
            RpcServer(22, self.sample_register)
            raise AssertionError("Shouldn't get here")
        except DynodError as e:
            assert e.rc == ResultCode.ERROR_SUBPROCESS_FAILED

    def test_get_info(self, client):
        # Try a "get info" call
        s = client.info.get(Empty())
        assert len(s.items) == 2
        info = s.items[0]
        assert info.name == dynod_commons.__title__
        assert info.version == dynod_commons.__version__
        assert info.current_api_version == InfoApiVersion.INFO_API_CURRENT
        assert info.supported_api_version == InfoApiVersion.INFO_API_SUPPORTED
        info = s.items[1]
        assert info.name == dynod_commons.__title__
        assert info.version == dynod_commons.__version__
        assert info.current_api_version == LogsApiVersion.LOGS_API_CURRENT
        assert info.supported_api_version == LogsApiVersion.LOGS_API_SUPPORTED

    def test_client_no_version(self, sample_server):
        # Try with client not providing API version
        c = RpcClient("127.0.0.1", self.rpc_port, {"logs": (LogsServiceStub, None)})
        s = c.logs.list(Empty())
        assert s.r.code == ResultCode.OK

    def test_client_too_old(self, sample_server):
        # Try with client with too old API version
        c = RpcClient("127.0.0.1", self.rpc_port, {"logs": (LogsServiceStub, LogsApiVersion.LOGS_API_CURRENT - 1)})
        s = c.logs.list(Empty())
        assert s.r.code == ResultCode.ERROR_API_CLIENT_TOO_OLD

    def test_server_too_old(self, sample_server):
        # Try with client with API version > server version
        c = RpcClient("127.0.0.1", self.rpc_port, {"logs": (LogsServiceStub, LogsApiVersion.LOGS_API_CURRENT + 1)})
        s = c.logs.list(Empty())
        assert s.r.code == ResultCode.ERROR_API_SERVER_TOO_OLD

    def test_no_server(self):
        # Test behavior when client request is made and server is not ready
        c = RpcClient("127.0.0.1", 1, {"logs": (LogsServiceStub, LogsApiVersion.LOGS_API_CURRENT)}, timeout=None)
        try:
            c.logs.list(Empty())
            raise AssertionError("Shouldn't get there")
        except RpcError as e:
            assert e.code() == StatusCode.UNAVAILABLE

    def test_no_server_timeout(self):
        # Same as above, with timeout
        c = RpcClient("127.0.0.1", 1, {"logs": (LogsServiceStub, LogsApiVersion.LOGS_API_CURRENT)}, timeout=1)
        try:
            c.logs.list(Empty())
            raise AssertionError("Shouldn't get there")
        except RpcError as e:
            assert e.code() == StatusCode.UNAVAILABLE

        # Verify we retried at least one time
        self.check_logs("(retry)")

    def test_not_implemented(self, client):
        # Normal call
        try:
            client.logs.stop(LogStop())
            raise AssertionError("Shouldn't get there")
        except RpcError as e:
            assert e.code() == StatusCode.UNIMPLEMENTED
