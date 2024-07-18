#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import inspect
from typing import Optional, Dict, Sequence, Union, Any, List, Type
from pydantic.fields import FieldInfo
from fastapi.datastructures import Default
from fastapi.encoders import DictIntStrAny, SetIntStr
from fastapi.routing import BaseRoute
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.params import Depends
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from pydantic.schema import model_process_schema, get_model_name_map, get_flat_models_from_fields
from fastapi_jsonapi.exception import serialize_error
from fastapi_jsonapi.responses import JsonapiResponse
from fastapi.openapi.constants import REF_PREFIX

REF_PREFIX_FILTER = '#/filters/schemas/'


def register_jsonapi_exception_handlers(app: FastAPI):
    """
    """
    async def _serialize_error(request: Request, exc: Exception) -> Response:
        return await serialize_error(request=request, exc=exc)

    app.add_exception_handler(Exception, _serialize_error)
    app.add_exception_handler(HTTPException, _serialize_error)
    # app.add_exception_handler(JsonapiException, _serialize_error)
    app.add_exception_handler(RequestValidationError, _serialize_error)


def filter_schema(model):
    ref_prefix = REF_PREFIX_FILTER
    filter_schema = []
    models = get_flat_models_from_fields(
        fields=[
            value for key,
            value in model.__fields__.items()],
        known_models=set())
    name = get_model_name_map(models)
    m_schema, m_definitions, m_nested_models = model_process_schema(
        model, model_name_map=name, ref_prefix=ref_prefix)
    filter_schema.append(m_definitions)
    return m_schema, m_definitions, m_nested_models


class InferInfo:
    """接口信息配置信息"""
    # path: str = ''
    status_code: int = 200
    tags: Optional[List[str]] = None
    dependencies: Optional[Sequence[Depends]] = None
    description: Optional[str] = ''
    response_description: str = "Successful Response"
    responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None
    deprecated: Optional[bool] = None
    operation_id: Optional[str] = None
    response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None
    response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None
    response_model_by_alias: bool = True
    response_model_exclude_unset: bool = True
    response_model_exclude_defaults: bool = False
    response_model_exclude_none: bool = False
    include_in_schema: bool = True
    response_class: Type[Response] = Default(JsonapiResponse)
    name: Optional[str] = None
    callbacks: Optional[List[BaseRoute]] = None

    @classmethod
    def dict(cls):
        return dict((name, getattr(cls, name)) for name in dir(cls)
                    if not name.startswith('__') and name != 'dict')


def update_dict(d1: dict, d2: dict):
    """
    多层嵌套字典更新
    Args:
        d1: 被更新的字典
        d2: 更新的属性和值

    Returns:更新后的字典

    """

    for i in d1:
        if d2.get(i, None) is not None:
            d1[i] = d2[i]
        if isinstance(d1[i], dict):
            update_dict(d1[i], d2)
    return d1


class CustomOpenapi():
    def __init__(self, app):
        self.app = app

    def openapi(self):
        if self.app.openapi_schema:
            return self.app.openapi_schema
        openapi_schema = get_openapi(
            title=self.app.title,
            version=self.app.version,
            openapi_version=self.app.openapi_version,
            description=self.app.description,
            terms_of_service=self.app.terms_of_service,
            contact=self.app.contact,
            license_info=self.app.license_info,
            routes=self.app.routes,
            tags=self.app.openapi_tags,
            servers=self.app.servers,
        )
        openapi_schema["filters"] = dict()
        openapi_schema["filters"]["schemas"] = dict()

        validation_openapi = {'422': {
            "description": "Validation Error",
            "content": {
                "application/vnd.api+json": {
                    "schema": {"$ref": REF_PREFIX + "HTTPValidationError"}
                }
            },
        }}
        update_dict(openapi_schema, validation_openapi)

        self.app.openapi_schema = openapi_schema

        return self.app.openapi_schema


def create_custom_openapi(app, openapi_schema: dict = None):
    if openapi_schema:
        app.openapi_schema = openapi_schema
    else:
        app.openapi = CustomOpenapi(app).openapi


def get_default_args(func):
    """取方法的形参及其默认值"""
    signature = inspect.signature(func)
    args = {}
    for k, v in signature.parameters.items():

        default = v.default
        if isinstance(v.default, Depends):
            continue
        if v and hasattr(v.default, 'alias'):
            k = getattr(v.default, 'alias') if getattr(v.default, 'alias') else k
        if isinstance(default, FieldInfo):
            default = default.default
        if v.default is inspect.Parameter.empty:
            default = None
        args[k] = default
    return args


class SessionMangerBase:
    """数据库链接管理基类"""
    _instance = None

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kw)
        return cls._instance

    def __init__(self):
        pass
    @classmethod
    def get(cls):
        pass
    @classmethod
    def close(cls):
        pass


if __name__ == '__main__':
    a = {'a': {'b': {'c': 2}, 'd': {'c': 3}}}
    update_dict(a, {'c': 's'})
    print(a)
