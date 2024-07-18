#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字段
"""
from typing import Any
from pydantic.fields import FieldInfo, Undefined


class Field(FieldInfo):
    """模型默认字段属性， 提供额外信息。
    与pydantic的field相比，增加了:
        onlyread: 标明此字段是否只读
        onlywrite：标明此字段是否只写
        inmany: 在资源列表中是否显示。=true显示
        ishide: 是否不在schema模型中隐藏。例如用户id,在响应模型中不需要，只在接口和数据库交互时使用。可置ishide=true
        isrel: 是否作为关系，默认否
    """
    __slots__ = (
        'default',
        'default_factory',
        'alias',
        'alias_priority',
        'title',
        'description',
        'exclude',
        'include',
        'const',
        'gt',
        'ge',
        'lt',
        'le',
        'multiple_of',
        'allow_inf_nan',
        'max_digits',
        'decimal_places',
        'min_items',
        'max_items',
        'unique_items',
        'min_length',
        'max_length',
        'allow_mutation',
        'repr',
        'regex',
        'discriminator',
        'extra',
        'mapping',
        'onlyread',
        'inmany',
        'onlywrite',
        'ishide',
        'isrel'

    )

    def __init__(self, default: Any = Undefined, **kwargs: Any):
        super(Field, self).__init__(default=default, **kwargs)
        self.onlyread = kwargs.pop('onlyread', False)
        self.inmany = kwargs.pop('inmany', True)
        self.onlywrite = kwargs.pop('onlywrite', False)
        self.ishide = kwargs.pop('ishide', False)
        self.isrel = kwargs.pop('isrel', False)
        self.mapping = kwargs.pop('mapping', None)


class Email(Field):
    """
    邮箱
    """

    def __init__(self, default: Any = Undefined, **kwargs: Any):
        super(Email, self).__init__(default=default, **kwargs)
        self.regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"


class URL(Field):
    """
    url
    """

    def __init__(self, default: Any = Undefined, **kwargs: Any):
        super(URL, self).__init__(default=default, **kwargs)
        self.regex = r'^https?:/{2}\w.+$'

class Phone(Field):
    pass
