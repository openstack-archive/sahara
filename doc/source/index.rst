Welcome to Elastic Hadoop on OpenStack documentation!
=====================================================

Create virtualenv that required for executing code and tests: ::

 # cd Elastic-Hadoop
 # tools/install_venv

Note, virtualenv needs to be updated any time code dependencies are changed.
Virtualenv is created in .venv folder.


REST API Doc Sample
-------------------

.. http:get:: /users/(int:user_id)/posts/(tag)

   The posts tagged with `tag` that the user (`user_id`) wrote.

   **Example request**:

   .. sourcecode:: http

      GET /users/123/posts/web HTTP/1.1
      Host: example.com
      Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/javascript

      [
        {
          "post_id": 12345,
          "author_id": 123,
          "tags": ["server", "web"],
          "subject": "I tried Nginx"
        },
        {
          "post_id": 12346,
          "author_id": 123,
          "tags": ["html5", "standards", "web"],
          "subject": "We go to HTML 5"
        }
      ]

   :query sort: one of ``hit``, ``created-at``
   :query offset: offset number. default is 0
           :query limit: limit number. default is 30
           :statuscode 200: no error
           :statuscode 404: there's no user


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


Docstring from code
-------------------
.. toctree::
    :maxdepth: 4

    apidoc/modules
