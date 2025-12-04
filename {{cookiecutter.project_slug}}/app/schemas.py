
from pydantic import BaseModel

{% for schema in cookiecutter.spec.schemas %}
class {{ schema.name }}(BaseModel):
    {% for field in schema.fields %}
    {{ field.name }}: {{ field.type }}{% if field.default is defined %} = {{ field.default }}{% endif %}
    {% endfor %}
{% endfor %}
