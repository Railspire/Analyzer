import copy
import json
import os
import numpy as np
import pandas as pd
from scipy import interpolate
from train_dynamics_package.rolling import Train
from train_dynamics_package.track import Profile
from bokeh.plotting import figure, output_file, save, show, gridplot
from bokeh.models import LinearAxis, Range1d, Legend, HoverTool
import time
from datetime import timedelta
from datetime import datetime
from pyAAR import classD, EMP
from pyAAR.LCCM import v2_3 as LCCM
import traceback
import argparse
#from rslib import Visualization

#Program Start Time
start_time = time.monotonic()

#Creating Directories
csv_path = "CSV_Data"
isExist = os.path.exists(csv_path)
if not isExist:
   os.makedirs(csv_path)
html_path = "HTML_Plots"
isExist = os.path.exists(html_path)
if not isExist:
   os.makedirs(html_path)
mission_path = "Mission_Data"
isExist = os.path.exists(mission_path)
if not isExist:
   os.makedirs(mission_path)
operation_path = "Operation_Data"
isExist = os.path.exists(operation_path)
if not isExist:
   os.makedirs(operation_path)

#Creating Arguments for Command Line Use
parser = argparse.ArgumentParser(description='Process MQTT log')
parser.add_argument('--path', type=str, required=True, help='filepath of mqtt.log')
parser.add_argument('--filename', type=str, required=False, default='mqtt.log', help='Name of File if not mqtt.log')
args = vars(parser.parse_args())

log_path = args['path']
log_name = args['filename']
if args['filename'] == 'mqtt.log':
    print('No Unique Log Filename Given, Using mqtt.log instead, Use --filename to supply unique filename ')

#Splitting Log by Operation for Data Storage and Analysis
print('Splitting Log by Operation')
with open(os.path.join(log_path,log_name), 'r') as data:
    data = data.read()
    data = data.split('\n')
    ii = 0
    op_counter = 1
    mission_counter = 1
    op_update_line_list = []
    mqtt_line_list = []
    mission_list = []

    SET_CONFIG_Flag = False
    Pause_Flag = False
    for line in data:
        ii+=1
        if ii < len(data):
            #print(ii)
            mqtt_line_list.append(line)
            if 'NCL/msm/operation_update' in line:
                jsonline = json.loads(line)
                msm_operation_update_data = jsonline['payload']
                operation_type = jsonline['payload']['type']
                if operation_type == 'SET-CONFIG':
                    #op_update_line_list.append(['op_start', ii, msm_operation_update_data['type'],op_counter, mission_counter])
                    SET_CONFIG_Flag = True
                if operation_type == 'LOCO-MOTION':
                    op_counter += 1
                    if SET_CONFIG_Flag == True:
                        #op_update_line_list.append(['op_end', ii, msm_operation_update_data['type'], op_counter, mission_counter])
                        SET_CONFIG_Flag = False
                    if Paused_Flag == True:
                        op_update_line_list.append(['op_end', ii, msm_operation_update_data['type'], op_counter, mission_counter])
                        Paused_Flag = False
                    op_update_line_list.append(['op_start', ii, msm_operation_update_data['type'],op_counter, mission_counter])
            if 'NCL/ose/state' in line:
                #msm_operation_update_data = jsonline['payload']
                jsonline = json.loads(line)
                ose_state = jsonline['payload']['state']
                if ose_state == 'done':
                    op_update_line_list.append(['op_end', ii,'ose-state', op_counter, mission_counter])
            if 'NCL/msm/state' in line:
                jsonline = json.loads(line)
                msm_state = jsonline['payload']['state']
                if msm_state == 'Paused':
                    Pause_Flag = True
                if msm_state == 'In Progress':
                    Paused_Flag = False
            if 'NCL/interface' in line:
                jsonline = json.loads(line)
                if jsonline['payload']['type'] == 'Mission':
                    mission = jsonline['payload']['Payload']
                    # mission = jsonline['payload']['payload']
                    op_counter = 0
                    mission_list.append(mission)
                #if jsonline['payload']['type'] == 'OCUTx':
                    #jsonline = json.loads(line)
                    #if 'LocomotiveStatus' in jsonline['payload']['Payload']:
                        #ocutx_payload = jsonline['payload']['Payload']
                        #ocutx_payload.replace("\\","")
                        #jsonocutx_payload = json.loads(ocutx_payload)
                        #print(jsonocutx_payload)
                        #chainage_ft = jsonocutx_payload['Payload']['Chainage Ft']
                        #chainage_ft_list.append(chainage_ft)
                        #print(chainage_ft)
                    if 'Mission State' in jsonline['payload']['Payload']:
                        ocutx_payload = jsonline['payload']['Payload']
                        ocutx_payload.replace("\\","")
                        jsonocutx_payload = json.loads(ocutx_payload)
                        mission_state = jsonocutx_payload['Payload']['Mission State']
                        if mission_state == 'Complete':
                            mission_counter += 1 #Counting Completed Missions Only
                            #try:
                                #if ii-op_update_line_list[-1][1] > 2:
                                    #op_update_line_list.append(['op_end', ii, msm_operation_update_data['type'], op_counter, mission_counter])
                            #except IndexError:
                                #pass
                #if jsonline['payload']['type'] == 'OCURx':
                    #jsonline = json.loads(line)
                    #if 'Mission Command' in jsonline['payload']['Payload']:
                        #ocurx_payload = jsonline['payload']['Payload']
                        #ocurx_payload.replace("\\", "")
                        #jsonocurx_payload = json.loads(ocurx_payload)
                        #mission_command = jsonocurx_payload['Payload']['Mission Command']
                        #if mission_command == 'End Operation': Keep commented out until this is implemented in the ocu
                            #op_update_line_list.append(['op_end', ii, msm_operation_update_data['type'], op_counter, mission_counter])
                        #if mission_command == 'Abort':
                            #if msm_operation_update_data['type'] == 'LOCO-MOTION':
                                #op_counter += 1
                                #try:
                                    #if ii-op_update_line_list[-1][1] > 2:
                                        #op_update_line_list.append(['op_end', ii, msm_operation_update_data['type'], op_counter, mission_counter])
                                #except IndexError:
                                    #pass
                        #if mission_command == 'End Operation':
                            #if msm_operation_update_data['type'] == 'LOCO-MOTION':
                                #op_counter += 1
                                #try:
                                    #if ii-op_update_line_list[-1][1] > 2:
                                        #op_update_line_list.append(['op_end', ii, msm_operation_update_data['type'], op_counter, mission_counter])
                                #except IndexError:
                                    #pass
                            #else:
                                #pass

print(op_update_line_list)
try: 
    print(op_update_line_list[-1][0])
    if op_update_line_list[-1][0] == 'op_start':
        print('force', ii)
        op_update_line_list.append(['op_end', ii, 'forced', op_counter, mission_counter])
except IndexError:
    print('No Ops')
    pass
print(op_update_line_list)
#Pairing Operation Beginning and Ends
print('Parsing Operations')
op_start = None
op_end = None
line_pair_list = []
for ndx, op_state in enumerate(op_update_line_list):
    #print(ndx)
    #print(op_update_line_list)
    op_start_or_end = op_state[0]
    op_line = op_state[1]
    op_type = op_state[2]
    operation_number = op_state[3]
    mission_number = op_state[4]
    if op_start_or_end == 'op_start':
        if op_start is None:
            op_start = op_line
    if op_start_or_end == 'op_end':
        if op_end is None:
            op_end = op_line
            try:
                if op_end-op_start > 2500000:
                    #print('Passing Mission Number {} due to length {}'.format(mission_number, (op_end-op_start)))
                    pass
            except TypeError:
                pass
            else:
                line_pair_list.append([op_start - 1, op_end -1, operation_number, mission_number])
            op_start = None
            op_end = None
        if op_start == None:
            pass 

#Storing Data for Inidividual Operations
print('Storing Operation Data')
operation_filenames = []
for pair in line_pair_list:
    data_start = pair[0]
    data_end = pair[1]
    operation_number = pair[2]
    mission_number = pair[3]
    op_data = mqtt_line_list[data_start:data_end]
    with open('Operation_Data/mission-{}_movement_operation-{}-data.txt'.format(mission_number, operation_number), 'w') as operation_file:
        operation_filenames.append('Operation_Data/mission-{}_movement_operation-{}-data.txt'.format(mission_number, operation_number))
        for line in op_data:
            operation_file.write("%s\n" % line)

#Clearing Variables
line_pair_list = []
mqtt_line_list = []
op_update_line_list = []
data = []

#Looping Through Operation Files for Generating Data Files and Plots
tdccount = 0
ccbtxcount = 0
ccbrxcount = 0
lccmtxcount = 0
lccmrxcount = 0

ccbtxlist = []
ccbrxlist = []
lccmtxlist = []
lccmrxlist = []

tdcccbrxdiff = []
tdcccbtxdiff = []
tdclccmrxdiff = []
tdclccmtxdiff = []
tltctrl = 0

stopping_position_list = []
stopping_time_list = []
last_tdc_time_list = []
last_tdc_position_list = []
last_lccmtx_time_list = []
last_lccmtx_position_list = []
tdc_time_list = []
flaglist = []
puck_list = []
for file in operation_filenames:

    data = open(file, 'r').read()
    data = data.split('\n')

    #Trimming File Path for Convenient Data Saving with df_to_csv later
    file = file.strip('Operation_Data/')
    print('Parsing Movement Operation for Plotting:', file.strip('-data.tx'))
    #file = file.strip('-data.tx')
    mission = file.split('_')[0]
    operation = file.split('_')[2].split('-')[1]

    ii = 0
    gps_data_list = []
    loco_data_list = []
    brake_data_list = []
    destination_list = []
    position_vals = []
    chainage_list = []
    ose_info_list = []
    tdcmd_list = []
    op_update_list = []
    elevation_list = []
    train = None
    prf = None
    ose_state_list = []
    msm_state_list = []
    will_list = []
    visual_clearance_data_list = []
    mse_speed_update_list = []
    op_counter = 0
    valid_speed_data = []
    mqtt_line_list = []
    ignore_mission_flag = False
    stop_flag = False
    unprocessed_command_flag = False
    chainage_ft_list = []
    ocu_tx_data_list = []
    for line in data:
        ii+=1
        if ii < len(data):
            #print(ii)
            jsonline = json.loads(line)
            mqtt_line_list.append(line)
            if 'NCL/ose/info' in line:
                ose_info_data = jsonline['payload']
                ose_info_list.append(ose_info_data)
            if 'NCL/train_dynamics/command' in line:
                train_dynamics_command_data = jsonline['payload']
                tdcmd_list.append(train_dynamics_command_data)
            if 'NCL/msm/operation_update' in line:
                msm_operation_update_data = jsonline['payload']
                #print(msm_operation_update_data)
                #op_counter += 1
                if jsonline['payload']['type'] == 'SET-CONFIG':
                    pass
                if jsonline['payload']['type'] == 'LOCO-MOTION':
                    loco_motion_operation_update = jsonline['payload']
                    op_update_list.append(msm_operation_update_data)
                    segment_files = jsonline['payload']['segment_files']
                    customer = jsonline['payload']['customer']
                    speed_limits = jsonline['payload']['speed_limits']
                    default_speed = jsonline['payload']['default_speed']
                    consist = jsonline['payload']['consist']
                    prf = Profile()
                    prf.load_track_profile_from_route(customer,segment_files)
                    #elevation_df = pd.DataFrame(prf.elevation)
                    #elevation_df.columns = ['elevation']
                    train = Train(profile=prf, consist=consist)
                    prf.change_default_speed_limit(default_speed)
                    try:
                        starting_position = train.profile.get_position_from_lat_long(gps_data['latitude_deg'], gps_data['longitude_deg'])
                    except NameError:
                        starting_position = 0
                        pass
                    destination_data = jsonline['payload']['destination']['coordinates']
                    destination_position = train.profile.get_position_from_lat_long(destination_data[0], destination_data[1])
                    #print('dest diff', destination_position-starting_position)
                    #if destination_position-starting_position > 50:
                        #ignore_mission_flag = True
            if 'NCL/ose/state' in line:
                ose_state_time = jsonline['tst']
                ose_state_data = jsonline['payload']
                ose_state_list.append([ose_state_time,ose_state_data])
            if 'NCL/msm/state' in line:
                msm_state_time = jsonline['tst']
                msm_state_data = jsonline['payload']
                msm_state_list.append([msm_state_time,msm_state_data])
            if 'NCL/will' in line:
                will_time = jsonline['tst']
                will_data = jsonline['payload']
                will_list.append([will_time,will_data])
            if 'NCL/visual/clearance' in line:
                visual_clearance_time = jsonline['tst']
                visual_clearance_data = jsonline['payload']
                print('Puck Detected: type: Visual clearance, Data:', visual_clearance_data)
                puck_list.append([mission, operation, 'Visual-Clearance', visual_clearance_time, visual_clearance_data])
            if 'NCL/visual/kick' in line:
                visual_kick_time = jsonline['tst']
                visual_kick_data = jsonline['payload']
                print('Puck Detected: type: Visual Kick, Data:', visual_kick_data)
                puck_list.append([mission, operation, 'Visual-Kick', visual_kick_time, visual_kick_data])
            if 'NCL/mse/speed_update' in line:
                mse_speed_update_data = jsonline['payload']
            if 'NCL/status' in line:
                gps_data = jsonline['payload']['gps']
                loco_data = jsonline['payload']['loco']
                brake_data = jsonline['payload']['brakes']
                gps_data_list.append(gps_data)
                loco_data_list.append(loco_data)
                brake_data_list.append(brake_data)
                if loco_data['engaged'] == False:
                    #print('not engaged')
                    pass
                else:
                    if train is not None:
                        chainage_data = train.profile.get_position_from_lat_long(gps_data['latitude_deg'], gps_data['longitude_deg'])
                        chainage_list.append(chainage_data)
                        valid_speed_data.append(gps_data['speed_fps'])
                    #try:
                        #chainage_data = train.profile.get_position_from_lat_long(gps_data['latitude_deg'],gps_data['longitude_deg'])
                        #chainage_list.append(chainage_data)
                    #except:
                        #pass
            if 'NCL/interface' in line:
                #jsonline = json.loads(line)
            #if jsonline['payload']['type'] == 'Mission':
                #mission = jsonline['payload']['Payload']
                # mission = jsonline['payload']['payload']
                #op_counter = 0
                #mission_list.append(mission)
                if jsonline['payload']['type'] == 'OCUTx':
                    jsonline = json.loads(line)
                    if 'LocomotiveStatus' in jsonline['payload']['Payload']:
                        ocutx_payload = jsonline['payload']['Payload']
                        ocutx_payload.replace("\\","")
                        jsonocutx_payload = json.loads(ocutx_payload)
                        ocu_tx_data_list.append(jsonocutx_payload['Payload'])
                        print(jsonocutx_payload)
                        chainage_ft = jsonocutx_payload['Payload']['Chainage Ft']
                        chainage_ft_list.append(chainage_ft)
                        print(chainage_ft)

            #Command vs Response Data
            # ToDo Combine Command vs Response with rest of loop by section title
            if ignore_mission_flag == True:
                pass
            if ignore_mission_flag == False:
                if jsonline['topic'] == 'NCL/status':
                    speed = gps_data['speed_fps']
                    lstime =jsonline['tst']
                    lstime =lstime[:-5]
                    lstime = datetime.strptime(lstime, '%Y-%m-%dT%H:%M:%S.%f')
                    lstime = datetime.timestamp(lstime)
                    if 0.1 < speed < 0.15: #Criteria for Stopping
                        if tltcmd == 0:
                            if stop_flag == True:
                                pass    #Ignoring GPS Noise/False Stops
                            if stop_flag == False:
                                #print('real stop', ii)  #Real Stopping Position of train
                                stopping_time_list.append(lstime)
                                stopping_position = train.profile.get_position_from_lat_long(gps_data['latitude_deg'], gps_data['longitude_deg'])
                                stopping_position_list.append(stopping_position)
                                last_tdc_time_list.append(last_tdc_time)
                                last_tdc_position_list.append(last_tdc_position)
                                last_lccmtx_time_list.append(lccmtxtime)
                                last_lccmtx_position_list.append(last_lccmtx_position)
                                stop_flag = True
                if jsonline['topic'] == 'NCL/train_dynamics/command':
                    tdctime =jsonline['tst']
                    tdctime =tdctime[:-5]
                    tdctime = datetime.strptime(tdctime, '%Y-%m-%dT%H:%M:%S.%f')
                    tdctime = datetime.timestamp(tdctime)
                    try:
                        tdcposition = train.profile.get_position_from_lat_long(gps_data['latitude_deg'], gps_data['longitude_deg'])
                    except (AttributeError, NameError):
                        pass
                    tdc = jsonline['payload']
                    tdccount += 1

                if jsonline['topic'] == 'NCL/interface':
                    if jsonline['payload']['type'] == 'CCBTx':
                        ccbtxtime = jsonline['tst']
                        ccbtxtime = ccbtxtime[:-5]
                        ccbtxtime = datetime.strptime(ccbtxtime, '%Y-%m-%dT%H:%M:%S.%f')
                        ccbtxtime = datetime.timestamp(ccbtxtime)
                        #print([ccbtxtime, 'CCBTx'])
                        ccbtxlist.append(ccbtxtime)
                        ccbtxcount += 1

                    if jsonline['payload']['type'] == 'LCCMTx':
                        lccmtxtime = jsonline['tst']
                        lccmtxtime = lccmtxtime[:-5]
                        lccmtxtime = datetime.strptime(lccmtxtime, '%Y-%m-%dT%H:%M:%S.%f')
                        lccmtxtime = datetime.timestamp(lccmtxtime)
                        lccmtxbytes = jsonline['payload']['Payload']
                        lccmtxbytes = bytearray.fromhex(lccmtxbytes)
                        #print([lccmtxtime, 'LCCMTx', LCCM.parse_lccm_message(lccmtxbytes)[0]['trainline_throttle_command']])
                        tltcmd = LCCM.parse_lccm_message(lccmtxbytes)[0]['trainline_throttle_command']
                        lccmtxcount += 1

                        try:
                            lccmtxposition = train.profile.get_position_from_lat_long(gps_data['latitude_deg'],
                                                                                   gps_data['longitude_deg'])
                        except AttributeError:
                            pass

                        if tltcmd !=  tltctrl: #Identifying Notch Changes
                            #print(tltcmd,tltctrl)
                            #print('@', tdc, speed)
                            lccmtxlist.append(lccmtxtime)
                            tdc_time_list.append(tdctime)
                            last_tdc_time = tdctime
                            last_tdc_position = tdcposition
                            last_lccmtx_position = lccmtxposition

                    if jsonline['payload']['type'] == 'CCBRx':
                        ccbrxtime = jsonline['tst']
                        ccbrxtime = ccbrxtime[:-5]
                        ccbrxtime = datetime.strptime(ccbrxtime, '%Y-%m-%dT%H:%M:%S.%f')
                        ccbrxtime = datetime.timestamp(ccbrxtime)
                        #print([ccbrxtime, 'CCBRx'])
                        ccbrxlist.append(ccbrxtime)
                        ccbrxcount += 1
                    if jsonline['payload']['type'] == 'LCCMRx':
                        lccmrxtime = jsonline['tst']
                        lccmrxtime = lccmrxtime[:-5]
                        lccmrxtime = datetime.strptime(lccmrxtime, '%Y-%m-%dT%H:%M:%S.%f')
                        lccmrxtime = datetime.timestamp(lccmrxtime)

                        lccmrxbytes = jsonline['payload']['Payload']
                        lccmrxbytes = bytearray.fromhex(lccmrxbytes)
                        #print([lccmrxtime, 'LCCMRx', LCCM.parse_lccm_message(lccmrxbytes)[0]['trainline_throttle_control']])
                        tltctrl = LCCM.parse_lccm_message(lccmrxbytes)[0]['trainline_throttle_control']
                        lccmrxlist.append(lccmrxtime)
                        lccmrxcount += 1

                        if tltcmd !=  tltctrl:
                            unprocessed_command_flag = True
                            flaglist.append(['unprocessed_command_flag', file])

    """
    #Interpolating Elevation
    for i in elevation_df['elevation']:
        elevation.append(i)
    f = interpolate.interp1d(np.arange(0, len(elevation)), elevation)
    elevation_interp = f(np.linspace(0.0, len(elevation) - 1, len(current_position_vals)))
    """

    #Creating Speed Limit Curve
    speedlimitlist = []
    acc_targ_list = []
    shortenedspeedlimits = []
    speedlimitchainagelist = []
    speedlimits = []
    #print(len(op_update_list), op_update_list)
    for op_update in op_update_list: #There will only be one
        for speedlimit in op_update['speed_limits']:
            slimit = speedlimit['limit']
            acc_targ = speedlimit['acceleration_target']
            speedlimitlist.append(slimit)
            acc_targ_list.append(acc_targ)
        prf.calculate_speed_reduction_curve(start_speed=speedlimitlist[0], end_speed=speedlimitlist[-1], start_chain=prf.chainage[0], target_accel_mphps=acc_targ_list[0])
        speedlimits = op_update['speed_limits']
        prf.change_speed_limits(speedlimits)
        speedlimitchainage = prf.chainage_to_speed_limts
        speedlimitchainagelist = speedlimitchainage[0].tolist()
        speedlimitchainagelist.pop()
        speedlimitchainagelist.pop()
        speedlimitchainagelist.pop()
        speedlimitchainagelist.pop()
        f = interpolate.interp1d(speedlimitchainagelist, prf.speed_limits)
        loco_status_array = np.zeros(len(gps_data_list))
        for i in loco_status_array:
            try:
                a = f(i)
                shortenedspeedlimits.append(a.tolist())
            except Exception:
                shortenedspeedlimits.append(0)
        #print(shortenedspeedlimits)
    #loco_status_array = np.zeros(len(gps_data_list))
    #loco_status_chainage =[]
    #g = interpolate.interp1d(loco_status_array, chainage_list)
    #for i in loco_status_array:
        #try:
            #a = f(i)
            #loco_status_chainage.append(a.tolist())
        #except Exception:
            #loco_status_chainage.append(0)
    #print(shortenedspeedlimits)

    #DataFrame Creation
    #Status DataFrames
    gps_df = pd.DataFrame(gps_data_list)
    gps_df = gps_df.add_prefix('gps_')
    loco_df = pd.DataFrame(loco_data_list)
    loco_df = loco_df.add_prefix('loco_')
    brakes_df = pd.DataFrame(brake_data_list)
    brakes_df = brakes_df.add_prefix('brakes_')
    ls1 = gps_df.join(loco_df, how='left')
    status_df = ls1.join(brakes_df, how='left')
    #OSE Info DataFrame
    oseinfodf = pd.DataFrame(ose_info_list)
    oseinfodf = oseinfodf.add_prefix('ose_info_')
    #Train Dynamics Command DataFrame
    tdcmddf = pd.DataFrame(tdcmd_list)
    tdcmddf = tdcmddf.add_prefix('td_cmd_')
    #Operation Update DataFrame
    op_updatedf = pd.DataFrame(op_update_list)
    op_updatedf = op_updatedf.add_prefix('op_update_')
    #Destination DataFrame
    destinationdf = pd.DataFrame(destination_list)
    destinationdf = destinationdf.add_prefix('destination_')
    #Chainage DataFrame
    chainagedf = pd.DataFrame(chainage_list, columns=['chainage'])
    #Speed Limit DataFrame
    speedlimitdf = pd.DataFrame(shortenedspeedlimits)
    speedlimitdf = speedlimitdf.add_prefix('speedlimit_')
    #print(speedlimitdf)
    #NCL State DataFrames
    ose_state_df = pd.DataFrame(ose_state_list)
    ose_state_df = ose_state_df.add_prefix('ose_state_')
    msm_state_df = pd.DataFrame(msm_state_list)
    msm_state_df = msm_state_df.add_prefix('msm_state_')
    will_df = pd.DataFrame(will_list)
    will_df = will_df.add_prefix('will_')
    #Visual Clearance Dataframes and MSE Speed Updates
    visual_clearance_data = pd.DataFrame(visual_clearance_data_list)
    mse_speed_update_data = pd.DataFrame(mse_speed_update_list)
    valid_speed_data_df = pd.DataFrame(valid_speed_data)
    valid_speed_data_df = valid_speed_data_df.add_prefix('valid_speed_data_')
    #Elevation Interp DataFrame (Needs Work Before Implementation
    elevation_interp = ['1']
    elevation_interp_df = pd.DataFrame(elevation_interp)
    elevation_interp_df.columns = ['elevation_interp']
    
    chainage_ft_df = pd.DataFrame(chainage_ft_list, columns=['chainage_ft'])
    
    ocu_tx_df = pd.DataFrame(ocu_tx_data_list)
    ocu_tx_df = ocu_tx_df.add_prefix('ocu_tx_')
    

    #Merging DataFrames
    df2 = status_df.join(oseinfodf, how='left')
    df3 = df2.join(tdcmddf, how='left')
    df4 = df3.join(op_updatedf, how='left')
    df5 = df4.join(destinationdf, how='left')
    df6 = df5.join(chainagedf, how='left')
    df7 = df6.join(speedlimitdf, how='left')
    df8 = df7.join(ose_state_df, how='left')
    df9 = df8.join(msm_state_df, how='left')
    df10 = df9.join(will_df, how='left')
    df11 = df10.join(visual_clearance_data, how='left')
    df12 = df11.join(mse_speed_update_data, how='left')
    df13 = df12.join(valid_speed_data_df, how='left')
    #df13 = df12.join(elevation_df,how='left')
    #df14 = df13.join(elevation_interp_df, how='left')
    df14 = df13.join(chainage_ft_df, how='left')
    df15 = df14.join(ocu_tx_df, how = 'left')
    df = df15

    #Saving Data as CSV
    df.to_csv('CSV_Data/{}-Dynamics_Data.csv'.format(file.strip('-data.txt')), index=True)

    try:
        #Position Data
        chainage = df['chainage']
        chainage_ft = df['chainage_ft']
        oseinfopos = df['ose_info_chainage'][0]

        #Time
        time = df['gps_time_ms']

        #Speed Data
        FPS_TO_MPH = 3600 / 5280
        speed_mph = df['gps_speed_fps'] * FPS_TO_MPH
        valid_speed_mph = df['valid_speed_data_0'] * FPS_TO_MPH

        #Brake Data
        twentyt = df['brakes_independent_ref_psi']
        eq_res = df['brakes_eq_res_psi']
        brake_cyl = df['brakes_brake_cyl_psi']
        main_res = df['brakes_main_res_psi']

        #Notch Data
        trainline_throttle = df['loco_trainline_throttle']

        #Force Data
        te_force = df['ose_info_te_force_lbs']
        be_force = df['ose_info_braking_force_lbs']
        grade_force = df['ose_info_grade_force_lbs']
        automatic_brake_force = df['ose_info_auto_brake_force_lbs']

        #Acceleration Data
        acceleration_correction = df['ose_info_accel_correction']
        corrected_acceleration = df['ose_info_corrected_accel']
        actual_acceleration = df['ose_info_actual_accel']
        simulated_acceleration = df['ose_info_simulated_accel']

        #Elevation Data
        #elevation = df['elevation_interp']

        """
        #Test Code for RSLIB
        from rslib import Visualization
        speed_chainage_plot = Visualization.plot_speed_chainage(chainage, speed_mph, speed_limits=prf.speed_limits, speed_unit = 'MPH')
        speed_time_plot =  Visualization.plot_speed_time(time, speed_mph, speed_unit = 'MPH')
        brake_chainage_plot = Visualization.plot_brakes_chainage(chainage, twentyt=twentyt, eq_res= eq_res, main_res = main_res, brake_cyl=brake_cyl)
        brake_time_plot = Visualization.plot_brakes_time(time, twentyt=twentyt, eq_res= eqres, main_res = main, brake_cyl=brake_cyl)
        notch_chainage_plot = Visualization.plot_notch_chainage(chainage, notch)
        notch_time_plot = Visualization.plot_notch_time(time, notch)
        force_chainage_plot = Visualization.plot_force_chainage(chainage, te_force=te_force, be_force=be_force, grade_force=grade_force, automatic_brake_force=automatic_brake_force)
        force_time_plot = Visualization.plot_force_time(time, te_force=te_force, be_force=be_force, grade_force=grade_force, automatic_brake_force=automatic_brake_force)
        acceleration_chainage_plot = Visualization.plot_acceleration_chainage(chainage, actual_acceleration=actual_acceleration, simulated_acceleration=simulated_acceleration, corrected_acceleration=corrected_acceleration)
        acceleration_time_plot = Visualization.plot_acceleration_time(time, actual_acceleration=actual_acceleration, simulated_acceleration=simulated_acceleration, corrected_acceleration=corrected_acceleration)
        p = gridplot([[speed_chainage_plot, brake_chainage_plot, notch_chainage_plot], [force_chainage_plot, acceleration_chainage_plot],[speed_time_plot, brake_time_plot, notch_time_plot], [force_time_plot, acceleration_time_plot]])
        """
        #generating bokeh plot

        speed_cplot = figure(title="Speed vs Chainage", x_axis_label='Chainage [ft]', y_axis_label='Speed [MPH]')
        if max(speed_mph) > max(shortenedspeedlimits):
            speed_cplot.y_range = Range1d(start=min(speed_mph), end=max(speed_mph))
        else:
            speed_cplot.y_range = Range1d(start=min(speed_mph), end=max(prf.speed_limits))
            #speed_cplot.x_range = Range1d(start=min(speedlimitchainagelist), end=max(speedlimitchainagelist))
        speed_cplot.x_range = Range1d(start=min(chainage), end=max(chainage))
        #speed_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #speed_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        speed_cplot.add_layout(Legend(), 'below')
        speed_cplot.legend.click_policy="hide"
        #print('chainage',chainage)
        #print('sp', speed_mph)
        speed_cplot.line(speedlimitchainagelist, prf.speed_limits, legend_label="Speed Limits [MPH]", line_width=3, color = "blue")
        #speed_cplot.line(chainage, shortenedspeedlimits, legend_label="Speed Limits [MPH]", line_width=3, color = "blue")
        speed_cplot.line(chainage, valid_speed_mph, legend_label="Speed [MPH]", line_width=3, color = "orange")
        #speed_plot.line(chainage, elevation, color="grey", y_range_name="y2")
        speed_cplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.00}")]
        speed_cplot.add_tools(HoverTool(tooltips=speed_cplot_TOOLTIPS))
        speed_cplot.grid.grid_line_width = 0.5

        brake_cplot = figure(title="Brake Status vs Chainage", x_axis_label='Chainage [ft]', y_axis_label='Pressure [PSI]')
        brake_cplot.y_range = Range1d(start=min(twentyt), end=max(main_res))
        #brake_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #brake_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        brake_cplot.add_layout(Legend(), 'below')
        brake_cplot.legend.click_policy="hide"
        brake_cplot.line(chainage, twentyt, legend_label="Independent Brake [PSI]", line_width=3, color = "blue")
        brake_cplot.line(chainage, eq_res, legend_label="Equalizing Reservoir [PSI]", line_width=3, color = "orange")
        brake_cplot.line(chainage, main_res, legend_label="Main Reservoir [PSI]", line_width=3, color = "black")
        brake_cplot.line(chainage, brake_cyl, legend_label="Brake Cylinder [PSI]", line_width=3, color = "red")
        #brake_plot.line(chainage, elevation, color="grey", y_range_name="y2")
        brake_cplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.0}")]
        brake_cplot.add_tools(HoverTool(tooltips=brake_cplot_TOOLTIPS))
        brake_cplot.grid.grid_line_width = 0.5

        notch_cplot = figure(title="Notch vs Chainage", x_axis_label='Chainage [ft]', y_axis_label='Notch')
        notch_cplot.y_range = Range1d(start=0, end=8)
        #notchc_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #notchc_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        notch_cplot.add_layout(Legend(), 'below')
        notch_cplot.legend.click_policy="hide"
        notch_cplot.line(chainage, trainline_throttle, legend_label="Trainline Throttle", line_width=3, color = "red")
        #notchc_plot.line(chainage, elevation, color="grey", y_range_name="y2")
        notch_cplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0}")]
        notch_cplot.add_tools(HoverTool(tooltips=notch_cplot_TOOLTIPS))
        notch_cplot.grid.grid_line_width = 0.5

        force_cplot = figure(title="Train Dynamics Forces vs Chainage", x_axis_label='Chainage [ft]', y_axis_label='Force [lb]')
        force_cplot.y_range = Range1d(start=min(grade_force), end=max(te_force))
        #forcec_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #forcec_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        force_cplot.add_layout(Legend(), 'below')
        force_cplot.legend.click_policy="hide"
        force_cplot.line(chainage, te_force, legend_label="Tractive Force [lb]", line_width=3, color = "orange")
        force_cplot.line(chainage, be_force, legend_label="Braking Force [lb]", line_width=3, color = "blue")
        force_cplot.line(chainage, grade_force, legend_label="Grade Force [lb]", line_width=3, color = "red")
        force_cplot.line(chainage, automatic_brake_force, legend_label="Automatic Brake Force [lb]", line_width=3, color = "black")
        #force_cplot.line(current_position, elevation, color="grey", y_range_name="y2")
        force_cplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.00}")]
        force_cplot.add_tools(HoverTool(tooltips=force_cplot_TOOLTIPS))
        force_cplot.grid.grid_line_width = 0.5

        acceleration_cplot = figure(title="Acceleration vs Chainage", x_axis_label='Chainage [ft]', y_axis_label='Acceleration [MPHPS]')
        acceleration_cplot.y_range = Range1d(start=min(simulated_acceleration), end=max(simulated_acceleration))
        #accelerationc_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #accelerationc_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        acceleration_cplot.add_layout(Legend(), 'below')
        acceleration_cplot.legend.click_policy="hide"
        acceleration_cplot.line(chainage, simulated_acceleration, legend_label="Simulated Acceleration [MPHPS]", line_width=3, color = "red")
        acceleration_cplot.line(chainage, actual_acceleration, legend_label="Actual Acceleration [MPHPS]", line_width=3, color = "green")
        acceleration_cplot.line(chainage, corrected_acceleration, legend_label="Corrected Acceleration [MPHPS]", line_width=3, color = "blue")
        #accelerationc_plot.line(chainage, elevation, color="grey", y_range_name="y2")
        acceleration_cplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.00}")]
        acceleration_cplot.add_tools(HoverTool(tooltips=acceleration_cplot_TOOLTIPS))
        acceleration_cplot.grid.grid_line_width = 0.5

        speed_tplot = figure(title="Speed vs Time", x_axis_label='Time [ms]', y_axis_label='Speed [MPH]')
        if max(speed_mph) > max(shortenedspeedlimits):
            speed_tplot.y_range = Range1d(start=min(speed_mph), end=max(speed_mph))
        else:
            speed_tplot.y_range = Range1d(start=min(speed_mph), end=max(shortenedspeedlimits))
        #speed_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #speed_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        speed_tplot.add_layout(Legend(), 'below')
        speed_tplot.legend.click_policy="hide"
        #print('chainage',chainage)
        #print('sp', speed_mph)
        speed_tplot.line(time, shortenedspeedlimits, legend_label="Speed Limits [MPH]", line_width=3, color = "blue")
        speed_tplot.line(time, valid_speed_mph, legend_label="Speed [MPH]", line_width=3, color = "orange")
        #speed_plot.line(time, elevation, color="grey", y_range_name="y2")
        speed_tplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.00}")]
        speed_tplot.add_tools(HoverTool(tooltips=speed_tplot_TOOLTIPS))
        speed_tplot.grid.grid_line_width = 0.5

        brake_tplot = figure(title="Brake Status vs Time", x_axis_label='Time [ms]', y_axis_label='Pressure[PSI]')
        brake_tplot.y_range = Range1d(start=min(twentyt), end=max(main_res))
        #braketplot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #braketplot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        brake_tplot.add_layout(Legend(), 'below')
        brake_tplot.legend.click_policy="hide"
        brake_tplot.line(time, twentyt, legend_label="Independent Brake [PSI]", line_width=3, color = "blue")
        brake_tplot.line(time, eq_res, legend_label="Equalizing Reservoir [PSI]", line_width=3, color = "orange")
        brake_tplot.line(time, main_res, legend_label="Main Reservoir [PSI]", line_width=3, color = "black")
        brake_tplot.line(time, brake_cyl, legend_label="Brake Cylinder [PSI]", line_width=3, color = "red")
        #braketplot.line(time, elevation, color="grey", y_range_name="y2")
        brake_tplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.0}")]
        brake_tplot.add_tools(HoverTool(tooltips=brake_tplot_TOOLTIPS))
        brake_tplot.grid.grid_line_width = 0.5

        notch_tplot = figure(title="Notch vs Time", x_axis_label='Time [ms]', y_axis_label='Notch')
        notch_tplot.y_range = Range1d(start=0, end=8)
        #notcht_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #notcht_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        notch_tplot.add_layout(Legend(), 'below')
        notch_tplot.legend.click_policy="hide"
        notch_tplot.line(time, trainline_throttle, legend_label="Trainline Throttle", line_width=3, color = "red")
        #notcht_plot.line(time, elevation, color="grey", y_range_name="y2")
        notch_tplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0}")]
        notch_tplot.add_tools(HoverTool(tooltips=notch_tplot_TOOLTIPS))
        notch_tplot.grid.grid_line_width = 0.5

        force_tplot = figure(title="Train Dynamics Forces vs Time", x_axis_label='Time [ms]', y_axis_label='Force [lb]')
        force_tplot.y_range = Range1d(start=min(grade_force), end=max(te_force))
        #forcet_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #forcet_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        force_tplot.add_layout(Legend(), 'below')
        force_tplot.legend.click_policy="hide"
        force_tplot.line(time, te_force, legend_label="Tractive Force [lb]", line_width=3, color = "orange")
        force_tplot.line(time, be_force, legend_label="Braking Force [lb]", line_width=3, color = "blue")
        force_tplot.line(time, grade_force, legend_label="Grade Force [lb]", line_width=3, color = "red")
        force_tplot.line(time, automatic_brake_force, legend_label="Automatic Brake Force [lb]", line_width=3, color = "black")
        #forcetcplot.line(current_position, elevation, color="grey", y_range_name="y2")
        force_tplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.00}")]
        force_tplot.add_tools(HoverTool(tooltips=force_tplot_TOOLTIPS))
        force_tplot.grid.grid_line_width = 0.5

        acceleration_tplot = figure(title="Acceleration vs Time", x_axis_label='Time [ms]', y_axis_label='Acceleration [MPHPS]')
        acceleration_tplot.y_range = Range1d(start=min(simulated_acceleration), end=max(simulated_acceleration))
        #accelerationt_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #accelerationt_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        acceleration_tplot.add_layout(Legend(), 'below')
        acceleration_tplot.legend.click_policy="hide"
        acceleration_tplot.line(time, simulated_acceleration, legend_label="Simulated Acceleration [MPHPS]", line_width=3, color = "red")
        acceleration_tplot.line(time, actual_acceleration, legend_label="Actual Acceleration [MPHPS]", line_width=3, color = "green")
        acceleration_tplot.line(time, corrected_acceleration, legend_label="Corrected Acceleration [MPHPS]", line_width=3, color = "blue")
        #accelerationt_plot.line(chainage, elevation, color="grey", y_range_name="y2")
        acceleration_tplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0.00}")]
        acceleration_tplot.add_tools(HoverTool(tooltips=acceleration_tplot_TOOLTIPS))
        acceleration_tplot.grid.grid_line_width = 0.5
        
        position_tplot = figure(title="Position vs Time", x_axis_label='Time [ms]', y_axis_label='Position [ft]')
        #position_tplot.y_range = Range1d(start=0, end=8)
        #notcht_plot.extra_y_ranges = {"y2": Range1d(start=min(elevation),end=max(elevation))}
        #notcht_plot.add_layout(LinearAxis(y_range_name="y2"), 'right')
        position_tplot.add_layout(Legend(), 'below')
        position_tplot.legend.click_policy="hide"
        position_tplot.scatter(time, chainage, legend_label="Position", line_width=3, color = "red")
        position_tplot.scatter(time, chainage_ft, legend_label="Position_bill", line_width=3, color = "black")
        #notcht_plot.line(time, elevation, color="grey", y_range_name="y2")
        position_tplot_TOOLTIPS = [("x", "$x{0.00}"),("y", "$y{0}")]
        position_tplot.add_tools(HoverTool(tooltips=notch_tplot_TOOLTIPS))
        position_tplot.grid.grid_line_width = 0.5
        
        
        p = gridplot([[speed_cplot, brake_cplot, notch_cplot], [force_cplot, acceleration_cplot],[speed_tplot, brake_tplot, notch_tplot], [force_tplot, acceleration_tplot, position_tplot]])
        output_file(filename="custom_filename.html", title="Static HTML file")
        save(p, 'HTML_Plots/{}-html_plot.html'.format(file.strip('-data.txt')))

    except Exception:
        traceback.print_exc()
        pass

puck_missions = []
for puck in puck_list:
    print('Adding Found Pucks to Mission Files')
    #with open('Mission_Data/{}.json'.format(puck[0]), 'r') as mission:\
    mission_number = int(puck[0].split('-')[1])
    mission = mission_list[mission_number-1]
    puck_missions.append(mission_number-1)
    operation_number = int(puck[1])
    mission_json = json.loads(mission)
    mission_json = copy.deepcopy(mission_json)
    opcount = 0
    for op in mission_json['operations']:
            if op['type'] == 'LOCO-MOTION':
                opcount += 1
                if opcount == operation_number:
                    op['pucks'].append({'type': puck[2], 'puck': puck[4]})
    with open('Mission_Data/mission-{}.json'.format(mission_number), 'w') as MissionFile:
        json.dump(mission_json, MissionFile, indent=2)
    #mission = json.load('Mission_Data/{}.json'.format(puck[0]))
    #print(mission)

#Saving Off Mission Data, Should save a second file for Mission with pucks if it exists
for mission_index, mission in enumerate(mission_list):
    if mission_index not in puck_missions:
        with open('Mission_Data/mission-{}.json'.format(mission_index+1), 'w') as MissionFile:
            json_object = json.loads(mission)
            json.dump(json_object, MissionFile, indent=2)
            #for op in json_object['operations']:
                #if op['type'] == 'LOCO-MOTION':
                    #print('Pucks Found for Mission {}:'.format(mission_index+1), puck_list)


#Command Vs Response Plotting
print('Plotting Command vs Response Timing')
#Creating containers for storing calculated differences
difflist = []
tdc_time_to_stop_list = []
lccmtx_time_to_stop_list = []
tdc_distance_to_stop_list = []
lccmtx_distance_to_stop_list = []
#Calculating and storing data for plotting
for ndx, item in enumerate(tdc_time_list):
    if ndx > 0:
        lccmtime = lccmtxlist[ndx]
        tdctime = item
        diff = lccmtime-tdctime
        difflist.append(diff)
for ndx, item in enumerate(last_tdc_time_list):
    last_tdc_time = item
    stopping_time = stopping_time_list[ndx]
    diff = stopping_time - last_tdc_time
    tdc_time_to_stop_list.append(diff)
for ndx, item in enumerate(last_lccmtx_time_list):
    last_lccmtx_time = item
    stopping_time = stopping_time_list[ndx]
    diff = stopping_time - last_lccmtx_time
    lccmtx_time_to_stop_list.append(diff)
for ndx, item in enumerate(last_tdc_position_list):
    last_tdc_position = item
    stopping_position = stopping_position_list[ndx]
    diff = stopping_position - last_tdc_position
    tdc_distance_to_stop_list.append(diff)
for ndx, item in enumerate(last_lccmtx_position_list):
    last_lccmtx_position = item
    stopping_position = stopping_position_list[ndx]
    diff = stopping_position - last_lccmtx_position
    lccmtx_distance_to_stop_list.append(diff)
#Initializing plotting variables
difflist_index = np.arange(0, len(difflist))
lccmtx_and_tdc_diff_plot = figure(title="Time Difference Between Lccmtx and TDC After Notch Change", x_axis_label='Index', y_axis_label='Time [s]')
#lccmtx_and_tdc_diff_plot.y_range = Range1d(start=min(difflist), end=max(difflist))
lccmtx_and_tdc_diff_plot.add_layout(Legend(), 'below')
lccmtx_and_tdc_diff_plot.line(difflist_index, difflist)
lccmtx_and_tdc_diff_plot_TOOLTIPS = [("x", "$x{0.00}"), ("y", "$y{0.00}")]
lccmtx_and_tdc_diff_plot.add_tools(HoverTool(tooltips=lccmtx_and_tdc_diff_plot_TOOLTIPS))
lccmtx_and_tdc_diff_plot.grid.grid_line_width = 0.5

hist, edges = np.histogram(tdc_time_to_stop_list, density=True, bins=20)
tdc_and_stopping_time_diff_plot = figure(title="Difference Between Last TDC Time and Stopping Time", x_axis_label='Time [s]', y_axis_label='Frequency')
tdc_and_stopping_time_diff_plot.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], line_color="white")

hist, edges = np.histogram(lccmtx_time_to_stop_list, density=True, bins=20)
lccmtx_and_stopping_time_diff_plot = figure(title="Difference Between Last LccmTx Time and Stopping Time", x_axis_label='Time [s]', y_axis_label='Frequency')
lccmtx_and_stopping_time_diff_plot.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], line_color="white")

hist, edges = np.histogram(tdc_distance_to_stop_list, density=True, bins=20)
tdc_and_stopping_distance_diff_plot = figure(title="Difference Between Last TDC position and Stopping position", x_axis_label='Position [ft]', y_axis_label='Frequency')
tdc_and_stopping_distance_diff_plot.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], line_color="white")

hist, edges = np.histogram(lccmtx_distance_to_stop_list, density=True, bins=20)
lccmtx_and_stopping_distance_diff_plot = figure(title="Difference Between Last LccmTx position and Stopping position", x_axis_label='Position [ft]', y_axis_label='Frequency')
lccmtx_and_stopping_distance_diff_plot.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], line_color="white")

p = gridplot([[lccmtx_and_tdc_diff_plot, tdc_and_stopping_time_diff_plot, lccmtx_and_stopping_time_diff_plot],[tdc_and_stopping_distance_diff_plot, lccmtx_and_stopping_distance_diff_plot]])
output_file('Command_vs_Respone_Plots.html')
save(p, 'HTML_Plots/Command_vs_Response_Plots.html')

#NCL Interface counts printed to terminal
print('Number of tdc:', tdccount)
print('Number of lccmtx:', lccmtxcount)
print('Number of lccmrx:', lccmrxcount)
print('Number of ccbtx:', ccbtxcount)
print('Number of ccbrx:', ccbrxcount)

#Printed flaglist for debugging
print('Flags:', flaglist)

#Program End Time
import time
end_time = time.monotonic()
#Program Runtime
print('Runtime: ', timedelta(seconds=end_time - start_time))

#Freeing up memory
objects = dir()
for obj in objects:
    if not obj.startswith("__"):
        del globals()[obj]

#ToDo Debug Emergency/State Plot Include locations of abort
#ToDo Expand on Flaglist for debugging
#ToDo Add Elevation to Plots + touch up on elevation logic
#Todo add visual clearance effect on speed limits
#Todo fix xlabels for time plots
