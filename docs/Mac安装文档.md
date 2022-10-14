### Mac 安装文档

---

!> Python 版本支持 3.7、3.8、3.9、3.10，不然运行会报 RuntimeError 错误

> 前置条件
> 已经安装 git、Anaconda、MySQL、Redis

1. 克隆项目到本地

        git clone https://github.com/yijixiuxin/chanlun-pro.git
        cd chanlun-pro
2. pip 安装项目依赖包

         # 创建项目运行 Python 环境
         conda create -y -n chanlun python=3.10
         # 切换到新创建的 chanlun 环境  
         conda activate chanlun
             
         # conda 安装相关的库会比较方便
         conda install -y pandas requests numpy redis matplotlib pymysql  
         conda install -y -c conda-forge ta-lib  ipywidgets  
             
         # PIP 安装项目依赖包
         pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/
         pip3 install -r requirements.txt
             
         # 安装 pytdx 包
         pip3 install wheel
         pip3 install package/pytdx-1.72r2-py3-none-any.whl


4. 设置 `PYTHONPATH` 环境变量

         vim ~/.bashrc
         # 在最后一行增加  project_path 替换成项目所在的目录
         export PYTHONPATH=$PYTHONPATH:/project_path/chanlun-pro/src:
         source ~/.bashrc

5. 在 `src/chanlun` 目录， 复制拷贝 `config.py.demo` 文件为 `config.py` 并修改其中的 [配置项](配置文件说明.md)

6. 执行以下命令获取本机 mac 地址，并发送给作者，获取授权许可文件，并放置在项目中的 `src/pytransform` 目录下

         pip install pyarmor
         pyarmor hdinfo
         # 将 Default Mac address: "****"  内容发送给作者，获取授权文件

7. 到 `web/chanlun_web` 目录，启动 web 服务

         cd web/chanlun_web
         python manage.py runserver 0.0.0.0:8000

8. 浏览器访问 http://127.0.0.1:8000/ 即可显示缠论解缠主页
    