#!/usr/bin/env python3
# -*- coding=utf-8 -*-

"""
"""
__version__ = "0.1.1"

from fastapi import FastAPI
from fastapi import Request
from fastapi_jsonapi.exception import JsonapiException, ResourceDuplicate, ResourceNotFound, AuthError, QureyError
from fastapi_jsonapi.schema import SchemaBase as SchemaBase, field_mapping as field_mapping, Relationship as Relationship
from fastapi_jsonapi.resource import BaseResource as BaseResource, UploadFileBaseResource, DownloadFileResource
from fastapi_jsonapi.query import ArgParse, FilterAnd, Filter, FilterOr
from fastapi_jsonapi.auth import Auth