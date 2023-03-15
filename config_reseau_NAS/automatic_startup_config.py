import xml.etree.ElementTree as ET
import os
from pathlib import Path

tree = ET.parse("config_routers_NAS.xml")
root = tree.getroot()

#création du dossier dynamips et vérification bgp
try :
    os.mkdir("/project-files/dynamips")
except : 
    print("Dynamips existe déjà")
bgp_enable = eval(root.attrib["bgp"])

for as_elem in root.findall("as"):

    as_number = int(as_elem.attrib["number"])
    rip_enable = eval(as_elem.attrib["rip"])
    ospf_enable = eval(as_elem.attrib["ospf"])
    ip_subnet = as_elem.attrib["ip_address_subnet"]
    ip_mask = as_elem.attrib["ip_mask"]
    loopback_subnet = as_elem.attrib["loopback_subnet"]

    print(f"rip : {rip_enable}")
    print(f"ospf : {ospf_enable}")
    #liste sans doublons de tous les réseaux qui existent dans l'as
    set_networks_as = set()
    #nombre total de routers dans l'as
    how_many_routers = 0

    for router_elem in as_elem.findall("router"):
        how_many_routers +=1

    for router_elem in as_elem.findall("router"):

        #en partant du potulat qu'on nomme les routers("PE{as_number}{router_num}. router_id correspond au numéro du router au niveau des configs. router_br indique si le router est de bordure ou pas")
        router_name = str(router_elem.attrib["name"])
        router_num = int(router_elem.attrib["num"])
        router_PE = router_elem.attrib["PE"]

        #buffer pour fichiers de config
        config_lines = []

#*******************************************************************préli et config @loopback******************************************************************************
        config_lines.append(f"version 15.2\nservice timestamps debug datetime msec\nservice timestamps log datetime msec\n!\nhostname {router_name}\n!\nboot-start-marker\nboot-end-marker\n!\nno aaa new-model\nno ip icmp rate-limit unreachable\nip cef\n!\nno ip domain lookup\nipv6 unicast-routing\nipv6 cef\n!\nmultilink bundle-name authenticated\n!\nip tcp synwait-time 5\n!\n!")
        config_lines.append(f"interface Loopback0\nno ip address\nnegotiation auto")

        #config_lines.append(f"ipv4 address {loopback_subnet}/128")
        if rip_enable == True :
            config_lines.append(f"ip rip ripng enable")
        if ospf_enable == True :
            config_lines.append(f"ip ospf 100 area 1")
        config_lines.append(f"!")

#*******************************************************************config @ipv4 sur int correspondantes et activation rip/ospf*******************************************************************
        for neighbor_elem in router_elem.findall("neighbor"):
            
            neighbor_name = str(neighbor_elem.attrib["name"])
            neighbor_int = neighbor_elem.attrib["int"]
            neighbor_num = int(neighbor_elem.attrib["num"])

            #on veut que ca fonctionne en Fast et en Gigabit ethernet : 
            neighbor_int_tab = neighbor_int.split(" ")
            if str(neighbor_int_tab[0]) == "G" : 
                config_lines.append(f"interface GigabitEthernet{neighbor_int_tab[1]}/0")
            elif str(neighbor_int_tab[0]) == "F" : 
                config_lines.append(f"interface FastEthernet{neighbor_int_tab[1]}/0")

            if neighbor_num>router_num : 
                set_networks_as.add(f"{router_num}{neighbor_num}")
                config_lines.append(f"ip address {ip_subnet}{router_num}{neighbor_num}.{router_num} {ip_mask}")
            elif neighbor_num<router_num :  
                set_networks_as.add(f"{neighbor_num}{router_num}")
                config_lines.append(f"ip address {ip_subnet}{neighbor_num}{router_num}.{router_num} {ip_mask}")

            config_file.append("negocitation auto")
            if rip_enable == True :
                config_lines.append(f"ipv6 rip ripng enable")
            if ospf_enable == True :
                config_lines.append(f"ipv6 ospf 100 area {as_number}")
            config_lines.append(f"!")

#*******************************************************************config ospf*******************************************************************
        if ospf_enable == True :
            config_lines.append(f"router ospf 100")
            config_lines.append(f"")


#*******************************************************************config bgp préli******************************************************************************************
        if bgp_enable == True : 
            config_lines.append(f"router bgp {as_number}")
            config_lines.append(f"bgp router {as_number}{router_num}.{as_number}{router_num}.{as_number}{router_num}.{as_number}{router_num}")
            config_lines.append(f"bgp log-neighbor-changes")
            config_lines.append(f"no bgp default ipv4-unicast")
            config_lines.append(f"redistribute connected")

#*******************************************************************suite en fin config************************************************************************************
        config_lines.append(f"ip forward-protocol nd\n!\nno ip http server\nno ip http secure-server\n!")

        if rip_enable == True :
            config_lines.append(f"ipv6 router rip ripng")
        if ospf_enable == True :
            config_lines.append(f"ipv6 router ospf 100\nrouter-id {router_num}.{router_num}.{router_num}.{router_num}")
        config_lines.append(f"!\ncontrol-plane\n!\nline con 0\nexec-timeout 0 0\nprivilege level 15\nlogging synchronous\nstopbits 1\nline aux 0\nexec-timeout 0 0\nprivilege level 15\nlogging synchronous\nstopbits 1\nline vty 0 4\nlogin\n!\nend")
        

#*******************************************************************écriture dans les fichiers******************************************************************************
# gns3 fy
        id_chelou = 0
        if router_num == 1 :
            id_chelou = "62cd0337-d9cf-4364-bf19-b0ea089593e9"
        elif router_num == 2 :
            id_chelou =  "380fdfa4-d704-4e80-b769-3582eb938c21"
        elif router_num == 3 :
            id_chelou =  "2c679b1b-8eec-4f24-8d1c-0b61af2a72ae"
        elif router_num == 4 :
            id_chelou =  "0d402282-206f-4a86-9850-c2241253d22e"
        
        path = os.getcwd()+"/project-files/dynamips/"+str(id_chelou)+"/configs"
        #print(path)
        #try :
            #os.mkdir(path, mode = 0o777)
        #except OSError as e : 
            #print(os.strerror(e.errno))

        path = path+"/i"+str(router_num)+"_startup-config.cfg"
        with open(path, "w") as config_file:
            config_file.write("\n".join(config_lines))
