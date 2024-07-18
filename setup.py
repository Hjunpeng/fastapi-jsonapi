#!/usr/bin/env python3
# -*- coding=utf-8 -*-

"""
"""

from setuptools import setup, find_packages


setup(
    name="fastapi-jsonapi",
    version="0.1.0",
    author="so.car",
    author_email="socar@so.car",
    description="Api架构框架",
    install_requires=['fastapi==0.92.0', 'jquery-unparam', 'PyYAML', 'treelib', 'bitarray', 'python-multipart'],

    # 项目主页
    url="https://gitee.com/socar/api_frame",

    # 你要安装的包，通过 setuptools.find_packages 找到当前目录下有哪些包
    packages=find_packages()
)
