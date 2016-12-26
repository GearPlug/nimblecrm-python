import json
import account.views
import account.forms
import apps.user.forms
from django.core.urlresolvers import reverse
from django.shortcuts import render, HttpResponse, redirect
from django.template import loader, Context
from django.views.generic import View
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


def get_flow():
    return client.OAuth2WebServerFlow(
        client_id='292458000851-9q394cs5t0ekqpfsodm284ve6ifpd7fd.apps.googleusercontent.com',
        client_secret='eqcecSL7Ecp0hiMy84QFSzsD',
        scope='https://www.googleapis.com/auth/drive',
        redirect_uri='http://localhost:8000/account/google_auth/')


class ConnectionsView(View):
    template_name = 'home/connections.html'

    def get(self, request, *args, **kwargs):
        ctx = {'AuthUri': get_flow().step1_get_authorize_url()}
        return render(request, self.template_name, ctx)


class GoogleAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET['code']
        credentials = get_flow().step2_exchange(code)

        # Guardar en credencial en Modelo en vez de sesion
        request.session['google_credentials'] = credentials.to_json()
        return redirect(reverse('connections'))


def get_authorization(request):
    credentials = client.OAuth2Credentials.from_json(request.session['google_credentials'])
    return credentials.authorize(httplib2.Http())


def email_test(request):
    http_auth = get_authorization(request)

    drive_service = discovery.build('drive', 'v3', http_auth)
    files = drive_service.files().list().execute()

    sheet_list = []
    for f in files['files']:
        if 'mimeType' in f and f['mimeType'] == 'application/vnd.google-apps.spreadsheet':
            sheet_list.append((f['id'], f['name']))

    spreadsheet_id = sheet_list[0][0]
    sheets_service = discovery.build('sheets', 'v4', http_auth)
    res = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="1:1").execute()

    values = res.get('values', [])

    try:
        fields_count = len(values[0])
    except IndexError:
        fields_count = 0

    for v in values:
        print(v)

    # from apps.gp.tasks import update_gears
    # update_gears.delay()
    # from django.core.mail import send_mail
    # send_mail('Subject here', 'Here is the message.', settings.EMAIL_HOST_USER, ['tavito.286@gmail.com'],
    #           fail_silently=False)
    return render(request, 'home/dashboard.html', {'sheets': sheet_list})


def async_spreadsheet_info(request, id):
    http_auth = get_authorization(request)

    sheets_service = discovery.build('sheets', 'v4', http_auth)

    result = sheets_service.spreadsheets().get(spreadsheetId=id).execute()

    sheets = tuple(i['properties'] for i in result['sheets'])  # % sheets[0]['gridProperties']['rowCount']

    _sheets = [(i['index'], i['title']) for i in sheets]

    request.session['google_sheets'] = _sheets

    template = loader.get_template('home/_spreadsheet_sheets.html')
    context = {'sheets': _sheets}

    ctx = {'Success': True, 'sheets': template.render(context)}
    return HttpResponse(json.dumps(ctx), content_type='application/json')


# def get_sheet_values(self, credentials_json, spreadshee_tid, worksheet_name, from=None)

def async_spreadsheet_values(request, id, sheet_id):
    http_auth = get_authorization(request)

    sheets_service = discovery.build('sheets', 'v4', http_auth)

    sheets = request.session['google_sheets']

    sheet_id = next((s[1] for s in sheets if s[0] == int(sheet_id)))

    res = sheets_service.spreadsheets().values().get(spreadsheetId=id, range='{0}!A1:Z100'.format(sheet_id)).execute()

    values = res['values']
    column_count = len(values[0])
    row_count = len(values)

    template = loader.get_template('home/_spreadsheet_table.html')
    context = {'Values': values}

    data = {'ColumnCount': column_count, 'RowCount': row_count, 'Table': template.render(context)}
    ctx = {'Success': True, 'Data': data}
    return HttpResponse(json.dumps(ctx), content_type='application/json')


def google_sheets_write(request):
    http_auth = get_authorization(request)

    sheets_service = discovery.build('sheets', 'v4', http_auth)

    values = [
        ['alpha', 'gamma', 'beta'],
    ]

    body = {
        'values': values
    }

    res = sheets_service.spreadsheets().values().update(spreadsheetId='1ujsgXnEQzYg9FcWlfyuYUvOxWy95k9yy10yqUlOx4gQ',
                                                        range="'HOJA OP'!A1:C1", valueInputOption='RAW',
                                                        body=body).execute()

    print(res)
    return render(request, 'home/google_sheets_write.html')
