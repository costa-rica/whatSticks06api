from flask import Flask
from wsh_config import ConfigDev, ConfigProd
# from wsh_models import login_manager
# from flask_mail import Mail

config_object = ConfigDev()
# mail = Mail()
def create_app():
    app = Flask(__name__)
    app.config.from_object(config_object)

    # login_manager.init_app(app)
    # mail.init_app(app)

    from app_package.scheduler.routes import sched_route
    # from app_package.dashboard.routes import dash
    
    app.register_blueprint(sched_route)
    # app.register_blueprint(dash)
    
    return app      
