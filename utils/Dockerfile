FROM pritunl/archlinux
RUN pacman -S python python-pip python-psycopg2 --noconfirm
RUN mkdir /codeg
WORKDIR /codeg
ADD requirements.txt /codeg/
RUN pip install -r requirements.txt
ADD . /codeg/
RUN django-admin.py startproject apitest
#RUN python apitest/manage.py runserver
