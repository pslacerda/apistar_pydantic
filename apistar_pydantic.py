import inspect
import json
from typing import Any, Callable, Tuple, Optional

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


class QueryData:
    pass


class FormData:
    pass


class BodyData:
    pass


class PydanticHTTPResolver(dependency.HTTPResolver):
    """
    Handles resolving parameters for HTTP requests with pydantic.
    """

    @staticmethod
    def coerce(type_cls, value):
        if value is None or isinstance(value, type_cls):
            return value
        return type_cls(value)

    @staticmethod
    def coerce_model(model_cls, data):
        try:
            return model_cls(**data)
        except pydantic.ValidationError as exc:
            raise exceptions.ValidationError(
                detail=exc.errors_dict
            )

    def resolve(self,
                param: inspect.Parameter,
                func: Callable) -> Optional[Tuple[str, Callable]]:
        annotation = param.annotation
        key = '%s:%s' % (annotation.__name__.lower(), param.name)

        if annotation is inspect.Parameter.empty:
            key = 'empty:' + param.name
            return key, self.empty

        elif issubclass(annotation, (str, int, float, bool, QueryData)):
            return key, self.url_or_query_argument

        elif issubclass(annotation, (dict, list, BodyData)):
            return key, self.body_argument

        elif issubclass(annotation, FormData):
            return key, self.form_argument

        else:
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
        if issubclass(coerce, pydantic.BaseModel):
            return self.coerce_model(coerce, dict(query_params))
        else:
            return self.coerce(coerce, query_params.get(name))

    def form_argument(self,
                      data: http.RequestData,
                      name: ParamName,
                      coerce: ParamAnnotation) -> Any:
        if not isinstance(data, dict):
            raise exceptions.ValidationError(
                detail='Request data must be an object.'
            )
        return self.coerce_model(coerce, data)

    def body_argument(self,
                      data: http.RequestData,
                      coerce: ParamAnnotation) -> Any:
        if isinstance(data, dict):
            return self.coerce_model(coerce, data)
        else:
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
