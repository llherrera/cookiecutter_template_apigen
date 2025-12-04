
from fastapi import APIRouter
router = APIRouter()

{% for route in cookiecutter.spec.routes %}
@router.{{ route.method|lower }}("{{ route.path }}")
async def {{ route.name }}({% if route.params %}{% for p in route.params %}{{ p.name }}: {{ p.type }}{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}):
    return {{ route.response_example|default({"status":"ok"}) }}
{% endfor %}
