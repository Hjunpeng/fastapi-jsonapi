#!/usr/bin/env python3
# -*- coding=utf-8 -*-
from typing import Optional, List, Any, Dict, Union, Type, Set, Tuple

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
from typing import Callable
import copy
from pydantic import create_model, BaseModel
from pydantic.fields import ModelField
from fastapi_jsonapi.field import Field
from fastapi_jsonapi.jsonapi import LinksSelfModel, LinksRelatedModel, Op, RefRel, ApiDataModelRequest, ResourcesRemoveModel
from fastapi_jsonapi.meta import registered_resources


class DataMeta(BaseModel):
    """data meta 数据模型， 值可以是ture, false, fields(attr+rel), PATCH(代表这条数可或不可更新)， DELETE(这条数可删除或不可)
        Args:
            disable: 不可修改，默认为False,所有字段可修改，指定字段时只有指定的不可修改
            enable: 可修改。默认为True,所有字段可修改，指定field只有指定的可修改
            token：用于告终前端访问url是否要带token,指定urls所在字段。如图片attr的url:token=['url']
            relationships: related中记录主资源和当前资源的关系数据，例如场景探索中记录usage有关的user的total的个数，使用{'pubscene':'total':10}.
        Returns:
            Basemodel
        """
    disable: Optional[Union[List, bool]] = Field(False, )
    enable: Optional[Union[List, bool]] = Field(None, )
    token: Optional[Union[List, bool]] = Field(None)
    relationships: Optional[Union[List, bool]] = Field(None)

    def dict(
            self,
            *,
            include: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
            exclude: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
            by_alias: bool = False,
            skip_defaults: bool = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
    ) -> 'DictStrAny':
        # 默认显示disable=False,该条数据可以被修改
        # disable 和enable 中只能存在一个。
        # token 不传值不在meta中显示
        meta_dict = super().dict()
        if self.enable is not None:
            meta_dict.pop('disable')
        elif self.enable is None:
            meta_dict.pop('enable')
        else:
            meta_dict.pop('enable')
            meta_dict['disable'] = False
        if self.token is None:
            meta_dict.pop('token')
        if self.relationships is None:
            meta_dict.pop('relationships')
        return meta_dict


class RelationshipsMeta(BaseModel):
    """关系的meta数据， 根据具体业务判断关系中是否添加，不添加时不显示
       Args:
           total: 默认不显示，计算关系数，如点赞/评论/版本作为关系时，统计点赞数，评论数。。。
           me: 默认不显示。如果关系和用户有关，那么指明当前用户是否与之有关，其值可以true或false，或者是数字。示例如下
                         1. 某个资源被人收藏，如果当前用户未收藏，false。如果收藏了，true
                         2. 某个资源被评论，如果当前用户评论了，则是该用户的评论数，如3，否则为0
       Returns:
           Basemodel
   """
    total: Optional[Union[List, bool]] = Field(None, )  # 计算关系数。
    me: Optional[Union[List, bool]] = Field(None, )  # 指明当前数据是否为当前访问者的数据。如评论作为关系时，当前评论是否。

    def dict(
            self,
            *,
            include: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
            exclude: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
            by_alias: bool = False,
            skip_defaults: bool = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
    ) -> 'DictStrAny':
        meta_dict = super().dict()
        if self.total is None:
            meta_dict.pop('total')
        if self.me is None:
            meta_dict.pop('me')
        return meta_dict


class RdentifierMeta(BaseModel):
    """资源标识符的meta数据， 根据具体业务判断关系中是否添加，不添加时不显示
       Args:
           relationships: 里面添加需要的信息，比如pub

       Returns:
           Basemodel
   """
    total: Optional[Union[List, bool]] = Field(None, )  # 计算关系数。
    me: Optional[Union[List, bool]] = Field(None, )  # 指明当前数据是否为当前访问者的数据。如评论作为关系时，当前评论是否。

    def dict(
            self,
            *,
            include: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
            exclude: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
            by_alias: bool = False,
            skip_defaults: bool = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
    ) -> 'DictStrAny':
        meta_dict = super().dict()
        if self.total is None:
            meta_dict.pop('total')
        if self.me is None:
            meta_dict.pop('me')
        return meta_dict


def field_mapping(field):
    """
    Field mapping 装饰器，将被装饰的函数赋值给field的mapping属性
    :param field: 字段对象
    :return:
    """
    def dec(f: Callable):
        field.mapping = f
        return
    return dec


class SchemaBase(BaseModel):
    """属性对象基类，重写资源属性
    """
    # id: Any
    Meta: DataMeta = Field(DataMeta(), title='data的meta数据', ishide=True)  # 对外隐藏字段

    class Config:
        orm_mode = True

    @classmethod
    def add_fields(cls, **field_definitions) -> Type['SchemaBase']:
        """添加新的字段属性
           ! 注意，添加属性会返回模型本身，全局修改模型结构，如若更改资源模型，注意Field应配置必要的参数。
        Args:
            **field_definitions: 属性名称：(属性类型, Field).
                                例1：user=(str, Field(None, isrel=True, onlyread=True)) 等同于
                                在模型中添加字段 user: str = Field(None, isrel=True, onlyread=True).
                                例2：user=None 等同于在模型中添加字段 user: str = Field(None)

        Returns:
            cls
        """

        new_fields: Dict[str, Field] = {}
        new_annotations: Dict[str, Optional[type]] = {}

        for f_name, f_def in field_definitions.items():
            if isinstance(f_def, tuple):
                try:
                    f_annotation, f_value = f_def
                except ValueError as e:
                    raise Exception("字段应该定义为一个包含类型和默认值的元组 (<type>, <Field()>) 或者是"
                                    "一个默认值，不能是一个只包含默认值或类型的元组") from e
            else:
                f_annotation, f_value = str if f_def is None else type(f_def), Field(None)   # 给定数据时，类型为数据类型，如果为None，默认类型是字符串
            if f_annotation:
                new_annotations[f_name] = f_annotation

            new_fields[f_name] = ModelField.infer(
                name=f_name,
                value=f_value,
                annotation=f_annotation,
                class_validators=None,
                config=cls.__config__)
        cls.__fields__.update(new_fields)
        cls.__annotations__.update(new_annotations)
        return cls

    @classmethod
    def filter_fields(cls):  # 资源筛选字段（不包含关系的）
        model_fields = {}
        fields = copy.deepcopy(cls.__fields__)
        for key, item in fields.items():
            if not item.field_info.isrel and not item.field_info.ishide:
                model_fields[key] = cls.__annotations__.get(key)
        return model_fields

    @classmethod
    def post_fields(cls):  # 新增数据模型
        model_fields = {}
        fields = copy.deepcopy(cls.__fields__)
        for key, item in fields.items():
            if not item.field_info.isrel and not item.field_info.ishide and not item.field_info.onlyread and key != 'id':
                model_fields[key] = item
        return model_fields

    @classmethod
    def patch_fields(cls):  # 更新数据模型，所有字段可为None
        model_fields = {}
        fields = copy.deepcopy(cls.__fields__)
        for key, item in fields.items():
            if not item.field_info.isrel and not item.field_info.ishide and not item.field_info.onlyread and key != 'id':
                item.required = None
                model_fields[key] = item
        return model_fields

    @classmethod
    def response_fields(cls, many=False):
        """单个资源和资源列表的模型所用字段不同。
        filed.inmany = flase 表示不在资源列表中显示"""
        model_fields = {}

        for key, item in cls.__fields__.items():
            if not item.field_info.isrel and (not item.field_info.ishide) and (not item.field_info.onlywrite and key != 'id') \
                    and ((item.field_info.inmany and many) or (not many)):
                model_fields[key] = item

        return model_fields


class Relationship(object):
    """
    关系基类
        Args:
            rel_resource: 资源模型类名。通过名称找类对象
            mapping_field: 关系在资源模型中对应的字段, 取字段的值作为获取关系资源的id. 有值,则有data, 为None, data为空当relationships中没有data'
            cond_fun: 方法名，获取关系资源的条件。 mapping_field 和cond必须有一个不为空,
            has_data: 默认有，没有data 时，接口不能使用include参数
            has_self: 是否显示self, 默认true; 当为False时,relationships中没有self链接, 接口中也没有source/{id}/relationships/rel_name 接口
            has_related: 是否显示related, 默认true; 当为False时,relationships中没有related链接, 接口中也没有'source/{id}/rel_name' 接口
            one_to_one: 默认关系一对一.
            required： 关系是否必须有
            has_api: 是否有关系数据增删改接口
            modify: 是否在request中可以修改
            inlcude_limit: 控制include的显示条数
            Meta: relationships的元信息，

            **kwargs:
        Returns:
            Relationship
    """
    Meta: RelationshipsMeta

    def __init__(
            self,
            rel_resource: str,
            mapping_field: str = None,
            cond_fun: str = None,
            has_data: bool = True,
            has_self: bool = True,
            has_related: bool = True,
            one_to_one: bool = True,
            has_api: bool = True,
            modify: bool = True,
            required: bool = False,
            inlcude_limit: int = None,
            **kwargs):
        if (mapping_field and cond_fun) or (not mapping_field and not cond_fun):
            raise Exception("mapping_field和cond_fun 有且仅有一个不为None")
        self.rel_resource = rel_resource
        self.mapping_field = mapping_field
        self.cond_fun = cond_fun
        self.has_data = has_data
        self.has_self = has_self
        self.has_related = has_related
        self.one_to_one = one_to_one
        self.has_api = has_api
        self.modify = modify
        self.required = required
        self.include_limit = inlcude_limit
        self.Meta = RelationshipsMeta()


class CreatModel(object):

    def __init__(self, resource_model, exits_model={}):
        """
        init中生成会多次复用的模型
        Args:
            resource_model:
        """
        self.resource_model = resource_model
        self.validation()
        self._exits = {}
        if exits_model:
            self._exits.update(exits_model)

        # 放在init中供关系数据的增删改查使用
        self.rel_identifier_model = self.create_rel_identifier_model(self.resource_model, tag='Post')
        self.rel_identifier_model_response = self.create_rel_identifier_model(self.resource_model, tag='Response')
        self.includes_model = []
        self.includes_model = self.create_include_models(
            resource_model=self.resource_model,
            include_model=self.includes_model)
    #
    # def _clear_rel_field(self, resource_model, attr_field):
    #     """去除attibute中的关系字段"""
    #     relationships_field = []
    #     for field, value in resource_model.rel_resources().items():
    #         relationships_field.append(value.mapping_field)
    #     for field in relationships_field:
    #         attr_field.pop(field)
    #     return attr_field

    def create_resquest_attribute_model(self, tag):
        """创建response需要的attribute_model"""
        attr_model_name = self.resource_model.__name__ + 'Attr' + tag
        if self._exits and self._exits.get(attr_model_name):
            return self._exits.get(attr_model_name)
        attr_model = create_model(attr_model_name)
        # attribute在新增和更新时不同
        if tag == 'Post':
            attr_field = self.resource_model.model.post_fields()
        else:
            attr_field = self.resource_model.model.patch_fields()
        # attr_field = self._clear_rel_field(
        #     resource_model=self.resource_model,
        #     attr_field=attr_field)
        attr_model.__fields__ = attr_field
        self._exits[attr_model_name] = attr_model
        return attr_model

    def create_response_attribute_model(self, resource_model, many=False):
        """创建response需要的attribute_model"""

        if many:
            attr_model_name = resource_model.__name__ + 'Attr' + 'ManyResponse'
        else:
            attr_model_name = resource_model.__name__ + 'Attr' + 'SingleResponse'

        if self._exits and self._exits.get(attr_model_name):
            return self._exits.get(attr_model_name)

        attr_model = create_model(attr_model_name)
        attr_field = resource_model.model.response_fields(many=many)
        # attr_field = self._clear_rel_field(
        #     resource_model=resource_model, attr_field=attr_field)
        attr_model.__fields__ = attr_field
        self._exits[attr_model_name] = attr_model
        return attr_model

    def creat_resquest_apidata_model(self, resource, attribute, relationships, post=True):
        tag = 'Post' if post else 'Patch'
        model_name = resource.__name__ + 'ApiData' + tag
        if self._exits and self._exits.get(model_name):
            return self._exits.get(model_name)

        rel_required = None
        attr_required = None
        if post:  # 新增模型 required为必填。 更新模型全都是非必填
            for name, field in self.resource_model.model.post_fields().items():
                if field.required:
                    attr_required = ...
                    break
            for field, rel in self.resource_model.rel_resources().items():
                if rel.required:
                    rel_required = ...
                    break
        id_required = None if post else ...
        if relationships:
            model = create_model(
                model_name,
                id=(resource.model.__annotations__.get('id'), id_required),
                type=(Literal[resource.Meta.type_], resource.Meta.type_),
                attributes=(attribute, attr_required),
                relationships=(relationships, rel_required),
            )
        else:
            model = create_model(
                model_name,
                id=(resource.model.__annotations__.get('id'), id_required),
                type=(Literal[resource.Meta.type_], resource.Meta.type_),
                attributes=(attribute, attr_required),
                # relationships=(relationships, rel_required),
            )
        self._exits[model_name] = model
        return model

    def creat_response_apidata_model(
            self,
            resource,
            attribute,
            relationships,
            many=False):
        if many:
            model_name = resource.__name__ + 'ApiData' + 'ManyResponse'
        else:
            model_name = resource.__name__ + 'ApiData' + 'SingleResponse'
        if self._exits and self._exits.get(model_name):
            return self._exits.get(model_name)
        if relationships:
            model = create_model(
                model_name,
                id=(resource.model.__annotations__.get('id'), None),
                type=(Literal[resource.Meta.type_], resource.Meta.type_),
                attributes=(attribute, None),
                relationships=(relationships, None),
                links=(LinksSelfModel, None),
                meta=(Optional[Dict], None)
            )
        else:
            model = create_model(
                model_name,
                id=(resource.model.__annotations__.get('id'), None),
                type=(Literal[resource.Meta.type_], resource.Meta.type_),
                attributes=(attribute, None),
                # relationships=(relationships, None),
                links=(LinksSelfModel, None),
                meta=(Optional[Dict], None)
            )
        self._exits[model_name] = model

        return model

    def create_relationship_model(self, resource_model, rel_identifier_model, tag):
        rel_model = copy.deepcopy(rel_identifier_model)
        model_name = resource_model.__name__ + 'Relationship' + tag
        if self._exits and self._exits.get(model_name):
            return self._exits.get(model_name)
        if tag == 'Post' or tag == 'Patch':
            for field, rel in self.resource_model.rel_resources().items():
                if not rel.modify:
                    rel_model.pop(field)
        if not rel_identifier_model:
            return None
        relationship_model = create_model(
            model_name,
            **rel_model
        )
        self._exits[model_name] = relationship_model
        return relationship_model

    def create_rel_identifier_model(
            self, resource_model, tag='Post') -> Dict[str, Tuple[Type[BaseModel], None]]:
        """
        Args:
            tag:
            resource_model: 资源模型
        Returns: 生成所有的资源关系的标识符对象
        """
        relationships_model = {}

        for field, rel in resource_model.rel_resources().items():
            if tag == 'Response':  # request时不显示link
                model_field = {'links': (LinksRelatedModel, None), 'meta': (dict, None)}
            else:
                model_field = {}
            if tag == 'Post' and rel.required:  # 只有新增时考虑关系是否必填
                required = ...
            else:
                required = None

            rel_resource = registered_resources.get(rel.rel_resource)
            if not rel_resource:
                raise Exception('没有找到%s的资源对象' % rel.rel_resource)
            if not rel_resource.model:
                raise Exception('资源%s没有model' % rel.rel_resource)
            rel_model = rel_resource.model
            # if tag == 'Response' and not rel.mapping_field and rel.one_to_one:
            #     model_name = resource_model.__name__ + field.capitalize() + 'OvoRel' + tag
            # elif tag == 'Response' and not rel.mapping_field and not rel.one_to_one:
            #     model_name = resource_model.__name__ + field.capitalize() + 'OvmRel' + tag
            if rel.one_to_one:
                identifier_model_name = resource_model.__name__ + field.capitalize() + 'OvoRelData' + tag
                if self._exits and self._exits.get(identifier_model_name):
                    rel_data = self._exits.get(identifier_model_name)
                else:
                    rel_data = create_model(resource_model.__name__ +
                                            field.capitalize() +
                                            'OvoRelData' + tag,
                                            id=(rel_model.__annotations__.get('id'), None),
                                            type=(Literal[rel_resource.Meta.type_], rel_resource.Meta.type_),
                                            meta=(dict, None)
                                            )
                self._exits[identifier_model_name] = rel_data
                model_name = resource_model.__name__ + field.capitalize() + 'OvoRel' + tag
                model_field.update({'data': (rel_data, required)})  # 关系必填，data必填
            else:
                identifier_model_name = resource_model.__name__ + field.capitalize() + 'OvmRelData' + tag
                if self._exits and self._exits.get(identifier_model_name):
                    rel_data = self._exits.get(identifier_model_name)
                else:
                    rel_data = create_model(resource_model.__name__ +
                                            field.capitalize() +
                                            'OvmRelData' + tag,
                                            id=(rel_model.__annotations__.get('id'), None),
                                            type=(Literal[rel_resource.Meta.type_], rel_resource.Meta.type_),
                                            meta=(dict, None)
                                            )
                self._exits[identifier_model_name] = rel_data
                model_name = resource_model.__name__ + field.capitalize() + 'OvmRel' + tag
                model_field.update({'data': (List[rel_data], required)})  # 关系必填，data必填

            if self._exits and self._exits.get(model_name):
                model = self._exits.get(model_name)
            else:
                model = create_model(
                    model_name,
                    **model_field)
            self._exits[model_name] = model
            relationships_model[field] = (
                model,
                required)  # 某个关系是否必填

        return relationships_model

    def single_include_model(self, rel_resource, include_model):
        model_name = rel_resource.__name__ + 'ApiData' + 'ManyResponse'
        if self._exits and self._exits.get(model_name):
            include_model.append(self._exits.get(model_name))

        include_model.append(
            self.creat_response_apidata_model(
                resource=rel_resource,
                attribute=self.create_response_attribute_model(rel_resource, many=True),
                relationships=self.create_relationship_model(resource_model=rel_resource,
                                                             rel_identifier_model=self.create_rel_identifier_model(
                                                                 rel_resource,
                                                                 tag='Response'),
                                                             tag='Response'),
                many=True
            )
        )
        return include_model

    def create_include_models(self, resource_model, include_model=[]):
        """创建include中支持的model"""
        if not resource_model.rel_resources():
            return []

        for field, rel in resource_model.rel_resources().items():
            rel_resource = registered_resources.get(rel.rel_resource)  # 关系的资源模型
            self.single_include_model(rel_resource, include_model)

            if not rel_resource.rel_resources():   # 关系下是否还有关系
                continue

            for field, rel in rel_resource.rel_resources().items():
                relrel_resource = registered_resources.get(rel.rel_resource)  # 关系的关系资源模型
                if relrel_resource == resource_model:        # 如果关系的关系模型等于主资源，不再包含在include中
                    continue
                self.single_include_model(relrel_resource, include_model)

                if not relrel_resource.rel_resources():  # 关系下是否还有关系
                    continue

                for field, rel in relrel_resource.rel_resources().items():
                    relrelrel_resource = registered_resources.get(rel.rel_resource)  # 关系的关系资源模型
                    if relrelrel_resource == resource_model:  # 如果关系的关系的关系模型等于主资源，不再包含在include中
                        continue
                    self.single_include_model(relrelrel_resource, include_model)

        return include_model

    def create_response_model(
            self,
            many: bool = False
    ) -> Type[BaseModel]:
        """自动生成响应的josnapi 模型
        Args:
            model_name: 模型名称
            use_list: 是否资源列表
        Returns:
            BaseModel
        """

        if many:
            model_name = self.resource_model.__name__ + 'ManyResponse'
            if self._exits and self._exits.get(model_name):
                return self._exits.get(model_name)
            response_apidata_many_model = self.creat_response_apidata_model(
                resource=self.resource_model,
                attribute=self.create_response_attribute_model(self.resource_model, many=many),
                relationships=self.create_relationship_model(resource_model=self.resource_model,
                                                             rel_identifier_model=self.rel_identifier_model_response,
                                                             tag='ManyResponse'),
                many=many)

            data = List[response_apidata_many_model]
        else:
            model_name = self.resource_model.__name__ + 'SingleResponse'
            if self._exits and self._exits.get(model_name):
                return self._exits.get(model_name)
            response_apidata_model = self.creat_response_apidata_model(
                resource=self.resource_model,
                attribute=self.create_response_attribute_model(
                    self.resource_model, many=False),
                relationships=self.create_relationship_model(resource_model=self.resource_model,
                                                             rel_identifier_model=self.rel_identifier_model_response,
                                                             tag='SingleResponse'))
            data = response_apidata_model
        # 生成模型
        model_field = {
            'data': (data, None),
            'meta': (Optional[Any], None),
            'jsonapi': (Optional[str], None),
            'links': (Optional[LinksSelfModel], None),
        }
        # 没有include 不显示
        if self.includes_model:
            model_field.update(
                {'included': (List[Union[tuple(self.includes_model)]], None)})

        model = create_model(
            model_name,
            **model_field
        )
        self._exits[model_name] = model
        return model

    def create_post_model(
            self
    ) -> Type[BaseModel]:
        """新增数据模型"""
        tag = 'Post'
        model_name = self.resource_model.__name__ + tag
        # rel_identifier_model = self.create_rel_identifier_model()
        resquest_apidata_model = self.creat_resquest_apidata_model(
            resource=self.resource_model,
            attribute=self.create_resquest_attribute_model(tag=tag),
            relationships=self.create_relationship_model(self.resource_model, self.rel_identifier_model, tag=tag),
            post=True
        )
        return create_model(
            model_name,
            data=(
                resquest_apidata_model,
                ...,
            )
        )

    def create_patch_model(
            self
    ) -> Type[BaseModel]:
        """更新数据模型"""
        tag = 'Patch'
        model_name = self.resource_model.__name__ + tag
        rel_identifier_model = self.create_rel_identifier_model(self.resource_model, tag=tag)
        resquest_apidata_model = self.creat_resquest_apidata_model(
            resource=self.resource_model,
            attribute=self.create_resquest_attribute_model(tag=tag),
            relationships=self.create_relationship_model(self.resource_model, rel_identifier_model, tag=tag),
            post=False
        )
        return create_model(
            model_name,
            data=(
                resquest_apidata_model,
                ...,
            )
        )

    def create_atomic_operation_model(
            self,
            ops: Set[str] = {'GET', 'PATCH', 'POST', 'DELETE'}
    ) -> Type[BaseModel]:
        """生成原子操作jsonapi请求模型
        Args:
            model_name: 模型名称
            data_attributes_model: 属性对象模型
            ops: 操作符
            remove_res: 排除资源类型列表
        Returns:
            BaseModel
        """
        tag = 'Atomic'
        model_name = self.resource_model.__name__ + tag
        model = []  # 所有支持的模型
        # 主资源 update,add

        for field, rel in self.resource_model.rel_resources().items():
            rel_model = rel.rel_resource.model
            rel_resource = rel.rel_resource
            if rel.one_to_one:
                rel_data = create_model(self.resource_model.__name__ +
                                        field.capitalize() +
                                        'OvmRelData',
                                        id=(rel_model.__annotations__.get('id'), None),
                                        type=Field(default=rel_resource.Meta.type_))
            else:
                rel_data = create_model(self.resource_model.__name__ +
                                        field.capitalize() +
                                        'OvmRelData',
                                        id=(rel_model.__annotations__.get('id'), None),
                                        type=Field(default=rel_resource.Meta.type_))

            # 单独更新关系模型
            # 关系模型名称=关系+操作符+资源类型+关系类型+这部分可自定义用来区分不同模型+关系命名方式（文档说明。修改需和前端讨论）
            model.append(create_model(
                'relationship_' + 'op[add,update,remove]_' + self.resource_model.Meta.type_ +
                '_' + rel_resource.Meta.type_ + '_' + field + tag,
                op=(Op, ...),
                ref=(RefRel[Literal[self.resource_model.Meta.type_], Literal[rel_resource.Meta.type_]], ...),
                data=(rel_data, ...)
            ))

            # 相关资源
            if not rel.modify:  # 如果关系资源不允许在这里被修改，则不生成schema
                continue
            rel_data = ApiDataModelRequest[Literal[rel_resource.Meta.type_],
                                           Dict, rel_model]
            # 模型名称 = 资源+操作符 + 资源类型 +关系无定义+这部分可自定义用来区分不同模型(主资源+关系资源属性名)+资源命名方式
            model.append(create_model('resources_' +
                                      'op[add,update]_' +
                                      rel_resource.Meta.type_ +
                                      '_any' +
                                      '_' +
                                      self.resource_model.Meta.type_ +
                                      field +
                                      '_' +
                                      tag, op=(Op, ...), data=(rel_data, ...,)))
        # rel_identifier_model = self.create_rel_identifier_model()
        data = ApiDataModelRequest[Literal[self.resource_model.Meta.type_],
                                   self.relationship_model, self.create_resquest_attribute_model()]
        # 模型名称= 资源+ 操作符  + 资源类型+关系无定义 +这部分可自定义用来区分不同模型
        model.append(create_model(

            'resources_' + 'op[add,update]_' +
            self.resource_model.Meta.type_ + '_any' + '_' + tag,  # 资源命名方式
            op=(Op, ...),
            data=(
                data,
                ...,
            )
        ))
        # 删除模型
        if 'DELETE' in ops:
            model.append(ResourcesRemoveModel[Literal['remove']])

        return create_model(
            model_name,
            operations=(List[Union[tuple(model)]], None)
        )

    def validation(self):
        for rel in self.resource_model.rel_resources().values():
            if rel.mapping_field and rel.mapping_field not in self.resource_model.model.__fields__:
                raise Exception('关系映射字段%s不在模型字段%s中' %
                                (rel.mapping_field, self.resource_model.model))
