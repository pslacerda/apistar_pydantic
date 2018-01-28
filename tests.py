import datetime
from typing import List, Dict

import pytest
import coreschema

from apistar import Route
from apistar.test import TestClient
from apistar.handlers import serve_schema
from apistar.interfaces import Schema
from pydantic import BaseModel
from coreapi import Field, Link
from coreapi.codecs import CoreJSONCodec

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

    def query_argument_view(model: QueryData[Model]):
        return model.compute()

    client = client_factory(app_class, [
        Route('/query_argument', 'GET', query_argument_view)
    ])

    res = client.get('/query_argument', params=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_form_model(app_class):
    class FormModel(BaseModel):
        integer: List[int]
        text: List[str]

        def compute(self):
            return {
                'integer': 10 * self.integer[0],
                'text': self.text[0].upper()
            }

    def form_argument_view(model: FormData[FormModel]):
        return model.compute()

    client = client_factory(app_class, [
        Route('/form_argument', 'POST', form_argument_view)
    ])

    res = client.post('/form_argument', data=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_body_model(app_class):

    def body_argument_view(model: BodyData[Model]):
        return model.compute()

    client = client_factory(app_class, [
        Route('/body_argument', 'PUT', body_argument_view)
    ])
    res = client.put('/body_argument', json=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_mixed_arguments(app_class):

    def mixed_arguments_view(query: QueryData[Model],
                             body: BodyData[Model]):
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


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_renderer_datetime(app_class):

    now = datetime.datetime.now()

    def render() -> datetime.datetime:
        return now

    client = client_factory(app_class, [
        Route('/render', 'GET', render)
    ])

    res = client.get('/render')
    assert res.json() == now.timestamp()


@pytest.mark.parametrize('app_class', [ASyncIOApp, WSGIApp])
def test_schema(app_class):

    def add_model(model: BodyData[Model]):
        """
            add_model description
        """
        return model.integer

    def list_models():
        """list_models description"""
        return

    def show_model(id: int):
        """show_model description"""
        return

    def show_model2(id: int):
        """show_model2 description"""
        return

    app = app_class(
        routes=[
            Route('/add_model', 'POST', add_model),
            Route('/list_models', 'GET', list_models),
            Route('/show_model', 'GET', show_model),
            Route('/show/model/{id}', 'GET', show_model2),
            Route('/schema', 'GET', serve_schema),
        ],
        settings={
            'SCHEMA': {'TITLE': 'My API'}
        }
    )
    client = TestClient(app)

    schema = Schema(title='My API', url='/schema/', content={
        'add_model': Link(
            url='/add_model',
            action='POST',
            description='add_model description',
            fields=[
                Field(
                    name='integer',
                    location='form',
                    required=True,
                    schema=coreschema.Integer()
                ),
                Field(
                    name='text',
                    location='form',
                    required=True,
                    schema=coreschema.String()
                )
            ]
        ),
        'list_models': Link(
            url='/list_models',
            action='GET',
            description='list_models description',
            fields=[]
        ),
        'show_model': Link(
            url='/show_model',
            action='GET',
            description='show_model description',
            fields=[
                Field(
                    name='id',
                    location='query',
                    required=True,
                    schema=coreschema.Integer()
                )
            ]
        ),
        'show_model2': Link(
            url='/show/model/{id}',
            action='GET',
            description='show_model2 description',
            fields=[
                Field(
                    name='id',
                    location='path',
                    required=True,
                    schema=coreschema.Integer()
                )
            ]
        )
    })

    res = client.get('/schema')
    assert res.status_code == 200

    codec = CoreJSONCodec()
    document = codec.decode(res.content)

    assert document.url == '/schema'
    assert document.title == schema.title
    for name, link in schema.links.items():
        assert name in document
        assert link.url == document[name].url
        assert link.action == document[name].action
        assert link.description == document[name].description
        for expected, result in zip(sorted(link.fields), sorted(document[name].fields)):
            assert expected.__class__ == result.__class__

