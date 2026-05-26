"""启动招聘防骗：默认网页版；加参数 --float 为悬浮窗。"""

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--float", "-f"):
        from float_app import main

        main()
    else:
        import uvicorn

        uvicorn.run("app.main:app", host="127.0.0.1", port=8765, reload=True)
