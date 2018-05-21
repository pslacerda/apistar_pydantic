from inspect import Parameter

from apistar import codecs, exceptions, Route as _Route
from apistar.conneg import negotiate_content_type
from apistar.server.components import Component
from apistar.http import PathParams, QueryParams, Body, Headers
try:
    import pydantic
except ImportError:
    pydantic = None


__ALL__ = ['QueryParam', 'PathParam', 'DictBodyData']


class ParamData:

    def __getitem__(self, type_cls):
        return type(type_cls.__name__, (type_cls, self.__class__), {})


class _QueryParam(ParamData):
    pass


class _PathParam(ParamData):
    pass


class _DictBodyData(ParamData):
    pass


class _DictQueryData(ParamData):
    pass


QueryParam = _QueryParam()
PathParam = _PathParam()
DictBodyData = _DictBodyData()
DictQueryData = _DictQueryData()


if pydantic:
    class _PydanticBodyData(ParamData):
        pass

    class _PydanticQueryData(ParamData):
        pass

    PydanticBodyData = _PydanticBodyData()
    PydanticQueryData = _PydanticQueryData()


class Route(_Route):

    def __init__(self, *args, **kwargs):
        kwargs['documented'] = False
        super().__init__(*args, **kwargs)

    def generate_link(self, *args):
        pass


def _resolve(parameter: Parameter, params_dict):
    try:
        value = params_dict[parameter.name]
    except KeyError:
        if parameter.default is not parameter.empty:
            return parameter.default
        else:
            raise exceptions.NotFound(f"Parameter {parameter.name} not resolved")
    try:
        return parameter.annotation(value)
    except Exception:
        raise exceptions.BadRequest(f"Parameter {parameter.name} invalid")


class ParameterHandlerMixin:

    annotation = None

    def can_handle_parameter(self, parameter: Parameter):
        return issubclass(parameter.annotation, self.annotation)


class PathParamsComponent(ParameterHandlerMixin, Component):

    annotation = _PathParam

    def resolve(self,
                parameter: Parameter,
                path_params: PathParams):
        return _resolve(parameter, path_params)


class QueryParamComponent(ParameterHandlerMixin, Component):

    annotation = _QueryParam

    def resolve(self,
                parameter: Parameter,
                query_params: QueryParams):
        return _resolve(parameter, query_params)


class DataComponent(Component):

    def handle_parameter(self, parameter: Parameter, value_dict):
        return parameter.annotation(value_dict)


class DictBodyDataComponent(ParameterHandlerMixin, DataComponent):

    annotation = _DictBodyData

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


components = [
    PathParamsComponent(),
    QueryParamComponent(),
    DictBodyDataComponent(),
    DictQueryDataComponent(),
]


if pydantic:

    class PydanticBodyDataComponent(DictBodyDataComponent):

        annotation = _PydanticBodyData

        def handle_parameter(self, parameter, value_dict):
            return parameter.annotation(**value_dict)

    class PydanticQueryDataComponent(DictQueryDataComponent):

        annotation = _PydanticQueryData

        def handle_parameter(self, parameter, value_dict):
            return parameter.annotation(**value_dict)

    components.extend([
        PydanticBodyDataComponent(),
        PydanticQueryDataComponent(),
    ])
