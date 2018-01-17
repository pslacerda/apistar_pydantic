from typing import List, Dict

import pytest

from apistar import Route
from apistar.test import TestClient
from pydantic import BaseModel
from apistar_pydantic import (
    ASyncIOApp, WSGIApp, QueryData, FormData, BodyData,
    JSONRenderer
)


class Model(BaseModel):
    integer: int
    text: str

    def compute(self):
        return {
            'integer': 10 * self.integer,
            'text': self.text.upper()
        }


def client_factory(app_class, routes):
    app = app_class(
        settings={
            'RENDERERS': [JSONRenderer()]
        },
        routes=routes
    )
    return TestClient(app)


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_url(app_class):
    def url_argument_view(arg1: str):
        return arg1.upper()

    client = client_factory(app_class, [
        Route('/url_argument/{arg1}', 'GET', url_argument_view),
    ])
    res = client.get('/url_argument/aaa')
    assert res.json() == 'AAA'


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_query_simple(app_class):
    def query_argument_simple_view(arg1: int):
        return arg1 * 10

    client = client_factory(app_class, [
        Route('/query_argument_simple', 'GET', query_argument_simple_view),
    ])
    res = client.get('/query_argument_simple', params={'arg1': 10})
    assert res.json() == 100


args = {
    'integer': 10,
    'text': 'abc'
}
expected = {
    'integer': 100,
    'text': 'ABC'
}


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_query_model(app_class):
    class QueryModel(Model, QueryData):
        pass

    def query_argument_view(model: QueryModel):
        return model.compute()

    client = client_factory(app_class, [
        Route('/query_argument', 'GET', query_argument_view)
    ])

    res = client.get('/query_argument', params=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_form_model(app_class):
    class FormModel(BaseModel, FormData):
        integer: List[int]
        text: List[str]

        def compute(self):
            return {
                'integer': 10 * self.integer[0],
                'text': self.text[0].upper()
            }

    def form_argument_view(model: FormModel):
        return model.compute()

    client = client_factory(app_class, [
        Route('/form_argument', 'POST', form_argument_view)
    ])

    res = client.post('/form_argument', data=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_body_model(app_class):

    class BodyModel(Model, BodyData):
        pass

    def body_argument_view(model: BodyModel):
        return model.compute()

    client = client_factory(app_class, [
        Route('/body_argument', 'PUT', body_argument_view)
    ])
    res = client.put('/body_argument', json=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_mixed_arguments(app_class):
    class QueryModel(Model, QueryData):
        pass

    class BodyModel(Model, BodyData):
        pass

    def mixed_arguments_view(query: QueryModel, body: BodyModel):
        return query.integer * body.integer * query.text

    client = client_factory(app_class, [
        Route('/mixed_arguments', 'POST', mixed_arguments_view)
    ])

    res = client.post(
        '/mixed_arguments',
        params={
            'integer': 2,
            'text': 'a'
        },
        json={
            'integer': 2,
            'text': ''
        })
    assert res.json() == 'aaaa'


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_renderer(app_class):

    def render() -> Model:
        return Model(
            integer=100,
            text='ABC'
        )
    client = client_factory(app_class, [
        Route('/render', 'GET', render)
    ])

    res = client.get('/render')
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_renderer_mixed(app_class):

    def render() -> Dict[str, List[Model]]:
        return {
            'model': [Model(integer=100, text='ABC')]
        }

    client = client_factory(app_class, [
        Route('/render', 'GET', render)
    ])

    res = client.get('/render')
    assert res.json() == {
        'model': [expected]
    }
