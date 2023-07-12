This project both documents and provides a script to ceate a SQL proxy in Google Cloud Composer.  I am assuming you know why you need to create a proxy, as outlined here:

See: [Connect from Google Kubernetes Engine ](https://cloud.google.com/sql/docs/postgres/connect-kubernetes-engine)

Unfortunately, these instructions are hard to follow, and misleading, and probably inaccurate as well. There are also several blogs on how to do this, but these
seem outdated. Recent versions of Composer use namespaces in kubernetes, so much of the documentation (including that from Google itself) will not work.

Outline
=======

Quick Creation
-------------

If you create a proper ini file, you can simply run:

```bash
python create.py <path-to-ini file>

```

This assumes you are already connected to the Composer cluster, you have created the service account with the right permissions, and 
have created a proper config file

Detailed Creation
----------------

1. Get the name of your Compser cluster. This can be found by going the GCP console, and choosing composer

<img src="https://github.com/paulhtremblay/Google-Cloud-SQL-Composer-Proxy/blob/development/images/choose_composer.jpg?raw=true" alt="choose" width="200"/>

Click on your instance:

<img src="https://github.com/paulhtremblay/Google-Cloud-SQL-Composer-Proxy/blob/development/images/click_composer.jpg?raw=true" alt="click"/>


https://medium.com/nerd-for-tech/connecting-gcp-composer-to-cloud-sql-via-proxy-305743a388a


FOR SCRIPT
==========
1. gcloud components install gke-gcloud-auth-plugin
2. get cluster name from gui; get region name from gui
3. create a service account in console dedicated to this task. Assign it Cloud SQL Client IAM role 

https://stackoverflow.com/questions/50154306/google-cloud-composer-and-google-cloud-sql

Check that the pod was created kubectl get pods --all-namespaces

Check that the service was created kubectl get services --all-namespaces

Jump into a worker node kubectl --namespace=composer-1-6-1-airflow-1-10-1-<some-uid> exec -it airflow-worker-<some-uid> bash

Test mysql connection mysql -u composer -p --host <service-name>.default.svc.cluster.local
