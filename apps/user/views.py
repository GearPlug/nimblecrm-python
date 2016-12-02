import account.views
import account.forms
import apps.user.forms
from django.shortcuts import render
import httplib2
from oauth2client import client
from apiclient import discovery
from django.conf import settings


class SignupView(account.views.SignupView):
    form_class = apps.user.forms.SignupForm

    def generate_username(self, form):
        username = form.cleaned_data["email"]
        return username

    def user_credentials(self):
        self.identifier_field = 'email'
        return super(SignupView, self).user_credentials()

        # def form_valid(self, form):
        #     print("SI")
        #     return super(SignupView, self).form_valid(form)
        #
        # def form_invalid(self, form):
        #     print(form.errors)
        #     return super(SignupView, self).form_invalid(form)


class LoginView(account.views.LoginView):
    form_class = account.forms.LoginEmailForm


def email_test(request):
    code = request.GET.get('code', None)
    flow = client.OAuth2WebServerFlow(
        client_id='292458000851-9q394cs5t0ekqpfsodm284ve6ifpd7fd.apps.googleusercontent.com',
        client_secret='eqcecSL7Ecp0hiMy84QFSzsD',
        scope='https://www.googleapis.com/auth/drive',
        redirect_uri='http://localhost/account/test/')
    credentials = flow.step2_exchange(code)
    http_auth = credentials.authorize(httplib2.Http())
    drive_service = discovery.build('drive', 'v3', http_auth)
    files = drive_service.files().list().execute()
    sheet_list = []
    for f in files:
        if f == 'files':
            for i in files[f]:
                sheet_list.append((i['id'], i['name']))
        else:
            print("%s: %s" % (f, files[f]))
    print(sheet_list)
    print(sheet_list[0])
    spreadsheet_id = sheet_list[0][0]
    sheets_service = discovery.build('sheets', 'v4', http_auth)
    result = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = tuple(i['properties'] for i in result['sheets'])  # % sheets[0]['gridProperties']['rowCount']
    res = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="1:1").execute()
    values = res.get('values', [])
    try:
        fields_count = len(values[0])
    except IndexError:
        fields_count = 0
    print(fields_count)

    for v in values:
        print(v)

    # from apps.gp.tasks import update_gears
    # update_gears.delay()
    # from django.core.mail import send_mail
    # send_mail('Subject here', 'Here is the message.', settings.EMAIL_HOST_USER, ['tavito.286@gmail.com'],
    #           fail_silently=False)
    return render(request, 'home/dashboard.html', {'sheets': sheet_list})
