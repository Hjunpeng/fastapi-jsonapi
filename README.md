

#### 介绍

#### 软件架构
后端接口通用框架： FastAPI + Json:App


#### 使用说明

1.  pip安装本仓库
`pip install git+https://gitee.com/socar/api_frame`
`pip install git+https://gitee.com/socar/api_frame@lijun#egg=api_frame`
    
2. 版本概述

v0.3.22
判断接口是否有权限方法更改

v0.3.21
验证关系权限前判断关系是否存在

v0.3.20
更改url参数解析，使用urllib.parse, 解决jquery_unparam 解析时因参数中&符号产生的bug

v0.3.19
route命唯一名，方便追踪

v0.3.18
root 来自 root_path

v0.3.17
通过定义prefix 并在挂载中将上级prefix附加给下级做路由更改。权限验证取值时删除prefix.
由于内存问题依然没有使用include_router。

v0.3.16
sort 判断关系资源不存在

v0.3.15
/resource/{id}/rel, 调用主资源获取关系资源时，对主资源类返回请求的关系名称和关系资源类名

v0.3.14
关系排序验证，并添加到sort属性，删除relsort属性

v0.3.13
or 类型查询参数添加条件bug修复

v0.3.12
auth scope 解码bug修复

v0.3.11
float 支持  gt, gte, lte, lt, bt 过滤

v0.3.10
获取文件模型传递request

v0.3.9
模型验证失败返回 RequestValidationError

v0.3.8
array类型必须传值时不允许传入空列表[]

v0.3.7
float 类型筛选

v0.3.6
添加字段时，给定数据时，类型为数据类型，如果为None，默认类型是字符串

v0.3.5
SchemaBase 模型添加字段调整，可以指定字段属性。

v0.3.4
Filters 方法新增

v0.3.3
支持筛选操作符act,筛选数组类型的属性中是否包含子集数组

v0.3.2
增加数组的aeq操作符。
增加提示数组类eq 不再使用

v0.3.1
错误日志bug修复

v0.3.0
调整fastapi==0.92.0

v0.2.4
fastapi==0.27.0, 
功能趋于完善
