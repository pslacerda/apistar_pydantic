import re
from inspect import Parameter, signature
from typing import List, Type

from apistar import (
    codecs, exceptions, validators, http, types,
    Route as _Route,
)
from apistar.conneg import negotiate_content_type
from apistar.server.components import Component
from apistar.http import (
    PathParams, QueryParams, Body, Headers,
)
from apistar.document import Field
try:
    import pydantic
except ImportError:
    pydantic = None


__ALL__ = [
    'QueryParam', 'PathParam', 'BodyData', 'DictQueryData',
    'Route', 'components'
]

if pydantic:
    __ALL__.extend([
        'PydanticBodyData', 'PyDanticQueryData'
    ])


class ParamData:

    def __getitem__(self, type_cls):
        return type(type_cls.__name__, (type_cls, self.__class__), {})


class _QueryParam(ParamData):
    """Annotation for parameters received in the query string."""


class _PathParam(ParamData):
    """Annotation for parameters received in the path."""


class _BodyData(ParamData):
    """Annotation for parameters received in the body data.

    These parameters are poorly described in the generated schema and
    documentation.
    """


class _DictQueryData(ParamData):
    """Annotation for dict like parameters received in the query string.

    These parameters aren't documentable in the generated schema and
    documentation.
    """


QueryParam = _QueryParam()
PathParam = _PathParam()
BodyData = _BodyData()
DictQueryData = _DictQueryData()


if pydantic:
    class _PydanticBodyData(_BodyData):
        """Annotation for pydantic parameters received in the body data."""

    class _PydanticQueryData(_DictQueryData):
        """Annotation for pydantic parameters received in the query string."""

    PydanticBodyData = _PydanticBodyData()
    PydanticQueryData = _PydanticQueryData()


class Route(_Route):

    def generate_fields(self, url, method, handler):
        if not self.documented:
            return []

        fields = []

        for name, param in signature(handler).parameters.items():
            if issubclass(param.annotation, _PathParam):
                if issubclass(param.annotation, int):
                    validator_cls = validators.Integer
                elif issubclass(param.annotation, float):
                    validator_cls = validators.Number
                elif issubclass(param.annotation, str):
                    validator_cls = validators.String
                else:
                    raise exceptions.ConfigurationError(
                        f"Cannot handle {name} of {handler}")

                location = 'path'
                schema = validator_cls()
                field = Field(name=name, location=location, schema=schema)
                fields.append(field)

            elif issubclass(param.annotation, _QueryParam):
                if param.default is param.empty:
                    kwargs = {}
                elif param.default is None:
                    # TODO handle Optional
                    kwargs = {'default': None, 'allow_null': True}
                else:
                    kwargs = {'default': param.default}

                if issubclass(param.annotation, int):
                    validator_cls = validators.Integer
                elif issubclass(param.annotation, float):
                    validator_cls = validators.Number
                elif issubclass(param.annotation, str):
                    validator_cls = validators.String
                elif getattr(param.annotation, '__bool__', None):
                    validator_cls = validators.Boolean
                else:
                    raise exceptions.ConfigurationError(
                        f"Cannot handle {name} of {handler}")

                location = 'query'
                schema = validator_cls(**kwargs)
                field = Field(name=name, location=location, schema=schema)
                fields.append(field)

            elif issubclass(param.annotation, _BodyData):
                location = 'body'
                schema = validators.Object()
                field = Field(name=name, location=location, schema=schema)
                fields.append(field)

            elif issubclass(param.annotation, ParamData):
                raise exceptions.ConfigurationError(
                    f"{param.annotation} do not support documentation.")

            else:
                # fallback to original generate_fields() method
                path_names = [
                    item.strip('{}').lstrip('+')
                    for item in re.findall('{[^}]*}', url)
                ]
                if name in path_names:
                    schema = {
                        param.empty: None,
                        int: validators.Integer(),
                        float: validators.Number(),
                        str: validators.String()
                    }[param.annotation]
                    field = Field(name=name, location='path', schema=schema)
                    fields.append(field)

                elif param.annotation in (param.empty, int, float, bool, str,
                                          http.QueryParam):
                    if param.default is param.empty:
                        kwargs = {}
                    elif param.default is None:
                        kwargs = {'default': None, 'allow_null': True}
                    else:
                        kwargs = {'default': param.default}
                    schema = {
                        param.empty: None,
                        int: validators.Integer(**kwargs),
                        float: validators.Number(**kwargs),
                        bool: validators.Boolean(**kwargs),
                        str: validators.String(**kwargs),
                        http.QueryParam: validators.String(**kwargs),
                    }[param.annotation]
                    field = Field(name=name, location='query', schema=schema)
                    fields.append(field)

                elif issubclass(param.annotation, types.Type):
                    if method in ('GET', 'DELETE'):
                        items = param.annotation.validator.properties.items()
                        for name, validator in items:
                            field = Field(name=name, location='query',
                                          schema=validator)
                            fields.append(field)
                    else:
                        field = Field(name=name, location='body',
                                      schema=param.annotation.validator)
                        fields.append(field)

        return fields


def resolve(parameter: Parameter, params_dict):
    try:
        value = params_dict[parameter.name]
    except KeyError:
        if parameter.default is not parameter.empty:
            return parameter.default
        else:
            raise exceptions.NotFound(
                f"Parameter {parameter.name} not resolved")
    try:
        return parameter.annotation(value)
    except Exception:
        raise exceptions.BadRequest(f"Parameter {parameter.name} invalid")


class ParameterHandlerMixin:

    annotation: Type

    def can_handle_parameter(self, parameter: Parameter):
        return issubclass(parameter.annotation, self.annotation)


class PathParamsComponent(ParameterHandlerMixin, Component):

    annotation = _PathParam

    def resolve(self,
                parameter: Parameter,
                path_params: PathParams):
        return resolve(parameter, path_params)


class QueryParamComponent(ParameterHandlerMixin, Component):

    annotation = _QueryParam

    def resolve(self,
                parameter: Parameter,
                query_params: QueryParams):
        return resolve(parameter, query_params)


class DataComponent(Component):

    def handle_parameter(self, parameter: Parameter, value_dict):
        return parameter.annotation(value_dict)


class BodyDataComponent(ParameterHandlerMixin, DataComponent):

    annotation = _BodyData

    def __init__(self):
        self.codecs = [
            codecs.JSONCodec(),
            codecs.URLEncodedCodec(),
            codecs.MultiPartCodec(),
        ]

    def resolve(self,
                content: Body,
                headers: Headers,
                parameter: Parameter):
        if not content:
            raise NotImplementedError

        content_type = headers.get('Content-Type')
        try:
            codec = negotiate_content_type(self.codecs, content_type)
        except exceptions.NoCodecAvailable:
            raise exceptions.UnsupportedMediaType()
        try:
            value = codec.decode(content, headers=headers)
        except exceptions.ParseError as exc:
            raise exceptions.BadRequest(str(exc))
        try:
            return self.handle_parameter(parameter, value)
        except Exception:
            raise exceptions.BadRequest(f"{parameter.name} invalid")


class DictQueryDataComponent(ParameterHandlerMixin, DataComponent):

    annotation = _DictQueryData

    def resolve(self,
                parameter: Parameter,
                query_params: QueryParams):
        try:
            return self.handle_parameter(parameter, query_params)
        except Exception:
            raise exceptions.BadRequest(f"Parameter {parameter.name} invalid")


if pydantic:

    class PydanticBodyDataComponent(BodyDataComponent):

        annotation: Type = _PydanticBodyData

        def handle_parameter(self, parameter, value_dict):
            return parameter.annotation(**value_dict)

    class PydanticQueryDataComponent(DictQueryDataComponent):

        annotation: Type = _PydanticQueryData

        def handle_parameter(self, parameter, value_dict):
            return parameter.annotation(**value_dict)


components: List[Component] = []

if pydantic:
    # try pydantic components before others
    components.extend([
        PydanticBodyDataComponent(),
        PydanticQueryDataComponent(),
    ])

components.extend([
    PathParamsComponent(),
    QueryParamComponent(),
    BodyDataComponent(),
    DictQueryDataComponent(),
])
