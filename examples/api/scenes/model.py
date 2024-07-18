#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List
from fastapi_jsonapi import SchemaBase
from fastapi_jsonapi.field import Field
from typing import Dict, Union, List
from fastapi_jsonapi.field import Field


# 公共场景
class PubSceneModel(SchemaBase):
    id: str = Field(None, title='ID')
    event: str = Field(None, title='用车事件')
    affect: str = Field(None, title='影响')
    dem: str = Field(..., title='用户需求')
    usage: List[str] = Field(..., title='用途', isrel=True)
    user: List[str] = Field(..., title='利益相关者', isrel=True)
    journey: str = Field(..., title='journey', isrel=True)
    inten: str = Field(..., title='用户意图分类', isrel=True)
    # func: str = Field(None, title='function')
    variable: List[str] = Field(None, title='变量', isrel=True)
    task: str = Field(None, title='项目', isrel=True)
    taskscene: str = Field(None, title='项目场景', isrel=True)
    uid: str = Field(..., title='当前版本修改人', isrel=True,  onlyread=True)
    like: List[str] = Field(None, title='点赞', isrel=True,  onlyread=True)
    favorite: List[str] = Field(None, title='收藏', isrel=True, onlyread=True)
    comment: List[str] = Field(None, title='评论', isrel=True,  onlyread=True)
    taskscenequote: List[str] = Field(None, title='引用项目场景', isrel=True, onlyread=True)
    history: List[str] = Field(None, title='历史版本', isrel=True, onlyread=True)
    ver: str = Field(None, title='版本号')
    mine: str = Field(None, title='是否用户自己', onlyread=True, isrel=True)
    matter: List[str] = Field(None, title='素材', isrel=True)
    uptime: int = Field(None, title='更新时间')
    image: str = Field(None, title='图片', onlyread=True, isrel=True)
    hot: str = Field(None, title='热度', onlyread=True)
    edit: List[str] = Field(None, title='参与编辑者', onlyread=True, isrel=True)
    ufavorite: List[str] = Field(None, title='已收藏人', ishide=True)
    ulike: List[str] = Field(None, title='点赞人', ishide=True)
    ucomment: List[str] = Field(None, title='评论人', ishide=True)
    extend: dict = Field(None, title='扩展', ishide=True)


class PubImageModel(SchemaBase):
    id: str = Field(None, title='ID')
    url: str = Field(None, title='url')


# 用途
class UsageModel(SchemaBase):
    id: str = Field(None, title='ID')
    name: str = Field(..., title='名称', min_length=1)
    desc: str = Field(None, title='描述')
    order: int = Field(None, title='排序')
    uid: str = Field(None, title='操作人id', ishide=True)
    uptime: int = Field(None, title='更新时间')
    mine: str = Field(None, title='是否用户自己', onlyread=True, isrel=True)
    user: Union[List, Dict] = Field(None, title='user', onlyread=True, isrel=True)
    journey: Union[List, Dict] = Field(None, title='journey',onlyread=True, isrel=True)
    event: Union[List, Dict] = Field(None, title='事件', onlyread=True, isrel=True)
    demand: Union[List, Dict] = Field(None, title='需求', onlyread=True, isrel=True)
    matter: Union[List, Dict] = Field(None, title='相关素材', onlyread=True, isrel=True)
    pubscene: Union[List, Dict] = Field(None, title='相关公共场景', onlyread=True, isrel=True)
    inten: Union[List, Dict] = Field(None, title='需求层级', onlyread=True, isrel=True)


# 利益相关者
class UserModel(SchemaBase):
    id: str = Field(None, title='ID')
    name: str = Field(..., title='名称', min_length=1)
    desc: str = Field(None, title='描述')
    order: int = Field(None, title='排序')
    uptime: int = Field(None, title='更新时间')
    uid: str = Field(None, title='操作人id', ishide=True)
    mine: str = Field(None, title='是否用户自己', onlyread=True, isrel=True)
    usage: Union[List, Dict] = Field(None, title='usage', onlyread=True, isrel=True)
    journey: Union[List, Dict] = Field(None, title='journey', onlyread=True, isrel=True)
    event: Union[List, Dict] = Field(None, title='事件', onlyread=True, isrel=True)
    demand: Union[List, Dict] = Field(None, title='需求', onlyread=True, isrel=True)
    matter: Union[List, Dict] = Field(None, title='相关素材', onlyread=True, isrel=True)
    pubscene: Union[List, Dict] = Field(None, title='相关公共场景', onlyread=True, isrel=True)
    inten: Union[List, Dict] = Field(None, title='需求层级', onlyread=True, isrel=True)



