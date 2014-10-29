#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


# Configure Apache

# create a dummy SSL certificate
# http://blog.justin.kelly.org.au/how-to-create-a-self-sign-ssl-cert-with-no-pa/
cd /home/vagrant
openssl genrsa -out server.key 1024
openssl req -new -key server.key -out server.csr <<<'








'
openssl x509 -req -days 366 -in server.csr -signkey server.key -out server.crt


cat >>/etc/apache2/sites-enabled/000-default.conf <<<'
<VirtualHost *:443>
	SSLEngine	on
	SSLCertificateFile	/home/vagrant/server.crt
	SSLCertificateKeyFile	/home/vagrant/server.key

	DocumentRoot /var/www/html

	ErrorLog ${APACHE_LOG_DIR}/error.log
	CustomLog ${APACHE_LOG_DIR}/access.log combined

	<Location />
		AuthType		mod_auth_pubtkt
		TKTAuthPublicKey	/vagrant/vagrant/tkt_pubkey.pem

		TKTAuthLoginURL		https://login.futurice.com/
		TKTAuthTimeoutURL	https://login.futurice.com/?timeout=1
		TKTAuthUnauthURL	https://login.futurice.com/?unauth=1
		TKTAuthToken		"futu"

		Require valid-user
	</Location>

	Alias /static/ /vagrant/vimmasite/static/
	<Directory /vagrant/vimmasite/static/>
	</Directory>

	WSGIScriptAlias	/	/vagrant/vimmasite/vimmasite/wsgi.py
	WSGIDaemonProcess	vimmasite user=vagrant group=vagrant python-path=/vagrant/vimmasite:/home/vagrant/env/lib/python3.4/site-packages
	WSGIProcessGroup	vimmasite
</VirtualHost>
'

a2enmod ssl
service apache2 stop

update-rc.d apache2 disable
