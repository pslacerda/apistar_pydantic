import inspect
import json
from typing import Any, Callable, Tuple, Optional, Mapping

import pydantic

from apistar import exceptions, http
from apistar.interfaces import Injector
from apistar.components import dependency
from apistar.frameworks.wsgi import WSGIApp
from apistar.frameworks.asyncio import ASyncIOApp
from apistar.renderers import JSONRenderer
from apistar.types import (
    ParamName, KeywordArgs, ParamAnnotation, WSGIEnviron, Handler, UMIChannels,
    UMIMessage
)

__all__ = [
    'ASyncIOApp', 'WSGIApp',
    'JSONRenderer',
    'QueryData', 'FormData', 'BodyData'
]


class HTTPParameterData:
    def __getitem__(self, type_cls):
        return type(type_cls.__name__, (type_cls, self.__class__), {})


class _QueryData(HTTPParameterData):
    pass


class _FormData(HTTPParameterData):
    pass


class _BodyData(HTTPParameterData):
    pass


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


class WSGIApp(WSGIApp):

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

    def render(self, data: http.ResponseData) -> bytes:
        return json.dumps(data, default=self.default).encode('utf-8')
