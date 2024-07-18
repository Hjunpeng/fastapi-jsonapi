#!/usr/bin/env python3
# -*- coding=utf-8 -*-

"""
"""

# from lib.api_frame.resource import BaseResource
#
#
# class Api1(BaseResource):
#     type_ = 'api1'
#     version = 1
#
#     async def get(self,
#                   filter: str = Filter(ScenesCar),
#                   page_offset: int = Query(0, alias='page[offset]'),
#                   page_limit: int = Query(100, alias='page[limit]'),
#                   sortby: str = Query('id'),
#                   arg: dict = Depends(ArgParse(ScenesCar)),
#                   db: Session = Depends(Session(sessionScenes)),
#                   *args,
#                   **kwargs):
#         # 1.get数据
#         count = ApiCurd().count_multi(db, **arg)
#         routers = ApiCurd().get_multi(db, **arg)
#         page = JsonapiAdapter.pagination(
#             total=count, limit=page_limit, offset=page_offset)
#         self.register_routes()
#         return response
#
#
#
#
#
#
#
#
#
#
# class Api2(BaseResource):
#     type_ = 'api2'
#     version = 2
#
#
# class Api(BaseResource):
#     type_ = 'api'
#     childs= [Api1, Api2]
#
#
#
# class Cmpt(BaseResource):
#     type_ = 'cmpt'
#
#
#
