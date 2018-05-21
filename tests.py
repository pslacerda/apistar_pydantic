import pytest

from apistar import App, ASyncApp
from apistar.test import TestClient
from apistar.http import JSONResponse
from apistar.server.handlers import serve_schema
from pydantic import BaseModel

from apistar_pydantic import (
    PathParam, QueryParam, BodyData, DictQueryData,
    PydanticBodyData, PydanticQueryData,
    Route, components,
)


def _compute(self):
    return {
        'integer': 10 * self.integer,
        'text': self.text.upper()
    }


class Model(dict):

    def __init__(self, value):
        try:
            new_value = {}
            new_value['integer'] = int(value['integer'])
            new_value['text'] = str(value['text'])
            super().__init__(new_value)
        except Exception:
            raise Exception("Invalid model")

    def __getattr__(self, key):
        return self[key]

    compute = _compute


class PydanticModel(BaseModel):
    integer: int
    text: str

    compute = _compute


def client_factory(app_class, routes):
    app = app_class(
        components=components,
        routes=routes
    )
    return TestClient(app)


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_url(app_class):
    def handler(arg1: PathParam[str]):
        return JSONResponse(arg1.upper())

    client = client_factory(app_class, [
        Route('/resource/{arg1}', 'GET', handler),
    ])
    res = client.get('/resource/aaa')
    assert res.json() == 'AAA'


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_query_simple(app_class):
    def handler(arg1: QueryParam[int]):
        return arg1 * 10

    client = client_factory(app_class, [
        Route('/resource', 'GET', handler),
    ])
    res = client.get('/resource', params={'arg1': 10})
    assert res.json() == 100


args = {
    'integer': 10,
    'text': 'abc'
}


expected = {
    'integer': 100,
    'text': 'ABC'
}


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_query_model(app_class):

    def handler(model: DictQueryData[Model]):
        return model.compute()

    client = client_factory(app_class, [
        Route('/resource', 'GET', handler, documented=False)
    ])

    res = client.get('/resource', params=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_body_model(app_class):

    def handler(model: BodyData[Model]):
        return model.compute()

    client = client_factory(app_class, [
        Route('/resource', 'PUT', handler)
    ])
    res = client.put('/resource', json=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_mixed_arguments(app_class):

    def handler(query: DictQueryData[Model],
                body: BodyData[Model]):
        return JSONResponse(query.integer * body.integer * query.text)

    client = client_factory(app_class, [
        Route('/resource', 'POST', handler, documented=False)
    ])

    res = client.post(
        '/resource',
        params={
            'integer': 2,
            'text': 'a'
        },
        json={
            'integer': 2,
            'text': ''
        })
    assert res.json() == 'aaaa'


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_pydantic_model(app_class):

    def handler(query: PydanticQueryData[PydanticModel],
                body: PydanticBodyData[PydanticModel]):
        return JSONResponse(query.integer * body.integer * query.text)

    client = client_factory(app_class, [
        Route('/resource', 'POST', handler, documented=False)
    ])

    res = client.post(
        '/resource',
        params={
            'integer': 2,
            'text': 'a'
        },
        json={
            'integer': 2,
            'text': ''
        })
    assert res.json() == 'aaaa'


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_schema(app_class):

    def add_model(model: BodyData[Model]):
        """add_model description"""
        return model.integer

    def list_models():
        """list_models description"""
        return

    def show_model(id: int):
        """show_model description"""
        return

    def show_model2(id: PathParam[int], name: QueryParam[str]):
        """show_model2 description"""
        return

    app = app_class(
        routes=[
            Route('/add_model', 'POST', add_model),
            Route('/list_models', 'GET', list_models),
            Route('/show_model', 'GET', show_model),
            Route('/show/model/{id}', 'GET', show_model2),
            Route('/schema/', 'GET', handler=serve_schema, documented=False),
        ],
        # settings={
        #     'SCHEMA': {'TITLE': 'My API'}
        # }
    )
    client = TestClient(app)
    res = client.get('/schema')
    assert res.status_code == 200
    assert res.json() == {
        'openapi': '3.0.0',
        'info': {
            'title': '',
            'description': '',
            'version': ''
        },
        'paths': {
            '/add_model': {
                'post': {
                    'description': 'add_model description',
                    'operationId': 'add_model',
                    'requestBody': {
                        'content': {
                            'application/json': {
                                'schema': {'type': 'object'}
                            }
                        }
                    }
                }
            },
            '/list_models': {
                'get': {
                    'description': 'list_models description',
                    'operationId': 'list_models'
                }
            },
            '/show_model': {
                'get': {
                    'description': 'show_model description',
                    'operationId': 'show_model',
                    'parameters': [
                        {
                            'name': 'id',
                            'in': 'query',
                            'schema': {'type': 'integer'}
                        }
                    ]
                }
            },
            '/show/model/{id}': {
                'get': {
                    'description': 'show_model2 description',
                    'operationId': 'show_model2',
                    'parameters': [
                        {
                            'name': 'id',
                            'in': 'path',
                            'required': True,
                            'schema': {'type': 'integer'}
                        },
                        {
                            'name': 'name',
                            'in': 'query',
                            'schema': {'type': 'string'}
                        }
                    ]
                }
            }
        }
    }