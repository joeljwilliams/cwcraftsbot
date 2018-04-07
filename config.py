#!/usr/bin/env python3
import os

TOKEN = os.getenv('BOT_TOKEN')
APP_ENV = os.getenv('APP_ENV')

DB_USER = os.getenv('DATABASE_USER')
DB_PASS = os.getenv('DATABASE_PASSWORD')
DB_HOST = os.getenv('DATABASE_HOSTNAME')
DB_NAME = os.getenv('DATABASE_NAME')

if APP_ENV == 'PROD':
    LOGLEVEL = 'INFO'
else:
    LOGLEVEL = 'DEBUG'
