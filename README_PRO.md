# 缠论市场 WEB 分析工具

---

chanlun-pro 是基于 chanlun 包，扩展的行情数据可视化 WEB 项目，属于付费增值项目；

相比于免费版本的 chanlun 项目，增加了 走势中枢、背驰、买卖点的功能。

[在线 Demo 展示](http://www.chanlun-trader.com/)

在线Demo只做上证指数的缠论示例

### 项目当前功能

* 缠论图表展示(沪深股市、港股、期货、数字货币)
* 行情数据下载（沪深股市、港股、数字货币）
* 行情监控（背驰、买卖点）
* 行情回放练习
* 自定义缠论策略进行回测
* 实盘策略交易

### 特别说明

**chanlun-pro 项目限时优惠，原价1000元，永久使用权，截止 2022-04-17 24点**

要想愉快的享用本项目，需要有两个前提：

1. 了解缠论的 笔、线段、中枢、级别 等基础知识；

2. 编程基础，Python 要能写简单的程序，Linux也懂一些就更好了；

如满足以上条件，再考虑是否需要进行购买。

项目为个人开发与维护，精力有限，不太可能服务太多用户，所以定价为 1800 元/每年；   
如人数太多，保留后期调整价格的权利；

### 付费购买后的权利

* 私有仓库访问权限，可获取代码自行部署使用
* 安装与使用技术指导
* 可提个性化需求开发 1-2 个（视需求难易程度而定）
* 基于缠论的量化策略分享
* 付费交流群，可与群内大佬亲密交流


### 项目中的计算方法

缠论数据的计算，采用逐K方式进行计算，根据当前K线变化，计算并合并缠论K线，再计算分型、笔、线段、中枢、走势类型、背驰、买卖点数据；

再根据下一根K线数据，更新以上缠论数据；

如已经是形成并确认的分型、笔、线段、中枢、走势类型等，后续无特殊情况（标准化），则不会进行变更。

如上，程序会给出当下的一个背驰或买卖点信息，至于后续行情如何走，有可能确认，也有可能继续延续，最终背驰或买卖点消失；

这种情况就需要通过其他的辅助加以判断，如均线、布林线等指标，也可以看小级别的走势进行判断，以此来增加成功的概率。

这种计算方式，可以很方便实现增量更新，process_klines 方法可以一直喂数据，内部会判断，已处理的不会重新计算，新K线会重复以上的计算步骤；

在进行策略回测的时候，采用以上的增量计算，可以大大缩减计算时间，从而提升回测的效率。



### 感兴趣可加微信进行了解。

![微信](https://github.com/yijixiuxin/chanlun/raw/main/images/wx.jpg)

### 实际运行效果展示

![沪深行情页面](https://github.com/yijixiuxin/chanlun/raw/main/images/stock.png)

![港股行情页面](https://github.com/yijixiuxin/chanlun/raw/main/images/hk.png)

![期货行情页面](https://github.com/yijixiuxin/chanlun/raw/main/images/futures.png)

![数字货币页面](https://github.com/yijixiuxin/chanlun/raw/main/images/currency.png)

![回放页面](https://github.com/yijixiuxin/chanlun/raw/main/images/back.png)

![监控任务管理](https://github.com/yijixiuxin/chanlun/raw/main/images/check.png)

![策略回测结果查看](https://github.com/yijixiuxin/chanlun/raw/main/images/back_test_1.png)
![策略回测结果查看](https://github.com/yijixiuxin/chanlun/raw/main/images/back_test_2.png)
![策略回测结果查看](https://github.com/yijixiuxin/chanlun/raw/main/images/back_test_3.png)
![策略回测结果查看](https://github.com/yijixiuxin/chanlun/raw/main/images/back_test_4.png)
![策略回测结果查看](https://github.com/yijixiuxin/chanlun/raw/main/images/back_test_5.png)

