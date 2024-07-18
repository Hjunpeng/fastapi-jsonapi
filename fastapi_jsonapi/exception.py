#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
http错误处理
"""
from typing import List, Any
import logging
import json
from fastapi import status, Request
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi_jsonapi.jsonapi import ErrorResponse, ErrorModel
from fastapi_jsonapi.responses import JsonapiResponse


class JsonapiException(HTTPException):
    """
    jsonapi错误类
     Args:
        status_code: 错误http code
        detail: 错误详情
        errors: 错误列表

    """

    def __init__(self, status_code: int, detail: str = None, title: str = None,
                 errors: List[ErrorModel] = None, body: Any = None) -> None:
        super().__init__(status_code, detail=detail)
        self.errors = errors or []
        self.body = body
        self.errors.append(ErrorModel(detail=detail, status=status_code, title=title))


class AuthError(JsonapiException):
    """ HTTP 401 error,没有认证权限"""
    status_code: int = status.HTTP_401_UNAUTHORIZED
    title: str = '没有认证权限'

    def __init__(self, status_code: int = None, detail: str = None, title: str = None, body: Any = None) -> None:
        super().__init__(
            status_code if status_code is not None else self.status_code,
            title=title if title is not None else self.title,
            detail=detail,
            errors=None,
            body=body,
        )


class ResourceDuplicate(JsonapiException):
    """ HTTP 409 error,资源已存在"""
    status_code: int = status.HTTP_409_CONFLICT
    title: str = '资源重复创建'

    def __init__(self, status_code: int = None, detail: str = None, title: str = None, body: Any = None) -> None:
        super().__init__(
            status_code if status_code is not None else self.status_code,
            title=title if title is not None else self.title,
            detail=detail,
            errors=None,
            body=body
        )


class ResourceNotFound(JsonapiException):
    """ HTTP 404 error,资源不存在"""
    status_code: int = status.HTTP_404_NOT_FOUND
    title: str = '资源不存在'

    def __init__(self, status_code: int = None, detail: str = None, title: str = None, body: Any = None) -> None:
        super().__init__(
            status_code if status_code is not None else self.status_code,
            title=title if title is not None else self.title,
            detail=detail,
            errors=None,
            body=body
        )


class QureyError(JsonapiException):
    """ HTTP 400 error,查询参数错误"""
    status_code: int = status.HTTP_400_BAD_REQUEST
    title: str = '查询参数错误'

    def __init__(self, status_code: int = None, detail: str = None, title: str = None, body: Any = None) -> None:
        super().__init__(
            status_code if status_code is not None else self.status_code,
            title=title if title is not None else self.title,
            detail=detail,
            errors=None,
            body=body
        )


async def serialize_error(exc: BaseException, request: Request, msg: dict=None) -> JsonapiResponse:
    """
    错误处理，将所有错误类型转成json:api，
    JsonapiException: 预判规范内的错误，返给前端
    HTTPException: http错误，日志记录
    RequestValidationError，ValidationError：pydantic的验证错误，数据不合规范，记录日志
    对pydantic的验证错误做了处理。detail中指明了验证错误的具体字段和错误原因
    Args:
        exc: 处理对象
        request: Request
        msg: 日志信息
    Returns:JsonapiResponse

    """
    body = None
    if isinstance(exc, JsonapiException):
        status_code = exc.status_code
        errors = exc.errors
        body = exc.body
    elif isinstance(exc, HTTPException):
        status_code = exc.status_code
        errors = [ErrorModel(status=status_code,
                             detail=exc.detail,
                             meta={"headers": exc.headers})]
    elif isinstance(exc, RequestValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = [
            ErrorModel(
                detail='位置:' +
                '->'.join([str(loc) for loc in error.get('loc')]) +
                ', 错误:' +
                str(error.get('msg')),
                title=error.get('type'),
                status=status_code) for error in exc.errors()]
        body = exc.body
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        errors = [ErrorModel(status=status_code, detail='Internal server error')]
    error_body = ErrorResponse(errors=errors)

    if not msg:
        if request.headers.get('X-Real-IP'):
            cilent_ip = request.headers.get('X-Real-IP')
        else:
            cilent_ip = request.client.host
        if not body:
            if hasattr(request, '_json'):  # delete 主资源没有body
                body = request._json  # 其他有request body

            if hasattr(request, '_form') and request._form:
                for item, value in request._form.multi_items():
                    if item == 'data':
                        body = json.loads(value)

        msg = {
            "RequestMethod": request.method,
            "ResponseStatueCode": status_code,
            "url": str(request.url),
            "UserAgent": request.headers.get('user-agent'),
            "IP": cilent_ip,
            # "X-Process-Time(s)": process_time,
            "Token": request.headers.get('authorization'),
            "RequestBody": body,
            # "exc":  traceback.format_exc()
        }

    if status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        logging.error(msg, exc_info=exc)
    else:
        logging.warning(msg, exc_info=exc)

    return JsonapiResponse(status_code=status_code, content=error_body.dict())
