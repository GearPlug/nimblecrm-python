# -*- coding: utf-8 -*-
import smtplib

"""
   Script para en el envio sencillo de correo electronico, utiliza librerias locales
   smtplib: Conexion con servidor smtp.
"""


class SMTPCustomClient():
    client = None
    is_active = False

    def __init__(self, host, port, user, password, sender="noreply@grplug.com"):
        self.sender = sender
        try:
            self.client = smtplib.SMTP(host, port, timeout=3)
            self.client.ehlo()
            self.client.starttls()
            self.client.login(user, password)
            self.is_active = True
        except (smtplib.SMTPAuthenticationError, OSError):
            # Usuario y/o contraseña incorrectos, TimeOut
            self.is_active = False
        except Exception:
            # Hostname inalcanzable
            self.is_active = False

    def send_email(self, recipient=None, message="", subject=""):
        """
        Este metodo se encarga del envio del mensaje.

        :param sender - Email de quien envia el mensaje:
        :param recipient - Email de quien recibe el mensaje.:
        :param message - Texto del Email.:
        :return:
        """
        if not self.is_active:
            raise Exception("There's no active connection. Please provide valid credentials to continue.")
        if recipient is None:
            raise Exception("Recipient can't be empty.")
        email_content = 'To:{0} \nFrom:{1} \nSubject:{2} \n{3}'.format(recipient, self.sender, subject,
                                                                       message).encode('utf-8')
        try:
            self.client.sendmail(self.sender, recipient, email_content)
            return "Message successfully sent to: {}".format(recipient)
        except:
            return "The message to: {}  has FAILED.".format(recipient)

    def close(self):
        try:
            self.client.close()
            return True
        except:
            return False
