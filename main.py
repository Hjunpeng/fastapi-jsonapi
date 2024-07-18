from examples.app import create_app
# from api_frame.configure_logging import configure_logging

# 日志配置
log_addr = 'log.ini'
# configure_logging(log_addr)
app = create_app()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, debug=True)