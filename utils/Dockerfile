FROM ubuntu:16.04
MAINTAINER Gustavo Saavedra "gsaavedra@grplug.com"
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
RUN apt-get update; apt-get install apt-utils gcc python3 python3-dev python3-venv python3-pip libmysqlclient-dev rabbitmq-server supervisor -y;
RUN DEBIAN_FRONTEND=noninteractive apt-get install mysql-server -y;
RUN mkdir /home/www; mkdir /home/www/gearplug; mkdir /var/log/celery; #mkdir /var/log/supervisor;
ADD gearplug /home/www/gearplug
RUN cd /home/www/gearplug; mkdir log/; mkdir log/controller; mkdir log/django;
RUN pip3 install -r /home/www/gearplug/requirements.txt
RUN cp -r /home/www/gearplug/extra/supervisor/* /etc/supervisor/conf.d/
CMD ["/bin/sh /usr/sbin/rabbitmq-server &"]
CMD ["supervisord -c /etc/supervisor/conf.d/supervisord.conf"]