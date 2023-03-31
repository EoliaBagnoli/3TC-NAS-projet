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
i=1

for as_elem in root.findall("as"):

    as_number = int(as_elem.attrib["number"])
    rip_enable = eval(as_elem.attrib["rip"])
    ospf_enable = eval(as_elem.attrib["ospf"])
    mpls_enable = eval(as_elem.attrib["mpls"])
    ip_subnet = as_elem.attrib["ip_address_subnet"]
    ip_mask = as_elem.attrib["ip_mask"]
    loopback_subnet = as_elem.attrib["loopback_subnet"]
    loopback_mask = "255.255.255.255"

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
        router_PE = eval(router_elem.attrib["PE"])
        router_CE = eval(router_elem.attrib["CE"])
        liste_VRF = set()
        dico_VRF = {}

        #buffer pour fichiers de config
        config_lines = []
        
        if router_PE == True : 
            for neighbor_elem in router_elem.findall("neighbor"):
                if neighbor_elem.attrib["client"] == "True" : 
                    liste_VRF.add(neighbor_elem.attrib["VRF"])


#*******************************************************************config préli******************************************************************************
        config_lines.append(f"version 15.2\nservice timestamps debug datetime msec\nservice timestamps log datetime msec\n!\nhostname {router_name}\n!\nboot-start-marker\nboot-end-marker\n!")

#*******************************************************************définition du VRF******************************************************************************
        if router_PE == True : 
            for VRF in liste_VRF : 
                config_lines.append(f"vrf definition {VRF}")
                if VRF == "bleu" :
                    truc = "1:3"
                if VRF == "rouge" :
                    truc = "2:4"
                config_lines.append(f"rd {truc}")
                config_lines.append(f"route-target export {truc}")   
                config_lines.append(f"route-target import {truc}")  
                config_lines.append(f"!")
                config_lines.append(f"address-family ipv4")
                config_lines.append(f"exit-address-family")
                config_lines.append(f"!")
            config_lines.append(f"!")         
          
#*******************************************************************suite et fin config préli******************************************************************************                  
        config_lines.append(f"no aaa new-model\nno ip icmp rate-limit unreachable\nip cef\n!\nno ip domain lookup\nno ipv6 cef\n!\nmultilink bundle-name authenticated\n!\nip tcp synwait-time 5\n!\n!")
        
#*******************************************************************config mpls******************************************************************************
        """ if mpls_enable == True :
            config_lines.append(f"mpls ip")
            config_lines.append(f"mpls label protocol ldp")
            config_lines.append(f"!") """

#*******************************************************************config @loopback******************************************************************************
        config_lines.append(f"interface Loopback0")
        config_lines.append(f"ip address {loopback_subnet}{router_num} {loopback_mask}")
        if rip_enable == True :
            config_lines.append(f"ip rip ripng enable")
        if ospf_enable == True :
            config_lines.append(f"ip ospf 100 area 1 secondaries none")
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

            if router_PE == True and neighbor_elem.attrib["client"] == "True" :
                config_lines.append(f"vrf forwarding {neighbor_elem.attrib['VRF']}")

            if neighbor_num>router_num : 
                set_networks_as.add(f"{router_num}{neighbor_num}")
                link_address = f"{ip_subnet}{router_num}{neighbor_num}.{router_num}"
                config_lines.append(f"ip address {link_address} {ip_mask}")
            elif neighbor_num<router_num :  
                set_networks_as.add(f"{neighbor_num}{router_num}")
                link_address = f"{ip_subnet}{router_num}{neighbor_num}.{router_num}"
                config_lines.append(f"ip address {link_address} {ip_mask}")

            if router_PE == True and neighbor_elem.attrib["client"] == "True" : 
                if neighbor_num>router_num : 
                    remote_as_num = neighbor_elem.attrib["AS"]
                    neighbor_address = f"{ip_subnet}{router_num}{neighbor_num}.{neighbor_num} as {remote_as_num}"
                elif neighbor_num<router_num :  
                    remote_as_num = neighbor_elem.attrib["AS"]
                    neighbor_address = f"{ip_subnet}{router_num}{neighbor_num}.{neighbor_num} as {remote_as_num}"
                dico_VRF[neighbor_address] = neighbor_elem.attrib["VRF"]

            config_lines.append("negotiation auto")
            config_lines.append("no shutdown")
            if rip_enable == True :
                config_lines.append(f"ip rip ripng enable")
            if ospf_enable == True :
                if router_PE == False or (router_PE == True and neighbor_elem.attrib["client"] == "False") :
                    config_lines.append(f"ip ospf 100 area {as_number}")
            """ if mpls_enable == True :
                config_lines.append(f"mpls ip")
                config_lines.append(f"mpls ldp autoconfig") """
            config_lines.append(f"!")

#*******************************************************************config rip ospf******************************************************************************************
       
        if rip_enable == True :
            config_lines.append(f"ip router rip ripng")
        if ospf_enable == True :
            config_lines.append(f"router ospf 100\nrouter-id {router_num}.{router_num}.{router_num}.{router_num}")
            config_lines.append(f"mpls ldp autoconfig")
        config_lines.append(f"!")

#*******************************************************************config bgp préli******************************************************************************************
        if router_PE == True or router_CE == True : 
            config_lines.append(f"router bgp {as_number}")
            config_lines.append(f"bgp log-neighbor-changes")
            #config_lines.append(f"bgp log-neighbor-changes")
            #config_lines.append(f"redistribute connected")

#*******************************************************************bgp déclaration voisins*******************************************************************************

        if router_PE == True : 
            for neighbor_PE in as_elem.findall("router"):
                if neighbor_PE.attrib["PE"] == "True" and neighbor_PE.attrib["num"] != router_elem.attrib["num"] : 
                    neighbor_num = neighbor_PE.attrib["num"]
                    config_lines.append(f"neighbor 10.10.10.{neighbor_num} remote-as {as_number}")
                    config_lines.append(f"neighbor 10.10.10.{neighbor_num} update-source Loopback0")
            
        if router_CE == True :
            for neighbor_PE in router_elem.findall("neighbor"):
                neighbor_num = neighbor_PE.attrib["num"]
                neighbor_as = neighbor_PE.attrib["AS"]
                config_lines.append(f"network {loopback_subnet}{router_num} mask 255.255.255.240")
                config_lines.append(f"neighbor 10.10.10.{neighbor_num} remote-as {neighbor_as}")
                config_lines.append(f"neighbor 10.10.10.{neighbor_num} update-source Loopback0")
        
        config_lines.append(f"!")

#*******************************************************************config address family ******************************************************************************************
        if router_PE == True :
            config_lines.append(f"address-family ipv4")
            config_lines.append(f"network {loopback_subnet}{router_num} mask 255.255.255.240")
            for neighbor_PE in as_elem.findall("router"):
                if neighbor_PE.attrib["PE"] == "True" and neighbor_PE.attrib["num"] != router_elem.attrib["num"] : 
                    neighbor_num = neighbor_PE.attrib["num"]
                    config_lines.append(f"neighbor 10.10.10.{neighbor_num} activate")
            config_lines.append(f"exit-address-family")
        config_lines.append(f"!")


#*******************************************************************config VPN******************************************************************************************

        if router_PE == True :
            for routers in as_elem.findall("router"):
                if routers.attrib["PE"] == "True" and routers.attrib["num"] != router_elem.attrib["num"] : 
                    vpn4_neighbor_num = routers.attrib["num"]
                    config_lines.append(f"address-family vpnv4")
                    config_lines.append(f"neighbor 10.10.10.{vpn4_neighbor_num} activate")
                    config_lines.append(f"neighbor 10.10.10.{vpn4_neighbor_num} send-community extended")
                    config_lines.append(f"exit-address-family")
                    config_lines.append(f"!")

#*******************************************************************config VRF******************************************************************************************

        if router_PE == True :
            for VRF in liste_VRF : 
                config_lines.append(f"address-family ipv4 vrf {VRF}")
                config_lines.append(f"network {loopback_subnet}{router_num} mask 255.255.255.255")
                for i in dico_VRF.items() : 
                    if i[1] == VRF : 
                        name = i[0].split(" as ")
                        print(name)
                        config_lines.append(f"neighbor {name[0]} remote-as {name[1]}")
                        config_lines.append(f"neighbor {name[0]} activate")
                config_lines.append(f"exit-address-family")
                config_lines.append(f"!")



#*******************************************************************suite en fin config************************************************************************************
        config_lines.append(f"!\nip forward-protocol nd\n!\nno ip http server\nno ip http secure-server\n!")
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
        elif router_num == 5 :
            id_chelou =  "b23d42b0-7962-496c-8105-18bd5dca4c9f"
        elif router_num == 6 :
            id_chelou =  "ba57c209-668e-49ba-8286-3d3c36da5a19"
        elif router_num == 7 :
            id_chelou =  "16d20c03-ac13-473e-84bb-f39dad87ee00"
        elif router_num == 8 :
            id_chelou =  "8e5bab10-d167-4478-8efe-6000ec68eae0"
        
        path = os.getcwd()+"/project-files/dynamips/"+str(id_chelou)+"/configs"

        path = path+"/i"+str(router_num)+"_startup-config.cfg"
        with open(path, "w") as config_file:
            config_file.write("\n".join(config_lines))
