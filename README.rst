apistar-pydantic
################


Better handler parameters for `APIStar <http://github.com/encode/apistar/>`_
(and `pydantic <http://github.com/samuelcolvin/pydantic/>`_ support).


Installation
============

.. code-block:: sh

    $ pip install apistar-params


Usage
=====

.. code-block:: python

    from apistar import Route, Include
    from apistar.handlers import static_urls, docs_urls
    from apistar_pydantic import (
        WSGIApp as App,
        QueryData, BodyData, FormData,
        JSONRenderer
    )
    from pydantic import BaseModel

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

    def resource_query(city: QueryData[City]) -> str:
        return "%s has %d citizens." % (city.name, city.population)

    def resource_body(computer: BodyData[Computer]) -> str:
        return "%s costs R$ %.2f" % (computer.model, computer.price)

    def resource_mixed(city: QueryData[City],
                       computer: BodyData[Computer]) -> ComputerCity:
        return ComputerCity(**city.dict(), **computer.dict())

    #
    # Start the app
    #

    app = App(
        settings={
            'RENDERERS': [JSONRenderer()],
        },
        routes=[
            Route('/resource_query', 'GET', resource_query),
            Route('/resource_body', 'POST', resource_body),
            Route('/resource_mixed', 'POST', resource_mixed),

            Include('/docs', docs_urls),
            Include('/static', static_urls)
        ]
    )

    if __name__ == '__main__':
        app.main()
