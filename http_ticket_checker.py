#!/usr/bin/env python

import sys, time, re, json
import requests, pylibmc
from flask import Flask, request, send_from_directory
from decorator import decorator


app = Flask(__name__)
app.config.from_envvar("HTTP_TICKET_CHECKER_CONFIG")

prefix = app.config['PREFIX'] or ""
if not prefix.startswith('/'):
    prefix = '/' + prefix
if not prefix.endswith('/'):
    prefix += '/'

ticket_id_pattern = re.compile('[0-9a-zA-Z:-]+')


def to_ascii(unicode):
    return unicode.encode('ascii', 'replace')


def retry(exception, count=5, delay=0.25):
    @decorator
    def retry_(f, *args, **kw):
        caught_exception = None
        for i in xrange(count):
            try:
                return f(*args, **kw)
            except exception as e:
                caught_exception = e
            time.sleep(delay)
            delay *= 2
        raise caught_exception

    return retry_


@app.route("%s<path:resource>" % prefix)
def get_file(resource):
    ticket_id = request.args.get("ticket")
    resource_id = resource.split("/")[-1].split(".")[0]
    print resource_id

    valid_ticket = False

    if ticket_id and ticket_id is not "":
        valid_ticket = validate_ticket(ticket_id, resource_id, request.remote_addr)

    if valid_ticket:
        return send_from_directory(app.config['FILE_DIR'],
                                   resource, as_attachment=False,
                                   mimetype="image/jpeg")
    else:
        return "Ticket invalid", 403



def get_backend(backend_url):
    match = re.match("(\w+)://(.+)", backend_url)
    if match:
        backend, address = match.groups()

        if backend == "memcached":
            servers = address.split(',')
            return memcached_backend_factory(servers)
        elif backend == "http" or backend == "https":
            return http_backend_factory(backend_url)

    print "Backend not configured, exiting.."
    sys.exit(1)


def memcached_backend_factory(servers):
    mc = pylibmc.Client(servers, binary=True)
    mc_pool = pylibmc.ThreadMappedPool(mc)

    @retry(pylibmc.Error, count=5)
    def memcached_backend(ticket_id):
        if mc_pool != None:
            with mc_pool.reserve() as mc:
                response = mc.get(to_ascii(ticket_id))
                try:
                    return json.loads(response)
                except:
                    return None

    return memcached_backend


def http_backend_factory(resolve_ticket_url):
    def http_backend(ticket_id):
        r = requests.get(resolve_ticket_url.replace("<ticket>", ticket_id))
        if r.status_code != 200:
            return False

        return r.json()

    return http_backend


# String -> String -> Boolean
def validate_ticket(ticket_id, resource_id, user_identifier):
    if ticket_id_pattern.match(ticket_id):
        raw_ticket = get_ticket(ticket_id)
        parsed_ticket = parse_ticket(raw_ticket)
        if parsed_ticket:
            resource_ids, presentation_type, user_id = parsed_ticket
            # strip everything up to, and including, "..uuid:" from the resource-id's
            stripped_resource_ids = map(lambda r: r.split(":")[-1], resource_ids)
            is_valid = (app.config['CONTENT_TYPE'] == presentation_type
                and resource_id in stripped_resource_ids
                and user_identifier == user_id)
            return is_valid

    return False

# Ticket -> (String, String, String)
def parse_ticket(ticket):
    if ticket:
        if not False in [key in ticket for key in ["resources", "type", "userIdentifier"]]:
            return ticket["resources"], ticket["type"], ticket["userIdentifier"]
        else:
            return None


get_ticket = get_backend(app.config["BACKEND"])

if __name__ == "__main__":
    app.run()
