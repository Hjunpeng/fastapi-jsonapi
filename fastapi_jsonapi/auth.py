import abc
import math
from typing import List
from fastapi import Security, routing, Depends, Request
from pydantic import BaseModel, Field
from fastapi.security import SecurityScopes, OAuth2PasswordBearer
from treelib import Tree, Node
from bitarray import bitarray
from bitarray.util import ba2base, base2ba
from fastapi_jsonapi.meta import registered_resources
from fastapi_jsonapi.exception import QureyError
from fastapi.dependencies.utils import get_parameterless_sub_dependant


class ScopeTree:
    def __init__(self, project_scopes: List[dict]) -> None:
        self.project_scopes = project_scopes
        self.scope_dict = {}
        self.scope_tree = Tree()

        for scope in project_scopes:
            self.scope_dict[scope["scope"]] = scope["id"]
            node = Node(data=scope["scope"],
                        tag=scope["name"],
                        identifier=scope["id"])
            if scope["pid"] is not None:
                self.scope_tree.add_node(node, parent=scope["pid"])
            else:
                self.scope_tree.add_node(node)

    def scopes(self):
        scopes = {}
        for scope in self.project_scopes:
            scopes.update({scope['scope']: scope['name']})
        return scopes

    def sub(self, tag: str) -> list:
        sub = []
        nodeid = self.scope_dict[tag]
        children = self.scope_tree.children(nodeid)
        for child in children:
            childlist = self.sub(child.data)
            sub.append(child.data)
            sub = sub + childlist
        return sub

    def children(self, tags: list) -> list:
        family = []
        for node in tags:
            family.append(node)
            family = family + self.sub(node)
        family = list(set(family))
        return family

    def to_base(self, checked: list) -> str:
        family = []
        for node in checked:
            family.append(node)
            family = family + self.sub(node)
        family = list(set(family))
        ba_len = math.ceil(len(self.scope_dict) / 6) * 6
        ba = bitarray(ba_len)
        ba.setall(0)
        for item in self.scope_dict:
            if item in family:
                ba[self.scope_dict[item]] = 1
        return str(ba2base(64, ba))

    def to_sope(self, ba_str: str) -> list:
        ba = base2ba(64, ba_str)
        scopes = []
        for item in self.scope_dict:
            index = self.scope_dict[item]
            if index <= len(ba) - 1 and ba[index]:
                scopes.append(item)
        return scopes


class User(BaseModel):
    id: str = Field(..., title='id')
    name: str = Field(None, title='姓名')
    headimage: str = Field(None, title='头像')
    token: str = Field(None, title='token')
    scope: List[str] = Field(None, title='scope')


class Auth(metaclass=abc.ABCMeta):
    """权限验证基类"""

    def __init__(self, cert, token_url: str = None, scopes: List[dict] = None):
        self.cert = cert
        self.token_url = token_url
        self.scope_tree = ScopeTree(scopes)
        self.user = None

    def _scopes(self) -> dict:
        # 项目全部的scopes集合
        return self.scope_tree.scopes()

    def _oauth(self) -> OAuth2PasswordBearer:
        # 权限依赖
        oauth2_scheme = OAuth2PasswordBearer(
            tokenUrl=self.token_url,
            scopes=self._scopes(),
        )

        return oauth2_scheme

    def scope(self, ba_str) -> list:
        """
        64位的scope字符串转成列表
        :param ba_str: 64进制字符串
        :return: token中的scope对应的列表
        """
        return self.scope_tree.to_sope(ba_str)

    @abc.abstractmethod
    async def auth(self, security_scopes: SecurityScopes,
                   token: str) -> User:
        """子类必须实现，权限验证方法"""
        raise NotImplementedError


class SecurityConfig(Auth):
    """权限安全配置"""

    def __init__(self, api_scopes: dict, cert: str, token_url: str = None, scopes: List[dict] = None):

        super().__init__(cert, token_url, scopes)
        self.api_scopes = api_scopes
        self.res = None

    def get_scopes(self, api_url, method):
        """
        获取接口方法对应scope
        Args:
            api_url: api链接
            method: 方法

        Returns: scope

        """
        api = self.api_scopes.get(api_url)
        if not api:
            return None
        scope = api.get(method, None)
        return scope

    async def api_auth(self, api_url, method) -> bool:
        """
        判断用户有没有接口权限
        Args:
            api_url: 接口url
            method: 接口方法

        Returns:bool

        """
        api_scope = self.get_scopes(api_url=api_url, method=method)
        if self.user and self.user.scope:
            user_scope = self.user.scope
        else:
            user_scope = []
        if set(api_scope).intersection(set(user_scope)):
            auth = True
        else:
            auth = False
        return auth

    def _get_auth(self, res):
        """
        生成权限判断函数
        Args:
            res: 资源

        Returns:

        """
        async def wrapper(
                request: Request,
                security_scopes: SecurityScopes,
                token: str = Depends(self._oauth())
        ) -> User:
            # include中关系的关系权限判断
            if request.query_params.get('include'):
                for include in request.query_params.get('include').split(','):
                    if include.count('.') == 1:
                        rel_name, relrel_name = include.split('.')
                        path_parma = request.scope.get('path').split('/')
                        if 'id' in request.path_params and request.path_params.get('id') == path_parma[-2]:
                            res_temp = res.rel_resources()
                            rel_res_temp = res_temp[request.scope.get('path').split('/')[-1]]
                            rel_resource = registered_resources.get(rel_res_temp.rel_resource)
                            rels = rel_resource.rel_resources()
                        else:
                            rels = res.rel_resources()
                        if rel_name not in rels:
                            raise QureyError(
                                detail='include 参数 %s 不存在' % (rel_name))
                        rel_res = rels[rel_name]
                        rel_resource = registered_resources.get(rel_res.rel_resource)
                        rel_rels = rel_resource.rel_resources()
                        if relrel_name not in rel_rels:
                            raise QureyError(
                                detail='include 参数 %s 不存在' % (relrel_name))
                        relrel_res = registered_resources.get(rel_rels[relrel_name].rel_resource)
                        scope = self.get_scopes(api_url=relrel_res.Meta.link,
                                                 method='GET')
                        await self.auth(security_scopes=SecurityScopes(scopes=scope), token=token)

            user = await self.auth(security_scopes, token)
            self.user = user
            return user
        return wrapper

    def run(self, res):
        """
        app路由添加权限验证
        Args:
            res: FastApi
            auth: 权限

        Returns:

        """
        for route in res.route.routes:
            api_url = route.path_format[len(res.prefix):]  #  route.path_format里有prefix，查找时在前面去除掉
            scopes = self.get_scopes(api_url=api_url,
                                      method=list(route.methods)[0])
            if scopes:
                if isinstance(route, routing.APIRoute):
                    route.dependant.dependencies.insert(
                        0,
                        get_parameterless_sub_dependant(depends=Security(self._get_auth(res),
                                                                         scopes=scopes), path=route.path_format),
                    )
        return res
