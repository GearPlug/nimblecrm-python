import requests
import urllib
import re


class Client(object):
    """
    Clase para envío de mensajes de texto con el API de nrsgateway
    """

    username = None
    password = None
    base_api_url = "https://gateway.plusmms.net/send.php"
    url_params = {"coding": "0", "dlr-mask": "8"}

    def __init__(self, username, password):
        """

        :param username:
        :param password:
        """
        self.username = username
        self.password = password
        self.url_params.update({'username': username, 'password': password})

    def send_message(self, number_to, message, sender_identifier):
        """
        Función para el envío del mensaje
        :param number_to:
        :param message:
        :param sender_identifier:
        :return:
        """
        params = {'to': self.prepare_number(number_to), 'text': self.prepare_text(message),
                  'from': self.prepare_text(sender_identifier)}
        params.update(self.url_params)
        url_params = urllib.parse.urlencode(params)
        return requests.get("{0}{1}{2}".format(self.base_api_url, '?', url_params))

    def prepare_number(self, number):
        """
        Función para preformatear el numero celular
        :param number:
        :return:
        """

        #TODO: ESTA VALIDACION NO DEBE EXISTIR AQUI. LOS NUMEROS DEBEN TENER EL CODIGO DEL PAIS.
        clean_number = re.sub(r'\D+', '', number)
        l = len(clean_number)
        if l >= 10:
            last_10_numbers = clean_number[l - 10:]
            code = clean_number[0:l - 10] or '57'
        else:
            raise Exception("El número no tiene 10 digitos.")
        return code + last_10_numbers

    def prepare_text(self, text):
        """
        Función para preformatear el texto que se envía
        :param text:
        :return:
        """
        clean_text = re.sub(r'\s+', ' ', text)
        return clean_text
