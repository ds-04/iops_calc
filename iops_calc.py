#!/usr/bin/env python3

# Author D SIMPSON 2024

# TODO:
# 1. multi config output
# 2. EC config/penalties - not just RAID


#IMPORTANT NOTE - Use at own risk !!!
#IMPORTANT NOTE - interpret results at own risk !!!

import argparse
import sys

# *** PREAMBLE AND PENALTY DICT ***

#EXAMPLE spec calculation
#TYPE: 2.5 SATA hard drive
#RPM: 10,000 RPM
#Av latency: 3 ms (0.003 seconds)
#Av seek time: 4.2 (r)/4.7 (w) = 4.45 ms (0.0045 seconds)
# 1 / (seek + latency) = IOPS
#IOPS approx: 1/(0.003 + 0.0045) = ~133 IOPS


INFO_STRING='''
# Numbers here a rough guide only
Drive Type       Average IOPS
7.2k rpm SATA    80 IOPs
10k rpm SATA     125 IOPs
10k rpm SAS      140 IOPS
15k rpm SAS      180 IOPS
SSD              6k IOPS

Reads from disk have no penalty, Writes to disk incur penalty due to raid parity.
'''

# 1 is no penalty
RAID_PENALTY_DICT={"RAID-1": 1, #JBOD MODE no penalty, here called RAID-1 to enable lookup
                   "RAID0": 1, 
                   "RAID1": 2, 
                   "RAID5": 4, 
                   "RAID6": 6,
                   "RAID10": 2}


# *** ARGS ***
parser = argparse.ArgumentParser(description="IOPs calculator for RAID/JBOD - Author D SIMPSON 2024",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#future feature
#parser.add_argument("-a", "--advanced_mode," type=int, default=40, help="advanced mode") #WIP FEATURE REQUEST - COMPARE MULTI CONFIG
#
# jbod mode
parser.add_argument("-j", "--jbod_mode", type=int, default=0, help="jbod mode")
# raid params
parser.add_argument("-r", "--readpc", type=int, default=75, help="read percent (default 75)")
parser.add_argument("-w", "--writepc", type=int, default=25, help="write percent (default 25)")
parser.add_argument("-p", "--raid_type_penalty", type=int, default=6, help="raid type, used to determine the raid penalty (default 6 for RAID6) - other options RAID=[0,1,5,6,10]")
parser.add_argument("-d", "--drives_per_group", type=int, help="drives per group (no default)")
parser.add_argument("-n", "--raid_groups_no", type=int, default=1, help="total number of raid groups")
# general params for raid and jbod
parser.add_argument("-t", "--total_drives", type=int, default=400, help="total drives (sum all raid groups)")
parser.add_argument("-s", "--drive_size", type=int, default=4, help="drives size TB (default 4TB)")
parser.add_argument("-i", "--iops", type=int, default=80, help="iops per drive (default 150)")
# output type
parser.add_argument("-c", "--csv", action='store_true', help="Print in csv form")
parser.add_argument("-o", "--table", action='store_true', help="Print in tabulate form")
parser.add_argument("-x", "--no_header", action='store_true', help="Suppress CSV/Table header")
parser.add_argument("-z", "--no_param_report", action='store_true', help="Suppress parameter report - options values are printed otherwise")
#
args = vars(parser.parse_args())


# *** VARS ***
#DRIVES and IOPS
DRIVES_SIZE=args["drive_size"] #-s
DRIVES_PGROUP=args["drives_per_group"] #-d
DRIVES_TOTAL=args["total_drives"] #-t
DRIVE_IOPS=args["iops"] #-i
GROUP_COUNT=args["raid_groups_no"] #-n

JBOD_MODE=args["jbod_mode"] #-j 0|1

#READ and WRITE
RPC=args["readpc"]
WPC=args["writepc"]
RAID_PENALTY=args["raid_type_penalty"]


# *** GLOBAL PASS/FAIL CHECKS ***

if args["csv"] != True and args["table"] != True:
   print("ERROR NO OUTPUT TYPE: choose output type -c --csv AND/OR -o --table")
   sys.exit(1)

if (JBOD_MODE not in [0,1]):
   print("JBOD MODE INVALID - HAS TO BE 0 or 1")
   sys.exit(1)
#If JBOD_MODE is active, then lookup RAID-1 and no penalty
if (JBOD_MODE in [1]):
   RAID_PENALTY=-1

# CHECK VALID RAID LEVEL -1 for JBOD
if (RAID_PENALTY not in [-1,0,1,5,6,10]):
   print("RAID TYPE INVALID")
   sys.exit(1)
# Dont accept drive less than 1TB
if DRIVES_SIZE < 1:
   print("ERROR - CANT HAVE A DRIVE SIZE < 1")
   sys.exit(1)
# JBOB or RAID0,1
if DRIVES_TOTAL < 2:
   print("ERROR - CANT HAVE DRIVE COUNT < 2")
   sys.exit(1)
#RAID 5 min 3 disk
if DRIVES_TOTAL < 3 and RAID_PENALTY in [5]:
   print("ERROR - CANT HAVE DRIVE COUNT < 3 AND RAID5")
   sys.exit(1)
#RAID 6,10 min 4 disk
if DRIVES_TOTAL < 4 and RAID_PENALTY in [6,10]:
   print("ERROR - CANT HAVE DRIVE COUNT < 4 AND RAID6 OR RAID10")
   sys.exit(1)   

# CHECK R/W RATIO
if (RPC+WPC) != 100:
   print("ERROR - READ / WRITE RATIO INVALID")
   print(str(RPC)+" "+str(WPC)+" != 100")
   sys.exit(1)

# CHECK RAID 10 DIVISIBLE BY 2
if RAID_PENALTY in [10] and ((DRIVES_TOTAL% 2) != 0):
   print("ERROR - RAID10 requires disk count is a multiple of 2")
   sys.exit(1)

# ***CAPACITY LOSS DUE TO RAID***
#JBOD or RAID0 STRIPE
if (RAID_PENALTY in [-1,0]):
   #force vars, all drives same
   DRIVES_PGROUP=DRIVES_TOTAL
   GROUP_COUNT=1
   RAID_CAPACITY=((DRIVES_PGROUP*DRIVES_SIZE)*GROUP_COUNT)
#RAID 1,10
if (RAID_PENALTY in [1,10]):
   if DRIVES_PGROUP is None:
     #force a global RAID
     DRIVES_PGROUP=DRIVES_TOTAL
     GROUP_COUNT=1
   RAID_CAPACITY=(((DRIVES_PGROUP*DRIVES_SIZE)*GROUP_COUNT)/2)
#RAID 5
if (RAID_PENALTY in [5]):
   if DRIVES_PGROUP is None:
     #force a global RAID
     DRIVES_PGROUP=DRIVES_TOTAL
     GROUP_COUNT=1
   RAID_CAPACITY=(((DRIVES_PGROUP-1)*DRIVES_SIZE)*GROUP_COUNT)
#RAID 6
if (RAID_PENALTY in [6]):
   if DRIVES_PGROUP is None:
     #force a global RAID
     DRIVES_PGROUP=DRIVES_TOTAL
     GROUP_COUNT=1
   RAID_CAPACITY=(((DRIVES_PGROUP-2)*DRIVES_SIZE)*GROUP_COUNT)

# CHECK DRIVES PER GROUP MAKES SENSE...
if (( DRIVES_PGROUP * GROUP_COUNT) != DRIVES_TOTAL):
   print("ERROR - TOTAL DRIVES != (DRIVES PER GROUP * RAID GROUP COUNT)")
   print(str(DRIVES_TOTAL)+"!="+str(DRIVES_PGROUP)+"*"+str(GROUP_COUNT))
   print(str(DRIVES_TOTAL)+"!="+str(DRIVES_PGROUP * GROUP_COUNT))
   sys.exit(1)


# LOOKUP RAID PENALTY FROM DICT
RAID_PENALTY_INT=RAID_PENALTY_DICT[str("RAID"+str(RAID_PENALTY))]


# ***CALCULATIONS ***
RAW_CAPACITY=int(DRIVES_TOTAL*DRIVES_SIZE)
RAW_IOPS=int(DRIVES_TOTAL*DRIVE_IOPS)
EFFICIENCY=float((RPC/100)+(float((WPC/100)*RAID_PENALTY_INT)))
FUNCT_RESULT=float(RAW_IOPS/EFFICIENCY)
FUNCTIONAL_IOPS_STR=(str(int(round(FUNCT_RESULT,0))))

# ***OUTPUT ***
if args["no_param_report"] != True:
   print("-------------------------------------------------------------------------------------------")
   print("")
   print("-s --drive_size - drive size       -  is set to: "+str(DRIVES_SIZE))
   print("-i --iops       - iops for drive   -  is set to: "+str(DRIVE_IOPS))
   print("-t --drives     - total drives     -  is set to: "+str(DRIVES_TOTAL))
   print("")
   # this is a RAID config
   if (JBOD_MODE in [0]):
      print("-d --drives_per_group -  is set to: "+str(DRIVES_PGROUP))
      print("-n --raid_groups_no  -  is set to: "+str(GROUP_COUNT))
      print("-r --readpc  - workload read %  -  is set to: "+str(RPC))
      print("-w --writepc - workload write % -  is set to: "+str(WPC))
      print("")
      print("-p --raid_type_penalty   is set to RAID: "+str(RAID_PENALTY))
      print("-j --jbod_mode           is set to INACTIVE: 0")
   # this is a JBOD config
   if (JBOD_MODE in [1]):
      print("-j --jbod_mode           is set to ACTIVE: 1")
   print("")


if args["csv"] == True:
   if (JBOD_MODE in [0]):
      csv_output=[str(DRIVES_SIZE),str(DRIVE_IOPS),str(DRIVES_TOTAL),str(RAW_CAPACITY),str(RAID_CAPACITY),str(RAW_IOPS),str(FUNCTIONAL_IOPS_STR),str(RPC),str(WPC),str(RAID_PENALTY),str(RAID_PENALTY_INT),str(DRIVES_PGROUP),str(GROUP_COUNT)]
      if args["no_header"] != True:
         headers =['DRIVE_SIZE','IOPS FOR DRIVE','TOTAL DRIVES','RAW_CAPACITY','RAID_CAPACITY','RAW_IOPS','FUNCTIONAL_IOPS','READ %','WRITE %','RAID TYPE','RAID PENALTY (1=none)','DRIVES PER RAID GROUP','NUMBER OF RAID GROUPS']
   if (JBOD_MODE in [1]):
      csv_output=[str(DRIVES_SIZE),str(DRIVE_IOPS),str(DRIVES_TOTAL),str(RAW_CAPACITY),str(RAID_CAPACITY),str(RAW_IOPS),str(FUNCTIONAL_IOPS_STR)]
      if args["no_header"] != True:    
         headers =['DRIVE_SIZE','IOPS FOR DRIVE','TOTAL DRIVES','RAW_CAPACITY','JBOD_CAPACITY','RAW_IOPS','FUNCTIONAL_IOPS']
   #print(headers)
   #print(csv_output)
   
   if args["no_header"] != True:
      headers_string = ",".join(str(element) for element in headers)
      print(headers_string)
  
   csv_output_string = ",".join(str(element2) for element2 in csv_output)
   print(csv_output_string)


if args["table"] == True:
   from tabulate import tabulate
   if (JBOD_MODE in [0]):
      table_output=[[str(DRIVES_SIZE),str(DRIVE_IOPS),str(DRIVES_TOTAL),str(RAW_CAPACITY),str(RAID_CAPACITY),str(RAW_IOPS),str(FUNCTIONAL_IOPS_STR),str(RPC),str(WPC),str(RAID_PENALTY),str(RAID_PENALTY_INT),str(DRIVES_PGROUP),str(GROUP_COUNT)]]
      if args["no_header"] != True:
         headers =['DRIVE_SIZE','IOPS FOR DRIVE','TOTAL DRIVES','RAW_CAPACITY','RAID_CAPACITY','RAW_IOPS','FUNCTIONAL_IOPS','READ %','WRITE %','RAID TYPE','RAID PENALTY (1=none)','DRIVES PER RAID GROUP','NUMBER OF RAID GROUPS']
   if (JBOD_MODE in [1]):
      table_output=[[str(DRIVES_SIZE),str(DRIVE_IOPS),str(DRIVES_TOTAL),str(RAW_CAPACITY),str(RAID_CAPACITY),str(RAW_IOPS),str(FUNCTIONAL_IOPS_STR)]]
      if args["no_header"] != True:
         headers =['DRIVE_SIZE','IOPS FOR DRIVE','TOTAL DRIVES','RAW_CAPACITY','JBOD_CAPACITY','RAW_IOPS','FUNCTIONAL_IOPS']
         
   if args["no_header"] != True:
      print(tabulate(table_output, headers, tablefmt="heavy_grid"))
   if args["no_header"] == True:
      print(tabulate(table_output, tablefmt="heavy_grid"))


