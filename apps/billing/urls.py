from django.conf.urls import url
from apps.billing.views import BillingProfileView, ServiceRechargeView

urlpatterns = [
    url(r'^accounts/billing/$', BillingProfileView.as_view(), name='profile'),
    url(r'^accounts/billing/recharge/$', ServiceRechargeView.as_view(), name='recharge'),

]
