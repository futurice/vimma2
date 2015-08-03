FROM ubuntu:14.04
MAINTAINER Jussi Vaihia <jussi.vaihia@futurice.com>

WORKDIR /opt/app

# Configure apt to automatically select mirror
RUN echo "deb mirror://mirrors.ubuntu.com/mirrors.txt trusty main restricted universe\n\
deb mirror://mirrors.ubuntu.com/mirrors.txt trusty-updates main restricted universe\n\
deb mirror://mirrors.ubuntu.com/mirrors.txt trusty-security main restricted universe" > /etc/apt/sources.list

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
	build-essential vim htop wget \
	python3 python3-pip python3-dev \
	supervisor libpq-dev \
	git unzip redis-server \
    libpcre3 libpcre3-dev libssl-dev

# Node.js
# Download node.js from Futurice CDN S3 bucket over SSL. Files there have verified checksums. Official site downloads are over insecure connection.
ENV NODE_VERSION 0.10.36
RUN wget --quiet -O /tmp/node.tar.gz https://s3-eu-west-1.amazonaws.com/futurice-cdn/node/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.gz \
	&& cd /usr/local \
	&& mkdir node \
	&& cd node \
	&& tar xfz /tmp/node.tar.gz \
	&& ln -s node* current \
	&& update-alternatives --install /usr/local/bin/node node /usr/local/node/current/bin/node 5000 \
	&& update-alternatives --install /usr/local/bin/npm npm /usr/local/node/current/bin/npm 5000

# Nginx
RUN apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys 573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62
RUN echo "deb http://nginx.org/packages/ubuntu/ trusty nginx" >> /etc/apt/sources.list
RUN apt-get update && apt-get install -y nginx
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

# Set timezone to Europe/Helsinki
RUN echo 'Europe/Helsinki' > /etc/timezone && rm /etc/localtime && ln -s /usr/share/zoneinfo/Europe/Helsinki /etc/localtime

# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN useradd -m app
RUN mkdir -p /opt/app
RUN chown app /opt/app

ADD docker/requirements.txt /opt/app/
ADD docker/package.json /opt/app/
ADD docker/dev/bower.json /opt/app/static/
RUN chown -R app static/

RUN pip3 install -r requirements.txt

USER app

RUN npm install
RUN mkdir -p /opt/app/static/bower_components
RUN cd static/ && /opt/app/node_modules/.bin/bower install

ADD docker/supervisord.conf /etc/supervisor/supervisord.conf
ADD docker/nginx-site.conf /etc/nginx/conf.d/

COPY . /opt/app/

ADD scripts/* /opt/app/scripts/
RUN mkdir logs/

ENV DJANGO_SETTINGS_MODULE vimmasite.settings
ENV PYTHONPATH config
ENV SECRET_KEY default_insecure_secret
ENV CELERY_LOG_LEVEL info

RUN mkdir -p static
RUN python3 manage.py collectstatic --noinput --clear --link

EXPOSE 8000

USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
