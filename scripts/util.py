#!/usr/bin/python3

# borrowed extensively from https://github.com/ccp-project/eval-scripts/blob/master/fct_scripts/fct_exp.py

import os.path
import subprocess as sh

CAIDA_FILE =  "./empirical-traffic-gen/CAIDA_CDF"
client_config_params = {"load": "72Mbps", "fanout": "1 100", "num_reqs": "100000", "req_size_dist": CAIDA_FILE}
outfile = "fct.log"
server_binary = "./empirical-traffic-gen/bin/server"
client_binary = "./empirical-traffic-gen/bin/client"

def write_mahimahi_trace(fn, mbps):
    num_lines = int(mbps/12)
    with open(fn, 'w') as f:
        for _ in range(num_lines):
            f.write("1\n")

def kill_processes(bin_name):
    awk_command = "awk '{printf $2;printf \" \";}'"
    content = sh.check_output("ps aux | grep {} | grep -v grep | {}".format(server_binary, awk_command), stderr=sh.STDOUT, shell=True)
    content = [x.strip().decode('utf-8') for x in content.split()]
    for process in content:
        sh.run("sudo kill -9 {}".format(process), shell=True)
    sh.run("killall {}".format(client_binary), stderr=sh.STDOUT, shell=True)
    sh.run("sudo pkill {}".format(bin_name), stderr=sh.STDOUT, shell=True)
    sh.run("sudo ccp-kernel/ccp_kernel_unload", shell=True)

# for server - spawn process to listen at specific port
def port(server_num):
    return str(5000 + server_num)

def write_client_config(config_filename, params, num_servers=50):
    with open(config_filename, "w") as f:
        for i in range(num_servers):
            f.write("server 100.64.0.1 {}\n".format(port(i)))
        for key in params:
            f.write("{} {}\n".format(key, params[key]))

def spawn_servers(alg, num_servers=50):
    for i in range(num_servers):
        sh.Popen(["{} -t {} -p {} >> /dev/null".format(server_binary, alg, port(i))], shell=True)

def spawn_clients(mahimahi_file, rtt, exp_config, logname):
    delay = int(rtt / 2) # mm-delay adds the delay in both directions

    # run mahimahi, set fq on the interface & run the client file
    mahimahi_command = "mm-delay {} \
        mm-link {} {} --downlink-queue=droptail --downlink-queue-args=\'packets=800\' \
        ./scripts/client_script.sh {} {} {}"
    mahimahi_command = mahimahi_command.format(delay, mahimahi_file, mahimahi_file, exp_config, logname, client_binary)
    # command to set fq on the interface
    find_mahimahi = "sleep 1;\
        x=$(ifconfig | grep delay | awk '{print $1}'| sed 's/://g') \
        && sudo tc qdisc add dev $x root fq && echo $x"
    processes = []
    for command in [mahimahi_command, find_mahimahi]:
        processes.append(sh.Popen(command, shell=True))
    return processes

def get_logname(algname, it):
    return "{}-{}-{}-{}-{}".format(algname, it, client_config_params['load'], client_config_params['num_reqs'], "CAIDA_CDF")

def get_log(logname, impl):
    awk_command = "awk '{{print $1,$2}}' {}_flows.out | \
        egrep -o '[0-9]+' | \
        paste -d ' ' - - | \
        awk '{{print $1,$2,\"{}\"}}' \
        > {}.fct".format(logname, impl, logname)
    sh.check_output(awk_command, shell=True)

def make_graph_file(algs, num_iters, outfile):
    sh.check_output("echo 'Size FctUs Impl' > {}".format(outfile), shell=True)
    for it in range(num_iters):
        for alg in algs:
            logname = get_logname(algname, it)
            sh.check_output("cat {}.fct >> {}".format(logname, outfile), shell=True)
            sh.check_output("rm {}_flows.out".format(logname), shell=True)
            sh.check_output("rm {}_reqs.out".format(logname), shell=True)
            sh.check_output("rm {}.fct".format(logname), shell=True)

def setup_ccp(alg_binary, alg_args, outprefix):
    sh.run("sudo pkill {}".format(alg_binary), shell=True)
    kmod_loaded = sh.check_output("lsmod | grep -c ccp || true", shell=True)
    if int(kmod_loaded.decode('utf-8')) == 0:
        sh.check_output("cd ccp-kernel && sudo ./ccp_kernel_load ipc=0", shell=True)

    # run portus
    sh.Popen("sudo {} {} > {} 2>&1".format(alg_binary, alg_args, os.path.join(outprefix, "ccp.log")), shell=True)

def get_logname(algname, it):
    return "{}-{}-{}-{}-{}".format(algname, it, client_config_params['load'], client_config_params['num_reqs'], "CAIDA_CDF")

def run_alg(algname, alg_binary, alg_args, outprefix, num_iters):
    kill_processes(alg_binary.split('/')[-1])

    # empirical traffic generator configuration
    client_config_name = "clientConfig"
    client_config_name = os.path.join(outprefix, client_config_name)
    if not os.path.isfile(client_config_name):
        write_client_config(client_config_name, client_config_params)

    # mahimahi trace file
    mahimahi_trace_fn = "bw96.mahi"
    if not os.path.isfile(mahimahi_trace_fn):
        mahimahi_file = write_mahimahi_trace(mahimahi_trace_fn, 96)

    for it in range(num_iters):
        setup_ccp(alg_binary, alg_args, outprefix)
        logname = os.path.join(outprefix, get_logname(algname, it))

        print("Starting {}".format(logname))

        spawn_servers('ccp')
        processes = spawn_clients(mahimahi_trace_fn, 20, client_config_name, logname)

        for proc in processes:
            proc.wait()

        kill_processes(alg_binary.split('/')[-1])
        get_log(logname, algname)

    #make_graph_file(NUM_EXPTS, outfile)
    #sh.check_output("{} {}".format(PLOTTING_SCRIPT, outfile), shell=True)

    ## shell = true
    #sh.check_output("rm {}".format(client_config_name), shell=True)
    #sh.check_output("rm ccp.log", shell=True)
    #sh.check_output("rm {}".format(outfile), shell=True)

if __name__ == '__main__':
    run_alg('reno', './portus/ccp_generic_cong_avoid/target/debug/reno', '--ipc=netlink', 'results', 1)
