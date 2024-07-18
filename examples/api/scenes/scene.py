#!/usr/bin/env python3
# -*- coding=utf-8 -*-

"""
"""
from typing import List
from fastapi_jsonapi.resource import BaseResource, Request, JsonapiException
from fastapi_jsonapi.resource import SchemaBase, Relationship
from fastapi_jsonapi.field import Field
from uuid import UUID
from fastapi_jsonapi.query import Filters, Sort



class UserAuthModel(SchemaBase):
    id: str = Field(None, title='ID')
    name: str = Field(None, title='名称')

    class Meta:
        type_ = 'user'

class UserAuthRes(BaseResource):
    link = 'user'
    model = UserAuthModel

    @classmethod
    async def before_request(cls, request: Request):
        # token = await OAuth2PasswordBearer(tokenUrl='url').__call__(request)
        #解析token获取用户id
        uid = 1
        #检查用户权限
        user = cls(request).get_many(id=uid)

        # user = None
        if not user:
            raise JsonapiException(status_code=401, detail='无权限')
        return user


    def get_many(self, **kwargs) ->List[UserAuthModel]:

        return [UserAuthModel(id='1',
                        name='test',
                        )]




class UserModel(SchemaBase):
    id: UUID = Field(None, title='ID')
    name: str = Field(None, title='名称')
    order: str = Field(None, title='排序')
    parent_id: UUID = Field(None, title='ID')

    class Meta:
        type_ = 'user'
        link = 'scenes/user'


class UserParent(BaseResource):
    model = UserModel
    # link = 'user'


    def get_many(self, **kwargs) -> List[UserModel]:
        return [UserModel(id='11ebf5c7-ef53-38e3-9df5-6c92bfa11b38',
                    name='自用',
                    order='398',
                    parent_id=None,
                    )
                 ]


class User(UserParent):
    # link = 'user'
    model = UserModel

    class RelResources:
        usage_rel = Relationship(rel_resource=UserParent, mapping_field='parent_id', show_link=False)

    def get_many(self, **kwargs):

        return [UserModel(id='11ebf5d7-430d-ce0e-9df5-6c92bfa11b38',
                        name='车主',
                        order='1',
                        parent_id='11ebf5c7-eeb6-6f5a-9df5-6c92bfa11b38',
                        ),
                UserModel(id='11ebf5c7-a9d4-dc60-9df5-6c92bfa11b38',
                           name='朋友',
                           order='2',
                           parent_id='11ebf5c7-ef53-38e3-9df5-6c92bfa11b38',
                           ),
                ]




class UsageModel(SchemaBase):
    id: UUID = Field(None, title='ID')
    name: str = Field(None, title='名称')
    order: str = Field(None, title='排序')
    parent_id: UUID = Field(None, title='ID')

    class Meta:
        type_ = 'usages'
        link = 'scenes/usages'


class UsageParent(BaseResource):
    model = UsageModel
    # link = 'usages'


    def get_many(self, **kwargs):

        return [UsageModel(id='11ebf5c7-ef53-38e3-9df5-6c92bfa11b38',
                    name='创新',
                    order='398',
                    parent_id=None,
                    ),
                 UsageModel(id='11ebf5c7-eeb6-6f5a-9df5-6c92bfa11b38',
                            name='独特',
                            order='444',
                            parent_id=None,
                            ),
                 ]


class Usage(UsageParent):
    # link = 'usage'
    model = UsageModel

    class RelResources:
        usage_rel = Relationship(rel_resource=UsageParent, mapping_field='parent_id', show_link=False)

    def get_many(self, **kwargs):
        args = self.get_args()

        return [UsageModel(id='11ebf5d7-430d-ce0e-9df5-6c92bfa11b38',
                        name='off-road',
                        order='1',
                        parent_id='11ebf5c7-eeb6-6f5a-9df5-6c92bfa11b38',
                        ),
                UsageModel(id='11ebf5c7-a9d4-dc60-9df5-6c92bfa11b38',
                           name='ADAS',
                           order='2',
                           parent_id='11ebf5c7-ef53-38e3-9df5-6c92bfa11b38',
                           ),
                ]


class PriModel(SchemaBase):
    id: UUID = Field(None, title='一级场景ID')
    name: str = Field(None, title='名称', inmany=True)
    userid: UUID = Field(None, title='利益相关者')
    usageid: UUID = Field(None, title='用途')
    count: int = Field(None, title='对应三级场景数量统计', onlyget=True)

    class Meta:
        type_ = 'pri'
        link = '/scenes/pri'


class ScenesPri(BaseResource):
    model = PriModel
    # link = 'scenes/pri'
    limit = 300
    sortby = '-name'

    required = [UserAuthRes]

    class RelResources:
        usage = Relationship(rel_resource=Usage, mapping_field='usageid', show_link=True, modify=False, has_api=True, required=True)
        user = Relationship(rel_resource=User,  mapping_field='userid', show_link=True, modify=False, has_api=True, required=False)


    def get_many(self, **kwargs) -> List[PriModel]:

        args = self.get_args()
        # print(3333, args.__dict__)
        # print(333, args.sort[0].__dict__)


        def get_many(filter: Filters, skip: int, limit: int, sort: List[Sort]):
            return [PriModel(id='11ebf5d7-430d-ce0e-9df5-6c92bfa11b38',
                        userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b38',
                        usageid='11ebf5c7-a9d4-dfb0-9df5-6c92bfa11b38',
                         name = None,
                        count='273',
                        ),
                PriModel(id='11ebf5d7-430d-c291-9df5-6c92bfa11b38',
                         userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b37',
                         usageid='11ebf5c7-a9d4-dc60-9df5-6c92bfa11b38',
                         name = 'cc',
                         count=None,
                         )
                    ]

        db_data = get_many(filter=args.filter, skip=args.skip, limit=args.limit, sort=args.sort)

        #数据转换
        user = UserAuthRes(self.request)
        user = user.get_many()

        return db_data

    def get(self):

        return PriModel(id='11ebf5d7-430d-ce0e-9df5-6c92bfa11b38',
                        userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b38',
                        usageid='11ebf5c7-a9d4-dfb0-9df5-6c92bfa11b38',
                        count='273',
                        )

    def post(self, **kwargs):

        def insert(param):
            data = PriModel(id='11ebf5d7-430d-c291-9df5-6c92bfa11b35',
                         userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b35',
                         usageid='11ebf5c7-a9d4-dc60-9df5-6c92bfa11b35',
                         count='273',
                         )
            return data

        param = self.parse_body()
        #入库
        print(3333333, param)
        data = insert(param)
        return data


    def patch(self, **kwargs):
        print(3333333, self.parse_body())
        def update(param):
            data = PriModel(id='11ebf5d7-430d-c291-9df5-6c92bfa11b35',
                         userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b35',
                         usageid='11ebf5c7-a9d4-dc60-9df5-6c92bfa11b35',
                         count='273',
                         )
            return data

        param = self.parse_body()
        #入库
        data = update(param)
        return data

    def delete(self, **kwargs):
        data = PriModel(id='11ebf5d7-430d-c291-9df5-6c92bfa11b77',
                         userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b35',
                         usageid='11ebf5c7-a9d4-dc60-9df5-6c92bfa11b35',
                         count='273',
                         )
        return data


class SceneSec(SchemaBase):
    priid: UUID = Field(None, title='所属一级场景')
    journey: UUID = Field(None, title='二级场景分类')
    secid: UUID = Field(None, title='二级场景ID')
    secname: str = Field(None, title='二级场景名称')
    count: int = Field(None, title='对应三级场景数量统计')
    order: int = Field(None, title='排序')

class ScenesSec(BaseResource):
    model = SceneSec
    link = 'sec'

    class RelResources:
        pri = Relationship(rel_resource=ScenesPri, mapping_field='priid', show_link=True, modify=False, required=True)

    def primary_data(self):
        pass


class Scenes(BaseResource):
    # link = 'scenes'
    childs = [ScenesPri]


if __name__ == '__main__':
    # print(Pri.rel_resource()[0].router())
    from pydantic import create_model

    # model_field = {}
    # # for key,item in PriModel.__fields__.items():
    # #     if not item.field_info.onlyget:
    # #         model_field[key] = item
    # # print(model_field)
    # #
    # # Nww = create_model('s')
    # # Nww.__fields__ = model_field
    # # print(Nww.__fields__)
    # print(PriModel.request_model())
    # data = PriModel(username='ss')
    # d = 'username'
    # print(data.__getattribute__(d))
    # a = PriModel(id='11ebf5d7-430d-ce0e-9df5-6c92bfa11b38',
    #          userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b38',
    #          usageid='11ebf5c7-a9d4-dfb0-9df5-6c92bfa11b38',
    #          name=None,
    #          count='273',
    #          )
    data1 = [PriModel(id='11ebf5d7-430d-ce0e-9df5-6c92bfa11b38',
             userid='11ebf5c7-a9db-bd9d-9df5-6c92bfa11b38',
             usageid='11ebf5c7-a9d4-dfb0-9df5-6c92bfa11b38',
             count='273',
             )]
    data = PriModel()
    r = [data.from_orm(data) for data in data1]
    print(r)

