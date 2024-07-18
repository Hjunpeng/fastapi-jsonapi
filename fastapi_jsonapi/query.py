# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""查询 模块
"""
from typing import Dict, Any, List, Union, Optional
import ast
from uuid import UUID
from fastapi import Request
from fastapi_jsonapi.url_parse import query_parse
from fastapi_jsonapi.exception import QureyError
from fastapi_jsonapi.meta import registered_resources
from fastapi_jsonapi.util import get_default_args


class Sort():
    field: str
    asc: bool

    def __init__(self, field: str, asc: bool):
        """
        排序模型
        Args:
            field: 排序字段
            asc: 是否正序
        """
        self.field = field
        self.asc = asc


class Filter():
    field: str
    op: str
    value: Any

    def __init__(self, field, op, value):
        """
        查询过滤条件模型
        Args:
            field: 字段
            op: 操作符
            value: 值
        例：名称包含车 -》Filter(field='name',op='ct',value='车')
        """
        self.field = field
        self.op = op
        self.value = value


class Filters():
    filters: Union[List['Filters'], List[Filter]]
    op: str

    def __init__(self, filters: Union[List['Filters'], List[Filter]]):
        """过滤模型基类"""
        self.filters = filters

    def pop_and_filter(self, field) -> Optional[Filter]:
        """
        去除field对应的条件并返回结果，仅仅适用于当前数据是Filter组成的and条件数据，并且field在条件中唯一；
        若有多个field,仅pop第一个并返回。

        添加此功能的初始目的是为了解决前端传入条件中不适用于数据表中的筛选条件，
        需要把条件移除，在程序中根据条件另做筛选。
        :param field: 条件字段
        :return: 返回第一个条件 或 none
        """
        if not isinstance(self, FilterAnd):
            raise Exception('条件数据必须是and关系')

        for filter in self.filters:
            if not isinstance(filter, Filter):
                raise Exception('条件数据必须是Filter的and关系')
            if filter.field == field:
                self.filters.remove(filter)
                return filter

    def get_filter(self, field) -> Optional[Filter]:
        """
        获取条件
        :param field: 条件字段
        :return: value
        """
        if isinstance(self, FilterAnd):
            for filter in self.filters:
                if not isinstance(filter, Filter):
                    raise Exception('条件数据必须是Filter的and关系')
                if filter.field == field:
                    return filter
        elif isinstance(self, Filter):
            if self.field == field:
                return self
            else:
                return None
        else:
            raise Exception('filter必须是FilterAnd 或者Filter')

    def get_field_value(self, field) -> Optional[Filter]:
        """
        获取字段的条件值
        :param field: 条件字段
        :return: value
        """
        if isinstance(self, FilterAnd):
            for filter in self.filters:
                if not isinstance(filter, Filter):
                    raise Exception('条件数据必须是Filter的and关系')
                if filter.field == field:
                    return filter.value
        elif isinstance(self, Filter):
            if self.field == field:
                return self.value
            else:
                return None
        else:
            raise Exception('filter必须是FilterAnd 或者Filter')

    def __str__(self):
        def parse_filter(filter):
            if hasattr(filter, 'filters'):
                op = filter.op
                res = []
                for f in filter.filters:
                    res.append(parse_filter(f))
                return '( ' + op.join(res) + ') '
            else:
                if hasattr(filter, 'field'):
                    return ' (%s %s %s) ' % (filter.field, filter.op, filter.value)
                else:
                    return None
        filter_str = parse_filter(self)
        args_str = """筛选条件：%s""" % (filter_str)
        return args_str



class FilterAnd(Filters):
    """and操作"""
    op = 'and'


class FilterOr(Filters):
    """or操作"""
    op = 'or'


class ArgsModel():
    """
        查询参数模型
       Args:
           filter: 过滤参数
           sort: 排序参数
           skip: 分页skip
           limit: 分页limit
           include: include包含资源类型
           fields: 稀疏字段
    """
    filter: Union[Filter, Filters] = None
    sort: List[Sort]
    # relsort: List[Sort]
    skip: int = 0
    limit: Union[int, str] = 100
    include: List[str] = None
    fields: Dict[str, List[str]]
    q_data: List[str] = None
    warings: List[str] = None

    def __init__(self,
                 filter: Union[Filter, Filters] = None,
                 sort: List[Sort] = [Sort(field='id', asc=True)],
                 # relsort: List[Sort] = [Sort(field='id', asc=True)],
                 skip: int = 0,
                 limit: Union[int, str] = 100,
                 include: List[str] = [],
                 fields: Dict[str, List[str]] = None,
                 q_data: List[str] = [],
                 warnings: List[str] = []):

        self.filter = filter
        self.sort = sort
        # self.relsort = relsort
        self.skip = skip
        self.limit = limit
        self.include = include if include else []
        self.q_data = q_data if q_data else []
        self.fields = fields
        self.warings = warnings if warnings else []

    def add_filter_to_and(self, field, op, value) -> 'ArgsModel':
        """添加and条件"""
        if isinstance(self.filter, FilterAnd):
            self.filter.filters.append(
                Filter(field=field, op=op, value=value)
            )
        elif not self.filter:
            self.filter = FilterAnd(filters=[Filter(field=field, op=op, value=value)])
        return self

    def and_filters(self, filter: Union[Filters, Filter]) -> 'ArgsModel':
        """添加and条件"""
        if isinstance(self.filter, FilterOr):
            self.filter = FilterAnd(filters=[self.filter, filter])
        elif isinstance(self.filter, FilterAnd):
            self.filter.filters.append(filter)
        elif not self.filter or not self.filter.filters:
            self.filter = filter
        return self

    def or_filters(self, filter: Union[Filters, Filter]) -> 'ArgsModel':
        """添加or条件"""
        if isinstance(self.filter, FilterOr):
            self.filter.filters.append(filter)
        elif isinstance(self.filter, FilterAnd):
            self.filter = FilterOr(filters=[self.filter, filter])
        elif not self.filter or not self.filter.filters:
            self.filter = FilterOr(filters=filter)
        return self

    def pop_and_filter(self, field) -> Optional[Filter]:
        """
        去除field对应的条件并返回结果，仅仅适用于当前数据是Filter组成的and条件数据，并且field在条件中唯一；
        若有多个field,仅pop第一个并返回。

        添加此功能的初始目的是为了解决前端传入条件中不适用于数据表中的筛选条件，
        需要把条件移除，在程序中根据条件另做筛选。
        :param field: 条件字段
        :return: 返回第一个条件 或 none
        """
        if not self.filter:
            return None
        if not isinstance(self.filter, FilterAnd):
            raise Exception('条件数据必须是and关系')

        for filter in self.filter.filters:
            if not isinstance(filter, Filter):
                raise Exception('条件数据必须是Filter的and关系')
            if filter.field == field:
                self.filter.filters.remove(filter)
                return filter

    def get_field_value(self, field) -> Optional[Filter]:
        """
        获取字段的条件值
        :param field: 条件字段
        :return: value
        """
        if not self.filter:
            return None
        if isinstance(self.filter, FilterAnd):
            for filter in self.filter.filters:
                if not isinstance(filter, Filter):
                    raise Exception('条件数据必须是Filter的and关系')
                if filter.field == field:
                    return filter.value
        elif isinstance(self.filter, Filter):
            if self.filter.field == field:
                return self.filter.value
            else:
                return None
        else:
            raise Exception('filter必须是FilterAnd 或者Filter')

    def __str__(self):
        def parse_filter(filter):
            if hasattr(filter, 'filters'):
                op = filter.op
                res = []
                for f in filter.filters:
                    res.append(parse_filter(f))
                return '( ' + op.join(res) + ') '
            else:
                if hasattr(filter, 'field'):
                    return ' (%s %s %s) ' % (filter.field, filter.op, filter.value)
                else:
                    return None
        filter_str = parse_filter(self.filter)
        sort_str = ['%s%s' % (sort.field, '升序' if sort.asc else '降序') for sort in self.sort] if self.sort else ''
        args_str = """筛选条件：%s\npage[limit]:%s\npage[offset]:%s\n排序：%s\n""" % (filter_str,
                                                                              str(self.limit),
                                                                              str(self.skip),
                                                                              str(sort_str))
        return args_str


class ArgParse(object):

    """参数解析和验证
      接口端查询参数名称定义：
        sortby: 排序，
        filter: 筛选
        page[limit]: 分页页数
        page[offset]: 分页偏移量
        include：included包含类型
        fields：稀疏字段

      Args:
          model: 资源数据模型
      Returns:
          参数模型
    """

    def __init__(self, resource_model):
        self.resource_model = resource_model
        self.model = resource_model.model
        self.rel = resource_model.rel_resources()
        self.res_filter = resource_model.filter_model()
        self.list_warnings = []  # warning 类信息。
        self.args = ArgsModel()

    def _verify_arg(self, request):
        # 验证查询参数
        full_arg = get_default_args(request.scope.get('endpoint'))
        query_params = list(request.query_params.keys())  # 获取前端查询参数
        for param in query_params:
            if param not in full_arg:  # 判断是否在接口参数内
                raise QureyError(detail='参数 [%s] 错误' % param)
        return True

    async def _parse_rel_filter(self, filter: Filter):
        # 根据关系资源属性筛选
        rel_name, rel_field = filter.field.split('.')
        rel = self.rel.get(rel_name)
        # if rel_field == 'id':  # 如果是id, 直接对应模型的字段
        return Filter(op=filter.op, field=rel.mapping_field, value=filter.value)

        #
        # # 若是其他字段，根据字段条件查出符合条件的关系数据id
        # rel_resource = registered_resources.get(rel.rel_resource)
        # query_args = ArgsModel()
        # query_args.filter = Filter(op=filter.op, field=rel_field, value=filter.value)
        # rel_res = rel_resource(request=None, query_args=query_args)
        # mdata = await rel_res.connect_data(func=rel_res.get_many) # 关系数据的id
        # if mdata:
        #     value = tuple([str(data.id) if isinstance(data.id, UUID) else data.id for data in mdata])
        # else:
        #     value = None
        #
        # return Filter(op='eq', field=rel.mapping_field, value=value)

    async def verify_filter(self, request) -> None:
        """过滤验证解析
        Args:
            request: 请求
        Returns:
            None
        """

        filter_params_list = request.query_params.getlist('filter')
        filter_or = []
        for filter in filter_params_list:
            try:
                filter_params_dict = query_parse(filter)
            except Exception as e:
                raise QureyError(detail='参数解析失败,%s' % e)
            filters_and = []       # 过滤条件， and关系

            for field, filter in filter_params_dict.items():

                if field not in self.res_filter.__fields__:
                    raise QureyError(detail='不支持过滤参数：%s' % field)

                if 'op' not in filter:  # 操作符必须是op
                    raise QureyError(detail='操作符有误， 应该为op')
                operator = filter.get('op')
                value_temp = filter.get('value')

                if operator not in ('em', 'nem') and not value_temp:  # en, nem除外value 不可为空
                    raise QureyError(detail='筛选参数值value 不能为空')

                if operator in ('aeq', 'act') and '[' not in value_temp:
                    raise QureyError(detail='数组操作符是aeq代表全等， act代表全部包含在属性值中，value必须array格式，即类似[]的字符串')
                elif operator not in ('aeq', 'act') and '[' in value_temp:
                    raise QureyError(detail='筛选属性值为单个元素或其组合，不能用array格式')
                elif isinstance(value_temp, str) and '[' in value_temp:  # 如果是[]列表格式的，值转换
                    try:
                        value = ast.literal_eval(value_temp)
                    except BaseException:
                        raise QureyError(detail='请检查参数格式是否有误：%s' % value_temp)
                elif isinstance(value_temp, str) and ',' in value_temp:
                    value = tuple(value_temp.split(','))
                else:
                    value = value_temp
                    if value == 'true':
                        value = True
                    elif value == 'false':
                        value = False
                    else:
                        pass

                if operator == 'eq' and value == 'null':  # 为null 操作符转换
                    operator = 'isnull'
                # 过滤验证，将值代入过滤模型，利用pydantic的定义的字段来验证
                try:
                    self.res_filter.__fields__.get(field).type_(
                        op=operator, value=value_temp)
                except Exception as e:
                    raise QureyError(detail=str(e))

                # 这是一个临时判断list 数组类型不再使用eq操作符, 之后会废弃会废弃会废弃
                if 'ListFilter' in self.res_filter.__fields__.get(field).type_.__name__ and operator == 'eq':
                    self.args.warings.append('数组类不再支持操作符eq, 请在2023年9月1号之前将%s的操作符更改为ct' % field)

                # 根据关系资源属性筛选
                if '.' in field:
                    # 验证
                    filter = await self._parse_rel_filter(Filter(op=operator, field=field, value=value))
                else:
                    # value映射转换
                    value_mapping = self.model.__fields__.get(field).field_info.mapping
                    if value_mapping:
                        if isinstance(value, tuple):
                            value = [value_mapping(v) for v in value]
                        else:
                            value = value_mapping(value)
                    filter = Filter(op=operator, field=field, value=value)
                filters_and.append(filter)

            filter_or.append(FilterAnd(filters=filters_and))
        if len(filter_or) == 1:  # 现阶段只有and
            self.args.filter = filter_or[0]
        elif len(filter_or) == 0:
            self.args.filter = None
        else:
            self.args.filter = FilterOr(filters=filter_or)
        return self.args.filter

    def verify_sortby(self, request) -> None:
        """排序验证解析
        Args:
            request: 请求
        Returns:
            None
        """
        sortby_params_str = request.query_params.get(
            'sort', self.resource_model.sortby)
        if sortby_params_str:
            sort_list = sortby_params_str.split(',')

            sortby = []
            # relsort = False
            for sort in sort_list:
                if sort[0] == '-':
                    asc = False
                    sort = sort[1:]
                else:
                    asc = True

                if '.' in sort:
                    # relsort = True
                    if sort.count('.') > 1:
                        raise QureyError(
                            detail='只支持主资源属性排序和主资源的关系属性排序')

                    rel_name, rel_field = sort.split('.')
                    if rel_name not in self.rel:
                        raise QureyError(
                            detail='字段不存在，%s不能作为排序参数' %
                                   (sort))
                    rel_resource = registered_resources.get(self.rel[rel_name].rel_resource)
                    if rel_field not in rel_resource.model.__fields__:
                        raise QureyError(
                            detail='字段不存在，%s不能作为排序参数' %
                                   (sort))
                    else:
                        sortby.append(Sort(field=sort, asc=asc))
                else:
                    if sort not in self.model.__fields__:
                        raise QureyError(
                            detail='字段不存在，%s不能作为排序参数' %
                                   (sort))
                    sortby.append(Sort(field=sort, asc=asc))
            # if relsort:
            #     self.args.relsort = sortby
            # else:
            self.args.sort = sortby
            self.args.sort.append(Sort(field='id', asc=True))
        else:
            self.args.sort = None
        return self.args.sort

    def verify_page(self, request) -> tuple:
        """分页解析验证,
        Args:
            request: 响应
        Returns:
            None
         """
        offset_params = request.query_params.get(
            'page[offset]', self.resource_model.offset)
        limit_parmas = request.query_params.get(
            'page[limit]', self.resource_model.limit)

        self.args.skip = offset_params
        # if isinstance(limit_parmas, str) and limit_parmas != 'null':
        #     raise QureyError( detail='page[limit]不支持字符串%s, 只支持null' %(limit_parmas))
        if limit_parmas == 'null' and not self.resource_model.allow_all_pages:
            raise QureyError(detail='page[limit]不支持为null')
        self.args.limit = None if limit_parmas == 'null' and self.resource_model.allow_all_pages else limit_parmas
        if self.args.skip:
            try:
                int(self.args.skip)
            except BaseException:
                raise QureyError(detail='page[skip] 必须为数值型整数')

        if self.args.limit:
            try:
                int(self.args.limit)
            except BaseException:
                raise QureyError(detail='page[limit] 必须为数值型整数')

        return (self.args.skip, self.args.limit)

    def _verify_fields(self, request) -> None:
        """稀疏字段 解析验证
        Args:
            request: 响应
        Returns:
            None
        """
        # self.args['fields'] = dict()
        fields = {}
        fields_params_str = request.query_params.get('fields')
        if fields_params_str:
            fields_params_dict = query_parse(fields_params_str)
            for obj, field in fields_params_dict.items():
                fields_list = field.split(',')
                model = self.res.get(obj)
                if not model:
                    raise QureyError(detail='资源不存在：%s ' % (obj))
                for field in fields_list:
                    if not model.__fields__.get(field, None):
                        raise QureyError(detail='资源字段不存在：%s.%s' %
                                         (obj, field))
                fields[obj] = fields_list
        self.args.fields = fields

    def verify_include(self, request) -> tuple:
        """include 解析验证
        Args:
            request: 响应
        Returns:
            None
        """
        include_params_str = request.query_params.get('include')
        if include_params_str:
            include_fields = tuple(
                include_params_str.replace(
                    '-', '_').split(','))
            for include in include_fields:
                rel_name_list = include.split('.')
                if len(rel_name_list) > 3:
                    raise QureyError(
                        detail='include 最深支持 3层 关系查询')

                if rel_name_list[0] not in self.rel:
                    raise QureyError(
                        detail='include 参数 %s 不存在' % (include))
                if len(rel_name_list) == 1:
                    continue

                rel_resource = registered_resources.get(self.rel[rel_name_list[0]].rel_resource)
                relrel_source = rel_resource.rel_resources()
                if rel_name_list[1] not in relrel_source:
                    raise QureyError(
                        detail='include 参数 %s 不存在' % (include))
                if len(rel_name_list) == 2:
                    continue

                relrel_resource = registered_resources.get(relrel_source[rel_name_list[1]].rel_resource)
                relrelrel_source = relrel_resource.rel_resources()
                if rel_name_list[2] not in relrelrel_source:
                    raise QureyError(
                        detail='include 参数 %s 不存在' % (include))

            self.args.include = include_fields
        return self.args.include

    def verify_data(self, request) -> tuple:
        """include 解析验证
        Args:
            request: 响应
        Returns:
            None
        """
        params_str = request.query_params.get('_data')
        if params_str:
            q_data_fields = tuple(
                params_str.replace(
                    '-', '_').split(','))
            for q_data in q_data_fields:
                rel_name_list = q_data.split('.')
                if len(rel_name_list) > 3:
                    raise QureyError(
                        detail='include 最深支持 3层 关系查询')

                if rel_name_list[0] not in self.rel:
                    raise QureyError(
                        detail='include 参数 %s 不存在' % (q_data))
                if len(rel_name_list) == 1:
                    continue

                rel_resource = registered_resources.get(self.rel[rel_name_list[0]].rel_resource)
                relrel_source = rel_resource.rel_resources()
                if rel_name_list[1] not in relrel_source:
                    raise QureyError(
                        detail='include 参数 %s 不存在' % (q_data))
                if len(rel_name_list) == 2:
                    continue

                relrel_resource = registered_resources.get(relrel_source[rel_name_list[1]].rel_resource)
                relrelrel_source = relrel_resource.rel_resources()
                if rel_name_list[2] not in relrelrel_source:
                    raise QureyError(
                        detail='include 参数 %s 不存在' % (q_data))

            self.args.q_data = q_data_fields
        return self.args.q_data

    async def get_args(self, request: Request) -> ArgsModel:
        self.args_default = {}   # 参数默认值
        if not self._verify_arg(request):  # 验证查询参数
            return self.args
        await self.verify_filter(request)  # 验证filter参数
        self.verify_sortby(request)
        self.verify_page(request)
        self._verify_fields(request)
        self.verify_include(request)
        self.verify_data(request)

        return self.args


if __name__ == '__main__':
    filter1 = Filter(field='name', op='ct', value='c,g')
    filter2 = Filter(field='title', op='ct', value='d')
    filter3 = Filter(field='user.name', op='ct', value='d')

    filter11 = FilterOr(filters=[FilterAnd(filters=[filter1, filter2])])
    filter22 = FilterOr(filters=[FilterAnd(filters=[FilterOr(filters=[filter1, filter2]), FilterOr(filters=[filter3])]),
                                 FilterAnd(filters=[filter1, filter2, filter3])])

    filter33 = FilterAnd(filters=[filter1])

    def parse_filter(filter):
        if hasattr(filter, 'filters'):
            op = filter.op
            res = []
            for f in filter.filters:
                res.append(parse_filter(f))
            return '( ' + op.join(res) + ') '
        else:
            return ' (%s %s %s) ' % (filter.field, filter.op, filter.value)

    # filter33.filters.append(filter3)
    res = parse_filter(filter22)
    print(res)

    a = ArgsModel(filter=filter33)
    print(a.filter.filters)
    # res = parse_filter(a.filter)
    # print(res)
    # a.add_filter_to_and(field='name', op='ct', value='s')
    # print(a.filter.filters)
    # res = parse_filter(a.filter)
    # print(res)
    #
    # b = ArgsModel()
    # b.add_filter_to_or()
