#!/usr/bin/env python3
# -*- coding=utf-8 -*-
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
import copy
from typing import Optional, List, Any, Dict, Union, TypeVar, Generic
from enum import Enum
from pydantic import BaseModel
from pydantic.generics import GenericModel


class LinksSelfModel(BaseModel):
    """jsonapi 链接对象"""
    self: str = None


class LinksRelatedModel(BaseModel):
    """jsonapi 链接资源对象"""
    self: str = None
    related: Any = None


class ErrorModel(BaseModel):
    """错误对象"""
    # id: Optional[int]
    status: Optional[int] = None
    # code: Optional[int]
    title: Optional[str] = None
    detail: Optional[str]


class ErrorResponse(BaseModel):
    """错误响应"""
    errors: List[ErrorModel]


RelType = TypeVar('RelType', bound=str)
RelId = TypeVar('RelId', bound=Any)


class ResourceIdentifier(GenericModel, Generic[RelId, RelType]):
    id: RelId = None
    type: RelType = None
    meta: Optional[Dict] = None


class RelationshipModel(BaseModel):
    """关系对象"""
    links: Optional[LinksRelatedModel] = None
    data: Optional[Union[List[ResourceIdentifier],
                         ResourceIdentifier]] = None  # list在前，映射空[]
    meta: Optional[Dict] = None


TypeT = TypeVar('TypeT', bound=str)
RelT = TypeVar('RelT')
AttributesT = TypeVar('AttributesT')


class ApiDataModelResponse(GenericModel, Generic[TypeT, RelT, AttributesT]):
    """资源对象响应模型"""
    id: Optional[Any] = None
    type: TypeT
    attributes: AttributesT
    relationships: RelT = None
    links: LinksSelfModel = None
    meta: Optional[Dict] = None


class ApiDataModelRequest(GenericModel, Generic[TypeT, RelT, AttributesT]):
    """资源对象请求模型"""
    id: Optional[Any] = None
    type: TypeT
    attributes: AttributesT
    relationships: RelT = None


DataT = TypeVar('DataT', bound=ApiDataModelResponse)


class JsonApiModel(GenericModel, Generic[DataT]):
    """jsonapi模型"""
    meta: Optional[Dict] = None
    data: Optional[Union[DataT, List[DataT]]] = None
    links: LinksSelfModel = None
    jsonapi: Optional[Dict] = None
    included: List[DataT] = None


class Op(str, Enum):
    # 操作符枚举类
    add = 'add'
    update = 'update'


RelationshipT = TypeVar('RelationshipT', bound=Enum)


class RefRel(GenericModel, Generic[TypeT, RelationshipT]):
    """原子操作ref对象"""
    id: Union[str, int]
    type: TypeT
    relationship: RelationshipT


class RefRes(GenericModel, Generic[RelId, TypeT]):
    """原子操作关联资源数据"""
    id: RelId
    type: TypeT


RemoveT = TypeVar('OpT', bound=Literal['remove'])


class ResourcesRemoveModel(GenericModel, Generic[RemoveT]):
    """原子操作删除模型"""
    op: RemoveT
    ref: RefRes


class JsonapiAdapter(object):

    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    async def response_data(
            data: Optional[Dict],
            meta: Optional[Any] = None,
            jsonapi: Optional[str] = None,
            links: Optional[Dict] = None,
            included: Optional[List[Dict]] = None
    ) -> dict:
        """jsonapi适配器
        Args:
            data: 文档的”primary data”.
            meta: 元信息
            jsonapi: 描述服务器实现的对象.
            links: 与primary data相关的链接对象.
            included: 复合文档,类型同ApiDataModel，与primary data或其他资源相关的资源对象("included resources")列表
        Returns:
            jsonapi
        """
        return {
            'data': data,
            'meta': meta,
            'jsonapi': jsonapi,
            'links': links,
            'included': included,
        }

    @staticmethod
    async def api_data(
            id_: Optional[Any],
            type_: str,
            attributes: Union[Dict, BaseModel] = None,
            relationships: Dict[str, RelationshipModel] = None,
            links=None,
            meta: Optional[Dict] = None,
            fields: Dict[str, list] = None  # 稀疏字段
    ) -> dict:
        """
        资源对象生成适配器
        Args:
            id: 资源id
            type: 资源type
            attributes: attribute，属性对象代表资源的某些数据.
            relationships: 关系数据,关联对象描述该资源与其他JSON API资源之间的关系.
            links: 链接资源包含与资源相关的链接.
            meta: 元数据资源包含与资源对象相关的非标准元信息，这些信息不能被作为属性或关联对象表示.
            fields:  稀疏字段。dict类型。key，str类型，为资源type。 value，list,资源属性
        Returns:
            ApiData
        """
        if links:
            links = {'self': links}
        if isinstance(attributes, BaseModel):
            attributes = attributes.dict()
        new_attributes = copy.deepcopy(attributes)
        if fields and type_ in tuple(fields.keys()):
            for key in attributes.keys():
                if key != 'id' and key not in fields[type_]:
                    new_attributes.pop(key)
                    if relationships and key in relationships:
                        relationships.pop(key)

        return {
            'id': id_,
            'type': type_,
            'attributes': attributes,
            'links': links,
            'relationships': relationships,
            'meta': meta,
        }


    @staticmethod
    async def resource_identifier(id_, type_, meta):
        """最小关系资源单位
        Args:
            id:id
            type:相关资源类型
            **kwargs:元数据
        Returns:
            关系资源中的data部分
        """
        return {
            'type': type_,
            'id': id_,
            'meta': meta}

    @staticmethod
    async def relationship(self_=None,
                           related=None,
                           resources: Optional[Union[ResourceIdentifier,
                                                     List[ResourceIdentifier]]] = None,
                           resources_show: bool = True,
                           meta: Optional[Dict] = None
                           ) -> dict:
        """
        关联对象（关系资源）
        Args:
            self_: 关系数据链接("relationship link")
            related: 相关资源链接
            resources: 资源
            **kwargs:元数据
        Returns:
            关系资源relationship
        """
        if self_ is None and related is None:
            links = None
        else:
            links = {
                'self': self_,
                'related': related,
                # meta = meta
            }

        relationship = {
            'links': links,
            'meta': meta
        }
        if resources_show:
            relationship.update({'data': resources})
        return relationship

    @staticmethod
    async def pagination(total, limit, offset) -> dict:
        """
        分页信息生成
        :param total: 全部页数
        :param limit:
        :param offset:
        :return:dict
        """
        return {"pagination": {
            "total": total,
            "limit": limit,
            "offset": offset}}
