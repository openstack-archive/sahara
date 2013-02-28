from eho.server.service import api
from flask import request
import traceback

from eho.server.utils.api import Rest, render, abort_and_log, request_data


rest = Rest('v01', __name__)


@rest.route('/node-templates', methods=['GET', 'POST'])
def templates():
    if request.method == 'GET':
        try:
            return render(
                templates=[nt.dict for nt in api.get_node_templates()])
        except Exception, e:
            abort_and_log(500, "Exception while listing NodeTemplates: %s" % e)
    elif request.method == 'POST':
        data = request_data()
        try:
            return render(api.create_node_template(data).dict)
        except Exception, e:
            abort_and_log(500, "Exception while adding NodeTemplate: %s" % e)


@rest.route('/node-templates/<template_id>', methods=['GET', 'PUT', 'DELETE'])
def template(template_id):
    if request.method == 'GET':
        nt = None
        try:
            nt = api.get_node_template(id=template_id)
        except Exception, e:
            abort_and_log(500, "Exception while getting NodeTemplate by id "
                               "'%s': %s" % (template_id, e))
        if nt is None:
            abort_and_log(404, "NodeTemplate with id '%s' not found"
                               % template_id)

        return render(nt.dict)
    elif request.method == 'PUT':
        raise NotImplementedError("Template update op isn't implemented yet")
    elif request.method == 'DELETE':
        api.terminate_node_template(id=template_id)
        return render(status=204)


@rest.route('/clusters', methods=['GET', 'POST'])
def clusters():
    if request.method == 'GET':
        try:
            return render(clusters=[c.dict for c in api.get_clusters()])
        except Exception, e:
            abort_and_log(500, 'Exception while listing Clusters: %s' % e)
    elif request.method == 'POST':
        data = request_data()
        try:
            return render(api.create_cluster(data).dict)
        except Exception, e:
            traceback.print_exc()
            abort_and_log(500, "Exception while adding new Cluster: %s" % e)


@rest.route('/clusters/<cluster_id>', methods=['GET', 'PUT', 'DELETE'])
def cluster(cluster_id):
    if request.method == 'GET':
        c = None
        try:
            c = api.get_cluster(id=cluster_id)
        except Exception, e:
            abort_and_log(500, 'Exception while getting Cluster with id '
                               '\'%s\': %s' % (cluster_id, e))

        if c is None:
            abort_and_log(404, 'Cluster with id \'%s\' not found' % cluster_id)

        return render(c.dict)
    elif request.method == 'PUT':
        raise NotImplementedError("Cluster update op isn't implemented yet")
    elif request.method == 'DELETE':
        api.terminate_cluster(id=cluster_id)
        return render(status=204)
