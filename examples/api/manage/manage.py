from examples.api.manage.interface.api import Api
from examples.api.manage.interface.cmpt import Cmpt
from fastapi_jsonapi import BaseResource



class Manage(BaseResource):
    link = 'manage'
    childs = [Api, Cmpt]

