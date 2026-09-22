import os
import shutil
import time
import random
import subprocess
from create_arch import create_arch
from math import ceil
import numpy as np

class RunData:
    def __init__(self, place_mode, logfile=None, netlist_filename=None):

        self.logic_block_area = np.nan
        self.routing_area = np.nan
        self.clbs_used = np.nan
        self.clbs_total = np.nan
        self.big_clbs_total = np.nan
        self.big_clbs_used = np.nan
        self.max_frequency = np.nan
        self.route_chan_width = np.nan
        self.num_clbs_primary = np.nan
        self.num_clbs_secondary = np.nan

        if logfile is None:
            return

        self.status = 'FileError'

        try:
            with open(logfile, 'r') as log_file:
                self.status = 'Error'
                lines = log_file.readlines()
                for i,line in enumerate(lines):
                    if 'Total logic block area' in line:
                        self.logic_block_area = float(line.split(':')[-1].strip())
                    elif 'Total routing area:' in line:
                        self.routing_area = float(line.split(':')[1].split(',')[0])
                    elif 'blocks of type: clb' in line and 'Netlist' in lines[i-1]:
                        self.clbs_used = int(line.split()[0])
                    elif 'blocks of type: clb' in line and "Architecture" in lines[i-1]:
                        self.clbs_total = int(line.split()[0])
                    elif 'blocks of type: big_clb' in line and 'Netlist' in lines[i-1]:
                        self.big_clbs_used = int(line.split()[0])
                    elif 'blocks of type: big_clb' in line and "Architecture" in lines[i-1]:
                        self.big_clbs_total = int(line.split()[0])
                    elif 'Final critical path' in line and 'Fmax:' in line:
                        self.max_frequency = float(line.split('Fmax: ')[1].split(' MHz')[0])
                    elif 'successfully routed with a channel width factor' in line:
                        self.route_chan_width = float(line.split('of ')[1].split('.')[0])
                    elif 'VPR failed' in line:
                        self.status = 'Failed'
                    elif 'VPR succeeded' in line:
                        self.status = 'Success'
        except:
            pass

        if self.status == 'Success':
            if np.nan in [
                self.logic_block_area,
                self.routing_area,
                self.clbs_used,
                self.clbs_total,
                self.max_frequency
            ]:
                print('Could not find all run data')
            else:
                print('Found all run data')
        else:
                print(f'{self.status}')
                
class PowerData:
    def __init__(self, logfile=None):

        self.sb_power = np.nan
        self.cb_power = np.nan
        self.global_routing_power = np.nan
        self.clock_power = np.nan

        if logfile is None:
            print('Power Report Not Generated !!')
            return

        try:
            with open(logfile, 'r') as log_file:
                lines = log_file.readlines()
                for i,line in enumerate(lines):
                    if 'Switch Box' in line:
                        self.sb_power = float(line.split()[2])
                    elif 'Connection Box' in line:
                        self.cb_power = float(line.split()[2])
                    elif 'Global Wires' in line:
                        self.global_routing_power = float(line.split()[2])
                    elif 'Clock' in line:
                        self.clock_power = float(line.split()[1])
        except:
            pass

        if np.nan in [self.sb_power,self.cb_power,self.global_routing_power,self.clock_power]:
            print('Could not find all Power data')
        else:
            print('Found all Power data')