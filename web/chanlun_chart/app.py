import sys
import pathlib
import traceback
from gevent.pywsgi import WSGIServer
import webbrowser
from multiprocessing import cpu_count, Process


cmd_path = pathlib.Path.cwd()
sys.path.append(str(cmd_path))

try:
    from app import create_app
except Exception as e:
    print(e)
    traceback.print_exc()

    input('出现异常，按回车键退出')

if __name__ == "__main__":
    try:
        app = create_app()
        http_server = WSGIServer(('0.0.0.0', 9900), app)
        webbrowser.open('http://127.0.0.1:9900')
        http_server.start()


        def server_forever():
            http_server.start_accepting()
            http_server._stop_event.wait()


        for i in range(int(cpu_count() / 2)):
            p = Process(target=server_forever)
            p.start()

    except Exception as e:
        print(e)
        traceback.print_exc()

        input('出现异常，按回车键退出')
