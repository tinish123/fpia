import os
import sys
import re
import random
import threading, time
import ast
import numpy as np
import math
from pathlib import Path

import sys
import os
import jinja2
import shutil
import subprocess

from try_parameters import RunData
from try_parameters import PowerData


import concurrent.futures
from pathlib import Path
import matplotlib.pyplot as plt

import tempfile

VPR_EXECUTABLE = '/home/tinish/vtr-verilog-to-routing-2023/vpr/vpr'

class TilingExperimentManager:
    def job_build_dir(self, build_dir, num_inputs, num_outputs, num_channels, seed):
        return os.path.join(build_dir, f'{num_inputs}_{num_outputs}_{num_channels}_({seed})')



    def build_dir_job(self, build_dir):
        pattern = r'(\d+)_(\d+)_(\d+)_\((\d+)\)'
        match = re.match(pattern, os.path.basename(build_dir))

        if match:
            num_inputs = int(match.group(1))
            num_outputs = int(match.group(2))
            num_channels = int(match.group(3))
            seed = int(match.group(4))

            return num_inputs, num_outputs, num_channels, seed
        else:
            raise ValueError('Invalid build_dir format.')

    def __init__(self, blif_path, build_dir, arch_data_dir, **kwargs):
        self.blif_path   = blif_path
        self.build_dir   = build_dir
        self.archive = []
        
        if "area_assumption" in kwargs:
            self.area_assumption = kwargs["area_assumption"]
        else:
            self.area_assumption = None
            
        self.vpr_runtime_args = kwargs["vpr_runtime_constants"] if "vpr_runtime_constants" in kwargs.keys() else {
            "--full_stats": "on",
        }
        self.vpr_executable = kwargs["vpr_executable"] if "vpr_executable" in kwargs.keys() else VPR_EXECUTABLE
        self.place_mode = kwargs["place_mode"] if "place_mode" in kwargs.keys() else 1
        if self.place_mode==1:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_v3.xml"
        elif self.place_mode==3:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch.xml"
        elif self.place_mode==4:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_2clk.xml"
        elif self.place_mode==5:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_fb_sz.xml"
        elif self.place_mode==6:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_2clk_sep_clause_var_tracks.xml"
        elif self.place_mode==7:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_2clk_custom_sb.xml"
        elif self.place_mode==8:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_fb_sz_v2.xml"
        elif self.place_mode==9:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_power.xml"
        elif self.place_mode==10:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_openfpga_v1.xml"
        else:
            self.template_path = kwargs["arch_template"] if "arch_template" in kwargs.keys() else arch_data_dir+"arch_v2.xml"
            
        if "activity_file" in kwargs:
            self.activity_file = kwargs["activity_file"]
        else:
            self.activity_file = None
            
        if "vpr_power_tech_file" in kwargs:
            self.vpr_power_tech_file = kwargs["vpr_power_tech_file"]
        else:
            self.vpr_power_tech_file = None
            
    def create_arch(self, arch_params):
        
        template_path = Path(self.template_path)

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_path.parent)
        )

        template = env.get_template(template_path.name)

        #env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.getcwd()))
        #template = env.get_template(self.template_path)
        return template.render(arch_params)
    
    def prepare_run_dir(self, arch_params, run_params, build_dir):
        arch_contents = self.create_arch({v[0]: v[1] for (_,v) in arch_params.items()})
        arch_filename = f"arch.xml"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        with open(f"{build_dir}/{arch_filename}", 'w') as file:
            file.write(arch_contents)
        
        blif_filename = os.path.basename(self.blif_path)
        blif_dest = os.path.join(build_dir, blif_filename)
        shutil.copyfile(self.blif_path, blif_dest)

    def base_vpr_command(self, arch_params, run_params, arch_filename, seed):
        blif_filename = os.path.basename(self.blif_path)
        vpr_command = f"{self.vpr_executable} {arch_filename} {blif_filename}"
        for (k,v) in self.vpr_runtime_args.items():
            vpr_command += f" {k} {v}"
        vpr_command += f" --seed {seed}"
        for (_,v) in run_params.items():
            vpr_command += f" {v[0]} {v[1]}"
            
        return vpr_command

    def _run_vpr(self, vpr_command, build_dir, timeout=7200):
        try:
            log_stdout = open(build_dir + "/vpr_stdout.log", "a")
            log_stderr = open(build_dir + "/vpr.log", "a")
            result = subprocess.run(
                vpr_command.split(),
                shell=False,
                timeout=timeout,
                check=False,
                cwd=build_dir,
                stdout=log_stdout,
                stderr=log_stderr
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print("Timeout occurred.")
            return -1
        finally:
            log_stdout.close()
            log_stderr.close()

    def pack_vpr(self, arch_params, run_params, seed, build_dir):
        num_inputs = arch_params["num_inputs"][1]
        num_outputs = arch_params["num_outputs"][1]
        
        arch_contents = self.create_arch({v[0]: v[1] for (_,v) in arch_params.items()})
        arch_filename = f"arch_{num_inputs}_{num_outputs}.xml"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        with open(f"{build_dir}/{arch_filename}", 'w') as file:
            file.write(arch_contents)
            
        blif_filename = os.path.basename(self.blif_path)
        blif_dest = os.path.join(build_dir, blif_filename)
        shutil.copyfile(self.blif_path, blif_dest)
            
        vpr_command = self.base_vpr_command(arch_params, run_params, arch_filename, seed) + " --pack"
        pack_cmd_filename = build_dir + "/pack"
        with open(pack_cmd_filename, "w") as pack_cmd_file:
            pack_cmd_file.write(f"#! /bin/sh\n\n{vpr_command}")
        os.chmod(pack_cmd_filename, 0o755)

        retcode = self._run_vpr(vpr_command, build_dir)
        return retcode
    
    def place_vpr(self, arch_params, run_params, seed, build_dir):
        vpr_command = self.base_vpr_command(arch_params, run_params, "arch.xml", seed) + " --place"
        pack_cmd_filename = build_dir + "/pack"
        with open(pack_cmd_filename, "w") as pack_cmd_file:
            pack_cmd_file.write(f"#! /bin/sh\n\n{vpr_command}")
        os.chmod(pack_cmd_filename, 0o755)

        retcode = self._run_vpr(vpr_command, build_dir)
        return retcode
    
    def route_vpr(self, arch_params, run_params, seed, build_dir):
        vpr_command = self.base_vpr_command(arch_params, run_params, "arch.xml", seed) + " --route"
        pack_cmd_filename = build_dir + "/pack"
        with open(pack_cmd_filename, "w") as pack_cmd_file:
            pack_cmd_file.write(f"#! /bin/sh\n\n{vpr_command}")
        os.chmod(pack_cmd_filename, 0o755)

        retcode = self._run_vpr(vpr_command, build_dir)
        return retcode

    def pack(self, *args, **kwargs):
        self.pack_vpr(*args, **kwargs)

    def place(self, *args, **kwargs):
        self.place_vpr(*args, **kwargs)

    def route(self, *args, **kwargs):
        self.route_vpr(*args, **kwargs)
    
    def run_vpr_autochannels(self, arch_params, run_params, seed, explicit_autochannels=False, build_dir=None):
        num_inputs = arch_params["num_inputs"][1]
        num_outputs = arch_params["num_outputs"][1]
        # target_utilization = trial_config["target_utilization"]
        if build_dir == None:
            build_dir = self.job_build_dir(self.build_dir, num_inputs, num_outputs, -1, seed)
        # arch_params = {
        #     "NUM_INPUTS": num_inputs,
        #     "NUM_OUTPUTS": num_outputs,
        # }
        arch_contents = self.create_arch({v[0]: v[1] for (_,v) in arch_params.items()})
        arch_filename = f"arch_{num_inputs}_{num_outputs}.xml"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        with open(f"{build_dir}/{arch_filename}", 'w') as file:
            file.write(arch_contents)

        blif_filename = os.path.basename(self.blif_path)
        blif_dest = os.path.join(build_dir, blif_filename)
        shutil.copyfile(self.blif_path, blif_dest)

        vpr_command = f"{self.vpr_executable} {arch_filename} {blif_filename}"
        for (k,v) in self.vpr_runtime_args.items():
            vpr_command += f" {k} {v}"
        vpr_command += f" --seed {seed}"
        for (_,v) in run_params.items():
            vpr_command += f" {v[0]} {v[1]}"
        with open(build_dir + "/run_vpr", 'w') as f:
            f.write(f"!# /bin/sh\n\n{vpr_command}\n")
        os.chmod(build_dir + "/run_vpr", 0o755)

        try:
            log_stdout = open(build_dir + "/vpr_stdout.log", "w")
            log_stderr = open(build_dir + "/vpr.log", "w")
            result = subprocess.run(
                vpr_command.split(),
                shell=False,
                timeout=7200, # 120 minutes
                check=False,
                cwd=build_dir,
                stdout=log_stdout,
                stderr=log_stderr
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print("Timeout occurred.")
            return -1
        finally:
            log_stdout.close()
            log_stderr.close()

    def run_vpr(self, arch_params, run_params, seed, route_chan_width):
        num_inputs = arch_params["num_inputs"][1]
        num_outputs = arch_params["num_outputs"][1]
        # target_utilization = trial_config["target_utilization"]
        build_dir = self.job_build_dir(self.build_dir, num_inputs, num_outputs, route_chan_width, seed)
        # arch_params = {
        #     "NUM_INPUTS": num_inputs,
        #     "NUM_OUTPUTS": num_outputs,
        # }
        arch_contents = self.create_arch({v[0]: v[1] for (_,v) in arch_params.items()})
        arch_filename = f"arch_{num_inputs}_{num_outputs}.xml"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        with open(f"{build_dir}/{arch_filename}", 'w') as file:
            file.write(arch_contents)

        blif_filename = os.path.basename(self.blif_path)
        blif_dest = os.path.join(build_dir, blif_filename)
        shutil.copyfile(self.blif_path, blif_dest)

        vpr_command = f"{self.vpr_executable} {arch_filename} {blif_filename}"
        for (k,v) in self.vpr_runtime_args.items():
            vpr_command += f" {k} {v}"
        vpr_command += f" --seed {seed} --route_chan_width {route_chan_width}"
        for (_,v) in run_params.items():
            vpr_command += f" {v[0]} {v[1]}"
        with open(build_dir + "/run_vpr", 'w') as f:
            f.write(f"!# /bin/sh\n\n{vpr_command}\n")
        os.chmod(build_dir + "/run_vpr", 0o755)

        try:
            log_stdout = open(build_dir + "/vpr_stdout.log", "w")
            log_stderr = open(build_dir + "/vpr.log", "w")
            result = subprocess.run(
                vpr_command.split(),
                shell=False,
                timeout=7200, # 120 minutes
                check=False,
                cwd=build_dir,
                stdout=log_stdout,
                stderr=log_stderr
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print("Timeout occurred.")
            return -1
        finally:
            log_stdout.close()
            log_stderr.close()
            
    def run_vpr_autochannels_power(self, arch_params, run_params, seed, explicit_autochannels=False, build_dir=None):
        num_inputs = arch_params["num_inputs"][1]
        num_outputs = arch_params["num_outputs"][1]
        # target_utilization = trial_config["target_utilization"]
        if build_dir == None:
            build_dir = self.job_build_dir(self.build_dir, num_inputs, num_outputs, -1, seed)
        # arch_params = {
        #     "NUM_INPUTS": num_inputs,
        #     "NUM_OUTPUTS": num_outputs,
        # }
        arch_contents = self.create_arch({v[0]: v[1] for (_,v) in arch_params.items()})
        arch_filename = f"arch_{num_inputs}_{num_outputs}.xml"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        with open(f"{build_dir}/{arch_filename}", 'w') as file:
            file.write(arch_contents)

        blif_filename = os.path.basename(self.blif_path)
        blif_dest = os.path.join(build_dir, blif_filename)
        shutil.copyfile(self.blif_path, blif_dest)

        vpr_command = f"{self.vpr_executable} {arch_filename} {blif_filename}"
        for (k,v) in self.vpr_runtime_args.items():
            vpr_command += f" {k} {v}"
        vpr_command += f" --seed {seed}"
        for (_,v) in run_params.items():
            vpr_command += f" {v[0]} {v[1]}"
            
        if self.vpr_power_tech_file is None:
            print("Power Tech File Missing.....")
            sys.exit(1)
            
        if self.activity_file is None:
            print("Activity File Missing.....")
            sys.exit(1)
            
        vpr_command += " --power --tech_properties "+self.vpr_power_tech_file+" --activity_file "+self.activity_file
        with open(build_dir + "/run_vpr", 'w') as f:
            f.write(f"!# /bin/sh\n\n{vpr_command}\n")
        os.chmod(build_dir + "/run_vpr", 0o755)

        try:
            log_stdout = open(build_dir + "/vpr_stdout.log", "w")
            log_stderr = open(build_dir + "/vpr.log", "w")
            result = subprocess.run(
                vpr_command.split(),
                shell=False,
                timeout=7200, # 120 minutes
                check=False,
                cwd=build_dir,
                stdout=log_stdout,
                stderr=log_stderr
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print("Timeout occurred.")
            return -1
        finally:
            log_stdout.close()
            log_stderr.close()
            
    def run_vpr_power(self, arch_params, run_params, seed, route_chan_width):
        num_inputs = arch_params["num_inputs"][1]
        num_outputs = arch_params["num_outputs"][1]
        # target_utilization = trial_config["target_utilization"]
        build_dir = self.job_build_dir(self.build_dir, num_inputs, num_outputs, route_chan_width, seed)
        # arch_params = {
        #     "NUM_INPUTS": num_inputs,
        #     "NUM_OUTPUTS": num_outputs,
        # }
        arch_contents = self.create_arch({v[0]: v[1] for (_,v) in arch_params.items()})
        arch_filename = f"arch_{num_inputs}_{num_outputs}.xml"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        with open(f"{build_dir}/{arch_filename}", 'w') as file:
            file.write(arch_contents)

        blif_filename = os.path.basename(self.blif_path)
        blif_dest = os.path.join(build_dir, blif_filename)
        shutil.copyfile(self.blif_path, blif_dest)

        vpr_command = f"{self.vpr_executable} {arch_filename} {blif_filename}"
        for (k,v) in self.vpr_runtime_args.items():
            vpr_command += f" {k} {v}"
        vpr_command += f" --seed {seed} --route_chan_width {route_chan_width}"
        for (_,v) in run_params.items():
            vpr_command += f" {v[0]} {v[1]}"
            
        if self.vpr_power_tech_file is None:
            print("Power Tech File Missing.....")
            sys.exit(1)
            
        if self.activity_file is None:
            print("Activity File Missing.....")
            sys.exit(1)
            
        vpr_command += " --power --tech_properties "+self.vpr_power_tech_file+" --activity_file "+self.activity_file
        
        with open(build_dir + "/run_vpr", 'w') as f:
            f.write(f"!# /bin/sh\n\n{vpr_command}\n")
        os.chmod(build_dir + "/run_vpr", 0o755)

        try:
            log_stdout = open(build_dir + "/vpr_stdout.log", "w")
            log_stderr = open(build_dir + "/vpr.log", "w")
            result = subprocess.run(
                vpr_command.split(),
                shell=False,
                timeout=7200, # 120 minutes
                check=False,
                cwd=build_dir,
                stdout=log_stdout,
                stderr=log_stderr
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print("Timeout occurred.")
            return -1
        finally:
            log_stdout.close()
            log_stderr.close()
    
    def test_point(self, arch_params, run_params, seed, route_chan_width=-1, archive=True):
        num_inputs = arch_params["num_inputs"][1]
        num_outputs = arch_params["num_outputs"][1]
        build_dir = self.job_build_dir(self.build_dir, num_inputs, num_outputs, route_chan_width, seed)
        start_time = time.time()
        if route_chan_width==-1:
            retcode = self.run_vpr_autochannels(
                arch_params, run_params, seed
            )
        else:
            retcode = self.run_vpr(
                arch_params, run_params, seed, route_chan_width
            )
        end_time = time.time()
        print("VPR Run Time: ",end_time-start_time)
        netlist_filename = build_dir+'/'+os.path.basename(self.blif_path).replace('.blif','')+'.net'
        print("Final Netlist: ",netlist_filename)
        rundata = RunData(self.place_mode,build_dir + "/vpr_stdout.log")
        r = {
            "blif_path": self.blif_path,
            # "num_inputs": num_inputs,
            # "num_outputs": num_outputs,
            **{
                k:v[1] for (k,v) in arch_params.items()
            },
            "route_chan_width": rundata.route_chan_width if route_chan_width==-1 else route_chan_width,
            "seed": seed,
            # "target_utilization": run_params["target_utilization"][1],
            **{
                k:v[1] for (k,v) in run_params.items()
            },
            "PR_status": rundata.status,
            "netlist_filename": netlist_filename,
            "logic_block_area": rundata.logic_block_area,
            "routing_area": rundata.routing_area,
            "max_frequency": rundata.max_frequency,
            "clbs_total": rundata.clbs_total,
            "clbs_used": rundata.clbs_used,
        }
        
        if archive:
            # self.archive.loc[len(self.archive)] = r
            self.archive.append(r)
        return r
    
    def test_point_power(self, arch_params, run_params, seed, route_chan_width=-1, archive=True):
        num_inputs = arch_params["num_inputs"][1]
        num_outputs = arch_params["num_outputs"][1]
        build_dir = self.job_build_dir(self.build_dir, num_inputs, num_outputs, route_chan_width, seed)
        start_time = time.time()
        if route_chan_width==-1:
            retcode = self.run_vpr_autochannels_power(
                arch_params, run_params, seed
            )
        else:
            retcode = self.run_vpr_power(
                arch_params, run_params, seed, route_chan_width
            )
        end_time = time.time()
        print("VPR Time: ",end_time-start_time)
        netlist_filename = build_dir+'/'+os.path.basename(self.blif_path).replace('.blif','')+'.net'
        print(netlist_filename)
        rundata = RunData(self.place_mode,build_dir + "/vpr_stdout.log",netlist_filename)
        #print(os.path.basename(self.blif_path).replace('.blif','.power'))
        powerdata = PowerData(build_dir + "/" + os.path.basename(self.blif_path).replace('.blif','.power'))
        #print(powerdata)
        r = {
            "blif_path": self.blif_path,
            # "num_inputs": num_inputs,
            # "num_outputs": num_outputs,
            **{
                k:v[1] for (k,v) in arch_params.items()
            },
            "route_chan_width": rundata.route_chan_width if route_chan_width==-1 else route_chan_width,
            "seed": seed,
            # "target_utilization": run_params["target_utilization"][1],
            **{
                k:v[1] for (k,v) in run_params.items()
            },
            "PR_status": rundata.status,
            "netlist_filename": netlist_filename,
            "logic_block_area": rundata.logic_block_area,
            "routing_area": rundata.routing_area,
            "max_frequency": rundata.max_frequency,
            "clbs_total": rundata.clbs_total,
            "clbs_used": rundata.clbs_used,
            "sb_power": powerdata.sb_power,
            "cb_power": powerdata.cb_power,
            "global_routing_power": powerdata.global_routing_power,
            "clock_power": powerdata.clock_power,
            "total_routing_power": powerdata.sb_power+powerdata.cb_power+powerdata.global_routing_power+powerdata.clock_power,
        }
        
        if archive:
            # self.archive.loc[len(self.archive)] = r
            self.archive.append(r)
        return r
    