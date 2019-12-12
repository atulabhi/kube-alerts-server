from __future__ import print_function
import os
import sys
import urllib
import urllib2
from sqlalchemy import create_engine

from flask import Flask
from flask_restplus import Api, Resource
from flask_jsonpify import jsonify
from flask import request
from kubernetes import client, config, watch
from kubernetes.client.models.v1_event_list import V1EventList

db_connect = create_engine('sqlite:///monitor.db')
app = Flask(__name__)
api = Api(app=app)

with app.app_context():
    config.load_kube_config(os.path.join(os.environ["HOME"], '.kube/config'))
v1 = client.CoreV1Api()

# install ()alternative handler to stop urllib2 from following redirects

# class NoRedirectHandler(urllib2.HTTPRedirectHandler):
#     # alternative handler
#     def http_error_401(self, req, fp, code, msg, header_list):
#         data = urllib.addinfourl(fp, header_list, req.get_full_url())
#         data.status = code
#         data.code = code


#         return data
class NoRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl

    http_error_401 = http_error_302
    # http_error_301 = http_error_302
    # http_error_303 = http_error_302
    # http_error_307 = http_error_302


opener = urllib2.build_opener(NoRedirectHandler())
urllib2.install_opener(opener)


@api.route("/sites/")
class Sites(Resource):
    def get(self):
        conn = db_connect.connect()  # connect to database
        # This line performs query and returns json result
        query = conn.execute("select name from sites")
        result = [i[0] for i in query.cursor.fetchall()]
        content = []
        for r in result:
            try:
                status = urllib2.urlopen(r).getcode()
                x = {"name": r, "status": status}
                content.append(x)
            except Exception as e:
                print('Error', e, r, file=sys.stderr)

        content = jsonify(content)
        conn.close()
        return content

    @api.response(204, 'Category successfully created.')
    def post(self):
        conn = db_connect.connect()
        # all_cols = cursor.fetchall()
        # data = request.get_json()
        site_name = request.get_json()
        conn.execute("INSERT INTO site(name) VALUES (?)", (site_name['url']))
        conn.close()
        # print("{site_name}".format(site_name=site_name))
        print(site_name['url'])
        return None, 204

    @api.response(204, 'Category successfully updated.')
    def put(self):
        # all_cols = cursor.fetchall()
        data = request.get_json()
        print("{data}".format(data=data))
        return None, 204

    @api.response(204, 'Category successfully deleted.')
    def delete(self):
        # all_cols = cursor.fetchall()
        data = request.get_json()
        print("{data}".format(data=data))
        return None, 204


#  @api.route("/pods/")
class Pods(Resource):
    def get(self):
        result = []
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            # print("%s\t%s\t%s" % (i.status.phase, i.metadata.namespace, i.metadata.name))
            try:
                size = len(i.status.container_statuses)
                containerCount = 0
                for container in i.status.container_statuses:
                    if (container.state.running != None):
                        containerCount = containerCount + 1
                    ready = str(containerCount) + '/' + str(size)
                    print("%s\t%s" % (i.metadata.name, ready))
                    Pod = {
                        "name": i.metadata.name,
                        "ready": ready,
                    }
                    result.append(Pod)
            except Exception as e:
                print('Error', e, size, file=sys.stderr)
        return jsonify(result)


# @api.route("/events/")
class Events(Resource):
    def get(self):
        result = []
        # stream = watch.Watch().stream(v1.list_namespaced_pod, "default")
        # for event in stream:
        #     print("Event: %s %s %s " % (
        #         event['type'],  event['object'].kind, event['object'].metadata.name))
        #     # print("%s" %(stream.object))
        allNamespacesEvents = v1.list_event_for_all_namespaces()
        for item in allNamespacesEvents.items:
            # if item.type == "Warning" or item.type == "error":
            Event = {
                "name": item.metadata.name,
                "type": item.type,
                "message": item.message,
            }
            result.append(Event)

        return result


api.add_resource(Pods, '/pods')  # Route_1
api.add_resource(Events, '/events')  # Route_2
app.run(port='5002', debug=True)
