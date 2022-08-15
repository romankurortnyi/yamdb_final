from rest_framework.routers import SimpleRouter, Route


class CustomPostOnlyRouter(SimpleRouter):

    routes = [
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'post': 'create'
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
    ]
