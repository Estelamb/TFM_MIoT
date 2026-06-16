# Contributing

## Regenerate gRPC stubs

After modifying any `.proto` file in `shared/proto/`:

```bash
python -m grpc_tools.protoc \
  -I shared/proto \
  --python_out=shared/proto_gen \
  --grpc_python_out=shared/proto_gen \
  shared/proto/*.proto

for f in shared/proto_gen/*_pb2_grpc.py; do
  sed -i 's/^import \(.*_pb2\)/from shared.proto_gen import \1/' "$f"
done
```

## Build docs locally

```bash
cd docs && make html
# Output in docs/sphinx/build/html/
```

## Adding a new compiler

1. Create `services/mlops-service/app/compilers/<hw>.py`
2. Implement `CompilerBase.compile()`
3. Register in `COMPILER_REGISTRY` inside `compilation_handler.py`

## Adding a new hardware backend

1. Create `edge-runtime/aura_hw/backends/<hw>.py`
2. Implement `InferenceBackend` (`load`, `infer`, `unload`, `hardware_type`)
3. Register in `_get_backend()` inside `aura_hw/runtime.py`
4. Add detection logic in `aura_hw/detect.py`
