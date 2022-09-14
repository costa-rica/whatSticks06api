from flask import Blueprint
from flask import Flask, request, jsonify, make_response, current_app
from app_package.config import ConfigDev
from wsh_models import sess, Users, Oura_token, Oura_sleep_descriptions,\
    Locations, Weather_history, User_location_day
from datetime import datetime, timedelta

config = ConfigDev()

sched_route = Blueprint('sched_route', __name__)

@sched_route.route('/oura_tokens')
def oura_tokens():
    print('** api accessed ***')
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
        return jsonify({'message': 'success!', 'content': oura_tokens_dict})
    else:
        return make_response('Could not verify',
            401, 
            {'WWW-Authenticate' : 'Basic realm="Login required!"'})


@sched_route.route('/receive_oura_data')
def receive_oura_data():
    print('*** receive_oura_data endpoint called *****')
    request_data = request.get_json()
    if request_data.get('password') == config.WSH_API_PASSWORD:

        oura_response_dict = request_data.get('oura_response_dict')
        print('oura_requesta')
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
                        print('This is one session that is not in here: ', temp_bedtime_end)
                        #3a) remove any elements of oura_response.get('sleep')[0] not in Oura_sleep_descriptions.__table__
                        for element in list(session.keys()):
                            if element not in Oura_sleep_descriptions.__table__.columns.keys():
                                del session[element]

                        #3b) add wsh_oura_otken_id to dict
                        session['token_id'] = oura_response.get('wsh_oura_token_id')
                        session['user_id'] = user_id
                        print('Added token id: ', session['token_id'])

                        #3c) new oura_sleep_descript objec, then add, then commit
                        try:
                            print('ouraresponse.sleep[0] is:', session)
                            print('type:' , type(session))
                            new_oura_session = Oura_sleep_descriptions(**session)
                            sess.add(new_oura_session)
                            sess.commit()
                            wsh_oura_add_response_dict[user_id] = 'Added Successfully'
                            counter_all += 1
                            counter_user += 1
                        except:
                            wsh_oura_add_response_dict[user_id] = 'Failed to add data'
                    # else:
                    #     wsh_oura_add_response_dict[user_id] = 'No new sleep sessions availible'
            else:
                wsh_oura_add_response_dict[user_id] = f'No data added due to {oura_response.get("No Oura data reason")}'
        if counter_user == 0:
            wsh_oura_add_response_dict[user_id] = 'No new sleep sessions availible'
            
        print(f'added {counter_all} rows to Oura_sleep_descriptions')
        return wsh_oura_add_response_dict

    return make_response('Could not verify',
            401, 
            {'WWW-Authenticate' : 'Basic realm="Login required!"'})


@sched_route.route('/get_locations')
def get_locations():
    print('*** wsh api accessed: get_Locations ***')

    request_data = request.get_json()
    if request_data.get('password') == config.WSH_API_PASSWORD:
        print('password accepted')

        locations = sess.query(Locations).all()
        locations_dict = {i.id: [i.lat, i.lon] for i in locations}

        return locations_dict
    else:
        return make_response('Could not verify',
            401, 
            {'WWW-Authenticate' : 'Basic realm="Login required!"'})
        


@sched_route.route('/receive_weather_data')
def receive_weather_data():
    print('*** receive_weather_data endpoint called *****')
    request_data = request.get_json()
    if request_data.get('password') == config.WSH_API_PASSWORD:

        weather_response_dict = request_data.get('weather_response_dict')
        # print(weather_response_dict)

        counter_all = 0
        # wsh_oura_add_response_dict = {}
        # print('Finished weather data collection! YAY!!!!!!!!')

        #Add response to weather history table
        for loc_id, weather_response in weather_response_dict.items():

            forecast = weather_response.get('forecast').get('forecastday')[0]
            
            # weather_hist_list=[]
            # for forecast in hist_forecast_list:
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
        add_user_loc_day()

        return jsonify({'message': f'Successfully added {counter_all} weather hist rows'})
    else:
        return make_response('Could not verify',
                401, 
                {'WWW-Authenticate' : 'Basic realm="Login required!"'})


def add_user_loc_day():
    print('adding data for dashboard')

    #for each user
    users = sess.query(Users).all()
    yesterday = datetime.today() - timedelta(days=1)

    for user in users:
        new_loc_day_row_dict = {}
        new_loc_day_row_dict['user_id'] = user.id
        location_id = None
        if isinstance(user.lat, float):
        #     print('skipped user: ', user.email)
        # else:
            # pass
            #search for nearset locatoin
            location_id = location_exists(user)
            new_loc_day_row_dict['location_id'] = location_id
            
            yesterday_weather_loc = sess.query(Weather_history).filter_by(
                date = yesterday.strftime('%Y-%m-%d'),
                location_id = location_id).first()
            new_loc_day_row_dict['date'] =  yesterday.strftime('%m/%d/%Y')#yesterday's date from the weather hist table
            new_loc_day_row_dict['avgtemp_f'] = yesterday_weather_loc.avgtemp_f#yesterday's temperature form weather hist table
        
        yesterday_oura = sess.query(Oura_sleep_descriptions).filter_by(
            user_id = user.id,
            summary_date = yesterday.strftime('%Y-%m-%d')
        ).first()

        if yesterday_oura != None:
            new_loc_day_row_dict['score'] = yesterday_oura.score#sleep score from oura_table
        else:
            print('This user does not have oura')
            print(user)
        
        # print('locatoin_id: ', location_id)
        if isinstance(user.lat, float):

            #TODO: check that row doesn't already exist

            new_loc_day_row_dict['row_type'] = 'scheduler'

            new_loc_day = User_location_day(**new_loc_day_row_dict)
            sess.add(new_loc_day)
            sess.commit()


    #1) get their user_id
    #2) locatoin_id
    #3) yesterday's date - convert to '2022-09-13'
    #4) yesterday's weather -string
    #5) score
    #) row_type = 'scheduler'

def location_exists(user):
    
    min_loc_distance_difference = 1000

    locations_unique_list = sess.query(Locations).all()
    for loc in locations_unique_list:
        lat_diff = abs(user.lat - loc.lat)
        lon_diff = abs(user.lon - loc.lon)
        loc_dist_diff = lat_diff + lon_diff
        print('** Differences **')
        print('lat_difference:', lat_diff)
        print('lon_diff:', lon_diff)

        if loc_dist_diff < min_loc_distance_difference:
            print('-----> loc_dist_diff is less than min required')
            min_loc_distance_difference = loc_dist_diff
            location_id = loc.id

    if min_loc_distance_difference > .1:
        location_id = 0
    
    # returns location_id = 0 if there is no location less than sum of .1 degrees
    return location_id
