# # -*- coding: utf-8 -*-
import fastapi
import pydantic
from pydantic import BaseModel, Field
from fastapi import File, UploadFile, Body, Form, Response, APIRouter, Query


from fastapi import Body, FastAPI, Request, Response

import inspect
from fastapi.params import Depends
from fastapi import Request
from fastapi_jsonapi.exception import QureyError

class Data(BaseModel):
    name:str = Field(None)

def verify_arg(request):
    args_default = {}
    # 验证查询参数
    # if not request or request.method != 'GET':
    #     return False
    full_arg = inspect.getfullargspec(request.scope.get('endpoint'))
    if not full_arg.defaults:
        return True
    for arg, value in zip(full_arg.args, full_arg.defaults):
        if arg != 'arg' and arg != 'request':   # 获取参数属性
            if isinstance(value, Depends):
                continue
            if hasattr(value, 'alias') and getattr(value, 'alias'):
                arg = getattr(value, 'alias')
            else:
                arg = arg
            args_default[arg] = getattr(value, 'default')  # 默认参数值
    print(args_default)
    query_params = list(request.query_params.keys())  # 获取前端查询参数
    for param in query_params:
        if param not in args_default:  # 判断是否在接口参数内
            raise QureyError(detail='参数 [%s] 错误' % param)
    return True

app = FastAPI()


route = APIRouter(prefix='/file')

@app.post(path='/file')
async def file(
        s: str,
        request: Request = None,
        limit: str = Query(None, alias='page[limit]'),
        include: str = Query(None),
        db: str = Depends(verify_arg),
        data: Data = Body(..., media_type='application/vnd.api+json')


):
    print(999999)
    verify_arg(request)
    # print(files)
    return 'ok'


if __name__ == '__main__':

    # import uvicorn
    # uvicorn.run("form:app", host="0.0.0.0", port=8080, reload=True, debug=True)

    import inspect


    def get_default_args(func):
        signature = inspect.signature(func)
        args = {}
        for k, v in signature.parameters.items():

            default = v.default
            print(v.default)
            if isinstance(v.default, Depends):
                continue
            if v and hasattr(v.default, 'alias'):
                k = getattr(v.default, 'alias') if getattr(v.default, 'alias') else k
            #
            if isinstance(default, pydantic.fields.FieldInfo):
                default = default.default
            if v.default is inspect.Parameter.empty:
                default = None
            args[k] = default
        return args

    def gete(a:str, b:str='2'):
        print(a,b)

    print(get_default_args(file))