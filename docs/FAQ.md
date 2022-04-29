## FAQ 常见问题

---

### 如何获取当前网卡地址？

通过 getmac / ifconfig 等命令获取网卡地址会获取多个，不清楚到底哪一个是正确的，可使用一下命令获取

    pip install pyarmor
    pyarmor hdinfo

输出中 Default Mac address 后面的就是默认的网卡地址

### 找不到授权许可文件 Read file license.lic failed, No such file or directory

许可文件默认会在 src/pytransform/license.lic 查找，如文件位置存在却还是找不到，可以设置一下系统变量，指定许可文件地址；

    系统变量名称：PYARMOR_LICENSE
    系统变量值：D:/${you_project_path}/src/pytransform/license.lic

### 运行报错 License is not for this machine

许可文件绑定的网卡地址错误，可通过以上获取网卡地址的命令，重新获取网卡地址进行授权即可。