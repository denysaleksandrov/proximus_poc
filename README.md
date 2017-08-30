# Proximus poc 

Basic usage:
- add ipvpns
  
  ./add_ipvpn.py templates/devices ipvpn -n 2 -vid 2001 -nu 20 -nid 2201
  
- add epvn vpws instances 
  
  ./add_ipvpn.py templates/devices vpws -n 1 -vid 1

- add evpn vpls instances
  
  ./add_ipvpn.py templates/devices vpls -n 2 -vid 1001 -nid 701 -oid 101
  
- add "-pp" to any of the above in order to pretty print generated config insted of pushing it to PEs
