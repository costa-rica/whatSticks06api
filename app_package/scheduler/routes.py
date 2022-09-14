from flask import Blueprint
from flask import Flask, request, jsonify, make_response, current_app
from app_package.config import ConfigDev
from wsh_models import sess, Users, Oura_token, Oura_sleep_descriptions

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
        counter = 0
        wsh_oura_add_response_dict = {}
        for user_id, oura_response in oura_response_dict.items():
            if not oura_response.get('No Oura data reason'):
                
                #1) get all sleep enpoints for user
                user_sleep_sessions = sess.query(Oura_sleep_descriptions).filter_by(user_id = user_id).all()
                user_sleep_end_list = [i.bedtime_end for i in user_sleep_sessions]


                #2) check endsleep time if matches with existing skip
                # print('oura_response is type: ', type(oura_response))
                # print('oura_response.get(sleep)[0] is type: ', type(oura_response.get('sleep')[0]))
                # print('oura_response.get(sleep)[0].get(summary_date) is type: ', type(oura_response.get('sleep')[0].get('summary_date')))
                # temp_bedtime_end = oura_response.get('sleep')[0].get('summary_date').get('bedtime_end')
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
                            counter += 1
                        except:
                            wsh_oura_add_response_dict[user_id] = 'Failed to add data'
                    else:
                        wsh_oura_add_response_dict[user_id] = 'No new sleep sessions availible'
            else:
                wsh_oura_add_response_dict[user_id] = f'No data added due to {oura_response.get("No Oura data reason")}'
            
            print(f'added {counter} rows to Oura_sleep_descriptions')
            return wsh_oura_add_response_dict

    return make_response('Could not verify',
            401, 
            {'WWW-Authenticate' : 'Basic realm="Login required!"'})