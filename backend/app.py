
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix


from routes_auth   import auth_bp
from routes_api    import api_bp
from routes_crawl  import crawl_bp
from ai_assistant  import ai_bp
from models        import db, User




def create_app(with_scheduler: bool = False) -> Flask:
    load_dotenv()                                        


    app = Flask(
        __name__,
        static_folder="../frontend/build",
        static_url_path="/static",
    )


    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # fix proxy




    @app.errorhandler(Exception)  # catches global errors
    def handle_any_error(err):
        tb  = traceback.format_exc()
        app.logger.error(tb)
        return jsonify(error=str(err), trace=tb), 500
    # cookie settings
    is_prod = os.getenv("FLASK_ENV") == "production"
    app.config.update(
        SESSION_COOKIE_SECURE   =is_prod,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE = "None",   # allow request across sites
    )


    # database
    tmp_db = os.path.join("/tmp", "crawlernaut.db")
    app.config.update(
        SQLALCHEMY_DATABASE_URI        = os.getenv("DATABASE_URL", f"sqlite:///{tmp_db}"),
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
        SECRET_KEY                     = os.getenv("SECRET_KEY", "change_this_to_actual_one"),
    )


    # CORS setup
    raw_origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    print("▶︎ CORS origins:", origins)
    CORS(app,
        supports_credentials=True,
        resources={r"/api/*": {
            "origins": origins,
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        }},
    )


    # initialise database
    db.init_app(app)
    with app.app_context():
        db.create_all()
        if with_scheduler:
            from tasks import init_scheduler
            init_scheduler(app)


    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id)) # fetches user id from database


    # blueprints: prefixes routes with api, except api_bp
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(api_bp)            
    app.register_blueprint(crawl_bp, url_prefix="/api")
    app.register_blueprint(ai_bp,  url_prefix="/api/ai")


    # serves single page application
    @app.route("/")
    def index():
        return app.send_static_file("index.html")


    # 404 error handling
    @app.errorhandler(404)
    def handle_404(err):
        if request.path.startswith(("/api", "/static")):
            return  jsonify(error="Not found"), 404
        return app.send_static_file("index.html")


    return app




if __name__ == "__main__":  
    srv = create_app(with_scheduler=True)  
    srv.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5051)),
        debug=False,
        use_reloader=False,
    )


