import sys
from sqlalchemy import Column, Integer, String, MetaData, Table, Boolean, ForeignKey, select, UniqueConstraint, DateTime
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import sessionmaker
import json
import datetime

import yaml
with open("config.yaml", 'r') as stream:
    yaml_config = (yaml.safe_load(stream))

<<<<<<< HEAD
#engine = create_engine('sqlite:///sales.db', echo = True)
db_string = 'mysql://' + str(yaml_config['database']['username']) + ':' + str(yaml_config['database']['password']) + '@' + str(yaml_config['database']['server']) + '/' + str(yaml_config['database']['database'])
print(db_string)
engine = create_engine(db_string, echo = True)
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
=======
import logtool
logtool = logtool.LogTool()
logtool.setup_logger('DBLogger', yaml_config['logging']['logfiles']['database_logging_file'], level=yaml_config['logging']['level'])
DBLogger = logging.getLogger('DBLogger')
import pprint
DBLogger.info("DB Log Initialised.")
from logtool import *
>>>>>>> master

import os
from construct import Default
sys.path.append(os.path.realpath('lib'))
import S6a_crypt

<<<<<<< HEAD
# Create database if it does not exist.
if not database_exists(engine.url):
    create_database(engine.url)
=======


class MongoDB:
    import mongo
    import pymongo
    def __init__(self):
        DBLogger.info("Configured to use MongoDB server: " + str(yaml_config['database']['mongodb']['mongodb_server']))
        self.server = {}
        self.server['mongodb_server'] = yaml_config['database']['mongodb']['mongodb_server']
        self.server['mongodb_port'] = yaml_config['database']['mongodb']['mongodb_port']
        
    def QueryDB(self, imsi):
        #Search for user in MongoDB database
        myclient = self.pymongo.MongoClient("mongodb://" + str(self.server['mongodb_server']) + ":" + str(self.server['mongodb_port']) + "/")
        mydb = myclient["open5gs"]
        mycol = mydb["subscribers"]
        myquery = { "imsi": str(imsi)}
        DBLogger.debug("Querying MongoDB for subscriber " + str(imsi))
        return mycol.find(myquery)
        
    #Loads a subscriber's information from database into dict for referencing
    def GetSubscriberInfo(self, imsi):
        subscriber_details = {}
  
        try:
            mydoc = self.QueryDB(imsi)
        except:
            DBLogger.debug("Failed to pull subscriber info")
            raise ValueError("Failed to pull subscriber details for IMSI " + str(imsi) + " from MongoDB")

        #If query was completed Successfully extract data
        for x in mydoc:
            DBLogger.debug("Got result from MongoDB")
            DBLogger.debug(x)
            subscriber_details['K'] = x['security']['k'].replace(' ', '')
            try:
                subscriber_details['OP'] = x['security']['op'].replace(' ', '')
                DBLogger.debug("Database has OP stored - Converting to OPc")
                ##Convert to OPc
                subscriber_details['OPc'] = S6a_crypt.generate_opc(subscriber_details['K'], subscriber_details['OP'])
                #Remove OP reference from dict
                subscriber_details.pop('OP', None)
            except:
                subscriber_details['OPc'] = x['security']['opc'].replace(' ', '')
            subscriber_details['AMF'] = x['security']['amf'].replace(' ', '')
            try:
                subscriber_details['RAND'] = x['security']['rand'].replace(' ', '')
                subscriber_details['SQN'] = int(x['security']['sqn'])
            except:
                DBLogger.debug("Subscriber " + str() + " has not attached before - Generating new SQN and RAND")
                subscriber_details['SQN'] = 1
                subscriber_details['RAND'] = ''
            apn_list = ''
            for keys in x['slice'][0]['session']:
                apn_list += keys['name'] + ";"
            subscriber_details['APN_list'] = apn_list[:-1]      #Remove last semicolon
            DBLogger.debug("APN list is: " + str(subscriber_details['APN_list']))
            subscriber_details['pdn'] = x['slice'][0]['session']
            i = 0
            while i < len(subscriber_details['pdn']):
                #Rename from "name" to "apn"
                subscriber_details['pdn'][i]['apn'] = subscriber_details['pdn'][i]['name']
                #Store QCI data
                subscriber_details['pdn'][i]['qos']['qci'] = subscriber_details['pdn'][i]['qos']['index']
                #Map static P-GW Address
                if 'smf' in subscriber_details['pdn'][i]:
                    DBLogger.debug("SMF / PGW Address statically set in Subscriber profile")
                    subscriber_details['pdn'][i]['MIP6-Agent-Info'] = subscriber_details['pdn'][i]['smf']['addr']
                    DBLogger.debug("SMF IP is: " + str(subscriber_details['pdn'][i]['smf']['addr']))
                    #['PDN_GW_Allocation_Type'] ToDo - set to static
                i += 1
            DBLogger.debug(subscriber_details)
            return subscriber_details
        
        #if no results returned raise error
        raise ValueError("Mongodb has no matching subscriber details for IMSI " + str(imsi) + " from MongoDB")

    #Update a subscriber's information in MongoDB
    def UpdateSubscriber(self, imsi, sqn, rand, *args, **kwargs):
        DBLogger.debug("Updating " + str(imsi))
        
        #Check if MongoDB in use
        try:
            DBLogger.debug("Updating SQN for imsi " + str(imsi) + " to " + str(sqn))
            #Search for user in MongoDB database
            myclient = self.pymongo.MongoClient("mongodb://" + str(self.server['mongodb_server']) + ":" + str(self.server['mongodb_port']) + "/")
            mydb = myclient["open5gs"]
            mycol = mydb["subscribers"]
            myquery = { 'imsi': str(imsi) }
            newvalues = { "$set": {'security.rand': str(rand)} }
            mycol.update_one(myquery, newvalues)
            newvalues = { "$set": {'security.sqn': int(sqn)} }
            if 'origin_host' in kwargs:
                DBLogger.info("origin_host present - Storing location in DB")
                origin_host = kwargs.get('origin_host', None)
                newvalues = { "$set": {'origin_host': str(origin_host)} }
            mycol.update_one(myquery, newvalues)
            return sqn
        except:
            raise ValueError("Failed update SQN for subscriber " + str(imsi) + " in MongoDB")
        
    def GetSubscriberLocation(self, *args, **kwargs):
        DBLogger.debug("Called GetSubscriberLocation")
        if 'imsi' in kwargs:
            DBLogger.debug("IMSI present - Searching based on IMSI")
            try:
                imsi = kwargs.get('imsi', None)
                DBLogger.debug("GetSubscriberLocation IMSI is " + str(imsi))
                DBLogger.debug("Calling GetSubscriberLocation with IMSI " + str(imsi))
                mydoc = self.QueryDB(imsi)
                for x in mydoc:
                    DBLogger.debug(x)
                    try:
                        return x['origin_host']
                    except:
                        DBLogger.debug("No location stored for sub")
            except:
                DBLogger.debug("Failed to pull subscriber info")
                raise ValueError("Failed to pull subscriber details for IMSI " + str(imsi) + " from MongoDB")
     
        elif 'msisdn' in kwargs:
            DBLogger.debug("MSISDN present - Searching based on MSISDN ")
            try:
                msisdn = kwargs.get('msisdn', None)
                DBLogger.debug("msisdn is " + str(msisdn))
                DBLogger.debug("Calling GetSubscriberLocation with msisdn " + str(msisdn))
                mydoc = self.QueryDB(msisdn)
                for x in mydoc:
                    DBLogger.debug(x)
                    try:
                        return x['origin_host']
                    except:
                        DBLogger.debug("No location stored for sub")
            except:
                DBLogger.debug("Failed to pull subscriber info")
                raise ValueError("Failed to pull subscriber details for IMSI " + str(imsi) + " from MongoDB")
        

class MSSQL:
    import _mssql
    def __init__(self):
        DBLogger.info("Configured to use MS-SQL server: " + str(yaml_config['database']['mssql']['server']))
        self.server = yaml_config['database']['mssql']
        self._lock = threading.Lock()
        try:
            self.conn = self._mssql.connect(server=self.server['server'], user=self.server['username'], password=self.server['password'], database=self.server['database'])
            DBLogger.info("Connected to MSSQL Server")
        except:
            #If failed to connect to server
            DBLogger.fatal("Failed to connect to MSSQL server at " + str(self.server['server']))
            raise OSError("Failed to connect to MSSQL server at " + str(self.server['server']))
            sys.exit()

    def reset(self):
        DBLogger.info("Reinitializing / Instantiating DB Class")
        self.__init__()

    def GetSubscriberInfo(self, imsi):
        with self._lock:
            try:
                DBLogger.debug("Getting subscriber info from MSSQL for IMSI " + str(imsi))
                subscriber_details = {}
                sql = "hss_imsi_known_check @imsi=" + str(imsi)
                DBLogger.debug(sql)
                self.conn.execute_query(sql)
                DBLogger.debug("Ran hss_imsi_known_check OK - Checking results")
                DBLogger.debug("Parsing results to var")
                result = [ row for row in self.conn ]
                DBLogger.debug("Result total is " + str(result))
                DBLogger.debug("Getting first entry in result")
                result = result[0]
                DBLogger.debug("printing final result:")
                DBLogger.debug(str(result))
            except Exception as e:
                DBLogger.error("failed to run " + str(sql))
                DBLogger.error(e)
                logtool.RedisIncrimenter('AIR_hss_imsi_known_check_SQL_Fail')
                raise Exception("Failed to query MSSQL server with query: " + str(sql))

            try:
                #known_imsi: IMSI attached with sim returns 1 else returns 0
                if str(result['known_imsi']) != '1':
                    logtool.RedisIncrimenter('AIR_hss_imsi_known_check_IMSI_unattached_w_SIM')
                    raise ValueError("MSSQL reports IMSI " + str(imsi) + " not attached with SIM")

                #subscriber_status: -1 –Blocked or 0-Active
                if str(result['subscriber_status']) != '0':
                    logtool.RedisIncrimenter('AIR_hss_imsi_known_check_IMSI_Blocked')
                    raise ValueError("MSSQL reports Subscriber Blocked for IMSI " + str(imsi))

                apn_id = result['apn_configuration']


                DBLogger.debug("Running hss_get_subscriber_data_v2 for imsi " + str(imsi))
                sql = 'hss_get_subscriber_data_v2 @imsi="' + str(imsi) + '";'
                DBLogger.debug("SQL: " + str(sql))
                self.conn.execute_query(sql)
                result = [ row for row in self.conn ][0]

                DBLogger.debug("\nResult of hss_get_subscriber_data_v2_v2: " + str(result))
                #subscriber_status: -1 –Blocked or 0-Active (Again)
                if str(result['subscriber_status']) != '0':
                    logtool.RedisIncrimenter('AIR_hss_get_subscriber_data_v2_v2_IMSI_Blocked')
                    raise ValueError("MSSQL reports Subscriber Blocked for IMSI " + str(imsi))
                
                #Get data output and put it into structure PyHSS uses
                subscriber_details['RAT_freq_priorityID'] = result['RAT_freq_priorityID']
                subscriber_details['APN_OI_replacement'] = result['APN_OI_replacement']
                subscriber_details['3gpp_charging_ch'] = result['_3gpp_charging_ch']
                subscriber_details['ue_ambr_ul'] = result['MAX_REQUESTED_BANDWIDTH_UL']
                subscriber_details['ue_ambr_dl'] = result['MAX_REQUESTED_BANDWIDTH_DL']
                subscriber_details['K'] = result['ki']
                subscriber_details['SQN'] = result['seqno']
                subscriber_details['RAT_freq_priorityID'] = result['RAT_freq_priorityID']
                subscriber_details['3gpp-charging-characteristics'] = result['_3gpp_charging_ch']
                
                #Harcoding AMF as it is the same for all SIMs and not returned by DB
                subscriber_details['AMF'] = '8000'

                #Set dummy RAND value (No need to store it)
                subscriber_details['RAND'] = ""

                #Format MSISDN
                subscriber_details['msisdn'] = str(result['region_subscriber_zone_code']) + str(result['msisdn'])
                subscriber_details['msisdn'] = subscriber_details['msisdn'].split(';')[-1]
                subscriber_details['a-msisdn'] = str(result['msisdn'])

                #Convert OP to OPc
                subscriber_details['OP'] = result['op_key']
                DBLogger.debug("Generating OPc with input K: " + str(subscriber_details['K']) + " and OP: " + str(subscriber_details['OP']))
                subscriber_details['OPc'] = S6a_crypt.generate_opc(subscriber_details['K'], subscriber_details['OP'])
                subscriber_details.pop('OP', None)
                DBLogger.debug("Generated OPc " + str(subscriber_details['OPc']))


                DBLogger.debug("Getting APN info")
                sql = 'hss_get_apn_info @apn_profileId=' + str(apn_id)
                DBLogger.debug(sql)
                self.conn.execute_query(sql)
                DBLogger.debug("Ran query")
                subscriber_details['pdn'] = []
                DBLogger.debug("Parsing results to var")
                result = [ row for row in self.conn ][0]
                DBLogger.debug("Got results")
                DBLogger.debug("Results are: " + str(result))
                apn = {'apn': str(result['Service_Selection']),\
                        'pcc_rule': [], 'qos': {'qci': int(result['QOS_CLASS_IDENTIFIER']), \
                        'arp': {'priority_level': int(result['QOS_PRIORITY_LEVEL']), 'pre_emption_vulnerability': int(result['QOS_PRE_EMP_VULNERABILITY']), 'pre_emption_capability': int(result['QOS_PRE_EMP_CAPABILITY'])}},\
                        'ambr' : {'apn_ambr_ul' : int(result['MAX_REQUESTED_BANDWIDTH_UL']), 'apn_ambr_Dl' : int(result['MAX_REQUESTED_BANDWIDTH_DL'])},
                        'PDN_GW_Allocation_Type' : int(result['PDN_GW_Allocation_Type']),
                        'VPLMN_Dynamic_Address_Allowed' : int(result['VPLMN_Dynamic_Address_Allowed']),
                        'type': 2, 'MIP6-Agent-Info' : {'MIP6_DESTINATION_HOST' : result['MIP6_DESTINATION_HOST'], 'MIP6_DESTINATION_REALM' : result['MIP6_DESTINATION_REALM']}}
                subscriber_details['pdn'].append(apn)

                DBLogger.debug("Final subscriber data for IMSI " + str(imsi) + " is: " + str(subscriber_details))
                return subscriber_details
            except Exception as e:
                logtool.RedisIncrimenter('AIR_general')
                DBLogger.error("General MSSQL Error")
                DBLogger.error(e)
                raise ValueError("MSSQL failed to return valid data for IMSI " + str(imsi))   
                

    def GetSubscriberLocation(self, *args, **kwargs):
        with self._lock:
            DBLogger.debug("Called GetSubscriberLocation")
            if 'imsi' in kwargs:
                DBLogger.debug("IMSI present - Searching based on IMSI")
                try:
                    imsi = kwargs.get('imsi', None)
                    DBLogger.debug("Calling hss_get_mme_identity_by_info with IMSI " + str(imsi))
                    sql = 'hss_get_mme_identity_by_info ' + str(imsi) + ';'
                    DBLogger.info(sql)
                    self.conn.execute_query(sql)
                    DBLogger.debug(self.conn)
                except Exception as e:
                    DBLogger.error("failed to run " + str(sql))
                    DBLogger.error(e)
                    raise ValueError("MSSQL failed to run SP hss_get_mme_identity_by_info for IMSI " + str(imsi))     
            elif 'msisdn' in kwargs:
                DBLogger.debug("MSISDN present - Searching based on MSISDN")
                try:
                    msisdn = kwargs.get('msisdn', None)
                    DBLogger.debug("Calling hss_get_mme_identity_by_info with msisdn " + str(msisdn))
                    sql = 'hss_get_mme_identity_by_info ' + str(msisdn) + ';'
                    self.conn.execute_query(sql)
                    DBLogger.debug(self.conn)
                except:
                    DBLogger.critical("MSSQL failed to run SP hss_get_mme_identity_by_info for msisdn " + str(msisdn))
                    raise ValueError("MSSQL failed to run SP hss_get_mme_identity_by_info for msisdn " + str(msisdn)) 
                    
            else:
                raise ValueError("No IMSI or MSISDN provided - Aborting")
            
            try:
                DBLogger.debug(self.conn)
                result = [ row for row in self.conn ][0]
                DBLogger.debug("Returned data:")
                DBLogger.debug(result)
                DBLogger.debug("Stripping to only include Origin_Host")
                result = result['Origin_Host']
                DBLogger.debug("Final result is: " + str(result))
                return result
            except:
                DBLogger.debug("No location stored in database for Subscriber")
                raise ValueError("No location stored in database for Subscriber")

    def ManageFullSubscriberLocation(self, imsi, serving_hss, serving_mme, realm, dra):
        DBLogger.debug("Called ManageFullSubscriberLocation with IMSI " + str(imsi))
        with self._lock:
            try:
                DBLogger.debug("Getting full location for IMSI: " + str(imsi))
                sql = "hss_cancel_loc_get_imsi_info @imsi='" + str(imsi) + "';"
                DBLogger.debug(sql)
                self.conn.execute_query(sql)
                DBLogger.debug(self.conn)
                try:
                    DBLogger.debug(self.conn)
                    result = [ row for row in self.conn ][0]
                    DBLogger.debug("Final result is: " + str(result))
                except:
                    DBLogger.debug("Failed to get result from query")
            except Exception as e:
                DBLogger.error("MSSQL failed to run SP " + str(sql))  
                DBLogger.error(e)
            DBLogger.debug("Ran Query OK...")


            DBLogger.debug("Full MME Location to write to DB, serving HSS: " + str(serving_hss) + ", realm: " + str(realm) + ", serving_mme: " + str(serving_mme) + " connected via Diameter Peer " + str(dra))
            try:
                sql = 'hss_cancl_loc_imsi_insert_info @imsi=\'' + str(imsi) + '\', @serving_hss=\'' + str(serving_hss) + '\', @serving_mme=\'' + str(serving_mme) + '\', @diameter_realm=\'' + str(realm) + '\', @dra=\'' + str(dra) + '\';'
                DBLogger.debug(sql)
                self.conn.execute_query(sql)
                DBLogger.debug("Successfully ran hss_cancl_loc_imsi_insert_info for " + str(imsi))
            except:
                DBLogger.error("MSSQL failed to run SP hss_cancl_loc_imsi_insert_info with IMSI " + str(imsi))

            DBLogger.debug("Completed ManageFullSubscriberLocation")
            return result


    def UpdateSubscriber(self, imsi, sqn, rand, *args, **kwargs):
        with self._lock:
            try:
                DBLogger.debug("Updating SQN for imsi " + str(imsi) + " to " + str(sqn))
                try:
                    DBLogger.debug("Updating SQN using SP hss_auth_get_ki_v2")
                    sql = 'hss_auth_get_ki_v2 @imsi=' + str(imsi) + ', @NBofSeq=' + str(sqn) + ';'
                    DBLogger.debug(sql)
                    self.conn.execute_query(sql)
                    DBLogger.debug(self.conn)
                except Exception as e:
                    DBLogger.error("MSSQL failed to run SP hss_auth_get_ki_v2 with SQN " + str(sqn) + " for IMSI " + str(imsi))  
                    DBLogger.error(e)
                    raise ValueError("MSSQL failed to run SP hss_auth_get_ki_v2 with SQN " + str(sqn) + " for IMSI " + str(imsi))  

                #If optional origin_host kwag present, store UE location (Serving MME) in Database
                if 'origin_host' in kwargs:
                    DBLogger.debug("origin_host present - Updating MME Identity of subscriber in MSSQL")
                    origin_host = kwargs.get('origin_host', None)
                    DBLogger.debug("Origin to write to DB is " + str(origin_host))
                    if len(origin_host) != 0:
                        try:
                            DBLogger.debug("origin-host valid - Writing back to DB")
                            sql = 'hss_update_mme_identity @imsi=' + str(imsi) + ', @orgin_host=\'' + str(origin_host) + '\', @Cancellation_Type=0, @ue_purged_mme=0;'
                            DBLogger.debug(sql)
                            self.conn.execute_query(sql)
                            DBLogger.debug("Successfully updated location for " + str(imsi))
                        except:
                            DBLogger.error("MSSQL failed to run SP hss_update_mme_identity with IMSI " + str(imsi) + " and Origin_Host " + str(origin_host))
                    else:
                        try:
                            DBLogger.debug("Removing MME Identity as new MME Identity is empty")
                            sql = 'hss_delete_mme_identity @imsi=' + str(imsi) 
                            DBLogger.debug(sql)
                            self.conn.execute_query(sql)
                            DBLogger.debug("Successfully cleared location for " + str(imsi))
                        except:
                            DBLogger.error("MSSQL failed to run SP hss_delete_mme_identity with IMSI " + str(imsi))
                else:
                    DBLogger.debug("origin_host not present - not updating UE location in database")
                
            except:
                raise ValueError("MSSQL failed to update IMSI " + str(imsi))   
        
    def GetSubscriberIMSI(self, msisdn):
        with self._lock:
            try:
                DBLogger.debug("Getting Subscriber IMSI from MSISDN" + str(msisdn))
                sql = 'hss_get_imsi_by_msisdn @msisdn=' + str(msisdn) + ';'
                DBLogger.debug(sql)
                self.conn.execute_query(sql)
                DBLogger.debug(self.conn)
            except Exception as e:
                DBLogger.error("MSSQL failed to run SP " + str(sql))  
                DBLogger.error(e)
                raise ValueError("MSSQL failed to run SP " + str(sql))  
        DBLogger.debug("Ran Query OK...")
        try:
            DBLogger.debug(self.conn)
            result = [ row for row in self.conn ][0]
            DBLogger.debug("Returned data:")
            DBLogger.debug(result)
            DBLogger.debug("Stripping to only include imsi")
            result = result['imsi']
            DBLogger.debug("Final result is: " + str(result))            
            DBLogger.debug(result)
            DBLogger.debug("Final result is: " + str(result))
            return result
        except:
            DBLogger.debug("IMSI for MSISDN Provided.")
            raise ValueError("IMSI for MSISDN Provided.")

class MySQL:
    import mysql.connector
    def __init__(self):
        DBLogger.info("Configured to use MySQL server: " + str(yaml_config['database']['mysql']['server']))
        self.server = yaml_config['database']['mysql']
        self.mydb = self.mysql.connector.connect(
          host=self.server['server'],
          user=self.server['username'],
          password=self.server['password'],
          database=self.server['database'],
          auth_plugin='mysql_native_password'
        )
        self.mydb.autocommit = True
        self.mydb.SQL_QUERYTIMEOUT = 3
        cursor = self.mydb.cursor(dictionary=True)
        self.cursor = cursor
        
    def GetSubscriberInfo(self, imsi):
        DBLogger.debug("Getting subscriber info from MySQL for IMSI " + str(imsi))
        sql = "select * from subscribers \
            left join auc on subscribers.imsi = auc.imsi \
            left join apn on subscribers.apn_default  = apn.id  \
            where subscribers.imsi LIKE '" +  str(imsi) + "' and subscribers.enabled = True;"
        DBLogger.debug(sql)
        self.cursor.execute(sql)
        try:
            sql_result = self.cursor.fetchall()[0]
        except:
            DBLogger.info("Failed to get subscriber " + str(imsi))
            raise ValueError("No matching subscriber found in database")
        DBLogger.debug("sql_result: " + str(sql_result))


        #Format default APN
        APN_list = []
        apn_obj = { "apn": str(sql_result['apn']), "type": 3, "ambr" : {"uplink" : int(sql_result['apn_ambr_ul']), "downlink": int(sql_result['apn_ambr_dl'])},
                            'qos': {'qci': int(sql_result['qci']), 'arp': {'priority_level': int(sql_result['arp_priority']), 'pre_emption_vulnerability': int(sql_result['arp_preemption_vulnerability']), 'pre_emption_capability': int(sql_result['arp_preemption_capability'])}},
        }
        if sql_result['pgw-address'] is not None:
            DBLogger.debug("Static PGW selection set to " + str(sql_result['pgw-address']))
            apn_obj['MIP6-Agent-Info'] = str(sql_result['pgw-address'])

        APN_list.append(apn_obj)


        #Check if additional APNs set:
        if len(sql_result['apn_additional_list']) > 0:
            DBLogger.debug("Additional APNs set - Retrieving all APNs")
            try:
                apn_list = sql_result['apn_additional_list'].split(',')
                DBLogger.debug("Additional APN IDs: " + str(apn_list))
                #Get all the APNs from the database
                sql = "select * from apn;"
                DBLogger.debug(sql)
                self.cursor.execute(sql)
                apn_sql_result = self.cursor.fetchall()
                for apn in apn_sql_result:
                    if str(apn['id']) in apn_list:
                        DBLogger.debug("Adding APN ID " + str(apn['id']) + " " + str(apn['apn']) + " into APN list ")
                        DBLogger.debug(apn)
                        apn_obj = { "apn": str(apn['apn']), "type": 3, \
                            "ambr" : {"uplink" : int(apn['apn_ambr_ul']), "downlink": int(apn['apn_ambr_dl'])},
                            'qos': {'qci': int(apn['qci']), 'arp': {'priority_level': int(apn['arp_priority']), 'pre_emption_vulnerability': int(apn['arp_preemption_vulnerability']), 'pre_emption_capability': int(apn['arp_preemption_capability'])}}
                        }
                        if apn['pgw-address'] is not None:
                            DBLogger.debug("Static PGW selection set to " + str(apn['pgw-address']))
                            apn_obj['MIP6-Agent-Info'] = str(apn['pgw-address'])
                        APN_list.append(apn_obj)
                    else:
                        DBLogger.debug("APN ID " + str(apn['id']) + " " + str(apn['apn']) + " is not available for this subscriber")

            except Exception as E:
                DBLogger.error("Failed to retrieve all additional APNs for sub " + str(imsi))
                DBLogger.error(E)
        else:
            DBLogger.debug("Only default APN set")


        subscriber_details = {
            'imsi' : str(sql_result['imsi']),
            'K': str(sql_result['ki']), 'OPc': str(sql_result['opc']), 'AMF': str(sql_result['amf']), 'RAND': str(sql_result['rand']), 'SQN': int(sql_result['sqn']),
            'pdn' : APN_list,
            'msisdn' : str(sql_result['msisdn'])
        }
        DBLogger.debug(pprint.pprint(subscriber_details))


        return subscriber_details

    def UpdateSubscriber(self, imsi, sqn, rand, **kwargs):
        DBLogger.debug("Called UpdateSubscriber() for IMSI " + str(imsi) + " and kwargs " + str(kwargs))
        if 'serving_mme' in kwargs:
            DBLogger.debug("UpdateSubscriber called with Serving MME present")
            query = "update subscribers set serving_mme = '" + str(kwargs.get('serving_mme', None)) + "', serving_mme_timestamp = current_timestamp where imsi = '" + str(imsi) + "';"
            DBLogger.debug(query)
            self.cursor.execute(query)
            return

        if 'serving_pgw' in kwargs:
            DBLogger.debug("UpdateSubscriber called with Serving PGW present")
            query = "update subscribers set serving_pgw = '" + str(kwargs.get('serving_pgw', None)) + "', serving_pgw_timestamp = current_timestamp where imsi = '" + str(imsi) + "';"
            DBLogger.debug(query)
            self.cursor.execute(query)
            return

        if 'clearloc' in kwargs:
            DBLogger.debug("UpdateSubscriber called to clear location")
            if kwargs.get('clearloc', None) == 'pgw':
                query = "update subscribers set serving_pgw = NULL, serving_pgw_timestamp = NULL where imsi = '" + str(imsi) + "';"
            elif kwargs.get('clearloc', None) == 'mme':
                query = "update subscribers set serving_mme = NULL, serving_mme_timestamp = NULL where imsi = '" + str(imsi) + "';"
            DBLogger.debug(query)
            self.cursor.execute(query)
            return

        DBLogger.debug("Updating SQN for imsi " + str(imsi) + " to " + str(sqn))
        query = "update auc set sqn = " + str(sqn) + " where imsi = '" + str(imsi) + "';"
        DBLogger.debug(query)
        self.cursor.execute(query)
       
class Stub:
    def __init__(self):
        DBLogger.info("Configured to use stub database - No actual database connection exists")
        
    def GetSubscriberInfo(self, imsi):
        DBLogger.debug("Not getting subscriber info from Postgresql for IMSI " + str(imsi))
        return

    def UpdateSubscriber(self, imsi, sqn, rand, **kwargs):
        DBLogger.debug("Called UpdateSubscriber() for IMSI " + str(imsi) + " and kwargs " + str(kwargs))
        DBLogger.debug("Not updating subscriber info from Postgresql for IMSI " + str(imsi))
        return

class PostgreSQL:
    def __init__(self):
        import psycopg
        from psycopg.rows import dict_row
        DBLogger.info("Configured to use Postgresql server: " + str(yaml_config['database']['postgresql']['server']))
        self.serverinfo = yaml_config['database']['postgresql']
        self.mydb = psycopg.connect(
        host=self.serverinfo['server'],
        port=self.serverinfo['port'],
        dbname=self.serverinfo['database'],
        user=self.serverinfo['username'],
        password=self.serverinfo['password'],
        row_factory=dict_row)
        self.mydb.autocommit = True
        cursor = self.mydb.cursor()
        self.cursor = cursor
        
        
    def GetSubscriberInfo(self, imsi):
        DBLogger.debug("Getting subscriber info from Postgresql for IMSI " + str(imsi))
        sql = "select * from subscribers \
            left join auc on subscribers.imsi = auc.imsi \
            left join apn on subscribers.apn_default  = apn.id  \
            where subscribers.imsi = '" +  str(imsi) + "' and subscribers.enabled = True;"
        DBLogger.debug(sql)
        self.cursor.execute(sql)
        try:
            sql_result = self.cursor.fetchall()[0]
        except:
            DBLogger.info("Failed to get subscriber " + str(imsi))
            raise ValueError("No matching subscriber found in database")
        DBLogger.debug(sql_result)

        #Format default APN
        APN_list = []
        apn_obj = { "apn": str(sql_result['apn']), "type": 3, \
                            "ambr" : {"uplink" : int(sql_result['apn_ambr_ul']), "downlink": int(sql_result['apn_ambr_dl'])},
                            'qos': {'qci': int(sql_result['qci']), 'arp': {'priority_level': int(sql_result['arp_priority']), 'pre_emption_vulnerability': int(sql_result['arp_preemption_vulnerability']), 'pre_emption_capability': int(sql_result['arp_preemption_capability'])}},
        }
        if sql_result['pgw-address'] is not None:
            DBLogger.debug("Static PGW selection set to " + str(sql_result['pgw-address']))
            apn_obj['MIP6-Agent-Info'] = str(sql_result['pgw-address'])

        APN_list.append(apn_obj)

        #Check if additional APNs set:
        if len(sql_result['apn_additional_list']) > 0:
            DBLogger.debug("Additional APNs set - Retrieving all APNs")
            try:
                apn_list = sql_result['apn_additional_list'].split(',')
                DBLogger.debug("Additional APN IDs: " + str(apn_list))
                #Get all the APNs from the database
                sql = "select * from apn;"
                DBLogger.debug(sql)
                self.cursor.execute(sql)
                apn_sql_result = self.cursor.fetchall()
                for apn in apn_sql_result:
                    if str(apn['id']) in apn_list:
                        DBLogger.debug("Adding APN ID " + str(apn['id']) + " " + str(apn['apn']) + " into APN list ")
                        DBLogger.debug(apn)
                        apn_obj = { "apn": str(apn['apn']), "type": 3, \
                            "ambr" : {"uplink" : int(apn['apn_ambr_ul']), "downlink": int(apn['apn_ambr_dl'])},
                            'qos': {'qci': int(apn['qci']), 'arp': {'priority_level': int(apn['arp_priority']), 'pre_emption_vulnerability': int(apn['arp_preemption_vulnerability']), 'pre_emption_capability': int(apn['arp_preemption_capability'])}}
                        }
                        if apn['pgw-address'] is not None:
                            DBLogger.debug("Static PGW selection set to " + str(apn['pgw-address']))
                            apn_obj['MIP6-Agent-Info'] = str(apn['pgw-address'])
                        APN_list.append(apn_obj)
                    else:
                        DBLogger.debug("APN ID " + str(apn['id']) + " " + str(apn['apn']) + " is not available for this subscriber")

            except Exception as E:
                DBLogger.error("Failed to retrieve all additional APNs for sub " + str(imsi))
                DBLogger.error(E)
        else:
            DBLogger.debug("Only default APN set")


        subscriber_details = {
            'imsi' : str(sql_result['imsi']),
            'K': str(sql_result['ki']), 'OPc': str(sql_result['opc']), 'AMF': str(sql_result['amf']), 'RAND': str(sql_result['rand']), 'SQN': int(sql_result['sqn']),
            'pdn' : APN_list,
            'msisdn' : str(sql_result['msisdn']),
            'ue_ambr_ul' : int(sql_result['ue_ambr_ul']),
            'ue_ambr_dl' : int(sql_result['ue_ambr_dl']),
        }
        DBLogger.debug(pprint.pprint(subscriber_details))


        return subscriber_details

    def UpdateSubscriber(self, imsi, sqn, rand, **kwargs):
        DBLogger.debug("Called UpdateSubscriber() for IMSI " + str(imsi) + " and kwargs " + str(kwargs))
        if 'serving_mme' in kwargs:
            DBLogger.debug("UpdateSubscriber called with Serving MME present")
            query = "update subscribers set serving_mme = '" + str(kwargs.get('serving_mme', None)) + "', serving_mme_timestamp = current_timestamp where imsi = '" + str(imsi) + "';"
            DBLogger.debug(query)
            self.cursor.execute(query)
            return

        if 'serving_pgw' in kwargs:
            DBLogger.debug("UpdateSubscriber called with Serving PGW present")
            query = "update subscribers set serving_pgw = '" + str(kwargs.get('serving_pgw', None)) + "', serving_pgw_timestamp = current_timestamp where imsi = '" + str(imsi) + "';"
            DBLogger.debug(query)
            self.cursor.execute(query)
            return

        if 'clearloc' in kwargs:
            DBLogger.debug("UpdateSubscriber called to clear location")
            if kwargs.get('clearloc', None) == 'pgw':
                query = "update subscribers set serving_pgw = NULL, serving_pgw_timestamp = NULL where imsi = '" + str(imsi) + "';"
            elif kwargs.get('clearloc', None) == 'mme':
                query = "update subscribers set serving_mme = NULL, serving_mme_timestamp = NULL where imsi = '" + str(imsi) + "';"
            DBLogger.debug(query)
            self.cursor.execute(query)
            return

        DBLogger.debug("Updating SQN for imsi " + str(imsi) + " to " + str(sqn))
        query = "update auc set sqn = " + str(sqn) + " where imsi = '" + str(imsi) + "';"
        DBLogger.debug(query)
        self.cursor.execute(query)
       

#Load DB functions based on Config
for db_option in yaml_config['database']:
    DBLogger.debug("Selected DB backend " + str(db_option))
    break

if db_option == "mongodb":
    DB = MongoDB()
elif db_option == "mssql":
    DB = MSSQL()
elif db_option == "mysql":
    DB = MySQL()
elif db_option == "postgresql":
    DB = PostgreSQL()
elif db_option == "stub":
    DB = Stub()
>>>>>>> master
else:
    # Connect the database if exists.
    engine.connect()

class APN(Base):
    __tablename__ = 'apn'
    apn_id = Column(Integer, primary_key=True)
    apn = Column(String(50), nullable=False)
    pgw_address = Column(String(50))
    sgw_address = Column(String(50))
    charging_characteristics = Column( String(4), default='0800')
    apn_ambr_dl = Column(Integer, nullable=False)
    apn_ambr_ul = Column(Integer, nullable=False)
    qci = Column(Integer, default=9)
    arp_priority = Column(Integer, default=4)
    arp_preemption_capability = Column(Boolean, default=False)
    arp_preemption_vulnerability = Column(Boolean, default=True)

class Serving_APN(Base):
    __tablename__ = 'serving_apn'
    serving_apn_id = Column(Integer, primary_key=True)
    subscriber_id = Column(Integer, ForeignKey('subscriber.subscriber_id'))
    apn = Column(Integer, ForeignKey('apn.apn_id'))
    serving_pgw = Column(String(50))
    serving_pgw_timestamp = Column(DateTime)


class AUC(Base):
    __tablename__ = 'auc'
    auc_id = Column(Integer, primary_key = True)
    ki = Column(String(32))
    opc = Column(String(32))
    amf = Column(String(4))
    sqn = Column(Integer)


class SUBSCRIBER(Base):
    __tablename__ = 'subscriber'
    subscriber_id = Column(Integer, primary_key = True)
    imsi = Column(String(18), unique=True)
    enabled = Column(Boolean, default=1)
    auc_id = Column(Integer, ForeignKey('auc.auc_id'))
    default_apn = Column(Integer, ForeignKey('apn.apn_id'))
    apn_list = Column(String(18))
    msisdn = Column(String(18))
    ue_ambr_dl = Column(Integer, default=999999)
    ue_ambr_ul = Column(Integer, default=999999)
    nam = Column(Integer, default=0)
    subscribed_rau_tau_timer = Column(Integer, default=300)
    serving_mme = Column(String(50))
    serving_mme_timestamp = Column(DateTime)

class IMS_SUBSCRIBER(Base):
    __tablename__ = 'ims_subscriber'
    ims_subscriber_id = Column(Integer, primary_key = True)
    msisdn = Column(String(18), unique=True)
    msisdn_list = Column(String(1200))
    imsi = Column(String(18), unique=False)
    ifc_path = Column(String(18))
    sh_profile = Column(String(12000))
    scscf = Column(String(50))
    scscf_timestamp = Column(DateTime)


Base.metadata.create_all(engine)
Session = sessionmaker(bind = engine)
session = Session()

def GetObj(obj_type, obj_id):
    print("Called GetObj for type " + str(obj_type) + " with id " + str(obj_id))
    result = session.query(obj_type).get(obj_id)
    result = result.__dict__
    result.pop('_sa_instance_state')
    for keys in result:
        if type(result[keys]) == DateTime:
            result[keys] = str(result[keys])
    return result

def UpdateObj(obj_type, json_data, obj_id):
    print("Called UpdateObj() for type " + str(obj_type) + " id " + str(obj_id) + " with JSON data: " + str(json_data))
    obj_type_str = str(obj_type.__table__.name).upper()
    print("obj_type_str is " + str(obj_type_str))
    filter_input = eval(obj_type_str + "." + obj_type_str.lower() + "_id==obj_id")
    sessionquery = session.query(obj_type).filter(filter_input)
    print("got result: " + str(sessionquery.__dict__))
    sessionquery.update(json_data, synchronize_session = False)
    session.commit()
    return GetObj(obj_type, obj_id)

def DeleteObj(obj_type, obj_id):
    print("Called DeleteObj for type " + str(obj_type) + " with id " + str(obj_id))
    res = session.query(obj_type).get(obj_id)
    session.delete(res)
    session.commit()
    return {"Result":"OK"}

def CreateObj(obj_type, json_data):
    newObj = obj_type(**json_data)
    session.add(newObj)
    session.commit()
    session.refresh(newObj)
    result = newObj.__dict__
    result.pop('_sa_instance_state')
    return result

def Generate_JSON_Model_for_Flask(obj_type):
    from alchemyjsonschema import SchemaFactory
    from alchemyjsonschema import NoForeignKeyWalker
    import pprint as pp
    factory = SchemaFactory(NoForeignKeyWalker)
    dictty = dict(factory(obj_type))
    dictty['properties'] = dict(dictty['properties'])

    #Set the ID Object to not required
    obj_type_str = str(dictty['title']).lower()
    dictty['required'].remove(obj_type_str + '_id')
   
    return dictty

def Get_IMS_Subscriber(**kwargs):
    #Get subscriber by IMSI or MSISDN
    if 'msisdn' in kwargs:
        print("Get_IMS_Subscriber for msisdn " + str(kwargs['msisdn']))
        try:
            result = session.query(SUBSCRIBER).filter_by(msisdn=str(kwargs['msisdn'])).one()
        except:
            raise ValueError("IMS Subscriber not Found")
    elif 'imsi' in kwargs:
        print("Get_IMS_Subscriber for imsi " + str(kwargs['imsi']))
        try:
            result = session.query(IMS_SUBSCRIBER).filter_by(imsi=str(kwargs['imsi'])).one()
        except:
            raise ValueError("IMS Subscriber not Found")
    print("Converting result to dict")
    result = result.__dict__
    try:
        result.pop('_sa_instance_state')
    except:
        pass
    print("Returning IMS Subscriber Data: " + str(result))
    return result

def Get_Subscriber(imsi):
    print("Get_Subscriber for IMSI " + str(imsi))
    try:
        result = session.query(SUBSCRIBER).filter_by(imsi=imsi).one()
    except:
        raise ValueError("Subscriber not Found")
    result = result.__dict__
    result.pop('_sa_instance_state')
    return result

def Get_Vectors_AuC(auc_id, action, **kwargs):
    print("Getting Vectors for auc_id " + str(auc_id) + " with action " + str(action))
    key_data = GetObj(AUC, auc_id)
    vector_dict = {}
    
    if action == "air":
        rand, xres, autn, kasme = S6a_crypt.generate_eutran_vector(key_data['ki'], key_data['opc'], key_data['amf'], key_data['sqn'], kwargs['plmn']) 
        vector_dict['rand'] = rand
        vector_dict['xres'] = xres
        vector_dict['autn'] = autn
        vector_dict['kasme'] = kasme

        #Incriment SQN
        Update_AuC(auc_id, sqn=key_data['sqn']+100)

        return vector_dict

    elif action == "air_resync":
        print("Resync SQN")
        sqn, mac_s = S6a_crypt.generate_resync_s6a(key_data['ki'], key_data['opc'], key_data['amf'], kwargs['auts'], kwargs['rand'])
        print("SQN from resync: " + str(sqn) + " SQN in DB is "  + str(key_data['sqn']) + "(Difference of " + str(int(sqn) - int(key_data['sqn'])) + ")")
        Update_AuC(auc_id, sqn=sqn+100)
        return
    
    elif action == "sip_auth":
        SIP_Authenticate, xres, ck, ik = S6a_crypt.generate_maa_vector(key_data['ki'], key_data['opc'], key_data['amf'], key_data['sqn'], kwargs['plmn'])
        vector_dict['SIP_Authenticate'] = SIP_Authenticate
        vector_dict['xres'] = xres
        vector_dict['ck'] = ck
        vector_dict['ik'] = ik
        Update_AuC(auc_id, sqn=key_data['sqn']+100)
        return vector_dict

def Get_APN(apn_id):
    print("Getting APN " + str(apn_id))
    try:
        result = session.query(APN).filter_by(apn_id=apn_id).one()
    except:
        raise ValueError("APN not Found")
    result = result.__dict__
    result.pop('_sa_instance_state')
    return result    

def Update_AuC(auc_id, sqn=1):
    print("Incrimenting SQN for sub " + str(auc_id))
    print(UpdateObj(AUC, {'sqn': sqn}, auc_id))
    return

def Update_Serving_MME(imsi, serving_mme):
    print("Updating Serving MME for sub " + str(imsi) + " to MME " + str(serving_mme))
    result = session.query(SUBSCRIBER).filter_by(imsi=imsi).one()
    if type(serving_mme) == str:
        print("Updating serving MME")
        result.serving_mme = serving_mme
        result.serving_mme_timestamp = datetime.datetime.now()
    else:
        #Clear values
        print("Clearing serving MME")
        result.serving_mme = None
        result.serving_mme_timestamp = None
    session.commit()
    return

def Update_Serving_CSCF(imsi, serving_cscf):
    print("Update_Serving_CSCF for sub " + str(imsi) + " to SCSCF " + str(serving_cscf))
    result = session.query(IMS_SUBSCRIBER).filter_by(imsi=imsi).one()
    if type(serving_cscf) == str:
        print("Updating serving CSCF")
        result.scscf = serving_cscf
        result.scscf_timestamp = datetime.datetime.now()
    else:
        #Clear values
        print("Clearing serving CSCF")
        result.scscf = None
        result.scscf_timestamp = None
    session.commit()
    return    

def Update_Location(imsi, apn, diameter_realm, diameter_peer, diameter_origin):
    return

def Get_IMSI_from_MSISDN(msisdn):
    return

if __name__ == "__main__":


    import binascii,os
    apn2 = {'apn':'fadsgdsags', \
        'apn_ambr_dl' : 9999, 'apn_ambr_ul' : 9999, \
        'arp_priority': 1, 'arp_preemption_capability' : False, \
        'arp_preemption_vulnerability': True}
    newObj = CreateObj(APN, apn2)
    print(newObj)

    print(GetObj(APN, newObj['apn_id']))
    apn_id = newObj['apn_id']
    UpdatedObj = newObj
    UpdatedObj['apn'] = 'UpdatedInUnitTest'
    
    newObj = UpdateObj(APN, UpdatedObj, newObj['apn_id'])
    print(newObj)

    #Create AuC
    auc_json = {
    "ki": binascii.b2a_hex(os.urandom(16)).zfill(16),
    "opc": binascii.b2a_hex(os.urandom(16)).zfill(16),
    "amf": "9000",
    "sqn": 0
    }
    print(auc_json)
    newObj = CreateObj(AUC, auc_json)
    print(newObj)

    #Get AuC
    newObj = GetObj(AUC, newObj['auc_id'])
    auc_id = newObj['auc_id']
    print(newObj)

    #Update AuC
    newObj['sqn'] = newObj['sqn'] + 10
    newObj = UpdateObj(AUC, newObj, auc_id)

    #Generate Vectors
    Get_Vectors_AuC(auc_id, "air", plmn='12ff')
    print(Get_Vectors_AuC(auc_id, "sip_auth", plmn='12ff'))

    #New Subscriber
    subscriber_json = {
        "imsi": "001001000000006",
        "enabled": True,
        "msisdn": "12345678",
        "ue_ambr_dl": 999999,
        "ue_ambr_ul": 999999,
        "nam": 0,
        "subscribed_rau_tau_timer": 600,
        "auc_id" : auc_id,
        "default_apn" : apn_id,
        "apn_list" : apn_id
    }
    print(subscriber_json)
    newObj = CreateObj(SUBSCRIBER, subscriber_json)
    print(newObj)
    subscriber_id = newObj['subscriber_id']

    #Get SUBSCRIBER
    newObj = GetObj(SUBSCRIBER, subscriber_id)
    print(newObj)

    #Update SUBSCRIBER
    newObj['ue_ambr_ul'] = 999995
    newObj = UpdateObj(SUBSCRIBER, newObj, subscriber_id)

    #Set MME Location for Subscriber
    Update_Serving_MME(newObj['imsi'], "Test123")
    #Clear MME Location for Subscriber    
    Update_Serving_MME(newObj['imsi'], None)

    #New IMS Subscriber
    ims_subscriber_json = {
        "msisdn": newObj['msisdn'], 
        "msisdn_list": newObj['msisdn'],
        "imsi": subscriber_json['imsi'],
        "ifc_path" : "default_ifc.xml",
        "sh_profile" : "default_sh_user_data.xml"
    }
    print(ims_subscriber_json)
    newObj = CreateObj(IMS_SUBSCRIBER, ims_subscriber_json)
    print(newObj)
    ims_subscriber_id = newObj['ims_subscriber_id']


    #Test Get Subscriber
    GetSubscriber_Result = Get_Subscriber(subscriber_json['imsi'])
    print(GetSubscriber_Result)

    #Test IMS Get Subscriber
    print("\n\n\n")
    print(Get_IMS_Subscriber(imsi='001001000000006'))
    print(Get_IMS_Subscriber(msisdn='12345678'))

    #Set SCSCF for Subscriber
    Update_Serving_CSCF(newObj['imsi'], "NickTestCSCF")
    #Clear MME Location for Subscriber    
    Update_Serving_CSCF(newObj['imsi'], None)

    #Test getting APNs
    GetAPN_Result = Get_APN(GetSubscriber_Result['default_apn'])
    print(GetAPN_Result)


    #Delete IMS Subscriber
    print(DeleteObj(IMS_SUBSCRIBER, ims_subscriber_id))
    #Delete Subscriber
    print(DeleteObj(SUBSCRIBER, subscriber_id))
    #Delete AuC
    print(DeleteObj(AUC, auc_id))
    #Delete APN
    print(DeleteObj(APN, apn_id))
