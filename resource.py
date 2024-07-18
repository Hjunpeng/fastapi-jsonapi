#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import create_model
from treelib import Tree
from fastapi import FastAPI, APIRouter, Query, Request, Path, Body
from fastapi_jsonapi.meta import RegisteredResourceMeta, registered_resources
from fastapi_jsonapi.exception import HTTPException, serialize_error, ResourceNotFound
from fastapi_jsonapi.schema import SchemaBase, Relationship, CreatModel
from fastapi_jsonapi.jsonapi import JsonApiModel, RelationshipModel, JsonapiAdapter
from fastapi_jsonapi.responses import JsonapiResponse
from fastapi_jsonapi.filter import create_filter_model
from fastapi_jsonapi.query import ArgParse, ArgsModel
from fastapi_jsonapi.util import InferInfo, SessionMangerBase
from fastapi_jsonapi.auth import User, SecurityConfig
import traceback


class _BaseApiHandler:
    # 支持的接口方法。
    methods = {'GET', 'GETS', 'PATCH', 'POST', 'DELETE', 'ATOMIC'}
    relapi = True
    versions = {}  # 全部版本
    version = 1  # 当前版本
    required = []
    allow_all_pages = False

    def __init__(
            self,
            request: Request,
            request_context: dict = None,
            extract_params: Any = None,
            *args,
            **kwargs) -> None:
        self.request = request
        self.request_body = request_context.pop(
            'request_body') if request_context and 'request_body' in request_context else None
        self.request_context: dict = request_context
        self.extract_params = extract_params

    @classmethod
    async def handle_error(cls, request: Request, exc: BaseException) -> JsonapiResponse:
        """
        错误处理
        非http错误，非预期，打印详细日志
        Args:
            request: 请求
            exc: 错误

        Returns: jsonapi 格式的错误

        """
        if request.headers.get('X-Real-IP'):
            cilent_ip = request.headers.get('X-Real-IP')
        else:
            cilent_ip = request.client.host

        if hasattr(request, '_json'):  # delete 主资源没有body
            body = request._json  # 其他有request body

        if hasattr(request, '_form'):
            for item, value in request._form.multi_items():
                if item == 'data':
                    body = json.loads(value)
        log_msg = {
            "RequestMethod": request.method,
            "ResponseStatueCode": exc.status_code if hasattr(exc, 'status_code') else 500,
            "url": str(request.url),
            "UserAgent": request.headers.get('user-agent'),
            "IP": cilent_ip,
            # "X-Process-Time(s)": process_time,
            "Token": request.headers.get('authorization'),
            "RequestBody":body,
            # "exc":  traceback.format_exc()
        }

        # if not isinstance(exc, HTTPException):
        logging.error(log_msg, exc_info=exc)
        return serialize_error(exc=exc)

    @classmethod
    async def handle_response(cls, response, response_model=None) -> JsonapiResponse:
        """
        格式转换，响应模型验证
        Args:
            response: 模型数据
            response_model: 模型

        Returns: 符合jsonapi 模型的数据

        """
        if response_model:
            return response_model(**response.dict()).dict()
        else:
            return response

    @classmethod
    async def _version(cls, request) -> int:
        # TODO
        return None

    @classmethod
    async def _get_version(cls, request) -> Type['BaseResource']:
        request_version = await cls._version(request)  # 判断请求版本：
        if request_version != None:
            if request_version == cls.version:
                request_resource = cls
            else:
                request_resource = cls.versions.get(request_version)  # 当前版本资源类
        else:
            request_resource = cls
        return request_resource

    @classmethod
    async def _prase_args(cls, request: Request):
        if request:
            args = await ArgParse(cls).get_args(request)

        else:
            args = ArgsModel()
        return args

    @classmethod
    async def handle_request(
            cls,
            handler_response: str,
            handler_data: str,
            response_model: JsonapiResponse = None,
            request: Request = None,
            extract_params: dict = None,
            request_context: dict = None,
            query_args: ArgsModel = None,
            *args,
            **kwargs):
        # 接口方法前
        request_context = request_context or {}
        request_context.update(request_context)

        extract_params = extract_params or {}
        try:
            await cls.before_request(request=request, extract_params=extract_params)
        except BaseException as before_request_exc:
            response: JsonapiResponse = await cls.handle_error(request, exc=before_request_exc)
        else:
            try:
                # 选择版本
                request_resource = await cls._get_version(request)

                # 接口方法运行
                # if request and request.method not in cls.methods and not (
                #         request.method == 'GET' and 'GETS' in cls.methods):
                #     raise JsonapiException(status_code=405, title='接口没有%s访问方法' % request.method)

                if query_args:
                    query_args = query_args
                else:
                    query_args = await cls._prase_args(request=request)
                resource = request_resource(
                    request=request,
                    request_context=request_context,
                    extract_params=extract_params,
                    query_args=query_args,
                    *args,
                    **kwargs)

                data_func = getattr(resource, handler_data)
                # data = await data_func(*args, **kwargs)  # 获取数据
                data = await resource.connect_data(func=data_func, *args, **kwargs)
                handle_res = getattr(resource, handler_response)  # 转换jsonapi 的方法
                response = await handle_res(data)  # json:api 通过fastapi的response_model转换成response json
                # response = await cls.handle_response(response, response_model)
                del resource
                del data

            except BaseException as e:
                response: JsonapiResponse = await cls.handle_error(request, exc=e)
        finally:
            # 运行接口方法后处理
            try:
                await cls.after_request(request=request, extract_params=extract_params)
            except BaseException as after_request_exc:
                response: JsonapiResponse = await cls.handle_error(request, exc=after_request_exc)


        # gc.collect()
        return response

    @classmethod
    async def before_request(cls, request: Request = None, extract_params: dict = None):
        for res in cls.required:
            await res.before_request(request, extract_params)

    @classmethod
    async def after_request(cls, request: Request = None, extract_params: dict = None):
        for res in cls.required:
            await res.after_request(request, extract_params)


class BaseResource(_BaseApiHandler, metaclass=RegisteredResourceMeta):
    # 数据模型
    model: Type[SchemaBase] = None  # 作为接口时有model, 只挂载路由时model = None

    # 用于控制元类注册的开关。能够通过名称引用其他资源，
    # 默认情况下，注册子类。
    register_resource = True

    # 子路由
    childs = []

    # 默认版本。
    default_version = None

    session: SessionMangerBase = None

    # 关系
    class RelResources:
        pass

    class Meta:
        """标明资源类型和链接"""
        type_: str
        link: str

    # 分页offset
    offset = 0
    limit = 100

    # 排序
    sortby = 'id'

    # 查询参数
    args: ArgsModel()

    # 权限对象
    Auth: SecurityConfig = None

    # 资源关系对象
    # relres = None

    # 响应模型
    schema_model = None  # schema model实例化
    _relationships_model = {}  # _api中生成
    _response_models = {}

    class GetInfo(InferInfo):
        """get接口其他信息配置"""
        summary = 'get单个资源'

    class GetManyInfo(InferInfo):
        """get接口其他信息配置"""
        summary = 'get资源列表'
        # include_in_schema = False
        # response_model_exclude_unset = True

    class AtomicInfo(InferInfo):
        """post接口其他信息配置"""
        summary = '原子操作'
        path = '/atomic'

    class PostInfo(InferInfo):
        summary = '新增数据'

    class PatchInfo(InferInfo):

        summary = '更新数据'

    class DeleteInfo(InferInfo):

        summary = '删除数据'

    class RelGetInfo(InferInfo):
        summary = '获取关系数据'

    class RelPostInfo(InferInfo):
        summary = '新增关系数据'

    class RelPatchInfo(InferInfo):
        summary = '更新关系数据'

    class RelDelInfo(InferInfo):
        summary = '删除关系数据'

    class RelatedGetInfo(InferInfo):
        summary = '获取关系资源'

    def __init__(
            self,
            request=None,
            request_context: dict = None,
            extract_params: dict = None,
            host: str = None,
            query_args: ArgsModel = None,
            *args,
            **kwargs):
        super(
            BaseResource,
            self).__init__(
            request_context=request_context,
            request=request,
            extract_params=extract_params,
            *args,
            **kwargs)
        self.db = None
        # 查询参数
        if query_args:
            self.args = query_args
        else:
            self.args = ArgsModel()
        self._add_args()  # 额外参数
        # host
        if host:
            self.host = host
        else:
            self.host = self.get_host()

    def get_host(self):
        if self.request:
            if os.name == 'nt':
                host = self.request.base_url._url
            else:
                if self.request.headers.get('X-Forwarded-Proto'):
                    host = self.request.headers.get('X-Forwarded-Proto') + "://" + self.request.url.hostname + '/'
                else:
                    host = self.request.base_url._url.replace('http', 'https')
            return host

    def _add_args(self):
        # 额外的请求参数
        if self.request_context:
            for item, value in self.request_context.items():
                self.args.add_filter_to_and(field=item, op='eq', value=value)
        return self.args

    def get_args(self):
        """获取查询参数"""
        return self.args

    def get_path(self):
        """当前资源的根路径"""
        return self.Meta.link

    def request_path_url(self):
        """请求path"""
        path_url = self.request.scope.get('path')
        return path_url

    def rel_request_method(self) -> tuple:
        """
        关系数据请求方法
        Returns: 关系，对应方法
        """
        path_url = self.request_path_url()
        if 'relationships' in path_url:  # 关系的增删改
            rel_name = path_url.split('/')[-1]
            return (rel_name, self.request.method)
        else:
            return (None, None)

    @property
    def method(self):
        """请求方法"""
        return self.request.method

    @classmethod
    def router(cls, **kwargs) -> APIRouter:
        """接口路由"""
        prefix = cls.Meta.link if cls.Meta.link else ''
        cls.route = APIRouter(prefix=prefix, **kwargs)
        # return APIRouter(prefix=prefix, **kwargs)
        return cls.route

    @classmethod
    def filter_model(cls):
        """生成过滤模型"""
        filter_model_name = cls.__name__ + 'Filter'
        models = cls.rel_resources()
        fields = {}
        fields.update(cls.model.filter_fields())
        for rel_name, rel in models.items():
            if not rel.mapping_field:
                continue
            # 2022-09-02需求确认：由于权限和反爬控制， 接口的关系过滤只支持.id的格式，不支持关系的其它属性过滤
            # fields[rel_name + '.' + 'id'] = cls.model.__fields__.get(rel.mapping_field)
            fields[rel_name + '.' + 'id'] = cls.model.__annotations__.get(rel.mapping_field)
            # for name, value in rel_resource.model.__fields__.items():
            #     # 关系的属性用关系type.字段表示，如：user.id
            #
            #     # 关系的类型是关系模型中对应字段的类型
            #     # print(4444,rel_name + '.' + name, cls.model.__fields__.get(rel.mapping_field), value)
            #     value = cls.model.__fields__.get(rel.mapping_field)
            #     fields[rel_name + '.' + name] = value
        return create_filter_model(
            model_name=filter_model_name,
            fields=fields)

    async def connect_data(self, func, *args, **kwargs):
        """取数"""
        try:
            # session 等于 None  无需在数据库取数
            if self.session:
                self.db = self.session.get()
            data = await func(*args, **kwargs)
            return data
        finally:
            if self.session:
                self.session.close()

    async def get_many(self, *args, **kwargs) -> List['model']:
        # 资源集合数据
        pass

    async def get(self, *args, **kwargs) -> model:
        # 单个资源数据
        pass

    async def post(self, *args, **kwargs) -> model:
        # 新增数据
        pass

    async def patch(self, *args, **kwargs) -> model:
        # 更新数据
        pass

    async def delete(self, *args, **kwargs) -> model:
        # 删除
        pass

    async def rel_post(self, *args, **kwargs) -> SchemaBase:
        # 新增关系
        pass

    async def rel_patch(self, *args, **kwargs) -> SchemaBase:
        # 更新关系
        pass

    async def rel_delete(self, *args, **kwargs) -> SchemaBase:
        # 删除关系
        pass

    async def count(self, *args, **kwargs) -> int:
        # 总条数
        pass

    @classmethod
    def use_get(cls, response_model):
        """get操作"""

        async def wrapper(
                request: Request = None,
                id: Any = Path(..., ),
                include: str = Query(None),
                _data: str = Query(None)

        ):
            response = await cls.handle_request(handler_data='get_many',
                                                response_model=response_model,
                                                handler_response='handler_single_data',
                                                request=request,
                                                request_context={'id': id}
                                                )
            return response

        return wrapper

    @classmethod
    def use_get_many(cls, response_model):
        """get"""
        # cls.filter_model = cls.filter_model()
        # m_schema, m_definitions, m_nested_models = filter_schema(cls.filter_model)
        # filter = Query(None, properties=m_schema, filter=m_definitions)
        filter = Query(None)
        limit = Query(cls.limit, alias='page[limit]')
        offset = Query(cls.offset, alias='page[offset]')
        sortby = Query(cls.sortby)

        async def wrapper(
                request: Request = None,
                filter: List[str] = filter,
                page_offset: int = offset,
                page_limit: Union[int, str] = limit,
                sort: str = sortby,
                fields: str = Query(None),
                include: str = Query(None),
                _data: str = Query(None)

        ):
            response = await cls.handle_request(handler_data='get_many',
                                                response_model=response_model,
                                                handler_response='handler_many_data',
                                                request=request)
            return response

        return wrapper

    @classmethod
    def use_post(cls, response_model):
        """新增数据 post操作"""

        requset_model = cls.schema_model.create_post_model()

        async def wrapper(
                request: Request = None,
                request_body: requset_model = Body(..., media_type='application/vnd.api+json'),
                include: str = Query(None),
        ):
            request_context = {'request_body': request_body}
            response = await cls.handle_request(handler_data='post',
                                                handler_response='handler_single_data',
                                                request=request,
                                                response_model=response_model,
                                                request_context=request_context)
            return response

        return wrapper

    @classmethod
    def use_patch(cls, response_model):
        """更新数据 patch操作"""
        requset_model = cls.schema_model.create_patch_model()

        async def wrapper(
                request: Request = None,
                request_body: requset_model = Body(..., media_type='application/vnd.api+json'),
                id: Any = Path(..., ),
                include: str = Query(None),
        ):
            request_context = {'request_body': request_body}
            response = await cls.handle_request(handler_data='patch',
                                                handler_response='handler_single_data',
                                                response_model=response_model,
                                                request=request,
                                                request_context=request_context)
            return response

        return wrapper

    @classmethod
    def use_delete(cls):
        """删除数据 delete操作"""

        async def wrapper(
                request: Request = None,
                id: Any = Path(..., ),
        ):
            response = await cls.handle_request(handler_data='delete',
                                                handler_response='handler_single_onlyid',
                                                request=request)
            return response

        return wrapper

    @classmethod
    def use_atomic_post(cls):
        """原子操作"""
        requset_model = cls.schema_model.create_atomic_operation_model()

        async def wrapper(
                request: Request = None,
                request_body: requset_model = Body(..., media_type='application/vnd.api+json')
        ):
            pass
            # return await cls(request).post(request_body=request_body)
            return

        return wrapper

    @classmethod
    async def related_cond(
            cls,
            host,
            rel_name,
            rel_class,
            id,
            request: Request = None,
    ):
        """
        默认取related数据的条件，默认取relationships数据的id.特殊实例重写此方法
        :param rel_class:
        :param id:
        :return:
        """

        obj = cls(request_context={'id': id}, extract_params={'related': True}, host=host)
        mdata = await obj.connect_data(func=obj.get_many)
        if not mdata:
            raise ResourceNotFound
        if rel_class.mapping_field:  # mapping_field中取条件
            ids = mdata[0].__getattribute__(rel_class.mapping_field)
            if ids is None:
                return None
            else:
                request_context = {'request_context': {'id': ids}}
                return request_context
        else:
            cond_func = getattr(cls(), rel_class.cond_fun)
            cond = cond_func(datas=mdata)
            return cond

    @classmethod
    def use_related(cls, rel_name, rel_class, response_model):
        """"""
        limit = Query(cls.limit, alias='page[limit]')
        offset = Query(cls.offset, alias='page[offset]')
        filter = Query(None)
        sortby = Query(cls.sortby)

        async def wrapper(
                request: Request = None,
                id: Any = Path(..., ),
                filter: List[str] = filter,
                include: str = Query(None),
                _data: str = Query(None),
                sort: str = sortby,
                page_offset: int = offset,
                page_limit: Union[int, str] = limit,
        ):
            rel_resource = registered_resources.get(rel_class.rel_resource)
            host = request.base_url._url
            cond = await cls.related_cond(request=request, rel_name=rel_name, rel_class=rel_class, id=id, host=host)

            if not cond:
                datas = None if rel_class.one_to_one else []
                return await rel_resource()._jsonapi(datas=datas)
            else:
                if rel_class.one_to_one:
                    handler_response_method = 'handler_single_data'
                else:
                    handler_response_method = 'handler_many_data'
                if isinstance(cond, dict):
                    response = await rel_resource.handle_request(handler_data='get_many',
                                                                 response_model=response_model,
                                                                 handler_response=handler_response_method,
                                                                 request=request,
                                                                 **cond)
                else:
                    response = await rel_resource.handle_request(handler_data='get_many',
                                                                 response_model=response_model,
                                                                 handler_response=handler_response_method,
                                                                 request=request,
                                                                 query_args=cond)

                return response

        return wrapper

    @classmethod
    def use_relationships(cls, rel_name, rel, response_model):
        async def wrapper(
                request: Request = None,
                id: Any = Path(..., )
        ):
            response = await cls.handle_request(handler_response='handler_relationships',
                                                handler_data='get_many',
                                                response_model=response_model,
                                                request=request,
                                                extract_params={'rel_name': rel_name,
                                                                'rel': rel},
                                                request_context={'id': id}
                                                )
            return response

        return wrapper

    @classmethod
    def use_relationships_post(cls, rel, response_model):
        """关系数据post"""
        request_model = cls._relationships_model.get(rel)[0]

        async def wrapper(
                request: Request = None,
                id: Any = Path(..., ),
                request_body: request_model = Body(..., media_type='application/vnd.api+json'),
                include: str = Query(None),
        ):
            request_context = {'request_body': request_body}
            response = await cls.handle_request(handler_data='patch',
                                                handler_response='handler_single_data',
                                                response_model=response_model,
                                                request=request,
                                                request_context=request_context)
            return response

        return wrapper

    @classmethod
    def use_relationships_patch(cls, rel, response_model):
        """关系数据update"""
        request_model = cls._relationships_model.get(rel)[0]

        async def wrapper(
                request: Request = None,
                id: Any = Path(..., ),
                request_body: request_model = Body(..., media_type='application/vnd.api+json'),
                include: str = Query(None),
        ):
            request_context = {'request_body': request_body}
            response = await cls.handle_request(handler_data='patch',
                                                handler_response='handler_single_data',
                                                response_model=response_model,
                                                request=request,
                                                request_context=request_context)
            return response

        return wrapper

    @classmethod
    def use_relationships_delete(cls, rel, response_model):
        """关系数据delete"""
        request_model = cls._relationships_model.get(rel)[0]

        async def wrapper(
                request: Request = None,
                id: Any = Path(..., ),
                request_body: request_model = Body(..., media_type='application/vnd.api+json'),
                include: str = Query(None),
        ):
            request_context = {'request_body': request_body}
            response = await cls.handle_request(handler_data='patch',
                                                handler_response='handler_single_data',
                                                response_model=response_model,
                                                request=request,
                                                request_context=request_context)
            return response

        return wrapper

    async def sort(self, data: List[SchemaBase]) -> List[SchemaBase]:

        if not self.args.relsort:  # 无需排序
            return data

        #  TODO 关系排序
        # for sort in self.args.relsort:
        #     print(sort.field, sort.asc)
        #     if '.' in sort.field:
        #         relname, relfield = sort.field.split('.')

        return data

    async def handler_many_data(self, data: List[SchemaBase]) -> JsonApiModel:
        """
        资源列表jsonapi生成
        Args:
            data: 数据列表
        Returns:

        """

        data = await self.sort(data)

        count = await self.connect_data(func=self.count)
        response = await self._jsonapi(data, self.rel_resources(), pages=count)
        return response

    async def handler_single_data(self, data: Union[List[SchemaBase], SchemaBase]) -> JsonApiModel:
        """
        单个资源jsonapi生成
        Args:
            data: 主资源id为某个值时，得到的数据，应为一条数据
        Returns:

        """
        if not data:
            raise ResourceNotFound
        if isinstance(data, list):
            if len(data) > 1:
                raise Exception("错误数据：%s, 应为单条数据" % data)
            data = data[0]  # 只有一条数据
        response = await self._jsonapi(data, self.rel_resources(), pages=1)
        return response

    async def handler_single_no_include(self, data: SchemaBase) -> JsonApiModel:
        """
        单个资源jsonapi生成
        Args:
            data: 主资源id为某个值时，得到的数据，应为单条
        Returns:

        """
        response = await self._jsonapi(datas=data, rels=self.rel_resources())
        return response

    async def handler_single_onlyid(self, data: SchemaBase) -> JsonApiModel:
        """
        单个资源jsonapi生成
        Args:
            data: 主资源id为某个值时，得到的数据，应为单条
        Returns:

        """
        response = await self._jsonapi(datas=data, onlyid=True)

        return response

    async def handler_relationships(self, data: List[SchemaBase]) -> RelationshipModel:
        """
        生成关系数据， 对应接口  /articles/1/relationships/author
        Args:
            data: 主资源id为某个值时，得到的数据，应为单条

        Returns: 关系数据，
        """
        if not data:
            raise ResourceNotFound
        if len(data) > 1:
            raise Exception("错误数据：%s, 应为单条数据" % data)
        response = await self.single_serialize_related(
            data=data[0],
            rel=self.extract_params.get('rel'),
            rel_name=self.extract_params.get('rel_name'),
            include=[self.extract_params.get('rel_name')],
            q_data=[self.extract_params.get('rel_name')])
        return response

    @classmethod
    def rel_resources(cls) -> Dict[str, Relationship]:
        """
        关系资源
        Args:
        Returns: 关系资源字典{"关系名"：Relationship对象}

        """
        rel_resources = {}
        for item, rel in cls.RelResources.__dict__.items():
            if isinstance(rel, Relationship):
                rel_resources[item] = rel
        return rel_resources

    def _parse_relationships(self, rel_data):
        """
        解析relationship
        Args:
            rel_data: relationship data
        Returns: 关系数据ids

        """
        if rel_data and isinstance(rel_data, list):
            rel_ids = [data.get('id') for data in rel_data]
        elif rel_data and isinstance(rel_data, dict):
            rel_ids = rel_data.get('id')
        else:
            rel_ids = rel_data
        return rel_ids

    def generate_model_by_data(self, data, rel:bool=False):
        """
        根据具体数据生成对应模型，清除掉无用的字段。用来区分前端需要修改的数据有哪些，
        若在更新删除时，前端数据中没有提供此字段，说明不更改。
        Args:
            model_data: 数据
        Returns: 返回一个只包含data中的字段的write模型

        """
        if rel:
            model = create_model(__model_name='temp_model', __base__=SchemaBase)
            model.add_fields(**data)
            return model
        else:
            model = create_model(__model_name='temp_model', __base__=self.model)
            model_fields = model.__fields__.copy()
            for field, item in model_fields.items():
                if item.field_info.onlyread:
                    model.__fields__.pop(field)
                elif self.request.method != 'POST' and field not in data:
                    model.__fields__.pop(field)
        return model

    def parse_jsonapi_body(self, data):
        """
        解析jsonapi格式的requestbody
        Args:
            data:
            model_data: 要添加的参数

        Returns:

        """
        model_data = defaultdict()
        model_data['id'] = data.get('id')
        model_data.update(data.get('attributes', {}))
        relationships = data.get('relationships')

        if relationships:
            for field, data in relationships.items():
                rel_data = data.get('data')
                rel_ids = self._parse_relationships(rel_data=rel_data)
                if self.RelResources().__getattribute__(field).modify:  # 在主资源中可以修改
                    model_data.update(
                        {self.RelResources().__getattribute__(field).mapping_field: rel_ids})
        model = self.generate_model_by_data(model_data)
        print(22222222, model_data)
        deserialized_body = model(**model_data)
        return deserialized_body

    def parse_body(self) -> 'model':
        """
        解析request body，将前端需要增删改的数据转成模型数据返给业务层
        patch, post，delete中调用
        Returns: model模型数据

        """
        model_data = defaultdict()

        if self.request.path_params:
            model_data['id'] = self.request.path_params.get('id')
        if not hasattr(self.request, '_json'):  # delete 主资源没有body
            model = self.generate_model_by_data(model_data)
            return model(**model_data)
        else:
            body = self.request._json  # 其他有request body
            data = body.get('data')
            path_url = self.request.scope.get('path')

        if 'relationships' in path_url:  # 关系的增删改
            rel_name = path_url.split('/')[-1]
            rel_ids = self._parse_relationships(rel_data=data)
            model_data[self.RelResources().__getattribute__(
                rel_name).mapping_field] = rel_ids
            model = self.generate_model_by_data(model_data, rel=True)
            deserialized_body = model(**model_data)
        else:  # 主资源新增更改
            deserialized_body = self.parse_jsonapi_body(data)
        return deserialized_body

    def identifier_meta(self, rel, rel_name, data, relid) -> dict:
        """
        资源标识符的 meta 信息
        :param rel: 关系
        :param rel_name:关系名称
        :param data: 数据
        :param relid: 当前关系id
        :return: meta,范式：{'relationships':{'pubscene':{'total':2}}}
        """
        pass

    async def serialize_identifier(self, data, rel_name, rel):
        rel_resource = registered_resources.get(rel.rel_resource)
        rel_type = rel_resource.Meta.type_
        # 有无data,根据mapping_field判断
        if rel.mapping_field and rel.one_to_one:
            rel_ids = data.__getattribute__(rel.mapping_field)
            resources = None
            if rel_ids != None:
                identifier_meta = self.identifier_meta(rel=rel, rel_name=rel_name, data=data, relid=rel_ids)
                resources = await JsonapiAdapter.resource_identifier(type_=rel_type, id_=rel_ids, meta=identifier_meta)
            # total = 1 if rel_ids else 0    # meta total
        elif rel.mapping_field and not rel.one_to_one:
            # 去重
            rel_ids = data.__getattribute__(rel.mapping_field) if data.__getattribute__(
                rel.mapping_field) else None
            resources = []
            if rel_ids:
                for id_ in rel_ids:
                    identifier_meta = self.identifier_meta(rel=rel, rel_name=rel_name, data=data, relid=id_)
                    resource = await JsonapiAdapter.resource_identifier(type_=rel_type, id_=id_, meta=identifier_meta)
                    resources.append(resource)
            # total = len(rel_ids) if rel_ids else 0  # meta total
        elif rel.cond_fun and self.args.include and rel_name in self.args.include:  # 没有mapping.则在有inlcude时再显示relationships的data
            cond_func = getattr(self, rel.cond_fun)
            cond_query = cond_func([data])  # 查询条件
            # rel_ids = cond_query.get_field_value('id') if cond_query else None
            rel_ids = cond_query.get('request_context').get('id') if cond_query else None
            if rel.one_to_one:
                resources = None
                if rel_ids != None:
                    identifier_meta = self.identifier_meta(rel=rel, rel_name=rel_name, data=data, relid=rel_ids)
                    resources = await JsonapiAdapter.resource_identifier(type_=rel_type, id_=rel_ids[0])
            else:
                resources = []
                if rel_ids:
                    for id_ in rel_ids:
                        identifier_meta = self.identifier_meta(rel=rel, rel_name=rel_name, data=data, relid=rel_ids)
                        resource = await JsonapiAdapter.resource_identifier(type_=rel_type, id_=id_,
                                                                            meta=identifier_meta)
                        resources.append(resource)
            # total = rel_resource(request_context=rel_cond).count()
        else:
            resources = None

        return resources

    async def single_serialize_related(self, data, rel_name, rel, include, q_data):
        """
        单条关系数据
        :param data: 一条数据模型
        :param rel_name: 关系名称
        :param rel: 关系对象
        :param include: include
        :param q_data: 需要显示的关系标识
        :return: 示例：{
                  "links": {
                    "self": "/articles/1/relationships/author",
                    "related": "/articles/1/author"
                  },
                  "data": { "type": "people", "id": "9" }
                }
        """

        # related

        if rel.has_related:
            related = self.host[:-1] + self.Meta.link + '/{}/{}'.format(data.id, rel_name)
        else:
            related = None
        # self
        if rel.has_self:
            self_ = self.host[:-1] + self.Meta.link + '/{}/relationships/{}'.format(data.id, rel_name)
        else:
            self_ = None
        if rel_name in include or rel_name in q_data:
            resources = await self.serialize_identifier(data=data, rel=rel, rel_name=rel_name)
            rel_data = await JsonapiAdapter.relationship(
                self_=self_,
                related=related,
                resources=resources,
                resources_show=True,
                meta=rel.Meta.dict()
            )
        else:
            rel_data = await JsonapiAdapter.relationship(
                self_=self_,
                related=related,
                resources_show=False,
                meta=rel.Meta.dict()
            )
        return rel_data

    def rel_meta(self, data: SchemaBase):
        """realtionships 的meta生成"""
        pass

    async def serialize_related(self,
                                data: SchemaBase,
                                rels: Dict[str, Relationship],
                                include: list = [],
                                q_data: List = []) -> Dict[str, RelationshipModel]:
        """
        生成 jsonapi的关系数据
        Returns: 例：  {
                        "author": {
                          "links": {
                            "self": "/articles/1/relationships/author",
                            "related": "/articles/1/author"
                          },
                          "data": { "type": "people", "id": "9" }
                        }
                        ....
                      }
        """
        relationships = dict()
        self.rel_meta(data=data)  # relationships meta

        for item, rel in rels.items():
            rel_data = await self.single_serialize_related(data=data,
                                                           rel_name=item,
                                                           rel=rel,
                                                           include=include,
                                                           q_data=q_data)
            relationships[item] = rel_data
        return relationships

    async def serialize_attr(self,
                             data: SchemaBase,
                             attr_model: SchemaBase):
        attr = attr_model(**data.dict())
        return attr

    async def attr_model(self, many: bool = False):
        attr_model = create_model('attr_model')
        attr_field = self.model.response_fields(many=many)
        attr_model.__fields__ = attr_field
        return attr_model

    async def serialize_api(self,
                            datas: Union[List[SchemaBase],
                                         SchemaBase],
                            rels: Dict[str,
                                       Relationship],
                            include: list = [],
                            q_data: list = [],
                            **kwargs):
        """
        jsonapi data 生成
        Args:
            datas: 数据
            rels: 包含关系
            **kwargs:
        Returns: JsonapiDataModel

        """
        # fields_prams = self.args.fields if self.args else {}
        if isinstance(datas, list):  # 资源列表
            api_datas = []
            attr_model = await self.attr_model(many=True)
            for data in datas:
                meta = data.Meta.dict()  # data meta

                api_data = await JsonapiAdapter.api_data(
                    id_=data.id,
                    type_=self.Meta.type_,
                    attributes=await self.serialize_attr(data=data, attr_model=attr_model),
                    relationships=await self.serialize_related(data=data,
                                                               rels=rels,
                                                               include=include,
                                                               q_data=q_data),
                    links=self.host[:-1] + self.Meta.link + '/' + str(
                        data.id),
                    meta=meta,
                    # fields=fields_prams
                )
                api_datas.append(api_data)
        else:  # 单个资源
            data = datas
            attr_model = await self.attr_model()
            meta = data.Meta.dict()  # data meta
            api_datas = await JsonapiAdapter.api_data(id_=data.id,
                                                      type_=self.Meta.type_,
                                                      attributes=await self.serialize_attr(data=data,
                                                                                           attr_model=attr_model),
                                                      relationships=await self.serialize_related(data=data,
                                                                                                 rels=rels,
                                                                                                 include=include,
                                                                                                 q_data=q_data),
                                                      links=self.host[:-1] + self.Meta.link + '/' + str(data.id),
                                                      meta=meta,
                                                      # fields=fields_prams
                                                      )
        return api_datas

    async def include_condit(self,
                             datas: Union[List[SchemaBase],
                                          SchemaBase],
                             rel_name,
                             rel):
        """
        获取关系资源的条件，为生成富文本文档做准备
        :param datas:
        :param rels:
        :return:
        """

        relid = []
        if not isinstance(datas, list):
            datas = [datas]
        if rel.mapping_field:
            for data in datas:
                rel_ids = data.__getattribute__(rel.mapping_field)
                if rel_ids != None:
                    relid.extend(rel_ids) if isinstance(rel_ids, List) else relid.append(rel_ids)
            condition = {'request_context': {
                'id': list(set(relid))}}
        else:
            cond_func = getattr(self, rel.cond_fun)
            condition = cond_func(datas)  # 查询条件
        return condition

    async def get_rel_data(self, datas, rel_name, rel):
        """
        获取关系数据
        Args:
            datas: api_data
            rel_name: 关系名
            rel: Relationship类

        Returns: 关系资源模型数据

        """
        rel_resource = registered_resources.get(rel.rel_resource)
        rel_condition = await self.include_condit(datas, rel_name, rel)  # 关系ids
        if isinstance(rel_condition, dict):
            rel_class = rel_resource(request=None, host=self.host, **rel_condition)
        else:
            # rel_condition.limit = rel.include_limit
            rel_class = rel_resource(request=None, host=self.host, query_args=rel_condition)
        rel_class.args.limit = rel.include_limit
        rel_datas = await rel_class.connect_data(func=rel_class.get_many)
        # rel_datas =await rel_resource(
        #     request=None, host=self.host, **rel_condition).get_many()  # 关系数据
        # await rel.after_request()
        return rel_datas

    async def get_include_data(self, include_tree, q_data_tree, pid_node, node, exist_included_dict):
        """
        获取每一层的include数据
        Args:
            include_tree: 关系tree
            pid_node: 本层关系的上层 例： pubscene.journey
            node: 本层关系 例：pubscene.journey.journeycls

        Returns:

        """
        rel_name = include_tree[node].tag
        include_child = [node.tag for node in include_tree.children(node)]
        q_data_child = [node.tag for node in q_data_tree.children(node)] if q_data_tree.contains(node) else []
        rels = include_tree[pid_node].data.get('rel')  # 第n层关系的全部关系
        datas = include_tree[pid_node].data.get('data')  # 第n层关系的全部数据
        rel = rels[rel_name]  # 第n层关系对象
        rel_resource = registered_resources.get(rel.rel_resource)  # 第n层关系的关系资源
        type_ = rel_resource.Meta.type_
        relrels = rel_resource.rel_resources()  # 第n层关系的全部关系
        rel_datas_all = await self.get_rel_data(datas=datas,
                                            rel_name=rel_name,
                                            rel=rel)  # 第n层关系数据（pubscene）

        include_tree[node].data = {'rel': relrels, 'data': rel_datas_all}   # 构造tree需要全量数据，因为还有下一层需要取
        rel_datas = []
        for data in rel_datas_all:     # 已有数据排除
            if data.id not in exist_included_dict[type_]:
                rel_datas.append(data)
                exist_included_dict[type_].append(data.id)
        return await rel_resource(host=self.host).serialize_api(rel_datas, relrels, include_child, q_data_child), exist_included_dict

    async def serialize_include(
            self,
            datas: List[SchemaBase],
            rels: Dict[str, Relationship],
            include_res: list,
            q_data: list
    ):
        """
         includes数据。包含关系，及关系的关系。
        :param datas:
        :param rels:
        :param included:
        :param include_res:
        :return:
        """
        included = []
        include_tree = Tree()
        include_tree.create_node('main', 'main')
        include_tree['main'].data = {'rel': rels, 'data': datas}  # 主资源
        for inc in include_res:
            inc_list = inc.split('.')
            if not include_tree.contains(inc_list[0]):
                include_tree.create_node(inc_list[0], inc_list[0], parent='main')
            if len(inc_list) == 1:
                continue
            if not include_tree.contains('.'.join(inc_list[:2])):
                include_tree.create_node(inc_list[1], '.'.join(inc_list[:2]), parent=inc_list[0])
            if len(inc_list) == 2:
                continue
            include_tree.create_node(inc_list[2], '.'.join(inc_list), parent='.'.join(inc_list[:2]))

        q_data_tree = Tree()
        q_data_tree.create_node('main', 'main')
        q_data_tree['main'].data = {'rel': rels, 'data': datas}  # 主资源
        for inc in q_data:
            inc_list = inc.split('.')
            if not q_data_tree.contains(inc_list[0]):
                q_data_tree.create_node(inc_list[0], inc_list[0], parent='main')
            if len(inc_list) == 1:
                continue
            if not q_data_tree.contains('.'.join(inc_list[:2])):
                q_data_tree.create_node(inc_list[1], '.'.join(inc_list[:2]), parent=inc_list[0])
            if len(inc_list) == 2:
                continue
            q_data_tree.create_node(inc_list[2], '.'.join(inc_list), parent='.'.join(inc_list[:2]))

        exist_included_dict = defaultdict(list)
        for node in include_tree.expand_tree(mode=Tree.WIDTH, sorting=False):  # 层序遍历, 确保父级先获取数据
            if node == 'main':
                continue
            # include_child = [node.tag for node in include_tree.children(node)]
            # rel_name = include_tree[node].tag
            if node.count('.') == 0:  # 第一层关系
                rel_pid = 'main'
                include_data, exist_included_dict = await self.get_include_data(include_tree=include_tree, q_data_tree=q_data_tree,
                                                           node=node, pid_node=rel_pid, exist_included_dict=exist_included_dict)

                included.extend(include_data)
            elif node.count('.') == 1:  # 第二层关系
                rel_pid, _ = node.split('.')  # 父节点id
                include_data, exist_included_dict = await self.get_include_data(include_tree=include_tree, q_data_tree=q_data_tree,
                                                           node=node, pid_node=rel_pid, exist_included_dict=exist_included_dict)

                included.extend(include_data)
            elif node.count('.') == 2:  # 第三层关系
                rel_pid = '.'.join(node.split('.')[:2])  # 父节点id
                include_data, exist_included_dict = await self.get_include_data(include_tree=include_tree, q_data_tree=q_data_tree,
                                                           node=node, pid_node=rel_pid, exist_included_dict=exist_included_dict)

                included.extend(include_data)

        return included

    async def _jsonapi(
            self,
            datas: Union[SchemaBase, List[SchemaBase]],
            rels: Dict[str, Relationship] = None,
            include: bool = True,
            pages: int = None,
            onlyid: bool = False,
            *args,
            **kwargs
    ) -> JsonApiModel:
        """
        jsonapi response
        Args:
            datas: SchemaBase, 数据
            rels: dict, 关系
            include: bool, 是否需要include
            pages: int, 总条数
            onlyid: bool, 是否只返回id
            *args:
            **kwargs:

        Returns: jsonapi:data

        """
        meta = kwargs
        # 分页放在meta里
        if pages:
            pagination_kwargs = await JsonapiAdapter.pagination(
                total=pages, limit=self.args.limit, offset=self.args.skip)
            meta.update(pagination_kwargs)
        if not datas:  # 没有数据
            response_data = await JsonapiAdapter.response_data(
                data=datas,
                meta=meta
            )
            return response_data

        # 只返回id和type
        if onlyid:
            response_data = await JsonapiAdapter.response_data(
                data=await JsonapiAdapter.api_data(id_=datas.id,
                                                   type_=self.Meta.type_))
            return response_data
        # data
        api_datas = await self.serialize_api(datas=datas, rels=rels, include=self.args.include, q_data=self.args.q_data)
        # included
        if include and self.args.include:
            included = await self.serialize_include(
                datas=datas,
                rels=rels,
                include_res=self.args.include,
                q_data=self.args.q_data)
        else:
            included = None
        # print(3333333333, api_datas)
        # 组合response
        response_data = await JsonapiAdapter.response_data(
            data=api_datas,
            included=included,
            meta=meta
        )
        return response_data

    @classmethod
    def add_security(cls, security: SecurityConfig):
        """
        验证绑定到每个子路由，
        Args:
            app: fastapi
            auth: 权限验证

        Returns:None

        """

        def add_auth(res, auth):
            if not res.childs:
                res.Auth = auth
                for _, rel_class in res.rel_resources().items():
                    rel_resource = registered_resources.get(rel_class.rel_resource, None)
                    if not rel_resource:
                        raise Exception('%s 不在全局变量registered_resources中' % rel_class.rel_resource)
                    rel_resource.Auth = auth
            else:
                cls.Auth = auth
                for res in res.childs:
                    add_auth(res=res, auth=auth)

        add_auth(res=cls, auth=security)

    @property
    def user(self) -> Optional[User]:
        """获取用户"""
        if self.Auth:
            return self.Auth.user
        else:
            return None

    @classmethod
    def _api(cls, has_response_model: bool = True, **kwargs):
        """
         接口路由，挂载接口方法
         全部方法： 主资源：GET/GETS/POST/PATCH/DELETE
                   关系：GET/POST/PATCH/DELETE
                  关系对象：GET
        Args:
            route:  APIRouter 挂载的上级路由
            **kwargs:

        Returns:

        """
        print(cls.model)

        cls.route = cls.router()

        cls.schema_model = CreatModel(cls, exits_model=cls._response_models)

        cls._relationships_model = cls.schema_model.rel_identifier_model
        cls._relationships_model_response = cls.schema_model.rel_identifier_model_response

        many_response_model = cls.schema_model.create_response_model(
            many=True)
        single_response_model = cls.schema_model.create_response_model(
            many=False)
        # json:api 接口
        if 'GETS' in cls.methods:
            cls.route.add_api_route(
                path='',
                endpoint=cls.use_get_many(many_response_model),
                methods=['GET'],
                response_model=many_response_model if has_response_model else None,
                **cls.GetManyInfo.dict()
            )

        if 'GET' in cls.methods:
            cls.route.add_api_route(
                path='/{id}',
                endpoint=cls.use_get(single_response_model),
                methods=['GET'],
                response_model=single_response_model if has_response_model else None,
                **cls.GetInfo.dict()
            )

        if 'POST' in cls.methods:
            cls.route.add_api_route(
                path='',
                endpoint=cls.use_post(single_response_model),
                methods=['POST'],
                response_model=single_response_model if has_response_model else None,
                **cls.PostInfo.dict()
            )

        if 'PATCH' in cls.methods:
            cls.route.add_api_route(
                path='/{id}',
                endpoint=cls.use_patch(single_response_model),
                methods=['PATCH'],
                response_model=single_response_model if has_response_model else None,
                **cls.PatchInfo.dict()
            )

        if 'DELETE' in cls.methods:
            cls.route.add_api_route(
                path='/{id}',
                endpoint=cls.use_delete(),
                methods=['DELETE'],
                response_model=single_response_model if has_response_model else None,
                **cls.DeleteInfo.dict()

            )

        # if 'ATOMIC' in cls.methods:
        #     router.add_api_route(
        #         endpoint=cls.use_atomic_post(),
        #         methods=['POST'],
        #         # response_model=cls.atomic_response_model(),
        #         **cls.AtomicInfo.dict()
        #     )

        cls._response_models.update(cls.schema_model._exits)
        if cls.relapi:  # 是否有关系接口
            for rel_name, rel_class in cls.rel_resources().items():
                path = '/{id}/relationships/%s' % rel_name
                if rel_class.has_self:
                    cls.route.add_api_route(
                        path=path,
                        endpoint=cls.use_relationships(rel_name,
                                                       rel_class,
                                                       cls._relationships_model_response.get(rel_name)[0]),
                        methods=['GET'],
                        response_model=cls._relationships_model_response.get(rel_name)[
                            0] if has_response_model else None,
                        **cls.RelGetInfo.dict()
                    )
                if rel_class.has_api and not rel_class.one_to_one:
                    cls.route.add_api_route(
                        path=path,
                        endpoint=cls.use_relationships_post(rel_name, single_response_model),
                        response_model=single_response_model if has_response_model else None,
                        methods=['POST'],
                        **cls.RelPostInfo.dict()
                    )

                if rel_class.has_api:
                    cls.route.add_api_route(
                        path=path,
                        endpoint=cls.use_relationships_patch(rel_name, single_response_model),
                        response_model=single_response_model if has_response_model else None,
                        methods=['PATCH'],
                        **cls.RelPatchInfo.dict()
                    )

                if rel_class.has_api and not rel_class.one_to_one:
                    cls.route.add_api_route(
                        path=path,
                        endpoint=cls.use_relationships_delete(rel_name, single_response_model),
                        response_model=single_response_model if has_response_model else None,
                        methods=['DELETE'],
                        **cls.RelDelInfo.dict()
                    )

                if rel_class.has_related:
                    rel_resource = registered_resources.get(rel_class.rel_resource)
                    if rel_class.one_to_one:
                        model_name = rel_resource.__name__ + 'SingleResponse'
                        many = False
                    else:
                        model_name = rel_resource.__name__ + 'ManyResponse'
                        many = True
                    rel_response_model = cls.schema_model._exits.get(model_name)

                    if not rel_response_model:
                        schema_model = CreatModel(rel_resource, exits_model=cls._response_models)
                        rel_response_model = schema_model.create_response_model(
                            many=many)
                        cls._response_models.update(schema_model._exits)

                    cls.route.add_api_route(
                        path='/{id}/%s' % rel_name,
                        endpoint=cls.use_related(rel_name, rel_class, rel_response_model),
                        response_model=rel_response_model if has_response_model else None,
                        methods=['GET'],
                        **cls.RelatedGetInfo.dict()
                    )

        # 权限添加
        if cls.Auth:
            cls.Auth.run(cls)

        return cls.route

    @classmethod
    def _register_sub_routes(cls, child, has_response_model: bool = True):
        """
        挂载所有下级路由
        Args:
            route: APIRouter 挂载的上级路由
            child: Rescoure

        Returns:

        """
        if not child.childs:
            if child.default_version:
                child = child.default_version  # 版本
            else:
                child = child
            router = child._api(has_response_model=has_response_model)
            return router.routes
        else:
            routers = []
            for child in child.childs:
                routes = cls._register_sub_routes(child=child,
                                                  has_response_model=has_response_model)
                # router.include_router(route)
                routers.extend(routes)
        return routers

    @classmethod
    def register_routes(cls, app: FastAPI, has_response_model: bool = True, **kwargs):
        """
        向api挂载路由
        Args:
            api: FastAPI
            **kwargs: FastAPI.include_router 参数

        Returns:

        """
        routers = cls._register_sub_routes(cls, has_response_model)
        # app.include_router(router)
        # app.router = router
        app.router.routes.extend(routers)
        return cls
