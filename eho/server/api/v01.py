from eho.server.service import api

from eho.server.utils.api import Rest, render, abort_and_log, request_data


rest = Rest('v01', __name__)


@rest.get('/node-templates')
def templates_list():
    try:
        return render(templates=[nt.dict for nt in api.get_node_templates()])
    except Exception, e:
        abort_and_log(500, "Exception while listing NodeTemplates: %s" % e)


@rest.post('/node-templates')
def templates_create():
    data = request_data()
    try:
        return render(api.create_node_template(data).dict)
    except Exception, e:
        abort_and_log(500, "Exception while adding NodeTemplate: %s" % e)


@rest.get('/node-templates/<template_id>')
def templates_get(template_id):
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


@rest.put('/node-templates/<template_id>')
def templates_update(template_id):
    raise NotImplementedError("Template update op isn't implemented (id '%s')"
                              % template_id)


@rest.delete('/node-templates/<template_id>')
def templates_delete(template_id):
    api.terminate_node_template(id=template_id)
    return render()


@rest.get('/clusters')
def clusters_list():
    try:
        return render(clusters=[c.dict for c in api.get_clusters()])
    except Exception, e:
        abort_and_log(500, 'Exception while listing Clusters: %s' % e)


@rest.post('/clusters')
def clusters_create():
    data = request_data()
    try:
        return render(api.create_cluster(data).dict)
    except Exception, e:
        abort_and_log(500, "Exception while adding new Cluster: %s" % e)


@rest.get('/clusters/<cluster_id>')
def clusters_get(cluster_id):
    c = None
    try:
        c = api.get_cluster(id=cluster_id)
    except Exception, e:
        abort_and_log(500, 'Exception while getting Cluster with id '
                           '\'%s\': %s' % (cluster_id, e))

    if c is None:
        abort_and_log(404, 'Cluster with id \'%s\' not found' % cluster_id)

    return render(c.dict)


@rest.put('/clusters/<cluster_id>')
def clusters_update(cluster_id):
    raise NotImplementedError("Cluster update op isn't implemented (id '%s')"
                              % cluster_id)


@rest.delete('/clusters/<cluster_id>')
def clusters_delete(cluster_id):
    api.terminate_cluster(id=cluster_id)
    return render()
