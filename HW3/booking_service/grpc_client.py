import os
import grpc
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

import flight_pb2
import flight_pb2_grpc

FLIGHT_SERVICE_URL = os.getenv("FLIGHT_SERVICE_URL", "localhost:50051")
API_KEY = os.getenv("API_KEY", "secret-key-123")

channel = grpc.insecure_channel(FLIGHT_SERVICE_URL)
stub = flight_pb2_grpc.FlightServiceStub(channel)

def is_retryable(exception):
    if isinstance(exception, grpc.RpcError):
        code = exception.code()
        return code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)
    return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=0.4),
    retry=retry_if_exception(is_retryable),
    reraise=True
)
def call_flight_service(method_name, request):
    metadata = (('authorization', f'Bearer {API_KEY}'),)
    method = getattr(stub, method_name)
    return method(request, metadata=metadata)
