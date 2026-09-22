import os
import sys
import re
import random
import threading, time
import ast
import numpy as np
import math
from pysat.formula import CNF
from itertools import chain

area_assumption = []
power_assumption = []
area_assumption.append({
    "Afetmin" : 50,
    "Acell" : 60,
    "As" : 2500,
    "Ad" : 1500,
    "Asa" : 220,
    "Apewl" : 11500,
    "Apebl" : 0,
    "Swl" : 1000,
    "Sbl" : 1000,
})
area_assumption.append({
    "Afetmin" : 50,
    "Acell" : 180,
    "As" : 2500,
    "Ad" : 1500,
    "Asa" : 220,
    "Apewl" : 8200,
    "Apebl" : 5300,
    "Swl" : 1000,
    "Sbl" : 1000,
})
area_assumption.append({
    "Afetmin" : 50,
    "Acell" : 200,
    "As" : 1250,
    "Ad" : 1500,
    "Asa" : 220,
    "Apewl" : 1550,
    "Apebl" : 775,
    "Swl" : 1000,
    "Sbl" : 1000,
})

power_assumption.append({
    "Pcell" : 0.293,
    "Pd" : 1.88,
    "Ps" : 2.45,
})

def real_logic_area(results,area_assumptions=area_assumption,assume_mode="optimistic"):
    if assume_mode=="optimistic":
        ind = 0
    elif assume_mode=="pessimistic":
        ind = 1
    elif assume_mode=="sram":
        ind = 2
    
    nv_int_dim, nv_ext_dim, nc_int_dim, nc_ext_dim, new_xbar_size,_,_,_,_,_ = get_dualXbarSize(results["netlist_filename"],results["nvar"])
    tiles_per_side = math.ceil(results["clbs_total"]**(0.5))
    Axbar = new_xbar_size * area_assumptions[ind]["Acell"]*results["clbs_used"]
    Atilewl = (2*(nv_int_dim+nv_ext_dim)+nc_int_dim+nc_ext_dim) * area_assumptions[ind]["Ad"]*results["clbs_used"]
    Atilebl = (2*nv_int_dim+nc_int_dim) * (area_assumptions[ind]["As"])*results["clbs_used"]
    Apewltotal = tiles_per_side * (2*(nv_int_dim+nv_ext_dim)+nc_int_dim+nc_ext_dim) * area_assumptions[ind]["Apewl"] / area_assumptions[ind]["Swl"]
    Apebltotal = tiles_per_side * (2*nv_int_dim+nc_int_dim) * area_assumptions[ind]["Apebl"] / area_assumptions[ind]["Sbl"]
    
    if nc_int_dim >= nv_int_dim:
        tmp1 = results["num_outputs"] - nc_int_dim
        if tmp1 < nv_int_dim:
            config_area1 = nv_int_dim - tmp1
        else:
            config_area1 = 0
    else:
        tmp1 = results["num_outputs"] - nv_int_dim
        if tmp1 < nc_int_dim:
            config_area1 = nc_int_dim - tmp1
        else:
            config_area1 = 0
            
    if nc_ext_dim >= nv_ext_dim:
        tmp1 = results["num_inputs"] - nc_ext_dim
        if tmp1 < nv_ext_dim:
            config_area2 = nv_ext_dim - tmp1
        else:
            config_area2 = 0
    else:
        tmp1 = results["num_inputs"] - nv_ext_dim
        if tmp1 < nc_ext_dim:
            config_area2 = nc_ext_dim - tmp1
        else:
            config_area2 = 0
    
    #Aconfig = (results["num_inputs"]+results["num_outputs"])*area_assumptions[ind]["Asram"]
    Aconfig = (config_area1+config_area2)*area_assumptions[ind]["Asa"]*results["clbs_used"]
    
    return Axbar + Atilewl + Atilebl + Apewltotal + Apebltotal + Aconfig

def real_logic_power(results,power_assumptions=power_assumption,assume_mode="sram"):
    ind = 0
    
    nv_int_dim, nv_ext_dim, nc_int_dim, nc_ext_dim, new_xbar_size,_,_,_,_,_ = get_dualXbarSize(results["netlist_filename"],results["nvar"])
    Pxbar = new_xbar_size * power_assumptions[ind]["Pcell"]*results["clbs_used"]
    Ptilewl = (2*(nv_int_dim+nv_ext_dim)+nc_int_dim+nc_ext_dim) * power_assumptions[ind]["Pd"]*results["clbs_used"]
    Ptilebl = (2*nv_int_dim+nc_int_dim) * (power_assumptions[ind]["Ps"])*results["clbs_used"]
    
    return Pxbar + Ptilewl + Ptilebl
    
def real_logic_area_fixedXbar_gopt(results,area_assumptions=area_assumption,assume_mode="optimistic"):
    if assume_mode=="optimistic":
        ind = 0
    elif assume_mode=="pessimistic":
        ind = 1
    elif assume_mode=="sram":
        ind = 2
    
    nv_int_dim = results["nv_int_dim"]
    nv_ext_dim = results["nv_ext_dim"]
    nc_int_dim = results["nc_int_dim"]
    nc_ext_dim = results["nc_ext_dim"]
    new_xbar_size = 2*(nv_int_dim*(nc_ext_dim+nc_int_dim)+nc_int_dim*(nv_ext_dim+nv_int_dim))
    tiles_per_side = math.ceil(results["clbs_total"]**(0.5))
    Axbar = new_xbar_size * area_assumptions[ind]["Acell"]*results["clbs_used"]
    Atilewl = (2*(nv_int_dim+nv_ext_dim)+nc_int_dim+nc_ext_dim) * area_assumptions[ind]["Ad"]*results["clbs_used"]
    Atilebl = (2*nv_int_dim+nc_int_dim) * (area_assumptions[ind]["As"])*results["clbs_used"]
    Apewltotal = tiles_per_side * (2*(nv_int_dim+nv_ext_dim)+nc_int_dim+nc_ext_dim) * area_assumptions[ind]["Apewl"] / area_assumptions[ind]["Swl"]
    Apebltotal = tiles_per_side * (2*nv_int_dim+nc_int_dim) * area_assumptions[ind]["Apebl"] / area_assumptions[ind]["Sbl"]
    
    if nc_int_dim >= nv_int_dim:
        tmp1 = results["num_outputs"] - nc_int_dim
        if tmp1 < nv_int_dim:
            config_area1 = nv_int_dim - tmp1
        else:
            config_area1 = 0
    else:
        tmp1 = results["num_outputs"] - nv_int_dim
        if tmp1 < nc_int_dim:
            config_area1 = nc_int_dim - tmp1
        else:
            config_area1 = 0
            
    if nc_ext_dim >= nv_ext_dim:
        tmp1 = results["num_inputs"] - nc_ext_dim
        if tmp1 < nv_ext_dim:
            config_area2 = nv_ext_dim - tmp1
        else:
            config_area2 = 0
    else:
        tmp1 = results["num_inputs"] - nv_ext_dim
        if tmp1 < nc_ext_dim:
            config_area2 = nc_ext_dim - tmp1
        else:
            config_area2 = 0
    
    #Aconfig = (results["num_inputs"]+results["num_outputs"])*area_assumptions[ind]["Asram"]
    Aconfig = (config_area1+config_area2)*area_assumptions[ind]["Asa"]*results["clbs_used"]
    #Aconfig = (config_area1+config_area2)*area_assumptions[ind]["Asram"]
    
    return Axbar + Atilewl + Atilebl + Apewltotal + Apebltotal + Aconfig
    
def real_routing_area(results, area_assumptions=area_assumption, assume_mode="optimistic"):
    if assume_mode=="optimistic":
        ind = 0
    elif assume_mode=="pessimistic":
        ind = 1
    elif assume_mode=="sram":
        ind = 2
        
    return results["routing_area"] * area_assumptions[ind]["Afetmin"]


def get_MaxFanin(blif_filename):

    file = open(blif_filename, 'r')
    lines = file.readlines()
    max_fanin = 0
    for i,line in enumerate(lines):
        if ".names" in line:
            if len(lines[i+1].split()[0].split("1"))-1 > max_fanin:
                max_fanin = len(lines[i+1].split()[0].split("1"))-1
            
    return max_fanin

def get_dualXbarSize(net_filename,nvar):
    
    file = open(net_filename, 'r')
    lines = file.readlines()

    count = 0
    vpr_tile_inputs = []
    vpr_tile_outputs = []
    for i,line in enumerate(lines):
        if 'clb[' in line:
            tile_inputs = lines[i+2]
            tile_inputs = [int(j) for j in tile_inputs.split('>')[1].split('<')[0].replace("open","").replace("_x","").split()]
            tile_outputs_temp = lines[i+5]
            tile_outputs_temp = tile_outputs_temp.split('>')[1].split('<')[0].replace("open","").replace(" ","").split('-&gt;clbouts1')
            num_outputs = sum([1 for _ in tile_outputs_temp])-1
            curr_index = i+10
            output_lines_read = 0
            tile_outputs = []
            reached_end_of_clb = 0
            while reached_end_of_clb != 1:
                if "mode=\"default\"" in lines[curr_index] and "instance=\"ble[" in lines[curr_index]:
                    tile_outputs.append(int(lines[curr_index].split()[1].split("\"")[1].split("_l")[1]))
                    output_lines_read = output_lines_read + 1

                curr_index = curr_index + 1
                if 'clb[' in lines[curr_index] or '\"pclk\"' in lines[curr_index]:
                    reached_end_of_clb = 1

            vpr_tile_inputs.append(tile_inputs)
            vpr_tile_outputs.append(tile_outputs)

    num_clbs = len(vpr_tile_inputs)
    nv_int_arr = np.zeros((num_clbs,1))
    nv_ext_arr = np.zeros((num_clbs,1))
    nc_int_arr = np.zeros((num_clbs,1))
    nc_ext_arr = np.zeros((num_clbs,1))
    for i in range(num_clbs):
        input_temp = np.array(vpr_tile_inputs[i])
        output_temp = np.array(vpr_tile_outputs[i])
        nv_ext_arr[i] = len(np.where(input_temp<nvar+1)[0])
        nc_ext_arr[i] = len(np.where(input_temp>nvar)[0])
        nv_int_arr[i] = len(np.where(output_temp<nvar+1)[0])
        nc_int_arr[i] = len(np.where(output_temp>nvar)[0])

    nv_int_dim = np.max(nv_int_arr)
    nv_ext_dim = np.max(nv_ext_arr)
    nc_int_dim = np.max(nc_int_arr)
    nc_ext_dim = np.max(nc_ext_arr)
    new_xbar_size = 2*(nv_int_dim*(nc_ext_dim+nc_int_dim)+nc_int_dim*(nv_ext_dim+nv_int_dim))
    
    return nv_int_dim, nv_ext_dim, nc_int_dim, nc_ext_dim, new_xbar_size, np.min(nv_int_arr), np.min(nv_ext_arr), np.min(nc_int_arr), np.min(nc_ext_arr), num_clbs


def get_xbar_util_loss(net_filename,nvar):
    
    file = open(net_filename, 'r')
    lines = file.readlines()

    count = 0
    vpr_tile_inputs = []
    vpr_tile_outputs = []
    for i,line in enumerate(lines):
        if 'clb[' in line:
            tile_inputs = lines[i+2]
            tile_inputs = [int(j) for j in tile_inputs.split('>')[1].split('<')[0].replace("open","").replace("_x","").split()]
            tile_outputs_temp = lines[i+5]
            tile_outputs_temp = tile_outputs_temp.split('>')[1].split('<')[0].replace("open","").replace(" ","").split('-&gt;clbouts1')
            num_outputs = sum([1 for _ in tile_outputs_temp])-1
            curr_index = i+10
            output_lines_read = 0
            tile_outputs = []
            reached_end_of_clb = 0
            while reached_end_of_clb != 1:
                if "mode=\"default\"" in lines[curr_index] and "instance=\"ble[" in lines[curr_index]:
                    tile_outputs.append(int(lines[curr_index].split()[1].split("\"")[1].split("_l")[1]))
                    output_lines_read = output_lines_read + 1

                curr_index = curr_index + 1
                if 'clb[' in lines[curr_index] or '\"pclk\"' in lines[curr_index]:
                    reached_end_of_clb = 1

            vpr_tile_inputs.append(tile_inputs)
            vpr_tile_outputs.append(tile_outputs)

    num_clbs = len(vpr_tile_inputs)
    nv_int_arr = np.zeros((num_clbs,1))
    nv_ext_arr = np.zeros((num_clbs,1))
    nc_int_arr = np.zeros((num_clbs,1))
    nc_ext_arr = np.zeros((num_clbs,1))
    clb_xpoints_used = np.zeros((num_clbs,1))
    for i in range(num_clbs):
        input_temp = np.array(vpr_tile_inputs[i])
        output_temp = np.array(vpr_tile_outputs[i])
        nv_ext_arr[i] = len(np.where(input_temp<nvar+1)[0])
        nc_ext_arr[i] = len(np.where(input_temp>nvar)[0])
        nv_int_arr[i] = len(np.where(output_temp<nvar+1)[0])
        nc_int_arr[i] = len(np.where(output_temp>nvar)[0])
        clb_xpoints_used[i] = (nc_ext_arr[i]+nc_int_arr[i])*(nv_ext_arr[i]+nv_int_arr[i])*2

    nv_int_dim = np.max(nv_int_arr)
    nv_ext_dim = np.max(nv_ext_arr)
    nc_int_dim = np.max(nc_int_arr)
    nc_ext_dim = np.max(nc_ext_arr)
    new_xbar_size = 2*(nv_int_dim*(nc_ext_dim+nc_int_dim)+nc_int_dim*(nv_ext_dim+nv_int_dim))
    bidir_xbar_size = 2*(nv_int_dim+nv_ext_dim)*(nc_int_dim+nc_ext_dim)
    
    return np.sum(clb_xpoints_used)/(bidir_xbar_size*num_clbs)

def cnf2clausemat(nvar,clauses):
    nclause = len(clauses)
    clause_mat = np.zeros((nclause,nvar))
    for i in range(nclause):
        current_clause = clauses[i]
        for j in range(len(current_clause)):
            if current_clause[j] > 0:
                clause_mat[i,abs(current_clause[j])-1] = 1
            else:
                clause_mat[i,abs(current_clause[j])-1] = -1
                
    return clause_mat


def get_analysis(test_run,test_arch_params,test_run_params,num_iter=1,route_chan_width=-1,assume_mode="sram"):
    nvar = test_run.nvar
    nclause = test_run.nclause
    routing_area_arr = np.zeros((num_iter,1))
    tile_area_arr = np.zeros((num_iter,1))
    chan_width_arr = np.zeros((num_iter,1))
    err_indices = np.ones((num_iter,1))
    max_fop_arr = np.zeros((num_iter,1))
    output_dict = {}
    for i in range(num_iter):
        test_r = test_run.test_point(test_arch_params, test_run_params, np.random.randint(2**24), route_chan_width, archive=True)
        if test_r["PR_status"]=="Error":
            err_indices[i] = 0
        else:
            test_r["nvar"] = nvar
            test_r["nclause"] = nclause
            
            routing_area_arr[i,0] = real_routing_area(test_r,assume_mode=assume_mode)
            tile_area_arr[i,0] = real_logic_area(test_r,area_assumptions=area_assumption,assume_mode=assume_mode)
            
            max_fop_arr[i] = test_r["max_frequency"]
            chan_width_arr[i] = test_r["route_chan_width"]
            output_dict["clbs_used"] = test_r["clbs_used"]
            output_dict["clbs_total"] = test_r["clbs_total"]
            output_dict["num_inputs"] = test_r["num_inputs"]
            output_dict["num_outputs"] = test_r["num_outputs"]
            net_filename = test_r["netlist_filename"]
            nv_int_dim, nv_ext_dim, nc_int_dim, nc_ext_dim, new_xbar_size, _, _, _, _, _ = get_dualXbarSize(net_filename,nvar)
            output_dict["nv_int_dim"] = nv_int_dim
            output_dict["nv_ext_dim"] = nv_ext_dim
            output_dict["nc_int_dim"] = nc_int_dim
            output_dict["nc_ext_dim"] = nc_ext_dim
            output_dict["vpr_xbar_size"] = new_xbar_size
            output_dict["route_sr"] = np.mean(err_indices)

            output_dict["bidirec_xbar_nv"] = 2*(nv_int_dim+nv_ext_dim)
            output_dict["bidirec_xbar_nc"] = (nc_int_dim+nc_ext_dim)
            
        print("Completed Trials: ",(i+1)," of ",num_iter)
    
    output_dict["avg_routing_area"] = np.mean(routing_area_arr[np.where(err_indices==1)[0],0])
    output_dict["min_routing_area"] = np.min(routing_area_arr[np.where(err_indices==1)[0],0])
    output_dict["avg_tile_area"] = np.mean(tile_area_arr[np.where(err_indices==1)[0],0])
    
    output_dict["nvar"] = nvar
    output_dict["nclause"] = nclause
    output_dict["dataset_name"] = os.path.basename(test_run.blif_path).replace('.blif','')
    output_dict["chan_width"] = np.mean(chan_width_arr[np.where(err_indices==1)[0]])
        
    total_tile_area_in_mm2 = (output_dict["avg_tile_area"]*0.06*0.06)/(1000*1000)
    total_routing_area_in_mm2 = (output_dict["avg_routing_area"]*0.06*0.06)/(1000*1000)
    print("Successful Routing Trials: ",err_indices)
    print("CLBS USED/TOTAL: ",output_dict["clbs_used"],"/",output_dict["clbs_total"])
    print("Max Routing Frequency: ",np.mean(max_fop_arr[np.where(err_indices==1)[0],0])," MHz")
    print("FA XBAR: (",2*(nv_int_dim+nv_ext_dim),"x",nc_int_dim,"); BA XBAR: (",nc_int_dim+nc_ext_dim,"x",2*nv_int_dim,")")
    print("Total Area: ",total_tile_area_in_mm2+total_routing_area_in_mm2,"; XBAR: ",total_tile_area_in_mm2,"; Routing: ",total_routing_area_in_mm2)
        
    return output_dict


def get_power_analysis(test_run,test_arch_params,test_run_params,num_iter=1,route_chan_width=-1,assume_mode="sram"):
    nvar = test_run.nvar
    nclause = test_run.nclause
    routing_area_arr = np.zeros((num_iter,1))
    tile_area_arr = np.zeros((num_iter,1))
    chan_width_arr = np.zeros((num_iter,1))
    err_indices = np.ones((num_iter,1))
    tile_power_arr = np.zeros((num_iter,1))
    routing_power_arr = np.zeros((num_iter,1))
    max_fop_arr = np.zeros((num_iter,1))
    output_dict = {}
    for i in range(num_iter):
        test_r = test_run.test_point_power(test_arch_params, test_run_params, np.random.randint(2**24), route_chan_width, archive=True)
        if test_r["PR_status"]=="Error":
            err_indices[i] = 0
        else:
            test_r["nvar"] = nvar
            test_r["nclause"] = nclause
            
            routing_area_arr[i,0] = real_routing_area(test_r,assume_mode=assume_mode)
            tile_area_arr[i,0] = real_logic_area(test_r,area_assumptions=area_assumption,assume_mode=assume_mode)
            
            routing_power_arr[i,0] = test_r["total_routing_power"]
            tile_power_arr[i,0] = real_logic_power(test_r,assume_mode=assume_mode)/1000

            max_fop_arr[i] = test_r["max_frequency"]
            chan_width_arr[i] = test_r["route_chan_width"]
            
            output_dict["clbs_used"] = test_r["clbs_used"]
            output_dict["clbs_total"] = test_r["clbs_total"]
            output_dict["num_inputs"] = test_r["num_inputs"]
            output_dict["num_outputs"] = test_r["num_outputs"]
            net_filename = test_r["netlist_filename"]
            nv_int_dim, nv_ext_dim, nc_int_dim, nc_ext_dim, new_xbar_size, _, _, _, _, _ = get_dualXbarSize(net_filename,nvar)
            output_dict["nv_int_dim"] = nv_int_dim
            output_dict["nv_ext_dim"] = nv_ext_dim
            output_dict["nc_int_dim"] = nc_int_dim
            output_dict["nc_ext_dim"] = nc_ext_dim
            output_dict["vpr_xbar_size"] = new_xbar_size
            output_dict["bidirec_xbar_nv"] = 2*(nv_int_dim+nv_ext_dim)
            output_dict["bidirec_xbar_nc"] = (nc_int_dim+nc_ext_dim)
            
        print("Completed Trials: ",(i+1)," of ",num_iter)
    
    
    output_dict["route_sr"] = np.mean(err_indices)
        
    output_dict["avg_routing_area"] = np.mean(routing_area_arr[np.where(err_indices==1)[0],0])
    output_dict["min_routing_area"] = np.min(routing_area_arr[np.where(err_indices==1)[0],0])
    output_dict["avg_tile_area"] = np.mean(tile_area_arr[np.where(err_indices==1)[0],0])
    output_dict["avg_routing_power"] = np.mean(routing_power_arr[np.where(err_indices==1)[0],0])
    output_dict["avg_tile_power"] = np.mean(tile_power_arr[np.where(err_indices==1)[0],0])
    
    output_dict["nvar"] = nvar
    output_dict["nclause"] = nclause
    output_dict["dataset_name"] = os.path.basename(test_run.blif_path).replace('.blif','')
    output_dict["chan_width"] = np.mean(chan_width_arr[np.where(err_indices==1)[0]])
        
    total_tile_area_in_mm2 = (output_dict["avg_tile_area"]*0.06*0.06)/(1000*1000)
    total_routing_area_in_mm2 = (output_dict["avg_routing_area"]*0.06*0.06)/(1000*1000)
    print("Successful Routing Trials: ",err_indices)
    print("CLBS USED/TOTAL: ",output_dict["clbs_used"],"/",output_dict["clbs_total"])
    print("Max Routing Frequency: ",np.mean(max_fop_arr[np.where(err_indices==1)[0],0])," MHz")
    print("FA XBAR: (",2*(nv_int_dim+nv_ext_dim),"x",nc_int_dim,"); BA XBAR: (",nc_int_dim+nc_ext_dim,"x",2*nv_int_dim,")")
    print("Total Area: ",total_tile_area_in_mm2+total_routing_area_in_mm2,"; XBAR: ",total_tile_area_in_mm2,"; Routing: ",total_routing_area_in_mm2)
    print("Total Power: ",output_dict["avg_tile_power"]+output_dict["avg_routing_power"],"; XBAR: ",output_dict["avg_tile_power"],"; Routing: ",output_dict["avg_routing_power"])
        
    return output_dict
