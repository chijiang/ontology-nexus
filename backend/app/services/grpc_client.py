# backend/app/services/grpc_client.py
"""
动态 gRPC 客户端 (异步版)

使用 Server Reflection 发现服务定义，并支持动态方法调用。
不需要预编译 .proto 文件。
"""

import grpc
import grpc.aio
import logging
import json
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import message_factory
from google.protobuf.json_format import MessageToDict, ParseDict
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

logger = logging.getLogger(__name__)


class DynamicGrpcClient:
    def __init__(self, host: str, port: int):
        self.target = f"{host}:{port}"
        self.channel = None
        self.reflection_stub = None
        self.pool = descriptor_pool.DescriptorPool()
        self.factory = message_factory.MessageFactory(self.pool)
        self._loaded_files = set()
        self._services = {}  # service_name -> service_desc

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self, timeout: int = 5):
        """建立异步连接并验证连通性"""
        if self.channel:
            return

        try:
            self.channel = grpc.aio.insecure_channel(self.target)
            # 等待连接就绪
            await asyncio.wait_for(self.channel.channel_ready(), timeout=timeout)
            self.reflection_stub = reflection_pb2_grpc.ServerReflectionStub(
                self.channel
            )
            logger.info(f"Connected to gRPC server at {self.target} (async)")
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout to {self.target} after {timeout}s")
            if self.channel:
                await self.channel.close()
                self.channel = None
            raise Exception(
                f"连接超时 ({timeout}s)，请检查服务器地址 {self.target} 是否正确且服务已启动"
            )
        except Exception as e:
            logger.error(f"Failed to connect to {self.target}: {e}")
            if self.channel:
                await self.channel.close()
                self.channel = None
            raise

    async def close(self):
        """关闭连接"""
        if self.channel:
            await self.channel.close()
            self.channel = None
            self.reflection_stub = None

    async def _load_service_reflection(self, service_name: str):
        """通过反射加载服务定义到 DescriptorPool"""
        if service_name in self._services:
            return self._services[service_name]

        if not self.reflection_stub:
            await self.connect()

        # 发起反射请求
        def make_request():
            yield reflection_pb2.ServerReflectionRequest(
                file_containing_symbol=service_name
            )

        try:
            call = self.reflection_stub.ServerReflectionInfo(make_request())

            # 收集所有返回的描述符
            protos = []
            async for response in call:
                if response.HasField("file_descriptor_response"):
                    for (
                        file_data
                    ) in response.file_descriptor_response.file_descriptor_proto:
                        fd_proto = descriptor_pb2.FileDescriptorProto()
                        fd_proto.ParseFromString(file_data)
                        if fd_proto.name not in self._loaded_files:
                            protos.append(fd_proto)

                elif response.HasField("error_response"):
                    # 同原逻辑
                    if "not found" in response.error_response.error_message.lower():
                        logger.warning(
                            f"Symbol {service_name} not found, searching via list_services..."
                        )
                        all_services = await self.list_services()
                        full_name = next(
                            (s for s in all_services if s.endswith(f".{service_name}")),
                            None,
                        )
                        if full_name:
                            return await self._load_service_reflection(full_name)
                    raise Exception(
                        f"Reflection error: {response.error_response.error_message}"
                    )

            # 暴力循环添加直到全部成功或不再变化（解决依赖顺序问题）
            to_add = protos
            while to_add:
                new_to_add = []
                last_error = None
                for p in to_add:
                    try:
                        self.pool.Add(p)
                        self._loaded_files.add(p.name)
                        logger.debug(f"Added {p.name} to pool")
                    except Exception as e:
                        new_to_add.append(p)
                        last_error = e

                if len(new_to_add) == len(to_add):
                    # 进度陷入僵局
                    logger.error(
                        f"Failed to add some protos to pool. Last error: {last_error}"
                    )
                    break
                to_add = new_to_add

            # 从池中获取服务描述符
            try:
                service_desc = self.pool.FindServiceByName(service_name)
            except KeyError:
                # 尝试加上全限定名（如果知道包名）
                logger.error(f"Symbols in pool: {list(self._loaded_files)}")
                raise ValueError(
                    f"Service {service_name} not found in DescriptorPool after reflection. Available files: {list(self._loaded_files)}"
                )

            self._services[service_name] = service_desc
            return service_desc

        except Exception as e:
            logger.error(f"Failed to reflect service {service_name}: {e}")
            raise

    async def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """获取服务的详细描述"""
        service_desc = await self._load_service_reflection(service_name)

        methods = []
        message_types = {}

        def extract_msg(msg_desc):
            if msg_desc.full_name in message_types:
                return

            fields = []
            for field in msg_desc.fields:
                field_info = {
                    "name": field.name,
                    "type": field.type,
                    "type_name": (
                        field.message_type.full_name if field.message_type else None
                    ),
                    "label": field.label,
                }
                fields.append(field_info)
                if field.message_type:
                    extract_msg(field.message_type)

            message_types[msg_desc.full_name] = {
                "name": msg_desc.name,
                "full_name": msg_desc.full_name,
                "fields": fields,
            }

        for method in service_desc.methods:
            methods.append(
                {
                    "name": method.name,
                    "input_type": method.input_type.full_name,
                    "output_type": method.output_type.full_name,
                    "is_streaming": method.client_streaming or method.server_streaming,
                }
            )
            extract_msg(method.input_type)
            extract_msg(method.output_type)

        return {
            "service_name": service_name,
            "methods": methods,
            "message_types": list(message_types.values()),
        }

    async def call_method(
        self, service_name: str, method_name: str, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """动态调用 gRPC 方法"""
        service_desc = await self._load_service_reflection(service_name)
        method_desc = next(
            (m for m in service_desc.methods if m.name == method_name), None
        )

        if not method_desc:
            raise ValueError(
                f"Method {method_name} not found in service {service_name}"
            )

        InputMessageClass = message_factory.GetMessageClass(method_desc.input_type)
        request_msg = InputMessageClass()
        ParseDict(request_data, request_msg)

        method_path = f"/{service_desc.full_name}/{method_name}"

        if method_desc.client_streaming or method_desc.server_streaming:
            raise NotImplementedError("Streaming methods not supported")

        request_bytes = request_msg.SerializeToString()
        OutputMessageClass = message_factory.GetMessageClass(method_desc.output_type)

        try:
            unary_call = self.channel.unary_unary(
                method_path,
                request_serializer=lambda x: x,
                response_deserializer=lambda x: x,
            )
            response_bytes = await unary_call(request_bytes)

            response_msg = OutputMessageClass()
            response_msg.ParseFromString(response_bytes)

            return MessageToDict(response_msg, preserving_proto_field_name=True)
        except Exception as e:
            logger.error(f"Error calling {method_path}: {e}")
            raise

    async def list_services(self) -> List[str]:
        """列出服务器上的服务"""
        if not self.reflection_stub:
            await self.connect()

        def make_request():
            yield reflection_pb2.ServerReflectionRequest(list_services="")

        services = []
        try:
            call = self.reflection_stub.ServerReflectionInfo(make_request())
            async for response in call:
                if response.HasField("list_services_response"):
                    for s in response.list_services_response.service:
                        if s.name != "grpc.reflection.v1alpha.ServerReflection":
                            services.append(s.name)
        except Exception as e:
            logger.error(f"Failed to list services: {e}")

        return services

    async def test_connection(self) -> Tuple[bool, str, Optional[float]]:
        """测试连接并返回 (是否成功, 消息, 延迟ms)"""
        start_time = time.time()
        try:
            await self.connect()
            latency_ms = (time.time() - start_time) * 1000
            return True, "连接成功", round(latency_ms, 2)
        except Exception as e:
            return False, str(e), None
