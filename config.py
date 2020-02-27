import os


class Config:
	SECRET_KEY = os.getenv('SECRET_KEY', 'hard_to_guess_string')
	SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
	DEBUG = True
	# SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
 #            					os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data.sqlite')
	SQLALCHEMY_DATABASE_URI = os.getenv('DEV_DATABASE_URL', \
										'postgresql://postgres:aMhKuJqhbzLrRe93ypCB@localhost/ozon-parser')


class ProductionConfig(Config):
	SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')


config = {'dev': DevelopmentConfig, 'prod': ProductionConfig}
