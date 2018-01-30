import enum
import inspect
import json
import textwrap
from datetime import datetime
from typing import (
    Any, Callable, Tuple, Optional, Mapping, List, Set, Type, cast
)

import coreapi
import coreschema
import uritemplate
import pydantic
from apistar import exceptions, http, Settings, Route, Component
from apistar.core import flatten_routes
from apistar.interfaces import (
    Injector, Schema, Router, Templates, StaticFiles, CommandLineClient,
    Console, SessionStore
)
from apistar.components import (
    dependency, templates, statics, router, commandline, console,
    sessions
)
from apistar.frameworks.wsgi import WSGIApp
from apistar.frameworks.asyncio import ASyncIOApp
from apistar.renderers import JSONRenderer
from apistar.types import (
    ParamName, KeywordArgs, ParamAnnotation, WSGIEnviron, Handler, UMIChannels,
    UMIMessage, RouteConfig
)

__all__ = [
    'ASyncIOApp', 'WSGIApp',
    'JSONRenderer',
    'QueryData', 'FormData', 'BodyData'
]


class HTTPParameterData:
    _request_location: str = None
    _schema_location: str = None

    def __getitem__(self, type_cls):
        return type(type_cls.__name__, (type_cls, self.__class__), {})


class _QueryData(HTTPParameterData):
    _request_location: str = 'query'
    _schema_location: str = 'query'


class _FormData(HTTPParameterData):
    _data_location: str = 'form'
    _schema_location: str = 'form'


class _BodyData(HTTPParameterData):
    _data_location: str = 'body'
    _schema_location: str = 'form'


QueryData = _QueryData()
FormData = _FormData()
BodyData = _BodyData()


class PydanticHTTPResolver(dependency.HTTPResolver):
    """
    Handles resolving parameters for HTTP requests with pydantic.
    """

    @classmethod
    def coerce(cls, type_func, value):
        if value is None or isinstance(value, type_func):
            return value
        if issubclass(type_func, pydantic.BaseModel):
            if isinstance(value, Mapping):
                return type_func(**value)
        return type_func(value)

    def resolve(self,
                param: inspect.Parameter,
                func: Callable) -> Optional[Tuple[str, Callable]]:
        annotation = param.annotation
        key = '%s:%s' % (annotation.__name__.lower(), param.name)

        if annotation is inspect.Parameter.empty:
            key = 'empty:' + param.name
            return key, self.empty
        elif issubclass(annotation, (str, int, float, bool, _QueryData)):
            return key, self.url_or_query_argument
        elif issubclass(annotation, (dict, list, _BodyData)):
            return key, self.body_argument
        elif issubclass(annotation, _FormData):
            return key, self.form_argument
        return None

    def url_argument(self,
                     name: ParamName,
                     kwargs: KeywordArgs,
                     coerce: ParamAnnotation) -> Any:
        return self.coerce(coerce, kwargs[name])

    def query_argument(self,
                       name: ParamName,
                       query_params: http.QueryParams,
                       coerce: ParamAnnotation) -> Any:
        value = query_params.get(name)
        if issubclass(coerce, _QueryData):
            value = query_params
        return self.coerce(coerce, value)

    def form_argument(self,
                      data: http.RequestData,
                      name: ParamName,
                      coerce: ParamAnnotation) -> Any:
        if not isinstance(data, dict):
            raise exceptions.ValidationError(
                detail='Request data must be an object.'
            )
        return self.coerce(coerce, data)

    def body_argument(self,
                      data: http.RequestData,
                      coerce: ParamAnnotation) -> Any:
        return self.coerce(coerce, data)


class CoreAPISchema(Schema):

    native_types = [int, float, str, bool, datetime]

    def __init__(self,
                 router: Router,
                 routes: RouteConfig,
                 settings: Settings) -> None:
        try:
            url = router.reverse_url('serve_schema')
        except exceptions.NoReverseMatch:
            url = None

        content = {}
        for route in flatten_routes(routes):
            if getattr(route.view, 'exclude_from_schema', False):
                continue
            content[route.name] = self.get_link(route)

        schema_settings = settings.get('SCHEMA', {})
        title = schema_settings.get('TITLE', '')
        description = schema_settings.get('DESCRIPTION', '')
        url = schema_settings.get('URL', url)

        super().__init__(title=title, description=description, url=url, content=content)

    @classmethod
    def get_link(cls, route: Route) -> coreapi.Link:
        path, method, view, name = route

        fields: List[coreapi.Field] = []
        path_names = set(uritemplate.URITemplate(path).variable_names)
        for param in inspect.signature(view).parameters.values():
            fields += cls.get_field(param, path_names)

        description = cls.get_docstring(view, None)
        return coreapi.Link(url=path, action=method, description=description, fields=fields)

    @classmethod
    def get_field(cls,
                  param: inspect.Parameter,
                  path_names: Set[str]) -> List[coreapi.Field]:
        field_type = param.annotation
        if field_type is inspect.Signature.empty:
            field_type = str

        if not inspect.isclass(field_type):
            return []  # TODO callable

        if param.name in path_names:
            return [coreapi.Field(
                name=param.name,
                location='path',
                required=True,
                schema=cls.get_param_schema(field_type)
            )]

        elif (issubclass(field_type, pydantic.BaseModel)
                and issubclass(field_type, HTTPParameterData)):
            # TODO recursive models
            # TODO Optional and Union types
            return [
                coreapi.Field(
                    name=name,
                    location=field_type._schema_location,
                    required=True,
                    schema=cls.get_param_schema(value)
                )
                for name, value in field_type.__annotations__.items()
            ]

        return []

    @classmethod
    def get_param_schema(cls, annotated_type: Type) -> coreschema.schemas.Schema:
        schema_kwargs = {
            'description': cls.get_docstring(annotated_type, '')
        }
        if issubclass(annotated_type, bool):
            return coreschema.Boolean(**schema_kwargs)
        elif issubclass(annotated_type, int):
            return coreschema.Integer(**schema_kwargs)
        elif issubclass(annotated_type, float):
            return coreschema.Number(**schema_kwargs)
        elif issubclass(annotated_type, enum.Enum):
            choices = cast(Type[enum.Enum], annotated_type)
            choices = [c.value for c in choices]
            return coreschema.Enum(enum=choices, **schema_kwargs)
        return coreschema.String(**schema_kwargs)

    @classmethod
    def get_docstring(cls, obj: Type, default: Optional[str]) -> str:
        if obj.__doc__ and obj not in cls.native_types:
            return textwrap.dedent(obj.__doc__).strip()
        else:
            return default


class WSGIApp(WSGIApp):

    BUILTIN_COMPONENTS = [
        Component(Schema, init=CoreAPISchema),
        Component(Templates, init=templates.Jinja2Templates),
        Component(StaticFiles, init=statics.WhiteNoiseStaticFiles),
        Component(Router, init=router.WerkzeugRouter),
        Component(CommandLineClient, init=commandline.ArgParseCommandLineClient),
        Component(Console, init=console.PrintConsole),
        Component(SessionStore, init=sessions.LocalMemorySessionStore),
    ]

    def create_http_injector(self) -> Injector:
        http_components = {
            component.cls: component.init
            for component in self.HTTP_COMPONENTS
        }

        return self.INJECTOR_CLS(
            components={**http_components, **self.components},
            initial_state=self.preloaded_state,
            required_state={
                WSGIEnviron: 'wsgi_environ',
                Handler: 'handler',
                KeywordArgs: 'kwargs',
                Exception: 'exc',
                http.ResponseHeaders: 'response_headers',
                http.ResponseData: 'response_data'
            },
            resolvers=[PydanticHTTPResolver()]
        )


class ASyncIOApp(ASyncIOApp):

    BUILTIN_COMPONENTS = [
        Component(Schema, init=CoreAPISchema),
        Component(Templates, init=templates.Jinja2Templates),
        Component(StaticFiles, init=statics.WhiteNoiseStaticFiles),
        Component(Router, init=router.WerkzeugRouter),
        Component(CommandLineClient, init=commandline.ArgParseCommandLineClient),
        Component(Console, init=console.PrintConsole),
        Component(SessionStore, init=sessions.LocalMemorySessionStore),
    ]

    def create_http_injector(self) -> Injector:
        """
        Create the dependency injector for running handlers in response to
        incoming HTTP requests.
        """
        http_components = {
            component.cls: component.init
            for component in self.HTTP_COMPONENTS
        }

        return self.INJECTOR_CLS(
            components={**http_components, **self.components},
            initial_state=self.preloaded_state,
            required_state={
                UMIMessage: 'message',
                UMIChannels: 'channels',
                KeywordArgs: 'kwargs',
                Handler: 'handler',
                Exception: 'exc',
                http.ResponseHeaders: 'response_headers',
                http.ResponseData: 'response_data'
            },
            resolvers=[PydanticHTTPResolver()]
        )


class JSONRenderer(JSONRenderer):

    @staticmethod
    def default(obj):
        if isinstance(obj, pydantic.BaseModel):
            return obj.dict()
        if isinstance(obj, datetime):
            return obj.timestamp()
        raise TypeError(
            f"Object of type '{obj.__class__.__name__}' is not JSON serializable"
        )

    def render(self, data: http.ResponseData) -> bytes:
        return json.dumps(data, default=self.default).encode('utf-8')
