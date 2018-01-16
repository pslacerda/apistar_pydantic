# apistar-pydantic


[pydantic] integration for [APIStar]


[pydantic]: https://github.com/samuelcolvin/pydantic/
[APIStar]: https://github.com/encode/apistar/


## Installation

```bash
$ pip install apistar-pydantic
```

## Usage

```python
from typing import Dict
from apistar import Route
from apistar_pydantic import (
    WSGIApp as App,
    QueryParam, BodyData
)
from pydantic import BaseModel


class CityQuery(BaseModel, QueryParam):
    name: str
    population: int


class ComputerBody(BaseModel, BodyData):
    model: str
    price: float

def resource_query(city: CityQuery) -> str:
    return "%s has %d citizens." % (city.name, city.population)

def resource_body(computer: ComputerBody) -> str:
    return "%s costs R$ %.2f" % (computer.model, computer.price)

def resource_mixed(city: CityQuery,
                   computer: ComputerBody) -> Dict[str, BaseModel]:
    return {
        'city': city,
        'computer': computer
    }

app = App(
    routes=[
        Route('/resource_query', 'GET', resource_query),
        Route('/resource_body', 'POST', resource_body),
        Route('/resource_mixed', 'POST', resource_mixed),
    ]
)
```
