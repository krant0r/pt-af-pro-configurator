# af-pro-configurator.py
# конфигуратор для быстрого старта af-pro
# todo: не проверена работа с dhcp

__version__ = "0.1.1"

import sys
if sys.version_info < (3, 10, 5):
    print('Please upgrade your Python version to 3.10.4 or higher')
    sys.exit()
import argparse
# pip3 install ipcalc
import ipcalc

# pip3 install pandas
# pip3 install openpyxl
import pandas as pd

# выставим ширину вывода pandas-ы
pd.set_option('display.width', 300)
pd.set_option('display.max_columns', 50)

def main():
    # читаем параметры
    parser = argparse.ArgumentParser(prog="af-pro-configurator.py", prefix_chars="-", description="Конфигуратор конфигов для AF pro", usage="af-pro-configurator.py -e ""af-pro-configurator.xlsx"" -s ""Sheet1""")
    parser.add_argument("-e", "--excel", help="Excel file name", type=str, default="af-pro-configurator.xlsx", required=False)
    parser.add_argument("-s", "--sheet", help="Excel Sheet name", type=str, default="Sheet1", required=False)
    args = parser.parse_args()

    # загружаем Excel-файл
    df = read_excel(args.excel, args.sheet)

    # заменить NaN на ""
    df = df.fillna("")
    # получить узлы
    get_af_nodes(df)

    cmd = []
    cmd += create_config(df)

    # получить имя excel-файла
    from pathlib import Path
    filename = Path(args.excel).stem
    # распечатать команды
    with open(filename + ".txt", "w", encoding="utf-8", newline='\n') as txt_file:
        for line in cmd:
            txt_file.write(line + "\n")

    for x in cmd:
        print(x)

def create_config(df):
    clstr = []
    cmd = []
    hstn = []

    i = len(af_nodes)
    while i != 0:
        i -= 1
        if (af_nodes[i].node_role == ""):
            continue
            #break
        elif (len(af_nodes[i].node_role) > 0 and (af_nodes[i].ssh_password == "" or af_nodes[i].hostname == "" or af_nodes[i].eth0_ip == "")):
            print("Заполните все цветные поля или очистите!")
            exit(1)
        else:
            cmd.append('\n#\n# commands for ' + str(i+1) + ' node\n#')
            cmd.append('# зайти в ОС через консоль под login/pass - pt/positive\n#')
            cmd.append('# все команды выполняются из-под root')
            cmd.append('sudo su')
            cluster_ip = get_ip(af_nodes[i], "CLUSTER")[0]
            if cluster_ip == "None":
                print("Ошибка, не определен интерфейс с ролью CLUSTER!")
                exit(1)
            mgmt_ip, mgmt_eth, mgmt_mask, mgmt_gw = get_ip(af_nodes[i], "MGMT")
            if (mgmt_ip == "None"):
                mgmt_ip, mgmt_eth, mgmt_mask, mgmt_gw = get_ip(af_nodes[i], "WAN")
                if (mgmt_ip == "None"):
                    print("Ошибка, не определен интерфейс с ролью MGMT/WAN!")
                    exit(1)
            #if (i != 0):
            #    connect = 'sshpass -p ' + af_nodes[i].ssh_password + ' ssh -o StrictHostKeyChecking=accept-new -tt pt@' + \
            #              cluster_ip + ' -p 22013 bash -c \'echo ' + af_nodes[i].ssh_password + ' | sudo -S sh << EOF\n' + \
            #              af_nodes[i].ssh_password + '\n'
            #    cmd.append(connect)
            cmd.append('# настраиваем интерфейс управления')
            cmd.append("ifconfig " + mgmt_eth + " up")
            cmd.append("ip a add " + mgmt_ip + "/" + mgmt_mask + " dev " + mgmt_eth)
            if (len(mgmt_gw) > 0):
                cmd.append("ip route add default via " + mgmt_gw)
            cmd.append('#\n# подключаемся по SSH к серверу на MGMT интерфейс: ' + mgmt_ip + ":22013")
            cmd.append('# и выполняем команды ниже\n#')
            cmd.append('sudo su')
            cmd.append('# устанавливаем tmux, из-под которого будем работать (желательно изучить работу с ним)')
            cmd.append('apt-get install tmux -y; tmux')
            #commands.append('# отключаем cloud-init')
            #commands.append('touch /etc/cloud/cloud-init.disabled')
            #cmd.append('# отключаем автоматическое управление сетевыми интерфейсами в cloud-init')
            #cmd.append('mkdir -p /etc/cloud/cloud.cfg.d')
            #cmd.append('echo "network: {config: disabled}" > /etc/cloud/cloud.cfg.d/98-disable-network-config.cfg')
            cmd.append('# назначаем VIP-ы для manage, monitoring, border')
            cmd += vip(df)
            gwint = df.iloc[23]['param']
            cmd += eth(ip_addr=af_nodes[i].eth0_ip, mask=af_nodes[i].eth0_netmask, gw=af_nodes[i].eth0_gw, role=af_nodes[i].eth0_role, ethN="eth0", mode=af_nodes[i].eth0_mode, gwint=gwint)
            cmd += eth(ip_addr=af_nodes[i].eth1_ip, mask=af_nodes[i].eth1_netmask, gw=af_nodes[i].eth1_gw, role=af_nodes[i].eth1_role, ethN="eth1", mode=af_nodes[i].eth1_mode, gwint=gwint)
            cmd += eth(ip_addr=af_nodes[i].eth2_ip, mask=af_nodes[i].eth2_netmask, gw=af_nodes[i].eth2_gw, role=af_nodes[i].eth2_role, ethN="eth2", mode=af_nodes[i].eth2_mode, gwint=gwint)
            cmd += eth(ip_addr=af_nodes[i].eth3_ip, mask=af_nodes[i].eth3_netmask, gw=af_nodes[i].eth3_gw, role=af_nodes[i].eth3_role, ethN="eth3", mode=af_nodes[i].eth3_mode, gwint=gwint)
            cmd += dns(df)
            ntp_str = ntp(df)
            if (len(ntp_str) > 1):
                cmd += ntp_str
            cmd.append('# задаем hostname')
            hstn.append('echo "' + cluster_ip + " " + af_nodes[i].hostname + '" >> /etc/hosts')
            cmd.append('hostnamectl set-hostname ' + af_nodes[i].hostname)
            cmd.append('echo "'+ cluster_ip + " " + af_nodes[i].hostname + '" >> /etc/hosts')
            cmd.append('# задаем Timezone')
            cmd.append('wsc -c "timezone ' + df.iloc[31]['param'] + '"')

            cmd.append('\n#\n# после этой команды возможно прервется сеть, необходимо переподключиться в "sudo tmux a" и убедиться что commit прошел успешно и продолжить установку\n#')
            cmd.append('ip addr flush dev eth0 ; ip route flush dev eth0 ; ip addr flush dev eth1 ; ip route flush dev eth1 ; ip addr flush dev eth2 ; ip route flush dev eth2 ; ip addr flush dev eth3 ; ip route flush dev eth3 ; wsc -c "config commit force"')
            # commands.append('wsc -c "config commit"')

            role = ""
            if (af_nodes[i].node_role == "base-worker" or af_nodes[i].node_role == "base"):
                if (i == 0 or i == 1):
                    role = "master,worker-backend,postgresql,rabbitmq,minio,clickhouse"
                # если 5 узлов с ролью управления
                elif (i == 3 or i == 4) and (af_nodes[4].node_role == "base-worker" or af_nodes[4].node_role == "base"):
                    role = "master,worker-backend,postgresql,rabbitmq,minio,clickhouse"
                else:
                    role = "master,worker-backend,postgresql,rabbitmq,minio"
            elif (af_nodes[i].node_role == "worker"):
                role = "worker-traffic"
            if (af_nodes[i].node_role == "base-worker"):
                role = role + ",worker-traffic"

            clstr.append('wsc -c \'inventory node set ' + af_nodes[i].hostname + ' cluster_ip ' + cluster_ip + ' role ' + role + ' port 22013 user_name pt user_password ' +
                       af_nodes[i].ssh_password + ' sudo_password ' + af_nodes[i].ssh_password + '\'')
            # поскольку внизу массив clstr читаем с конца, то здесь обратный порядок (в начале set, потом add)
            clstr.append('wsc -c "inventory node add ' + af_nodes[i].hostname + '"')

            if (i != 0):
                #cmd.append('exit\nEOF\'\n')
                cmd.append('exit')
            if(i == 0):
                if (len(hstn) > 1):
                    cmd += hstn
                cmd.append('\n\n# настройка роли узла(ов)')
                cmd.append("# Важно! пароль должен совпадать. Если запустили с неправильным то нужно удалять и добавлять по новой \"inventory node del <name> force\"")
                cmd.append("# Узлов с ролью clickhouse должно быть четное число!")

                # добавляем узлы в кластер с base по worker (читаем массив clstr с конца)
                k = len(clstr)
                while k != 0:
                    k -= 1
                    cmd.append(clstr[k])
                cmd.append('wsc -c "inventory check"')
                cmd.append('wsc -c "inventory node list"')
                cmd.append('\n\n# установка инфраструктуры')
                if (len(ntp_str) != 0):
                    cmd.append('/var/pt/infra/current/install.sh')
                else:
                    cmd.append('# NTP НЕ УКАЗАН! (для продуктива рекомендуется указать)')
                    cmd.append('/var/pt/infra/current/install.sh --without-ntp')
                cmd.append('# установка Grafana')
                cmd.append('/var/pt/infra/current/install.sh --action=add_monitoring')
                #cmd.append('wsc -c "config commit"')
                cmd.append('# установка AF')
                cmd.append('/var/pt/ptaf-deploy/current/install.sh')

                cmd.append('#\n#\n# если установка завершилась без ошибок, то будет failed = 0')
                cmd.append('# подключаемся в UI под login/password - admin/positive и запрашиваем лицензию')
                cmd.append('# https://' + df.iloc[28]['node1'])
                cmd.append('# Grafana доступна по ссылке ниже, login/password - admin/admin')
                cmd.append('# https://' + df.iloc[28]['node1'] + ":3000")
    return(cmd)

def get_af_nodes(df):
    #
    # получаем данные по всем узлам
    #

    global af_nodes
    af_nodes = []
    for x in range(1, 11):
        af_nodes.append(AF_nodes(node_role=str(df.iloc[0]["node"+str(x)]),
                              hostname=str(df.iloc[2]["node" + str(x)]),
                              ssh_password=str(df.iloc[1]["node" + str(x)]),
                              eth0_ip=str(df.iloc[3]["node" + str(x)]),
                              eth0_netmask=str(df.iloc[4]["node" + str(x)]),
                              eth0_gw=str(df.iloc[5]["node" + str(x)]),
                              eth0_role=str(df.iloc[6]["node" + str(x)]),
                              eth0_mode=str(df.iloc[7]["node" + str(x)]),
                              eth1_ip=str(df.iloc[8]["node" + str(x)]),
                              eth1_netmask=str(df.iloc[9]["node" + str(x)]),
                              eth1_gw=str(df.iloc[10]["node" + str(x)]),
                              eth1_role=str(df.iloc[11]["node" + str(x)]),
                              eth1_mode=str(df.iloc[12]["node" + str(x)]),
                              eth2_ip=str(df.iloc[13]["node" + str(x)]),
                              eth2_netmask=str(df.iloc[14]["node" + str(x)]),
                              eth2_gw=str(df.iloc[15]["node" + str(x)]),
                              eth2_role=str(df.iloc[16]["node" + str(x)]),
                              eth2_mode=str(df.iloc[17]["node" + str(x)]),
                              eth3_ip=str(df.iloc[18]["node" + str(x)]),
                              eth3_netmask=str(df.iloc[19]["node" + str(x)]),
                              eth3_gw=str(df.iloc[20]["node" + str(x)]),
                              eth3_role=str(df.iloc[21]["node" + str(x)]),
                              eth3_mode=str(df.iloc[22]["node" + str(x)])))

class AF_nodes:
    #
    # узел AF
    #
    def __init__(self, node_role, hostname, ssh_password, eth0_ip, eth0_netmask, eth0_gw, eth0_role, eth0_mode, eth1_ip, eth1_netmask, eth1_gw, eth1_role, eth1_mode, eth2_ip, eth2_netmask, eth2_gw, eth2_role, eth2_mode, eth3_ip, eth3_netmask, eth3_gw, eth3_role, eth3_mode):
        self.node_role = node_role
        self.hostname = hostname
        self.ssh_password = ssh_password
        self.eth0_ip = eth0_ip
        self.eth0_netmask = eth0_netmask
        self.eth0_gw = eth0_gw
        self.eth0_role = eth0_role
        self.eth0_mode = eth0_mode
        self.eth1_ip = eth1_ip
        self.eth1_netmask = eth1_netmask
        self.eth1_gw = eth1_gw
        self.eth1_role = eth1_role
        self.eth1_mode = eth1_mode
        self.eth2_ip = eth2_ip
        self.eth2_netmask = eth2_netmask
        self.eth2_gw = eth2_gw
        self.eth2_role = eth2_role
        self.eth2_mode = eth2_mode
        self.eth3_ip = eth3_ip
        self.eth3_netmask = eth3_netmask
        self.eth3_gw = eth3_gw
        self.eth3_role = eth3_role
        self.eth3_mode = eth3_mode


def get_ip(node: AF_nodes, eth_role):
    #
    # получить IP-адрес интерфейса с указанной ролью
    #
    match eth_role:
        case node.eth0_role:
            return node.eth0_ip, "eth0", node.eth0_netmask, node.eth0_gw
        case node.eth1_role:
            return node.eth1_ip, "eth1", node.eth1_netmask, node.eth1_gw
        case node.eth2_role:
            return node.eth2_ip, "eth2", node.eth2_netmask, node.eth2_gw
        case node.eth3_role:
            return node.eth3_ip, "eth3", node.eth3_netmask, node.eth3_gw
        case _:
            return "None","None","None","None"

def vip(df):
    #
    # VIP
    #
    cmd = []
    cmd.append('wsc -c "vip set monitoring ' + df.iloc[28]['node1'] + '"')
    cmd.append('wsc -c "vip set manage ' + df.iloc[29]['node1'] + '"')
    cmd.append('wsc -c "vip set border ' + df.iloc[30]['node1'] + '"')
    return(cmd)

def eth(ip_addr,mask,gw,role,ethN,mode,gwint):
    #
    # настройка интерфейсов и маршрутов
    #

    cmd = []

    if (ip_addr != ""):
        if (mode == "static"):
            cmd.append('# настройка интерфейса ' + role)
            # если роль текущего интерфейса = интерфейсу на который вешаем дефолтный GW
            if(role == gwint):
                #commands.append('ip addr flush dev ' + ethN)
                if (ip_addr != ""):
                    if (gw != ""):
                        cmd.append('wsc -c "dhcp set routers false"')
                    cmd.append('wsc -c "if set ' + ethN + ' inet_method static inet_address ' + ip_addr + " inet_netmask " + mask + " inet_gateway " + gw + '"')
                if (role == "WAN"):
                    cmd.append('wsc -c "if set ' + ethN + ' role ' + gwint +'"')
            else:
                cmd.append('wsc -c "if set ' + ethN + ' inet_method static inet_address ' + ip_addr + " inet_netmask " + mask + '"')
                if (role == "WAN" or role == "CLUSTER"):
                    cmd.append('wsc -c "if set ' + ethN + ' role ' + role + '"')
                # если есть gw для LAN (для CLUSTER маршрут не добавляем, это должна быть изолировання подсеть)
                if (gw != "" and role != "CLUSTER"):
                    cmd.append('   # добавляем шлюз через отдельную таблицу для ' + role)
                    # номера таблиц должны отличаться, считаем, что у нас либо LAN, либо CLUSTER таблица
                    table_num = "128"
                    if (role == "LAN"):
                        table_num = "129"
                    cmd.append('wsc -c "route table add ' + ethN + ' ' + table_num + '"')
                    cmd.append('wsc -c "route add default via ' + gw + ' dev '+ ethN + ' table ' + ethN + '"')
                    cmd.append('wsc -c "route rule add '+ ethN + ' from ' + ip_addr + '/32 table ' + ethN  + '"')
                    cmd.append('wsc -c "route rule add '+ ethN + ' to ' + ip_addr + '/32 table ' + ethN  + '"')
                    addr = ipcalc.IP(ip=str(ip_addr), mask=str(mask))
                    cmd.append('wsc -c "route add ' + str(addr.guess_network()) + ' dev '+ ethN + ' src ' + ip_addr + ' table ' + ethN  + '"')
        else:
            print("Error: режим dhcp, но почему-то задан IP")
            exit(1)
    else:
        if (mode == "dhcp"):
            cmd.append('# настройка интерфейса ' + role)
            if (role == "WAN"):
                cmd.append('wsc -c "if set ' + ethN + ' role WAN"')
            elif (role == "CLUSTER"):
                cmd.append('wsc -c "if set ' + ethN + ' role CLUSTER"')
            return(cmd)
    #cmd.append('#')
    return(cmd)

def dns(df):
    #
    # DNS
    #
    cmd = []
    cmd.append("# Настройка DNS")
    if (df.iloc[27]['node1'] != ""):
        cmd.append('echo "nameserver ' + df.iloc[27]['node1'] + '" >> /etc/resolv.conf')
        if (df.iloc[27]['node2'] != ""):
            cmd.append('echo "nameserver ' + df.iloc[27]['node2'] + '" >> /etc/resolv.conf')
            if (df.iloc[27]['node3'] != ""):
                cmd.append('echo "nameserver ' + df.iloc[27]['node3'] + '" >> /etc/resolv.conf')
    return(cmd)

def ntp(df):
    #
    # NTP
    #
    cmd = []
    if (df.iloc[25]['node1'] != ""):
        cmd.append("# Настройка NTP")
        cmd.append('wsc -c "dhcp set ntp_servers false"')
        cmd.append('wsc -c "ntp add ' + df.iloc[25]['node1'] + '"')
        if (df.iloc[25]['node2'] != ""):
            cmd.append('wsc -c "ntp add ' + df.iloc[25]['node2'] + '"')
            if (df.iloc[25]['node3'] != ""):
                cmd.append('wsc -c "ntp add ' + df.iloc[25]['node3'] + '"')
    return(cmd)

def read_excel(excel_file, excel_sheet):
    #
    # Прочесть параметры AF pro, и вернуть в виде таблицы
    #

    # открываем файл Excel, и загружаем лист из него
    data = pd.read_excel(excel_file, sheet_name=excel_sheet)
    df = pd.DataFrame(data, columns=['param', 'node1', 'node2', 'node3', 'node4', 'node5', 'node6', 'node7', 'node8', 'node9', 'node10'])
    #print(df)
    return(df)

if __name__ == "__main__":
    # Вызов sys.exit() закрывает сессию интерпретатора
    # нужен import sys
    # sys.exit(main())
    main()