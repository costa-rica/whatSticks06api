from flask import Blueprint
from flask import Flask, request, jsonify, make_response, current_app
from wsh_config import ConfigDev, ConfigProd
from wsh_models import sess, Users, Oura_token, Oura_sleep_descriptions,\
    Locations, Weather_history, User_location_day
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import os


if os.environ.get('COMPUTERNAME')=='CAPTAIN2020' or os.environ.get('COMPUTERNAME')=='NICKSURFACEPRO4':
    config = ConfigDev()
    print('* Development')
else:
    config = ConfigProd()
    print('* ---> Configured for Production')

logs_dir = os.path.abspath(os.path.join(os.getcwd(), 'logs'))

#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_sched = logging.getLogger(__name__)
logger_sched.setLevel(logging.DEBUG)
# logger_terminal = logging.getLogger('terminal logger')
# logger_terminal.setLevel(logging.DEBUG)

#where do we store logging information
file_handler = RotatingFileHandler(os.path.join(logs_dir,'schd_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_sched.addHandler(file_handler)
logger_sched.addHandler(stream_handler)


sched_route = Blueprint('sched_route', __name__)

@sched_route.route('/are_we_running')
def our_we_running():
    return f"We're up and running today {datetime.today()}!"



@sched_route.route('/get_locations')
def get_locations():
    # print('*** wsh api accessed: get_Locations ***')
    logger_sched.info(f"--- wsh06 API get_locations endpoint")

    request_data = request.get_json()
    if request_data.get('password') == config.WSH_API_PASSWORD:
        # print('password accepted')

        locations = sess.query(Locations).all()
        locations_dict = {i.id: [i.lat, i.lon] for i in locations}

        #TODO: CHECK THIS Code ***
        #check weather_hist table for date and location id
        ## --> if exists remove from locations_dict
        loc_id_list = [loc_id for loc_id, _ in locations_dict.items()]

        for loc_id in loc_id_list:
            yesterday = datetime.today() - timedelta(days=1)
            yesterday_formatted =  yesterday.strftime('%Y-%m-%d')
            weather_history_records = sess.query(Weather_history).filter_by(
                date = yesterday_formatted,
                location_id = loc_id
            ).first()
            if weather_history_records:
                logger_sched.info(f"Deleting  {loc_id} ")
                del locations_dict[loc_id]
                logger_sched.info(f"Location deleted")

        
        logger_sched.info(f"Returning locations_dict")
        return locations_dict
    else:
        logger_sched.info(f"Error 401: could not verify")
        return make_response('Could not verify',
            401, 
            {'WWW-Authenticate' : 'Basic realm="Login required!"'})
        


@sched_route.route('/receive_weather_data')
def receive_weather_data():
    # print('*** receive_weather_data endpoint called *****')
    logger_sched.info(f"--- wsh06 API recieve_weather_data endpoint")
    request_data = request.get_json()
    if request_data.get('password') == config.WSH_API_PASSWORD:

        weather_response_dict = request_data.get('weather_response_dict')

        counter_all = 0

        #Add response to weather history table
        for loc_id, weather_response in weather_response_dict.items():

            forecast = weather_response.get('forecast').get('forecastday')[0]
            
            #check that weather does not already exist:
            row_exists = sess.query(Weather_history).filter_by(
                location_id= loc_id,
                date = forecast.get('date')).first()
            
            if not row_exists:
                weather_hist_temp = {}
                # Get location stuff
                weather_hist_temp['city_location_name'] = weather_response.get('location').get('name')
                weather_hist_temp['region_name'] = weather_response.get('location').get('region')
                weather_hist_temp['country_name'] = weather_response.get('location').get('country')
                weather_hist_temp['lat'] = weather_response.get('location').get('lat')
                weather_hist_temp['lon'] = weather_response.get('location').get('lon')
                weather_hist_temp['tz_id'] = weather_response.get('location').get('tz_id')
                weather_hist_temp['location_id'] = loc_id #needs location id*****
                
                #Get temperature stuff
                weather_hist_temp['date']= forecast.get('date')
                weather_hist_temp['maxtemp_f']= forecast.get('day').get('maxtemp_f')
                weather_hist_temp['mintemp_f']= forecast.get('day').get('mintemp_f')
                weather_hist_temp['avgtemp_f']= forecast.get('day').get('avgtemp_f')
                weather_hist_temp['sunset']= forecast.get('astro').get('sunset')
                weather_hist_temp['sunrise']= forecast.get('astro').get('sunrise')
                # weather_hist_list.append(weather_hist_temp)
                new = Weather_history(**weather_hist_temp)
                sess.add(new)
                sess.commit()
                counter_all += 1

        
        #Create another row in user_oura_weather_day
        if counter_all>0:
            add_user_loc_day()
            logger_sched.info(f"--- Succesfully added {counter_all} weather hist rows")
            return jsonify({'message': f'Successfully added {counter_all} weather hist rows'})
        else:
            logger_sched.info(f"-- No rows added because weather for the loc_ids / dates already existed")
            return jsonify({'message': f'No rows added because weather for the loc_ids / dates already existed'})
    else:
        logger_sched.info(f"Error 401: could not verify")
        return make_response('Could not verify',
                401, 
                {'WWW-Authenticate' : 'Basic realm="Login required!"'})


def add_user_loc_day():
    # print('adding data for dashboard')
    
    logger_sched.info(f"--- wsh06 API add_user_loc_day function: adding data for dashboard")

    #for each user
    users = sess.query(Users).all()
    yesterday = datetime.today() - timedelta(days=1)

    for user in users:
        new_loc_day_row_dict = {}
        new_loc_day_row_dict['user_id'] = user.id
        location_id = None
        if isinstance(user.lat, float):

            #search for nearset locatoin
            location_id = location_exists(user)
            new_loc_day_row_dict['location_id'] = location_id
            
            yesterday_weather_loc = sess.query(Weather_history).filter_by(
                date = yesterday.strftime('%Y-%m-%d'),
                location_id = location_id).first()
            # new_loc_day_row_dict['date'] =  yesterday.strftime('%m/%d/%Y')#yesterday's date from the weather hist table
            new_loc_day_row_dict['date'] =  yesterday.strftime('%Y-%m-%d')#yesterday's date from the weather hist table
            new_loc_day_row_dict['avgtemp_f'] = yesterday_weather_loc.avgtemp_f#yesterday's temperature form weather hist table
        
        yesterday_oura = sess.query(Oura_sleep_descriptions).filter_by(
            user_id = user.id,
            summary_date = yesterday.strftime('%Y-%m-%d')
        ).first()

        if yesterday_oura != None:
            new_loc_day_row_dict['score'] = yesterday_oura.score#sleep score from oura_table
        else:
            # print('This user does not have oura')
            logger_sched.info(f"--- This user does not have oura: {user}")
            # print(user)
        

        if isinstance(user.lat, float):
            #verify that row for this day does not already exists
            user_location_day_row_exists = sess.query(User_location_day).filter_by(
                date =yesterday.strftime('%m/%d/%Y'),
                user_id = user.id,
                location_id = location_id).first()

            if not user_location_day_row_exists:
                # print('*** No user_location_day_row_exists. It equals: ', user_location_day_row_exists)
                logger_sched.info(f"--- No user_location_day_row_exists. It equals:  {user_location_day_row_exists}")
                new_loc_day_row_dict['row_type'] = 'scheduler'

                new_loc_day = User_location_day(**new_loc_day_row_dict)
                sess.add(new_loc_day)
                sess.commit()
                logger_sched.info('---> Therefore, row added')
            else:
                logger_sched.info('Row turned down because it already exits in the table')
                logger_sched.info(user_location_day_row_exists)


    #1) get their user_id
    #2) locatoin_id
    #3) yesterday's date - convert to '2022-09-13'
    #4) yesterday's weather -string
    #5) score
    #) row_type = 'scheduler'

def location_exists(user):
    logger_sched.info('-- In location_exists function --')
    min_loc_distance_difference = 1000

    locations_unique_list = sess.query(Locations).all()
    for loc in locations_unique_list:
        lat_diff = abs(user.lat - loc.lat)
        lon_diff = abs(user.lon - loc.lon)
        loc_dist_diff = lat_diff + lon_diff
        logger_sched.info('** Differences **')
        logger_sched.info(f'lat_difference:{lat_diff}')
        logger_sched.info(f'lon_diff:{lon_diff}')

        if loc_dist_diff < min_loc_distance_difference:
            logger_sched.info('-----> loc_dist_diff is less than min required')
            min_loc_distance_difference = loc_dist_diff
            location_id = loc.id

    if min_loc_distance_difference > .1:
        location_id = 0
    
    # returns location_id = 0 if there is no location less than sum of .1 degrees
    return location_id




@sched_route.route('/oura_tokens')
def oura_tokens():
    # print('** api accessed ***')
    logger_sched.info(f'-- Accessed oura_token endpoint ---')
    #1) verify password
    request_data = request.get_json()
    if request_data.get('password') == config.WSH_API_PASSWORD:
        #2) get all users in db
        users = sess.query(Users).all()
        #3) search OUra_token table to get all user ora tokens
        oura_tokens_dict = {}
        
        for user in users:
            #4) put into a oura_tokens_dict = {user_id: [token_id, token]} <- user token is most current token assoc w/ user

            try:
                all_user_tokens = sess.query(Oura_token).filter_by(user_id = user.id).all()
                oura_token_list = [user.oura_token_id[0].id , all_user_tokens[-1].token]
                oura_tokens_dict[user.id] = oura_token_list

            except:
                all_user_tokens
                oura_tokens_dict[user.id] = ['User has no Oura token']
        logger_sched.info(f'-- Responded with a sucess ---')
        return jsonify({'message': 'success!', 'content': oura_tokens_dict})
    else:
        logger_sched.info(f'-- Responded with 401 could not verify ---')
        return make_response('Could not verify',
            401, 
            {'WWW-Authenticate' : 'Basic realm="Login required!"'})


@sched_route.route('/receive_oura_data')
def receive_oura_data():
    # print('*** receive_oura_data endpoint called *****')
    logger_sched.info(f'-- receive_oura_data endpoint called ---')
    request_data = request.get_json()
    if request_data.get('password') == config.WSH_API_PASSWORD:

        oura_response_dict = request_data.get('oura_response_dict')
        # print('oura_requesta')
        # print(oura_response_dict)
        counter_all = 0
        wsh_oura_add_response_dict = {}
        for user_id, oura_response in oura_response_dict.items():
            counter_user = 0
            if not oura_response.get('No Oura data reason'):
                
                #1) get all sleep enpoints for user
                user_sleep_sessions = sess.query(Oura_sleep_descriptions).filter_by(user_id = user_id).all()
                user_sleep_end_list = [i.bedtime_end for i in user_sleep_sessions]

                #2) check endsleep time if matches with existing skip
                for session in oura_response.get('sleep'):
                    # temp_bedtime_end = oura_response.get('sleep')[0].get('bedtime_end')
                    temp_bedtime_end = session.get('bedtime_end')
                    if temp_bedtime_end not in user_sleep_end_list:# append data to oura_sleep_descriptions
 
                        logger_sched.info(f'Attempting to add added session : {temp_bedtime_end} for user id: {user_id}')
                        #3a) remove any elements of oura_response.get('sleep')[0] not in Oura_sleep_descriptions.__table__
                        for element in list(session.keys()):
                            if element not in Oura_sleep_descriptions.__table__.columns.keys():
                                del session[element]

                        #3b) add wsh_oura_otken_id to dict
                        session['token_id'] = oura_response.get('wsh_oura_token_id')
                        session['user_id'] = user_id

                        #3c) new oura_sleep_descript objec, then add, then commit
                        flag_add_to_oura_sleep_descript = False
                        try:
                            new_oura_session = Oura_sleep_descriptions(**session)
                            sess.add(new_oura_session)
                            sess.commit()
                            wsh_oura_add_response_dict[user_id] = 'Added Successfully'
                            counter_all += 1
                            counter_user += 1
                            logger_sched.info(f'---> Successfully added session : {temp_bedtime_end} for user id: {user_id}')
                            flag_add_to_oura_sleep_descript = True
                            add_user_loc_day_oura(user_id, temp_bedtime_end)
                            
                        except:
                            wsh_oura_add_response_dict[user_id] = 'Failed to add data'
                            if not flag_add_to_oura_sleep_descript:
                                logger_sched.info(f'---> * FAILED * to added session : {temp_bedtime_end} for user id: {user_id}')
                            else:
                                logger_sched.info(f'---> * FAILED (only User_loc_day) * to added session : {temp_bedtime_end} for user id: {user_id}')
  
            else:
                wsh_oura_add_response_dict[user_id] = f'No data added due to {oura_response.get("No Oura data reason")}'
        if counter_user == 0:
            wsh_oura_add_response_dict[user_id] = 'No new sleep sessions availible'
            
        
        logger_sched.info(f"added {counter_all} rows to Oura_sleep_descriptions")
        logger_sched.info(f"****** Successfully finished routine!!! *****")
        return wsh_oura_add_response_dict
    logger_sched.info(f"Error 401: could not verify")
    return make_response('Could not verify',
            401, 
            {'WWW-Authenticate' : 'Basic realm="Login required!"'})

def add_user_loc_day_oura(user_id, bedtime_end):
    logger_sched.info(f' In add_user_loc_day_oura')
    oura_session = sess.query(Oura_sleep_descriptions).filter_by(
        user_id = user_id, bedtime_end = bedtime_end
    ).all()[-1]

    user_loc_day_oura_add = sess.query(User_location_day).filter_by(user_id = user_id,
        date = oura_session.summary_date).all()[-1]

    user_loc_day_oura_add.score = oura_session.score
    sess.commit()
    logger_sched.info(f'---> Successfully added oura score to User_loc_day for {oura_session.summary_date} for user id: {user_id}')
