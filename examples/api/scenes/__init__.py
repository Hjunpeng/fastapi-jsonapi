#!/usr/bin/env python3
# -*- coding=utf-8 -*-

"""
"""
from fastapi_jsonapi.resource import BaseResource

class Pri(BaseResource):
    type_ = 'pri'


class Sec(BaseResource):
    type_ = 'sec'





class Scenes(BaseResource):
    type_ = 'scene'
    childs = [Pri, Sec]