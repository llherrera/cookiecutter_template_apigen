import os
import json
import sys

try:
    import yaml
except Exception:
    yaml = None

from pathlib import Path

PROJECT_DIR = Path.cwd()

OPENAPI_PATH = PROJECT_DIR / "{{ cookiecutter.openapi_path }}"
MODELS_DIR = PROJECT_DIR / "{{ cookiecutter.models_package }}"
ROUTERS_DIR = PROJECT_DIR / "{{ cookiecutter.routers_package }}"
FRAMEWORK = "{{ cookiecutter.framework }}"
GENERATE = "{{ cookiecutter.generate_from_openapi }}" == "y"

def load_spec(path: Path):
    if not path.exists():
        print(f"[WARN] OpenAPI no encontrado: {path}")
        return None
    text = path.read_text(encoding="utf-8")
    # Detecta JSON vs YAML simple
    if path.suffix.lower() == ".json":
        return json.loads(text)
    else:
        if yaml is None:
            # Parser YAML no disponible; intenta heurística JSON
            try:
                return json.loads(text)
            except Exception:
                print("[ERROR] Necesitas PyYAML si el spec es YAML.")
                return None
        return yaml.safe_load(text)

def map_schema_to_pydantic(name: str, schema: dict) -> str:
    """
    Genera una clase Pydantic desde un schema OpenAPI simple (type=object, properties).
    No cubre todos los casos; amplíalo según tus necesidades.
    """
    required = set(schema.get("required", []))
    props = schema.get("properties", {})
    lines = [f"class {name}(BaseModel):"]
    if not props:
        lines.append("    pass")
        return "\n".join(lines)
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool"
    }
    for prop_name, prop in props.items():
        oatype = prop.get("type")
        pytype = type_map.get(oatype, "Any")
        optional = prop_name not in required
        default = " | None = None" if optional and pytype != "Any" else " = None" if optional else ""
        # Pydantic v2 typing
        annotation = f"{pytype}{'' if not optional else ' | None'}"
        lines.append(f"    {prop_name}: {annotation}{' = None' if optional else ''}")
    return "\n".join(lines)

def generate_models(spec: dict):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    init_path = MODELS_DIR / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")

    components = spec.get("components", {})
    schemas = components.get("schemas", {})
    if not schemas:
        print("[INFO] No hay components.schemas para generar modelos.")
        return

    header = (
        "from pydantic import BaseModel\n"
        "from typing import Any\n\n"
    )

    for name, schema in schemas.items():
        # Soporte $ref/oneOf/allOf queda pendiente para versiones avanzadas
        content = header + map_schema_to_pydantic(name, schema) + "\n"
        (MODELS_DIR / f"{name.lower()}.py").write_text(content, encoding="utf-8")
        print(f"[OK] Modelo generado: {name.lower()}.py")

def pascal_to_snake(name: str) -> str:
    out = []
    for ch in name:
        if ch.isupper():
            out.append("_" + ch.lower())
        else:
            out.append(ch)
    s = "".join(out)
    return s[1:] if s.startswith("_") else s

def generate_routers(spec: dict):
    if FRAMEWORK != "fastapi":
        print("[INFO] Generación de routers de ejemplo preparada para FastAPI.")
        return

    from_path = "from fastapi import APIRouter\n"
    ROUTERS_DIR.mkdir(parents=True, exist_ok=True)
    init_path = ROUTERS_DIR / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")

    paths = spec.get("paths", {})
    if not paths:
        print("[INFO] No hay paths en el OpenAPI.")
        return

    # Agrupar por tag (si existen), si no, por path base
    tag_groups = {}
    for path, ops in paths.items():
        for method, op in ops.items():
            if not isinstance(op, dict):
                continue
            tags = op.get("tags") or ["default"]
            for tag in tags:
                tag_groups.setdefault(tag, []).append((path, method.lower(), op))

    for tag, entries in tag_groups.items():
        router_name = pascal_to_snake(tag) if tag != "default" else "default"
        lines = [from_path, f"router = APIRouter(prefix=\"\", tags=[\"{tag}\"])\n\n"]
        for path, method, op in entries:
            operation_id = op.get("operationId") or f"{method}_{path.strip('/').replace('/', '_')}"
            # Simple: sin parámetros ni bodies complejos en este ejemplo
            lines.append(f"@router.{method}(\"{path}\")\n")
            lines.append(f"async def {pascal_to_snake(operation_id)}():\n")
            lines.append(f"    return {{\"ok\": True, \"op\": \"{operation_id}\"}}\n\n")

        file_path = ROUTERS_DIR / f"{router_name}.py"
        file_path.write_text("".join(lines), encoding="utf-8")
        print(f"[OK] Router generado: {file_path.name}")

def wire_fastapi_app():
    app_path = PROJECT_DIR / "src" / "app.py"
    if not app_path.exists():
        # Plantilla de app FastAPI mínima
        app_path.write_text(
            "from fastapi import FastAPI\n"
            "from src.api.routers import *  # noqa\n\n"
            "app = FastAPI(title=\"{{ cookiecutter.project_name }}\")\n"
            "from importlib import import_module\n"
            "import pkgutil\n"
            "for _, modname, _ in pkgutil.iter_modules(['src/api/routers']):\n"
            "    module = import_module(f'src.api.routers.{modname}')\n"
            "    if hasattr(module, 'router'):\n"
            "        app.include_router(module.router)\n",
            encoding="utf-8"
        )

def main():
    if not GENERATE:
        print("[INFO] Generación desde OpenAPI está deshabilitada.")
        return
    spec = load_spec(OPENAPI_PATH)
    if spec is None:
        return
    generate_models(spec)
    generate_routers(spec)
    if FRAMEWORK == "fastapi":
        wire_fastapi_app()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] post_gen_project: {e}")
        sys.exit(1)
