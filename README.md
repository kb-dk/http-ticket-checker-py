# HTTP Ticket Checker

Code and documentation: Work in progress.

## Deployment

### Apache

Requirements: mod_wsgi
Recommended: mod_xsendfile

Add something like this to your Apache configuration, and adapt the config-example- and wsgi-example-file to your needs.

```
XSendFile on
XSendFilePath /path/to/serve/files/from

WSGIPythonPath /optional/python/path
WSGISocketPrefix /var/run/wsgi
WSGIDaemonProcess ticket user=apache group=apache threads=5
WSGIScriptAlias / /path/to/wsgi/file>

<Directory /path/to/folder/containing/wsgi/file>
        WSGIProcessGroup ticket
        WSGIApplicationGroup %{GLOBAL}
        Order deny,allow
        Allow from all
</Directory>
```

