#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
filter 过滤模块

"""
import enum
from typing import Union, Generic, TypeVar, Type, Dict, Optional, List
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
from pydantic import BaseModel, create_model
from pydantic.generics import GenericModel
from enum import Enum
from datetime import datetime


class FilterBase(str, Enum):
    # 过滤操作符基类
    eq = 'eq'


class NumberFilter(str, Enum):
    # 数值型可用操作符
    eq = 'eq'
    gt = 'gt'
    gte = 'gte'
    lte = 'lte'
    lt = 'lt'
    ne = 'ne'
    bt = 'bt'
    in_ = 'in_'
    isnull = 'isnull'
    isnotnull = 'isnotnull'


class FloatFilter(str, Enum):
    # float可用操作符
    eq = 'eq'
    gt = 'gt'
    gte = 'gte'
    lte = 'lte'
    lt = 'lt'
    bt = 'bt'


class StringFilter(str, Enum):
    # 字符型可用操作符
    ct = 'ct'
    sw = 'sw'
    ew = 'ew'
    eq = 'eq'
    in_ = 'in_'
    ne = 'ne'
    isnull = 'isnull'
    isnotnull = 'isnotnull'


class ListFilter(str, Enum):
    # 列表型可用操作符
    eq = 'eq'    # 包含在list中，多个值时，任何一个值在数组中，这条数据被过滤出来
    ne = 'ne'    # 不包含在list中
    em = 'em'    # list 为空
    nem = 'nem'  # list 不为空
    cts = 'cts'  # 前端以逗号传入的一个或多个值都包含在此列表中，这条数据被过滤出来。
    aeq = 'aeq'  # 列表的全等操作。不同于ct。当给定数组完全等同于时返回。例： [1,2] aeq [1,2]
    ct = 'ct'  # 包含在list中，多个值时，任何一个值在数组中，这条数据被过滤出来, 例: 1 ct[1,2]
    act = 'act'  # 代表给定值包含在list中，比如[1,2] act [1,2,3]

class DatetimeFilter(str, Enum):
    # 时间型可用操作符
    eq = 'eq'
    gt = 'gt'
    gte = 'gte'
    lt = 'lt'
    lte = 'lte'
    bt = 'bt'


class BoolFilter(str, Enum):
    # 布尔型可用操作符
    eq = 'eq'


OperatorT = TypeVar('OperatorT')
ValueT = TypeVar('ValueT')


class FilterDemo(GenericModel, Generic[OperatorT, ValueT]):
    # 过滤参数模型
    op: OperatorT
    value: ValueT


def create_filter_model(
        model_name: str,
        # fields: Dict[str, ModelField]
        fields: Dict[str, type]
) -> Type[BaseModel]:
    """
    创建过滤模型
    Args:
        model_name: 模型名称
        fields: 属性
    Returns: 过滤模型
    """

    params = dict()

    # for name, value in fields.items():
    #     print(name, value._type_display(), value.type_, value.outer_type_, value._type_analysis())
    #     print(isinstance(value.type_, int))
    #     if hasattr(value.type_, 'Config'):
    #         continue
    #     if value._type_display() == 'Optional[int]' or value._type_display() == 'int' or value._type_display():
    #         params[name] = (FilterDemo[NumberFilter, Union[int, str]], None)
    #     elif value._type_display() == 'Optional[str]' or value._type_display() == 'str':
    #         params[name] = (FilterDemo[StringFilter, value.type_], None)
    #     elif value._type_display() == 'Optional[enum]':
    #         params[name] = (FilterDemo[StringFilter, Union[value.type_, str]], None)
    #     elif value._type_display() == 'Optional[datetime]':
    #         params[name] = (FilterDemo[DatetimeFilter, Union[datetime, str]], None)
    #     elif value.outer_type_ == 'Optional[bool]' or value._type_display() == 'bool':
    #         params[name] = (FilterDemo[BoolFilter, value.type_], None)
    #     elif value._type_display() == 'Union[int, str]':
    #         params[name] = (FilterDemo[NumberFilter, Union[int, str]], None)
    #     elif value._type_display() == 'Optional[List[str]]':   # 可为空，所以用Optional
    #         params[name] = (FilterDemo[ListFilter, Optional[value.type_]], None)
    #     elif value._type_display() == 'Optional[List[enum]]':
    #         params[name] = (FilterDemo[ListFilter, Union[value.type_, str]], None)
    #     elif value._type_display() == 'Optional[List[UUID]]':
    #         params[name] = (FilterDemo[FilterBase, Union[value.type_, str]], None)
    #     else:
    #         params[name] = (FilterDemo[StringFilter, Union[value.type_, str]], None)
    for name, type_ in fields.items():

        # if hasattr(value.type_, 'Config'):
        #     continue
        if type_ == int:
            params[name] = (FilterDemo[NumberFilter, Union[int, str]], None)
        elif type_ == float:
            params[name] = (FilterDemo[FloatFilter, Union[int, str]], None)
        elif type_ == str:
            params[name] = (FilterDemo[StringFilter, type_], None)
        elif type_ == enum or type_.__class__ == enum.EnumMeta:
            params[name] = (FilterDemo[StringFilter, Union[type_, str]], None)
        elif type_ == datetime:
            params[name] = (FilterDemo[DatetimeFilter, Union[datetime, int, str]], None)
        elif type_ == bool:
            params[name] = (FilterDemo[BoolFilter, Union[str, type_]], None)
        elif type_ == bytes:
            params[name] = (FilterDemo[StringFilter, Union[str,type_]], None)
        elif type_ == List[str] or type_ == List:
            params[name] = (FilterDemo[ListFilter, Optional[str]], None)
        elif type_ == Union[int, str]:
            params[name] = (FilterDemo[NumberFilter, Union[int, str]], None)
        else:
            params[name] = (FilterDemo[StringFilter, Union[type_, str]], None)
    model = create_model(
        model_name,
        **params
    )
    return model


if __name__ == '__main__':
    from pydantic.utils import PyObjectStr
    print(PyObjectStr('Optional[str]'))