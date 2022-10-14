from kubernetes import client, config
import os
import schedule
import time
import json
# config.load_kube_config()
config.load_incluster_config()
api_instance = client.CoreV1Api()
def write_data(list_nodes):
    with open('./list_nodes.txt', 'w') as f:
        f.write(json.dumps(list_nodes))
def read_data() -> list:
    with open('./list_nodes.txt', 'r') as f:
        list_nodes = json.load(f)
    return list_nodes
def get_list_nodes() -> (bool, list):
    list_nodes = read_data()
    new_list_nodes = {"master": {}, "worker": {}}
    try:
        nodes = api_instance.list_node()
        for node in nodes.items:
            key = node.status.addresses[1].address
            value = node.status.addresses[0].address
            if (node.spec.taints != None):
                new_list_nodes["master"][key] = value
            else:
                new_list_nodes["worker"][key] = value
        if new_list_nodes != list_nodes:
            write_data(new_list_nodes)
            return True, new_list_nodes
        return False, list_nodes
    except Exception as e:
        print(e)
    return False, list_nodes

def update_config_file():
    global urls
    with open('./telegraf.conf', 'r', encoding='utf-8') as file:
        data = file.readlines()
    # print(data)
    data[14] = "  urls = {}\n".format(urls)
    with open('./telegraf.conf', 'w', encoding='utf-8') as file:
        file.writelines(data)

def restart_telegraf():
    global urls
    namespace = os.getenv("NAMESPACE")
    cmd = "kill -9 $(pgrep -f 'telegraf')"
    #cmd1 = "cp ./telegraf_template.conf ./telegraf.conf"
    cmd1 = "telegraf --config ./telegraf.conf &"
    check, list_nodes = get_list_nodes()
    if check:
        os.system(cmd)
        #os.system(cmd1)
        urls = ["http://kube-state-metrics.{}:8080/metrics".format(namespace),
                "http://ingress-nginx-controller-metrics.ingress-nginx:10254/metrics"]
        for node_name in list_nodes["master"].keys():
            urls.append("https://{}:6443/metrics".format(list_nodes["master"][node_name]))
            urls.append("https://kubernetes.default.svc/api/v1/nodes/{}/proxy/metrics/cadvisor".format(node_name))
            urls.append("https://kubernetes.default.svc/api/v1/nodes/{}/proxy/metrics".format(node_name))
            urls.append("http://{}:9253/metrics".format(list_nodes["master"][node_name]))
            urls.append("http://{}:9100/metrics".format(list_nodes["master"][node_name]))
        for node_name in list_nodes["worker"].keys():
            urls.append("https://kubernetes.default.svc/api/v1/nodes/{}/proxy/metrics/cadvisor".format(node_name))
            urls.append("https://kubernetes.default.svc/api/v1/nodes/{}/proxy/metrics".format(node_name))
            urls.append("http://{}:9253/metrics".format(list_nodes["worker"][node_name]))
            urls.append("http://{}:9100/metrics".format(list_nodes["worker"][node_name]))
        update_config_file()
        os.system(cmd1)
    else:
        print("Do nothing")
if __name__ == '__main__':
    restart_telegraf()
    schedule.every(1).minutes.do(restart_telegraf)
    while True:
        schedule.run_pending()
        time.sleep(1)