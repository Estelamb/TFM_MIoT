"""gRPC stubs singleton for the gateway."""
import grpc
from shared.proto_gen import (
    device_pb2_grpc, ai_pb2_grpc, script_pb2_grpc,
    compilation_pb2_grpc, deployment_pb2_grpc, monitoring_pb2_grpc,
)
from app.config import get_settings

_stubs: dict = {}

def init_stubs():
    s = get_settings()
    _stubs["device"]      = device_pb2_grpc.DeviceServiceStub(grpc.aio.insecure_channel(s.device_service_grpc))
    _stubs["ai"]          = ai_pb2_grpc.AIServiceStub(grpc.aio.insecure_channel(s.ai_service_grpc))
    _stubs["script"]      = script_pb2_grpc.ScriptServiceStub(grpc.aio.insecure_channel(s.script_service_grpc))
    _stubs["compilation"] = compilation_pb2_grpc.CompilationServiceStub(grpc.aio.insecure_channel(s.compilation_service_grpc))
    _stubs["deployment"]  = deployment_pb2_grpc.DeploymentServiceStub(grpc.aio.insecure_channel(s.deployment_service_grpc))
    _stubs["monitoring"]  = monitoring_pb2_grpc.MonitoringServiceStub(grpc.aio.insecure_channel(s.monitoring_service_grpc))

def get_stub(name: str):
    return _stubs[name]
