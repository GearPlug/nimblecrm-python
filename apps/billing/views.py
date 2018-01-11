from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, CreateView
from apps.billing.models import ServiceValidity, ServiceRecharge
from apps.billing.forms import ServiceRechargeForm


class BillingProfileView(TemplateView):
    template_name = 'account/billing_profile.html'

    def get_context_data(self, **kwargs):
        context = super(BillingProfileView, self).get_context_data(**kwargs)
        queryset = ServiceValidity.objects.filter(user_id=str(self.request.user.id)).prefetch_related('current_fee')
        context['service_validity'] = queryset[0]
        return context


class ServiceRechargeView(CreateView):
    model = ServiceRecharge
    form_class = ServiceRechargeForm
    template_name = 'account/service_recharge.html'
    success_url = reverse_lazy('billing:profile')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self.object.recharge_amount < 20:
            raise Exception("El monto a recargar no puede ser menor a 20$.")
        self.object.service_validity = self.get_user_service_validity()
        if self.object.recharge_amount >= 50:
            expiration_days = 60
        else:
            expiration_days = 30
        self.object.expiration_date = timezone.now() + timezone.timedelta(days=expiration_days)
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_user_service_validity(self, user_id=None):
        if user_id is None:
            user_id = self.request.user.id
        return ServiceValidity.objects.get(user_id=str(user_id))
