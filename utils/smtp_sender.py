import smtplib

"""
   Script para en el envio sencillo de correo electronico, utiliza librerias locales
   smtplib: Conexion con servidor smtp.
"""


class smtpSender():
    smtp_client = None

    def __init__(self, server_name, server_port, server_user, server_password):
        self.server_name = server_name
        self.server_port = server_port
        self.server_user = server_user
        self.server_password = server_password

    def compose_mail(self, recipient, message, sender):
        """
        Este metodo se encarga de comṕoner el mensaje para su envio.

        :param recipient - Email de quien recibe el mensaje:
        :param message - Texto del mensaje:
        :param sender - Email de quien envia el mensaje:
        :return:
        """
        header = 'To:' + recipient + '\n' + 'From: ' + sender + '\n' + 'Subject:testing \n'
        full_mail = header + message
        return full_mail

    def stablish_connection(self):
        """
        Este metodo crea una conexion con un servidor SMTP.

        :param server_name:
        :param server_port:
        :param server_user:
        :param server_password:
        :param message - Texto del mensaje:
        :param recipient - Email que recibe el mensaje:
        :return:
        """
        self.smtp_client = smtplib.SMTP(self.server_name, self.server_port, timeout=3)
        self.smtp_client.ehlo()
        self.smtp_client.starttls()
        self.smtp_client.login(self.server_user, self.server_password)

    def send_mail(self, recipient, message, sender=None):
        """
        Este metodo se encarga del envio del mensaje.

        :param sender - Email de quien envia el mensaje:
        :param recipient - Email de quien recibe el mensaje.:
        :param message - Texto del Email.:
        :return:
        """
        self.stablish_connection()
        if sender is None:
            sender = "noreply@grplug.com"
        full_mail = self.compose_mail(recipient, message, sender)
        self.smtp_client.sendmail(sender, recipient, full_mail)
        self.smtp_client.close()

    def is_valid_connection(self):
        try:
            self.stablish_connection()
            return True
        except smtplib.SMTPAuthenticationError:
            # Usuario y/o contraseña incorrectos
            return False
        except OSError:
            # Timeout
            return False
        except Exception:
            # Hostname inalcanzable
            return False
