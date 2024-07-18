
import requests
import json


if __name__ == '__main__':
    # 10万并发请求
    data =["/usage/Ee0EQclZbQCa-GySv6EbOA/user?page%5Blimit%5D=10&page%5Boffset%5D=0","/usage/Ee0EQclZbQCa-GySv6EbOA/journey?page%5Blimit%5D=10&page%5Boffset%5D=0","/usage/Ee0EQclZbQCa-GySv6EbOA/inten?page%5Blimit%5D=10&page%5Boffset%5D=0","/usage/Ee0EQclZbQCa-GySv6EbOA/matter?include=taskscene%2Caccount%2Cvideo%2Cimage%2Cread%2Cfavorite%2Ccomment%2Cmine%2Ctopic%2Cedit%2Cpubscene.inten%2Cpubscene.journey%2Cpubscene.user%2Cpubscene.usage%2Cpubscene.variables%2Cpubscene.account%2Cpubscene%2Cmplink%2Cmplink.account%2Cmplink.pubscene&page%5Blimit%5D=10&page%5Boffset%5D=0"]
    response = requests.get(
        url='https://127.0.0.1:8000/pubscene',
        # data=json.dumps(data),
        headers={
            'Authorization': 'bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ1ZzBxUzVoUkVleTcwd3pFZWxiQUtnIiwiYXVkIjoiNHdoUmFaaFJFZXk3MHd6RWVsYkFLZyIsIm5iZiI6MTY2NTk0MTM4MiwiZXhwIjoxNjY2NTQ2MTgyLCJ1aWQiOiJkbldObml3TlBldWxRcGdIbnUwRkNnIiwidXYiOjMsInNjb3BlIjoidyJ9.Nzz8JRpZF5lOYdDAdenjToRC7_PGJtRlPWioVOtdG5eNCo0re05T9iwnVOPXHm-iBMC5Rzh35KAOE-jrCosp-Q'}
        )
    print(response.content.decode('utf-8'))



