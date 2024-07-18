# -*- coding: utf-8 -*-
from fastapi import FastAPI

from fastapi_jsonapi.util import register_jsonapi_exception_handlers, create_custom_openapi



def create_app():
    app = FastAPI()
    # register exception handlers
    register_jsonapi_exception_handlers(app)

    #自定义openapi
    create_custom_openapi(app)

    #行为日志(中间件实现）
    # behavior_record(app)

    #跨域(中间件)
    # cors(app)

    # register routes
    # from examples.api.manage import manage
    from examples.api.scenes import scene
    # manage.Manage.register_routes(api=app)
    scene.Scenes.register_routes(api=app)


    return app

#------------------main----------------------------
if __name__ == '__main__':
    # 日志配置
    create_app()

