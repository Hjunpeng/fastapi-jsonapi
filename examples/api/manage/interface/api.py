#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""接口管理接口
api_get() get接口
api_post() 原子操作
"""
from fastapi_jsonapi import BaseResource



class Api2(BaseResource):
    model = None
    link = 'api'
    version = 2

    def get(self):
        pass


class Api1(BaseResource):
    model = None
    link = 'api'
    version = 1
    versions = {2: Api2}
    relation = ''

    def get(self):
        pass


class Api(BaseResource):
    link = 'api'
    default_version = Api1



if __name__ == '__main__':
    print(Api1.__name__)

