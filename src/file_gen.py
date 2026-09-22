import numpy as np
import os
from multiprocessing import Process
import concurrent.futures
import itertools
import copy
import pickle
import math

def create_blif(nvar,clauses,blif_filename):

    nclause = len(clauses)
    #CNF -> BLIF conversion where primary & secondary array LUTs are packed into different tiles by using two different clocks.
    #Both array comprises of LUT+FF molecules. It is not possible to define two different dimensions for the arrays.
    file = open(blif_filename, 'w')
    s = '.model top\n'
    file.write(s)
    s = '.inputs pclk\n'
    file.write(s)
    s = '.outputs _x1\n'
    file.write(s)
    num_inter_nets = nvar+nclause
    for i in range(num_inter_nets):
        s = '.latch _l'+str(i+1)+' _x'+str(i+1)+' re pclk 2\n'
        file.write(s)

    for i in range(nclause):
        prefix = '.names'
        suffix = ''
        fan_in = len(clauses[i])
        for j in range(fan_in):
            var = clauses[i][j]
            suffix = suffix + '1'
            prefix = prefix + ' _x' + str(abs(var))

        prefix = prefix + ' _l'+str(nvar+1+i)+'\n'
        file.write(prefix)
        suffix = suffix + ' 1\n'
        file.write(suffix)

    for i in range(nvar):
        var = i+1
        prefix = '.names'
        suffix = ''
        for j in range(nclause):
            temp_list = []
            #for kk in range(len(clauses[j])):
            #    temp_list.extend(abs(clauses[j][kk]))
            if var in np.abs(clauses[j]):
                prefix = prefix + ' _x' + str(nvar+j+1)
                suffix = suffix + '1'

        prefix = prefix + ' _l' + str(var)+'\n'
        suffix = suffix + ' 1\n'
        file.write(prefix)
        file.write(suffix)

    file.write('.end')
    file.close()
    
    
def gen_kSATprob(nvar,nclause,k):
    
    rng = np.random.default_rng()
    clause_mat = np.zeros((nclause,nvar))
    literal_arr = np.arange(1,2*nvar+1,1)
    for i in range(nclause):
        pass_flag = 0
        while pass_flag==0:
            
            literal_cand = rng.choice(literal_arr,k,replace=False)
            inv_literal_cand = np.array(literal_cand)
            clause_entry = np.zeros((1,nvar))
            neg_lit_ind = np.where(literal_cand>nvar)[0]
            pos_lit_ind = np.where(literal_cand<nvar+1)[0]
            if len(neg_lit_ind)!=0:
                inv_literal_cand[neg_lit_ind] = inv_literal_cand[neg_lit_ind] - nvar
                clause_entry[0,inv_literal_cand[neg_lit_ind]-1] = -1
            if len(pos_lit_ind)!=0:
                inv_literal_cand[pos_lit_ind] = inv_literal_cand[pos_lit_ind] + nvar
                clause_entry[0,literal_cand[pos_lit_ind]-1] = 1
            
            tautological_arr = np.intersect1d(literal_cand,inv_literal_cand)
            if len(tautological_arr)==0:
                if i!=0:
                    clause_entry_rep = np.repeat(clause_entry,i,axis=0)
                    clause_mat_curr = clause_mat[0:i,:]
                    temp1 = np.absolute(clause_mat_curr - clause_entry_rep)
                    temp2 = np.sum(temp1,axis=1)
                    if len(np.where(temp2==0)[0])==0:
                        pass_flag = 1
                        clause_mat[i,] = clause_entry
                    else:
                        pass_flag = 0
                else:
                    pass_flag = 1
                    clause_mat[i,] = clause_entry
            else:
                pass_flag = 0
                
    return clause_mat


def extract_blif_nets(blif_file):
    nets = set()

    with open(blif_file, "r") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            tokens = line.split()

            if tokens[0] == ".inputs":
                nets.update(tokens[1:])

            elif tokens[0] == ".outputs":
                nets.update(tokens[1:])

            elif tokens[0] == ".latch":
                # .latch <input> <output> [type control init-val]
                if len(tokens) >= 3:
                    nets.add(tokens[1])
                    nets.add(tokens[2])

                # Add clock/control signal if present
                if len(tokens) >= 5:
                    nets.add(tokens[4])

            elif tokens[0] == ".names":
                # All arguments after .names are nets
                nets.update(tokens[1:])

    return nets


def write_activity_file(nets, output_file, nvar, clock_name="pclk"):
    with open(output_file, "w") as f:
        for net in sorted(nets):
            if net == clock_name:
                probability = 0.5
                transition_density = 2.0
            else:
                if '_x' in net:
                    element_num = int(net.split('_x')[1])
                    if element_num<=nvar:
                        probability = 0.5
                        transition_density = 0.03
                    else:
                        probability = 0.33
                        transition_density = 0.13                
                else:
                    element_num = int(net.split('_l')[1])
                    if element_num<=nvar:
                        probability = 0.5
                        transition_density = 0.03
                    else:
                        probability = 0.33
                        transition_density = 0.13

            f.write(
                f"{net} {probability:.2f} {transition_density:.2f}\n"
            )
                
def clausemat2CNF(clause_mat,dir_name,cnf_file_name):
    nvar = clause_mat.shape[1]
    nclause = clause_mat.shape[0]
    k = len(np.where(clause_mat[0,]!=0)[0])
    filename = dir_name+cnf_file_name
    file = open(filename, 'w')
    file.write('p cnf '+str(nvar)+' '+str(nclause)+'\n')
    for i in range(nclause):
        var_indices = np.where(clause_mat[i,]!=0)[0]
        line = ''
        for j in range(len(var_indices)):
            if clause_mat[i,var_indices[j]]>0:
                line = line+str(var_indices[j]+1)+' '
            else:
                line = line+str(-var_indices[j]-1)+' '
        
        line = line + '0\n'
        file.write(line)
    
    file.close()
    

def WalkSat_Solver_full_multiCore(clause_mat,params,num_cores):
    
    max_restarts = params['max_restarts']
    iter_counter = 0
    walksat_result = np.zeros((max_restarts,2))
    rs_list = []
    a_counter = 0
    b_counter = 0
    c_counter = 0
    non_zero_restart_counter = 0
    for i in np.arange(0,max_restarts,1):
        rs_list.append(np.random.RandomState())
    with concurrent.futures.ProcessPoolExecutor(num_cores) as executor:
        pool = executor.map(WalkSat_Solver_multicore, rs_list, itertools.repeat(clause_mat), itertools.repeat(params))
        for res in pool:
            walksat_result[iter_counter,0] = res[0]
            walksat_result[iter_counter,1] = res[1]
            if iter_counter==0:
                winning_variable_stat = res[2]
                all_cand_variable_stat = res[3]
                all_clause_stat = res[4]
            else:
                winning_variable_stat = np.concatenate((winning_variable_stat,res[2]),axis=1)
                all_cand_variable_stat = np.concatenate((all_cand_variable_stat,res[3]),axis=1)
                all_clause_stat = np.concatenate((all_clause_stat,res[4]),axis=1)
                
            #if res[6]!=-1:
            #    a_counter = a_counter + res[6]
            #    b_counter = b_counter + res[7]
            #    c_counter = c_counter + res[8]
            #    non_zero_restart_counter = non_zero_restart_counter + 1
                
                
            iter_counter = iter_counter + 1    
            
    avg_flips, prob_s, std_flips, tts_99 = get_stats(walksat_result)
    
    #print("alpha_wl_ba: ",a_counter/non_zero_restart_counter)
    #print("alpha_pattern_fa: ",b_counter/non_zero_restart_counter)
    #print("alpha_pattern_ba: ",c_counter/non_zero_restart_counter)
    
    #return avg_flips, prob_s, std_flips, tts_99, walksat_result, winning_variable_stat, all_cand_variable_stat, all_clause_stat, a_counter/non_zero_restart_counter, b_counter/non_zero_restart_counter, c_counter/non_zero_restart_counter 
    return avg_flips, prob_s, std_flips, tts_99, walksat_result, winning_variable_stat, all_cand_variable_stat, all_clause_stat

def WalkSat_Solver_multicore(rs_list,clause_mat,params):
    
    nvar = clause_mat.shape[1]
    nclause = clause_mat.shape[0]
    cnf_mat = clausemat2cnfmat(clause_mat)
    
    max_flips = params['max_flips']
    p1 = params['p1']
    p2 = params['p2']   
    heuristics = params['heuristics']
    
    #np.random.seed(iter_num)
    var_val_mat = rand_init(nvar,rs_list)
    var_time_mat = np.zeros((nvar,1))
    num_flips = 0
    success_flag = 0
    clause_stat_mat, sat_result, clause_f_mat = sat_eval(var_val_mat,clause_mat)
    winning_variable_stat = np.zeros((4,max_flips))
    all_cand_variable_stat = np.zeros((4,max_flips))
    all_clause_stat = np.zeros((2,max_flips))
    
    #sz_active_count = 0
    #num_true_lit_count = 0
    #make_break_values = 0

    for f in range(max_flips):

        if sat_result == 1:
            num_flips = f
            success_flag = 1
            break
        
        #sz_active_count = sz_active_count + len(np.where(clause_f_mat<2)[0])
        #num_true_lit_count = num_true_lit_count + np.sum(clause_f_mat)
        
        unsat_clause_list = np.where(clause_stat_mat==0)[0]
        chosen_clause_ind = np.random.choice(unsat_clause_list,size=1)[0]
        #var_val_mat, var_time_mat, winning_variable_stat_temp, all_cand_variable_stat_temp, clause_stat_mat, sat_result, clause_f_mat, temp1 = general_heuristics(rs_list,p1,p2,var_val_mat,var_time_mat,clause_mat,cnf_mat,clause_f_mat,chosen_clause_ind,clause_stat_mat,heuristics)
        var_val_mat, var_time_mat, winning_variable_stat_temp, all_cand_variable_stat_temp, clause_stat_mat, sat_result, clause_f_mat = general_heuristics(rs_list,p1,p2,var_val_mat,var_time_mat,clause_mat,cnf_mat,clause_f_mat,chosen_clause_ind,clause_stat_mat,heuristics)
        
        #make_break_values = make_break_values + temp1
        
        winning_variable_stat[:,f] = winning_variable_stat_temp[:,0]
        if f==0:
            all_cand_variable_stat = all_cand_variable_stat_temp
            all_clause_stat = np.array([len(np.where(clause_f_mat==0)[0]),len(np.where(clause_f_mat==1)[0])]).reshape(2,1)
        else:
            all_cand_variable_stat = np.concatenate((all_cand_variable_stat,all_cand_variable_stat_temp),axis=1)
            all_clause_stat = np.concatenate((all_clause_stat,np.array([len(np.where(clause_f_mat==0)[0]),len(np.where(clause_f_mat==1)[0])]).reshape(2,1)),axis=1)

    if success_flag == 0:
        clause_stat_mat, sat_result, clause_f_mat = sat_eval(var_val_mat,clause_mat)
        num_flips = max_flips
        if sat_result == 1:
            success_flag = 1  
            
    if 'status_display' in params: 
        if params['status_display']==1:
            if success_flag==1:
                print("#Flips: ",num_flips,"; Success: ",success_flag,"**********************************************************")
            else:
                print("#Flips: ",num_flips,"; Success: ",success_flag)
    
    #if num_flips!=0:
    #    a_val = sz_active_count/(nclause*num_flips)
    #    b_val = num_true_lit_count/(nclause*num_flips*2*nvar)
    #    c_val = make_break_values/(nclause*num_flips)
    #else:
    #    a_val = -1
    #    b_val = -1
    #    c_val = -1
    
    #return num_flips, success_flag, winning_variable_stat[:,0:num_flips], all_cand_variable_stat, all_clause_stat, var_val_mat, a_val, b_val, c_val
    return num_flips, success_flag, winning_variable_stat[:,0:num_flips], all_cand_variable_stat, all_clause_stat, var_val_mat


def general_heuristics(rs_list,p1,p2,var_val,var_time,clause_mat,cnf_mat,clause_f_mat,clause_ind,clause_stat_mat,heur):
    
    nvar = len(var_val)
    nclause = clause_mat.shape[0]
    var_list = np.where(clause_mat[clause_ind,]!=0)[0]
    clause_stat_change_mat = np.zeros((len(var_list),1))
    var_break_value_mat = np.zeros((len(var_list),1))
    xx = rs_list.random()
        
    s_vec = np.zeros((nclause,1))
    z_vec = np.zeros((nclause,1))
    
    s_vec[np.where(clause_f_mat==0)[0],0] = 1
    z_vec[np.where(clause_f_mat==1)[0],0] = 1
     
    a_vec = np.transpose(cnf_mat)@s_vec
    b_vec = np.transpose(cnf_mat)@z_vec
    
    var1_indices = np.where(var_val==1)[0]
    var0_indices = np.where(var_val==0)[0]
    lit1_indices = np.sort(np.concatenate((2*var1_indices,2*var0_indices+1)))
    lit0_indices = np.sort(np.concatenate((2*var0_indices,2*var1_indices+1)))
    bv_vec = b_vec[lit1_indices]
    mv_vec = a_vec[lit0_indices]
    gain_vec = mv_vec - bv_vec
    rand_vec = p2*rs_list.normal(0,1,(nvar,1))
    winning_variable_stat = np.zeros((4,1))
    all_cand_variable_stat = np.zeros((4,1))

    if heur=="WSKC":
        var_break_value_mat = bv_vec[var_list]
        clause_stat_change_mat = gain_vec[var_list]
        break_value_zero_ind = np.where(var_break_value_mat==0)[0]
        if len(break_value_zero_ind)!=0:
            chosen_var = var_list[rs_list.choice(break_value_zero_ind,size=1)[0]]
        elif xx <= p1:
            chosen_var = rs_list.choice(var_list[np.where(clause_stat_change_mat==np.max(clause_stat_change_mat))[0]],size=1)[0]
        else:
            chosen_var = rs_list.choice(var_list,size=1)[0]

        var_val[chosen_var] = ~var_val[chosen_var]
        clause_stat_mat_new, sat_result_new, clause_f_mat_new = get_clause_stat(chosen_var,clause_ind,clause_mat,clause_stat_mat,clause_f_mat)
    elif heur=="WB":
        var_break_value_mat = bv_vec[var_list]
        clause_stat_change_mat = gain_vec[var_list]
        break_value_zero_ind = np.where(var_break_value_mat==0)[0]
        if len(break_value_zero_ind)!=0:
            chosen_var = var_list[rs_list.choice(break_value_zero_ind,size=1)[0]]
        elif xx <= p1:
            chosen_var = rs_list.choice(var_list[np.where(var_break_value_mat==np.min(var_break_value_mat))[0]],size=1)[0]
        else:
            chosen_var = rs_list.choice(var_list,size=1)[0]
            
        all_cand_variable_stat = np.zeros((4,len(var_list)))
        all_cand_variable_stat[0,:] = gain_vec[var_list,0]
        all_cand_variable_stat[1,:] = mv_vec[var_list,0]
        all_cand_variable_stat[2,:] = bv_vec[var_list,0]
        all_cand_variable_stat[3,:] = var_time[var_list,0]

        var_val[chosen_var] = ~var_val[chosen_var]
        clause_stat_mat_new, sat_result_new, clause_f_mat_new = get_clause_stat(chosen_var,clause_ind,clause_mat,clause_stat_mat,clause_f_mat)
    
    
    winning_variable_stat[0,0] = gain_vec[chosen_var]
    winning_variable_stat[1,0] = mv_vec[chosen_var]
    winning_variable_stat[2,0] = bv_vec[chosen_var]
    winning_variable_stat[3,0] = var_time[chosen_var]
    
    all_other_variables = np.delete(np.arange(0,nvar,1),chosen_var)
    var_time[all_other_variables] = var_time[all_other_variables] + 1
    var_time[chosen_var] = 0
    
    #return var_val, var_time, winning_variable_stat, all_cand_variable_stat, clause_stat_mat_new, sat_result_new, clause_f_mat_new, (np.sum(bv_vec)+np.sum(mv_vec))/(2*nvar)
    return var_val, var_time, winning_variable_stat, all_cand_variable_stat, clause_stat_mat_new, sat_result_new, clause_f_mat_new

def get_clause_stat(i,clause_ind,clause_mat,clause_stat_mat,clause_f_mat):
    var_sign = clause_mat[clause_ind,i]
    A_sign = var_sign
    B_sign = -var_sign
    A_clause_ind = np.where(clause_mat[:,i]==A_sign)[0]
    A_clause_ind_pa = np.intersect1d(A_clause_ind,np.where(clause_stat_mat==0)[0])
    A_clause_ind_pb = np.intersect1d(A_clause_ind,np.where(clause_stat_mat==1)[0])
    B_clause_ind = np.where(clause_mat[:,i]==B_sign)[0]
    B_clause_ind_pa = np.intersect1d(B_clause_ind,np.where(clause_f_mat==1)[0])
    B_clause_ind_pb = np.intersect1d(B_clause_ind,np.where(clause_f_mat!=1)[0])
    clause_stat_mat_new = np.array(clause_stat_mat)
    clause_f_mat_new = np.array(clause_f_mat)
    clause_stat_mat_new[A_clause_ind_pa] = True
    clause_stat_mat_new[B_clause_ind_pa] = False
    clause_f_mat_new[A_clause_ind] = clause_f_mat_new[A_clause_ind] + 1
    clause_f_mat_new[B_clause_ind] = clause_f_mat_new[B_clause_ind] - 1
    sat_result_new = 1 if (np.sum(clause_stat_mat_new)==len(clause_stat_mat_new)) else 0
    
    return clause_stat_mat_new, sat_result_new, clause_f_mat_new

def sat_eval(var_val,clause_mat):
    
    nvar = len(var_val)
    nclause = clause_mat.shape[0]
    clause_stat_mat = np.zeros((nclause,1),dtype=bool)
    clause_f_mat = np.zeros((nclause,1))
    sat_result = 1
    
    for i in range(nclause):
        
        var_ind = np.where(clause_mat[i,]!=0)[0]
        clause_stat_mat[i], clause_f_mat[i] = clause_eval(var_val[var_ind],clause_mat[i,var_ind])
        sat_result = sat_result and clause_stat_mat[i]
        
    return clause_stat_mat, sat_result, clause_f_mat
        
def clause_eval(var_val,var_sign):
    
    nvar = len(var_val)
    clause_sum = 0
    clause_f_count = 0
    for i in range(nvar):
        if var_sign[i]==1:
            clause_sum = clause_sum or var_val[i]
            clause_f_count = clause_f_count + (1 if var_val[i] else 0)
        elif var_sign[i]==-1:
            clause_sum = clause_sum or ~var_val[i]
            clause_f_count = clause_f_count + (1 if ~var_val[i] else 0)
        else:
            clause_sum = clause_sum
            
    return clause_sum, clause_f_count

def rand_init(nvar,rs_list):
    
    #var_val_mat = np.random.rand(nvar,1)
    var_val_mat = rs_list.rand(nvar,1)
    var_val_mat = [1 if (i>0.5) else 0 for i in var_val_mat]
    var_val_mat = np.array(var_val_mat,dtype=bool)
    
    return var_val_mat


def clausemat2cnfmat(clause_mat):
    
    nvar = clause_mat.shape[1]
    nclause = clause_mat.shape[0]
    nlit = 2*nvar
    cnfmat = np.zeros((nclause,nlit))
    
    for i in range(nvar):
        pos_lit_ind = np.where(clause_mat[:,i]==1)[0]
        if len(pos_lit_ind)!=0:
            cnfmat[pos_lit_ind,2*i] = 1
            
        neg_lit_ind = np.where(clause_mat[:,i]==-1)[0]
        if len(neg_lit_ind)!=0:
            cnfmat[neg_lit_ind,2*i+1] = 1
            
    return cnfmat   


def get_stats(walksat_result):
        
    prob_s = np.mean(walksat_result[:,1])
    success_ind = np.where(walksat_result[:,1]==1)[0]
    avg_flips = np.mean(walksat_result[success_ind,0])
    std_flips = np.std(walksat_result[success_ind,0])
    
    max_restarts = np.shape(walksat_result)[0]
    p_targ = 0.99
    sorted_arr = walksat_result[walksat_result[:,0].argsort()]
    if prob_s>=p_targ:
        ind_tts = math.ceil(p_targ*max_restarts)-1
        tts_99 = sorted_arr[ind_tts,0]
    else:
        if prob_s == 0:
            tts_99 = 0
        else:
            tts_99 = sorted_arr[max_restarts-1,0]*(math.log((1-p_targ),10)/math.log((1-prob_s),10))
    
    return avg_flips, prob_s, std_flips, tts_99