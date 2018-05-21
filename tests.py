import pytest

from apistar import App, ASyncApp
from apistar.test import TestClient
from apistar.http import JSONResponse
from pydantic import BaseModel

from apistar_pydantic import (
    PathParam, QueryParam, DictBodyData, DictQueryData,
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
        # settings={
        #     'RENDERERS': [JSONRenderer()]
        # },
        components=components,
        routes=routes
    )
    return TestClient(app)


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_url(app_class):
    def url_argument_view(arg1: PathParam[str]):
        return JSONResponse(arg1.upper())

    client = client_factory(app_class, [
        Route('/url_argument/{arg1}', 'GET', url_argument_view),
    ])
    res = client.get('/url_argument/aaa')
    assert res.json() == 'AAA'


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_query_simple(app_class):
    def query_argument_simple_view(arg1: QueryParam[int]):
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


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_query_model(app_class):

    def query_argument_view(model: DictQueryData[Model]):
        return model.compute()

    client = client_factory(app_class, [
        Route('/query_argument', 'GET', query_argument_view)
    ])

    res = client.get('/query_argument', params=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_body_model(app_class):

    def body_argument_view(model: DictBodyData[Model]):
        return model.compute()

    client = client_factory(app_class, [
        Route('/body_argument', 'PUT', body_argument_view)
    ])
    res = client.put('/body_argument', json=args)
    assert res.json() == expected


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_mixed_arguments(app_class):

    def mixed_arguments_view(query: DictQueryData[Model],
                             body: DictBodyData[Model]):
        return JSONResponse(query.integer * body.integer * query.text)

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


@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_pydantic_model(app_class):

    def mixed_arguments_view(query: PydanticQueryData[PydanticModel],
                             body: PydanticBodyData[PydanticModel]):
        return JSONResponse(query.integer * body.integer * query.text)

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


@pytest.mark.skip
@pytest.mark.parametrize('app_class', [ASyncApp, App])
def test_schema(app_class):

    def add_model(model: DictBodyData[Model]):
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
        ],
        # settings={
        #     'SCHEMA': {'TITLE': 'My API'}
        # }
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
