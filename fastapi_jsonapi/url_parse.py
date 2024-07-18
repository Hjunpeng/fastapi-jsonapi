#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""deepobject 形式的 url和参数 解析
urlencode() 将字典转换成deepobject 形式的 url
query_parse() 解析deepobject 形式的 url 成python字典
"""
import re
from urllib import parse
from jquery_unparam import merge_structs


def flat_key(layer):
    """ 例: flat_key(["1","2",3,4]) -> "1[2][3][4]" """
    if len(layer) == 1:
        return layer[0]
    else:
        _list = ["[{}]".format(k) for k in layer[1:]]
        return layer[0] + "".join(_list)


def flat_dict(_dict: dict):
    """
    将嵌套字典转成单层字典。
    例：
         {'name':{'op': 'ct', 'value': '车'}}
         -> {'name[op]': 'ct', 'name[value]': '车'}
    Args:
        _dict: 字典
    Returns:
        单层字典
    """
    if not isinstance(_dict, dict):
        raise TypeError("argument must be a dict, not {}".format(type(_dict)))

    def __flat_dict(pre_layer, value):
        result = {}
        for k, v in value.items():
            layer = pre_layer[:]
            layer.append(k)
            if isinstance(v, dict):
                result.update(__flat_dict(layer, v))
            else:
                result[flat_key(layer)] = v
        return result
    return __flat_dict([], _dict)


def bool_to_str(_dict: dict):
    # 参数值为布尔类型，转换成小写字符串
    for key, value in _dict.items():
        if isinstance(value, bool):
            _dict[key] = str(value).lower()
    return _dict


def urlencode(_dict: dict):
    """将字典转换成deepobject 形式的 url
    Args:
        _dict: 查询参数的字典形式，
    Returns:
        url字符串
    """
    url_str = parse.urlencode(bool_to_str(flat_dict(_dict)), doseq=True)
    return parse.quote(url_str)


def parse_key_pair(keyval):
    """
    参考
    Args:
        keyval: jquery_unparam.parse_key_pair
        处理有 [] 的deepobject的情况

    Returns:

    """

    key, val = keyval

    if key == '':
        return {}

    groups = re.findall(r"\[.*?\]", key)
    groups_joined = ''.join(groups)
    if key[-len(groups_joined):] == groups_joined:
        key = key[:-len(groups_joined)]
        for group in reversed(groups):
            if group == '[]':
                val = [val]
            else:
                val = {group[1:-1]: val}
    return {key: val}


def query_parse(parmas: str) -> dict:
    """
    使用qs 解析参数，但是无法解析deepobject类，只能解析到第一层，参考jquery_unparam 的处理方法，解析deepobject
    Args:
        parmas:
    Returns:
        查询参数
    """

    qsl = parse.parse_qsl(parmas)
    key_pairs = [parse_key_pair(x) for x in qsl]
    p = merge_structs(key_pairs)
    return p


if __name__ == '__main__':
    # filter = {
    #      'count':{'op': 'gt', 'value': 2},
    #      'user.name':{'op': 'ct', 'value': '家人'}
    #      }
    filter = {
        "dim.id": {"op": "aeq", "value": "['331','53'],['53']"}
        }
    fields = {
        'dem': {'op': 'ct', 'value': '用户'},
        'usage.id': {'op': 'eq', 'value': 'EeyZ-yD9VeObSGySv6EbOA'}
    }
    include = 'user,usage.usage'
    v = urlencode(filter)
    print(v)
    print(query_parse('pri.name%255Bop%255D%3Dct%26pri.name%255Bvalue%255D%3Dfkshd%26title%255Bop%255D%3Dct%26title%255Bvalue%255D%3D%25E5%25AE%25B6%25E4%25BA%25BA'))
