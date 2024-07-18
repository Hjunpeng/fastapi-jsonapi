#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any, Type, Dict

# 资源名和类的映射
registered_resources = {}  # type: Dict[str, Type[Any]]


class RegisteredResourceMeta(type):
    """
    在字典中注册资源类，使其可访问动态地通过类名。
    默认情况下注册类，除非``register_resource=False``
    """
    def __new__(mcs, name, bases, attrs):
        klass = super().__new__(mcs, name, bases, attrs)

        # 默认注册类，除非在类级别指定“register_resource=False”
        if attrs.get('register_resource', True):
            registered_resources[name] = klass
        return klass
