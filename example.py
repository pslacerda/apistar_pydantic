from apistar import App
from pydantic import BaseModel
from apistar_pydantic import (
    QueryParam, PathParam, DictBodyData, DictQueryData,
    PydanticBodyData as BodyData,
    PydanticQueryData as QueryData,
    Route, components,
)


#
# Declare models
#

class City(BaseModel):
    """City info"""
    name: str
    population: int

class Computer(BaseModel):
    """Computer info"""
    model: str
    price: float

class ComputerCity(City, Computer):
    """A computer in a city"""


#
# Create views
#

def resource_complete(param1: QueryParam[str],
                      param2: QueryParam[int],
                      param3: DictBodyData[dict],
                      param4: DictQueryData[dict]):
    return repr(locals())

def resource_query(city: QueryData[City]):
    return "%s has %d citizens." % (city.name, city.population)

def resource_body(computer: BodyData[Computer]):
    return "%s costs R$ %.2f" % (computer.model, computer.price)

def resource_mixed(city: QueryData[City],
                   computer: BodyData[Computer]):
    return ComputerCity(**city.dict(), **computer.dict())


#
# Start the app
#

app = App(
    routes=[
        Route('/resource', 'GET', resource_query),
        Route('/resource_query', 'GET', resource_query),
        Route('/resource_body', 'POST', resource_body),
        Route('/resource_mixed', 'POST', resource_mixed),
    ],
    components=[
        *components
    ]
)

if __name__ == '__main__':
    app.serve('127.0.0.1', 3000, debug=True)
