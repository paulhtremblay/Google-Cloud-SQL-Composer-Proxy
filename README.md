This project both documents and provides a script to ceate a SQL proxy in Google Cloud Composer.  I am assuming you know why you need to create a proxy, as outlined here:

See: [Connect from Google Kubernetes Engine ](https://cloud.google.com/sql/docs/postgres/connect-kubernetes-engine)

Unfortunately, these instructions are hard to follow, and misleading, and probably inaccurate as well. There are also several blogs on how to do this, but these
seem outdated. Recent versions of Composer use namespaces in kubernetes, so much of the documentation (including that from Google itself) will not work.

The script will create a sql proxy connection for workload identity with the sidecar pattern. 


Detailed Creation
=================

1. Get the name of your Compser cluster. See the section below if you don't know this.


2. Install the kubectl client:
``` bash
gcloud components install gke-gcloud-auth-plugin
```

3. Create a config.ini file. See the examples

  * `ksa_name` can be anthing you want
  *  `cluster_name` the name of the cluster
  *  `region_name` name of region id of your cluster
  * `deployment_name` can be anyting
  * `db_secret_name` Optional, only if you need to create a kubernetes secret; can be anyting
  * `db_port` port of instance
  * `instance_connection_name` the name of your Cloud SQL instance, found in GCP console
  * `db_name` the name of db you are connecting to
  * `db_user_name` the name of db user you are connecting to
  * `service_account` can be anything
  * `project_id` project id

4. Run python scripts/create.py `<path to config>` 
  * use the -v option for verbosity. Default is no messaging. Use 1, 2, or 3 for more verbosity
  * use the -s or --use-secret if you want to create s kubernetes secret


Testing
=======

Get the identity of the worker pod (where composer has the workers, and where the connection to sql must exist):

```bash
kubectl get pods --all-namespaces
```

In the second column, look for a  name that is something like:  airflow-worker-xxxx. Note the name and the namespace for step 3


2. Check that the service was created 

```bash
kubectl get services --all-namespaces
```

You should see your service

3. connect to the worker pod: 

```bash
kubectl --namespace=<from step1> exec -it <from step 1>  bash

```

For postgres

```
psql -h <service-name>.default.svc.cluster.local --user <user> 
```

Getting Cluster Name
=====================

<img src="https://github.com/paulhtremblay/Google-Cloud-SQL-Composer-Proxy/blob/development/images/choose_composer.jpg?raw=true" alt="choose" width="200"/>

Click on your instance:

<img src="https://github.com/paulhtremblay/Google-Cloud-SQL-Composer-Proxy/blob/development/images/click_composer.jpg?raw=true" alt="click"/>

Click on "Environment Configuration"

<img src="https://github.com/paulhtremblay/Google-Cloud-SQL-Composer-Proxy/blob/development/images/choose_env_config.jpg?raw=true" alt="env-config"/>

Scroll down until you see the section "GKE Cluster". You cluster name is the string after the word "/clusters/"

<img src="https://github.com/paulhtremblay/Google-Cloud-SQL-Composer-Proxy/blob/development/images/composer_cluster_name.jpg?raw=true" alt="env-config"/>

This will be used in the config.ini file (see the examples), as well as for connecting to the cluster.

In addtion, get the region name. In this case, it is "us-west2"

