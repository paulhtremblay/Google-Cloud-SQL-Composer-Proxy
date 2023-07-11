import os
import subprocess
import configparser
from yaml import load, dump
import yaml
import pprint
import shutil
import argparse
pp = pprint.PrettyPrinter(indent=4)

class CreateProxyError(Exception):
    pass

def _get_args():
    parser = argparse.ArgumentParser(description = 'create proxy from confi file')
    parser.add_argument('path')
    parser.add_argument('--verbose', '-v', help = 'verbosity level', type = int, default = 0)
    parser.add_argument('--yaml', '-y', help = 'just create yaml', action = 'store_true')
    return  parser.parse_args()

def get_yaml_service(path):
    """
    helper function
    """
    with open(path, 'r') as read_obj:
        d = yaml.safe_load(read_obj)
    pp.pprint(d)

def get_configs(path):
    config = configparser.ConfigParser()
    config.read(path)
    return dict(config.items('default'))

    dir_path = os.path.dirname(os.path.abspath(path))
    config_path = os.path.join(dir_path, path)
    if not os.path.isfile(config_path):
        raise ValueError('no path')
    config.read(config_path)
    return dict(config.items('default'))

def _run_subprocess(args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        raise CreateProxyError(result.stderr.decode('utf8'))
    return result

def create_service_account(work_dir, ksa_name, verbose = 0,
                           just_yaml = False):
    if verbose >1:
        print('creating KSA service account')
    ser = {'apiVersion': 'v1', 'kind': 'ServiceAccount', 'metadata': {'name': ksa_name}}
    ser_path = os.path.join(work_dir, 'service_account.yaml')
    with open(ser_path, 'w') as write_obj:
        yaml.dump(ser, write_obj)
    args = ['kubectl', 'apply', '-f',  ser_path]  
    if just_yaml:
        if verbose:
            print(f'created yaml file "{ser_path}"')
        return
    result = _run_subprocess(args = args)
    if verbose > 0:
        print(f'created KSA service "{ksa_name}"')

def create_workload_identity(cluster_name, project_id, region_name,
                             verbose = 0):
    if verbose >1:
        print('creating workload identity')
    args = ['gcloud', 'container', 'clusters', 'update', 
            '--region', region_name,
            cluster_name, '--workload-pool', f'{project_id}.svc.id.goog'
            ]
    result = _run_subprocess(args = args)
    if verbose > 0:
        print(f'created workload identity for project "{project_id}" and cluster "{cluster_name}"')

def bind_ksa_gsa(project_id, ksa_name, service_account, 
                 verbose = 0):
    if verbose > 1:
        print('creating GSA-KSA binding')
    args = ['gcloud', 'iam', 'service-accounts', 'add-iam-policy-binding', 
            '--role','roles/iam.workloadIdentityUser', 
            '--member', f'serviceAccount:{project_id}.svc.id.goog[default/{ksa_name}]', 
            service_account
            ]
    if verbose > 2:
        print('args are')
        print(args)

    result = _run_subprocess(args = args)
    if verbose > 0:
        print(f'created binding between "{ksa_name}" and "{service_account}" ')
        print(result.stdout.decode('utf8'))

def annotate_ksa(ksa_name, service_account, verbose = 0):
    if verbose > 1:
        print('annotating GSA-KSA binding')
    args = ['kubectl', 'annotate', 'serviceaccount', 
            ksa_name,
            f'iam.gke.io/gcp-service-account={service_account}',
            ]
    if verbose > 2:
        print('args are')
        print(args)

    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        msg = 'error: at least one annotation update is required'
        msg2= ' --overwrite is false but found the following declared annotation(s)'
        if msg in result.stderr.decode('utf8') or msg2 in result.stderr.decode('utf8'):
            if verbose > 0:
                print(f'annotation {ksa_name}, {service_account} already exists')
            return
        else:
            raise CreateProxyError(result.stderr.decode('utf8'))

    if verbose > 0:
        print(f'annotated binding between "{ksa_name}" and "{service_account}" ')

def create_kubetcl_secret(db_secret_name,
                          db_user_name,
                          db_name,
                          verbose = 0):
    if verbose >1:
        print('creating kubernetes secret')
    args = ['kubectl', 'create', 'secret', 
            'generic', db_secret_name, 
            '--from-literal',f'username={db_user_name}', 
            '--from-literal','password={PW}'.format(
                PW= os.environ['PROXY_DB_PASSWORD']),
            '--from-literal',f'database={db_name}'
            ]
    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        already_exists = f'secrets "{db_secret_name}" already exists'
        if already_exists in result.stderr.decode('utf8'):
            if verbose > 0:
                print(f'secret {db_secret_name} already exists')
            return
        else:
            raise CreateProxyError(result.stderr.decode('utf8'))
    if verbose > 0:
        print(f'created secret for {db_secret_name}, for user {db_user_name} and database {db_name}')


def create_sidecar(work_dir,
                    deployment_name, 
                   cluster_name,
                   db_secret_name,
                   db_port,
                   instance_connection_name,
                   ksa_name,
                   just_yaml = False,
                   verbose = 0):
    if verbose >1:
        print('creating sidecar')
    d = {   'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'name': deployment_name},
    'spec': {   'selector': {'matchLabels': {'app': cluster_name}},
                'template': {   'metadata': {   'labels': {   'app': cluster_name}},
                                'spec': {   'containers': [   {   'args': [   '--structured-logs',
                                                                              '--address=0.0.0.0',
                                                                              f'--port={db_port}',
                                                                              instance_connection_name],
                                                                  'env': [   {   'name': 'DB_USER',
                                                                                 'valueFrom': {   'secretKeyRef': {   'key': 'username',
                                                                                                                      'name': db_secret_name}}},
                                                                             {   'name': 'DB_PASS',
                                                                                 'valueFrom': {   'secretKeyRef': {   'key': 'password',
                                                                                                                      'name': db_secret_name}}},
                                                                             {   'name': 'DB_NAME',
                                                                                 'valueFrom': {   'secretKeyRef': {   'key': 'database',
                                                                                                                      'name': db_secret_name}}}],
                                                                  'image': 'gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.1.0',
                                                                  'name': 'cloud-sql-proxy',
                                                                  'resources': {   'requests': {   'cpu': '1',
                                                                                                   'memory': '2Gi'}},
                                                                  'securityContext': {   'runAsNonRoot': True}}],
                                            'serviceAccountName': ksa_name}}}}

    side_path = os.path.join(work_dir, 'proxy_with_workload_identity.yaml')
    with open(side_path, 'w') as write_obj:
        yaml.dump(d, write_obj)
    if just_yaml:
        print(f'created yaml "{side_path}"')
        return
    args = ['kubectl', 'apply', '-f',  side_path]  
    result = _run_subprocess(args = args)
    if verbose > 0:
        print(f'created sidecar')
        print(result.stdout.decode('utf8'))

def create_service(work_dir,
                    deployment_name, 
                   cluster_name,
                   db_port,
                   just_yaml = False,
                   verbose = 0):
    d = {   'apiVersion': 'v1',
    'kind': 'Service',
    'metadata': {   'labels': {'run': f'{deployment_name}-service'},
                    'name': f'{deployment_name}-service'},
    'spec': {   'ports': [   {   'port': db_port,
                                 'protocol': 'TCP',
                                 'targetPort': db_port}],
                'selector': {'app': cluster_name},
                'type': 'ClusterIP'}}
    path = os.path.join(work_dir, 'service.yaml')
    with open(path, 'w') as write_obj:
        yaml.dump(d, write_obj)
    if just_yaml:
        print(f'created yaml "{path}"')
        return
    args = ['kubectl', 'apply', '-f',  path]  
    result = _run_subprocess(args = args)
    if verbose > 0:
        print(f'created service')
        print(result.stdout.decode('utf8'))

def make_work_dir(config_path, work_dir = None):
    if not work_dir:
        dir_path = os.path.dirname(os.path.abspath(config_path))
        work_dir = os.path.join(dir_path, 'proxy_work_dir')
    shutil.rmtree(work_dir, ignore_errors=True)
    os.mkdir(work_dir)
    return work_dir

def just_yaml(config_path, verbose):
    configs = get_configs(path = config_path)
    work_dir = make_work_dir(config_path = config_path)
    create_service_account(work_dir = work_dir, 
            ksa_name = configs['ksa_name'],verbose = verbose,
                           just_yaml = True
                           )
    create_sidecar(work_dir = work_dir,
                    deployment_name = configs['deployment_name'], 
                   cluster_name = configs['cluster_name'],
                   db_secret_name = configs['db_secret_name'],
                   db_port = configs['db_port'],
                   instance_connection_name = configs['instance_connection_name'],
                   ksa_name = configs['ksa_name'],
                   verbose = verbose,
                   just_yaml = True)
    create_service(work_dir,
                    deployment_name = configs['deployment_name'], 
                   cluster_name = configs['cluster_name'],
                   db_port = configs['db_port'],
                   just_yaml = True,
                   verbose = verbose)

def main(config_path, verbose):
    configs = get_configs(path = config_path)
    work_dir = make_work_dir(config_path = config_path)
    create_service_account(work_dir = work_dir, 
            ksa_name = configs['ksa_name'],verbose = verbose
                           )
    create_kubetcl_secret(db_secret_name = configs['db_secret_name'],
                          db_user_name = configs['db_user_name'],
                          db_name = configs['db_name'],
                          verbose = verbose
                          )
    create_workload_identity(cluster_name = configs['cluster_name'],
                             project_id = configs['project_id'],
                             region_name = configs['region_name'],
                             verbose = verbose
                             )


    bind_ksa_gsa(project_id = configs['project_id'], 
                            ksa_name = configs['ksa_name'], 
                            service_account = configs['service_account'], 
                            verbose = verbose)

    annotate_ksa(ksa_name = configs['ksa_name'], 
                     service_account = configs['service_account'], 
                     verbose = verbose)
    create_sidecar(work_dir = work_dir,
                    deployment_name = configs['deployment_name'], 
                   cluster_name = configs['cluster_name'],
                   db_secret_name = configs['db_secret_name'],
                   db_port = configs['db_port'],
                   instance_connection_name = configs['instance_connection_name'],
                   ksa_name = configs['ksa_name'],
                   verbose = verbose)

    create_service(work_dir,
                    deployment_name = configs['deployment_name'], 
                   cluster_name = configs['cluster_name'],
                   db_port = int(configs['db_port']),
                   verbose = verbose)

if __name__ == '__main__':
    args = _get_args()
    if args.yaml:
        just_yaml(config_path = args.path, verbose = args.verbose)
    else:
        main(config_path = args.path, verbose = args.verbose)
