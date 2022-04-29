from django.urls import path

from . import views

urlpatterns = [

    # 股票相关url配置
    path('', views.index_show),
    path('stock/kline', views.kline_chart),

]
