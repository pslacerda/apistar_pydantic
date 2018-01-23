from typing import Dict

from apistar import Route
from apistar_pydantic import (
    WSGIApp as App,
    QueryData, BodyData, FormData
)
from pydantic import BaseModel
from apistar.handlers import (
    serve_schema, serve_static, api_documentation, javascript_schema
)

#
# Declare models
#


class City(BaseModel):
    name: str
    population: int


class Computer(BaseModel):
    model: str
    price: float


#
# Create views
#

def resource_query(city: QueryData[City]) -> str:
    return "%s has %d citizens." % (city.name, city.population)


def resource_body(computer: BodyData[Computer]) -> str:
    return "%s costs R$ %.2f" % (computer.model, computer.price)


def resource_mixed(city: QueryData[City],
                   computer: BodyData[Computer]) -> Dict[str, BaseModel]:
    return {
        'city': city,
        'computer': computer
    }

#
# Start the app
#

app = App(
    routes=[
        Route('/resource_query', 'GET', resource_query),
        Route('/resource_body', 'POST', resource_body),
        Route('/resource_mixed', 'POST', resource_mixed),

        Route('/docs', 'GET', api_documentation),
        Route('/{path}', 'GET', serve_static),
        Route('/schema/', 'GET', serve_schema),
        Route('/schema.js', 'GET', javascript_schema),
    ]
)

app.main()
